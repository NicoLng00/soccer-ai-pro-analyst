# Architettura

Documento di riferimento tecnico. Il documento di progetto su claude.ai spiega il *perché*; qui c'è il *come*, al livello che serve per scrivere codice.

## Obiettivo

Per ogni partita il sistema produce una sola uscita: le probabilità di 1X2, Goal/NoGoal e Over/Under 2.5, la quota equa e l'edge rispetto al mercato. Tutto poggia su un dataset nostro, costruito e validato dalla nostra pipeline.

## Principi non negoziabili

Il codice che ne viola uno non entra in `main`.

1. **Point-in-time.** Ogni fatto ha un tempo di validità (`valid_at` o `valid_period`) e un periodo di conoscenza (`known_period`). Il limite inferiore di `known_period` è l'istante in cui il fatto è diventato conoscibile nel mondo. Una previsione all'istante T legge solo righe con `known_period @> T`.
2. **Append-only nel contenuto.** Nessuna riga di `ref`, `obs`, `mkt` o `ml.prediction` si cancella o cambia valore. L'unica modifica ammessa è chiudere il `known_period` di una riga quando arriva la versione successiva o una ritrattazione, registrando il motivo in `ops.correction_log`.
3. **Provenienza dichiarata.** Ogni riga porta `source_id`, `mode` (`live` o `backfill`), `knowledge_basis` e il riferimento all'origine (payload grezzo o esecuzione di derivazione). Due ruoli Postgres separati: `sap_live` scrive solo righe `live`, `sap_backfill` solo righe `backfill` (Row Level Security).
4. **Niente null nel core.** Tutte le colonne di `ref`, `obs`, `mkt` e `ml` sono `NOT NULL`. Ciò che può mancare è un'osservazione: se non lo sappiamo, la riga non esiste. I periodi aperti usano range con estremo superiore aperto.
5. **Deterministico dentro, probabilistico in uscita.** Stessi dati e stessa versione del codice danno le stesse feature e la stessa previsione. Seed fissi, versioni registrate, nessuna chiamata a LLM nel percorso che produce una previsione.
6. **Ogni fonte giustificata e isolata.** Una fonte entra solo se alimenta almeno una variabile del registro. Ogni fonte è un adapter con un contratto Pydantic che fallisce in modo esplicito.
7. **Valutazione sulla calibrazione.** Il sistema si giudica su centinaia di partite: log-loss, Brier, RPS, curve di calibrazione, confronto con la quota di chiusura. Nessuna variabile si aggiunge per spiegare una singola partita.

## Livelli del dato

```
fonte ──> adapter (contratto) ──> raw (R2 + ops.raw_ingest)
      ──> parse ──> clean (ref.*, ops.entity_map)
      ──> osservazioni (obs.*, mkt.*)
      ──> feature (obs.as_of(T) ──> ml.feature_snapshot)
      ──> previsione (ml.prediction) ──> valutazione (ml.evaluation)
```

- **raw**: il payload originale, compresso, su Cloudflare R2, indicizzato da `ops.raw_ingest` con SHA-256. Immutabile. Ogni download è un evento in `ops.fetch_log`, anche quando il contenuto è identico a uno già salvato.
- **clean**: entità canoniche in `ref`. La mappatura dalle chiavi delle fonti vive in `ops.entity_map`, con metodo e confidenza.
- **osservazioni**: tutto ciò che può mancare o cambiare, tipizzato dal registro `obs.variable`.
- **feature**: la matrice larga si costruisce solo al momento dell'addestramento o della previsione, "alla data T", e si salva come snapshot.
- **previsione e valutazione**: ogni previsione ha versione del modello e snapshot delle feature, e si salva prima del calcio d'inizio.

Dettaglio a livello di colonna: `docs/data-model.md`.

## Livelli di analisi

- **Macro**: competizione, club, allenatore, rosa, mercato. Cambia in settimane o stagioni.
- **Partita**: il contesto di quella squadra in quella partita (`ref.match_team`). Riposo, viaggio, slot, arbitro, meteo, quote.
- **Micro**: il singolo giocatore. Carico, disponibilità, rendimento.

## Componenti

| Componente | Tecnologia | Ruolo |
|---|---|---|
| Linguaggio | Python 3.12, uv | Tutto il codice |
| Database | PostgreSQL 18 con `btree_gist` | Unica fonte di verità strutturata |
| Accesso al DB | SQLAlchemy 2.x (Core per le query pesanti), Alembic, psycopg 3 | Schema versionato, query esplicite |
| Contratti | Pydantic v2 | Validazione di ogni payload in ingresso e di ogni output di un agente LLM |
| Qualità | Controlli come asset check di Dagster, risultati in `ops.quality_check_result` | I controlli di `docs/data-quality.md` |
| Orchestrazione | Dagster OSS (webserver + daemon) sulla VM | Asset, partizioni per stagione, backfill, sensori per i job legati al calcio d'inizio |
| Object storage | Cloudflare R2 (API S3) | Payload grezzi e backup |
| Analisi | Polars e DuckDB | Esplorazione e costruzione delle matrici |
| Modelli | SciPy (Dixon-Coles), LightGBM, scikit-learn per la calibrazione | Fase 4 e 5 |
| Tracciamento esperimenti | MLflow con backend Postgres | Fase 4 e 5 |
| Agenti LLM runtime | Pydantic AI, provider Gemini Flash-Lite sul piano gratuito | Solo ai margini: notizie e report. Vedi `docs/agents.md` |
| CLI | Typer | `sap ...` per operazioni manuali, compresa la gestione delle utenze (`sap admin`) |
| API | FastAPI | Area amministrativa, quasi solo lettura (fase 6, ADR 0008) |
| Frontend | Vite, React 19, TypeScript, Tailwind v4, framer-motion | Pagina d'ingresso e area `/app` (`docs/frontend/`) |
| Accesso da internet | Cloudflare Tunnel e Cloudflare Access | Nessuna porta aperta sulla VM; solo le email dei due admin raggiungono `/app` e l'API |
| Log | structlog in JSON | Un evento per riga, con `job_run_id` |

## Orchestrazione

Dagster modella la pipeline come asset con lineage esplicito, il che corrisponde ai nostri livelli.

- **Asset partizionati** per `competizione-stagione` (es. `ITA-SA/2024-25`): il backfill è un backfill di partizioni, riprendibile.
- **Asset check** implementano i controlli di qualità: un check fallito blocca gli asset a valle.
- **Sensori** leggono ogni minuto `ops.expected_slot` e lanciano i job legati al calcio d'inizio (quote a T-24h e T-1h, formazioni a T-60 e T-30 minuti). Quando un orario cambia, gli slot si ripianificano.
- **Schedule** per i job notturni e settimanali.
- Ogni esecuzione scrive anche in `ops.job_run`, indipendente da Dagster: se domani cambiamo orchestratore, la storia resta.

Dagster è una proposta da confermare nella fase 0 misurando la memoria sulla VM (ADR 0004). L'alternativa leggera è APScheduler con la stessa tabella `ops.expected_slot`.

## Agenti

Due livelli, descritti in `docs/agents.md`:

- **Sviluppo**: Claude Code con subagent specializzati, skill per le procedure ripetute, hook che fanno rispettare i principi, server MCP in sola lettura sul database.
- **Runtime**: agenti LLM che lavorano ai margini del sistema. Estraggono fatti dalle notizie e scrivono il report di ogni giornata con le ipotesi sugli errori. Non producono mai direttamente una previsione né attivano una variabile.

## Deploy

- **Sviluppo**: Postgres in Docker Compose, R2 simulato con SeaweedFS (S3 compatibile; MinIO community non è più mantenuto), `.env` locale.
- **Produzione**: VM Arm su Oracle Cloud Always Free (2 OCPU, 12 GB). Docker Compose con Postgres, Dagster webserver e daemon, codice dell'applicazione. Backup notturno di Postgres su R2. Installazione riproducibile da `scripts/provision-vm.sh`.
- **Frontend**: Cloudflare Workers con static assets. L'API gira sulla VM ed è raggiungibile solo tramite Cloudflare Tunnel, con Cloudflare Access davanti.
- **CI**: GitHub Actions per lint, type check, test, migrazioni da zero su un Postgres effimero. Un workflow orario controlla `ops.job_run` e segnala gli slot saltati.

## Sicurezza

- Segreti solo in variabili d'ambiente; `.env` mai nel repository, mai letto da Claude Code (regola `deny`).
- Ruoli Postgres oltre al proprietario: `sap_live`, `sap_backfill`, `sap_readonly` (usato dal server MCP), `sap_api` (API), `sap_useradmin` (solo comandi `sap admin`).
- Area amministrativa: accesso a due livelli (Cloudflare Access e autenticazione con TOTP), test di sicurezza continui per ogni endpoint, pentest prima della messa online. Dettagli in `docs/security.md`.
- I dati di terze parti non entrano mai nel repository pubblico.
