# Roadmap v1

Sei fasi. Le fasi 2 e 3 corrono in parallelo: la cattura live parte appena le fonti sono testate, perché il dato point-in-time di una settimana non catturata non si ricostruisce più. Una fase si chiude solo quando ogni criterio è verificato con un comando riproducibile, riportato nel PR di chiusura.

Stato corrente: aggiornare la riga `Fase corrente` quando si chiude una fase (la legge l'hook di inizio sessione).

Fase corrente: 0

## Fase 0 — Fondamenta

Prompt: `docs/prompts/fase-0.md`

- Tooling: uv, ruff, mypy strict, pytest, pre-commit, CI.
- Docker Compose di sviluppo: Postgres 18, SeaweedFS al posto di R2.
- Schema v1 completo da `docs/data-model.md` in migrazioni Alembic, con ruoli, RLS, vincoli di esclusione, trigger.
- Funzioni `obs.as_of_*` e relativi test.
- `sap registry sync`: carica `registry/sources.yaml` e `registry/variables.yaml`.
- Raw store: scrittura su R2 o SeaweedFS, `ops.raw_ingest`, `ops.fetch_log`.
- `ops.job_run` con decoratore per i job.
- Dagster minimo: una definizione, un asset di prova, un check. Misura della memoria.
- Sicurezza della catena dal primo giorno: gitleaks in pre-commit e in CI, audit delle dipendenze Python, Dependabot.

Criteri di completamento:

- [ ] `uv run alembic upgrade head` su un database vuoto in CI, e `downgrade base` pulito.
- [ ] Test point-in-time verdi: una riga conoscibile dopo T non compare in `as_of(T)`; una correzione compare solo prima della chiusura.
- [ ] Il ruolo `sap_live` non riesce a inserire una riga `backfill` (test).
- [ ] Nessuna colonna nullable in `ref`, `obs`, `mkt`, `ml` (test che interroga `information_schema`).
- [ ] Backup e ripristino di Postgres provati end-to-end.
- [ ] Memoria di Dagster misurata e annotata nell'ADR 0004.

## Fase 1 — Test delle fonti

Prompt: `docs/prompts/fase-1.md`

- Una sonda per ogni fonte live (`scripts/probe/<fonte>.py`) con chiavi reali: copertura, limiti, latenza, formato.
- Prova di raggiungibilità di Understat e dei feed RSS dalla VM.
- Contratti Pydantic per ogni fonte, da payload reali salvati come fixture.
- Rapporto di copertura in `reports/sources/coverage.md`: per ogni variabile del registro, fonte scelta o motivo dello scarto.

Criteri di completamento:

- [ ] Ogni variabile con `feasibility: to_test` ha una decisione.
- [ ] Ogni contratto ha almeno una fixture reale e un test che la valida.
- [ ] Budget mensile di chiamate calcolato per ogni API e sotto il limite gratuito.
- [ ] Nessuna voce `verified: false` in `curation/`, salvo le rivalità in attesa di Nico.

## Fase 2 — Backfill

Prompt: `docs/prompts/fase-2.md`

- Adapter storici nell'ordine: football_data (risultati e quote), openfootball (seconda fonte), understat, transfermarkt_ds, open_meteo, wikidata e curatela.
- Riconciliazione delle entità con coda di revisione.
- Asset partizionati per competizione e stagione; controlli di `docs/data-quality.md`.

Criteri di completamento:

- [ ] Top 5 campionati dal 2014/15, Serie A dal 2005/06, tutte le partizioni verdi o con eccezione documentata.
- [ ] Coda di revisione delle entità vuota.
- [ ] Report di qualità del backfill in `reports/quality/backfill-v1.md`.

## Fase 3 — Cattura live

Prompt: `docs/prompts/fase-3.md`

- Calendario e `ops.expected_slot`; sensori Dagster per i job legati al calcio d'inizio.
- Quote a T-24h, T-1h e chiusura; formazioni a T-60 e T-30 minuti; meteo; titoli RSS.
- Controllo orario degli slot saltati e notifica.
- Agente `quality-triage`.

Criteri di completamento:

- [ ] 4 giornate di Serie A consecutive senza slot saltati.
- [ ] Ritardo medio tra orario previsto e partenza reale misurato e riportato.

## Fase 4 — Variabili derivate e baseline

Prompt: `docs/prompts/fase-4.md`

- Derivazioni: Elo, forma, riposo, km, squalifiche, classifica, carico dei giocatori.
- Baseline Dixon-Coles con pesatura temporale.
- Valutazione walk-forward: log-loss, Brier, RPS, calibrazione, CLV contro la chiusura.

Criteri di completamento:

- [ ] Baseline calibrata su almeno due stagioni mai viste in addestramento.
- [ ] Report di valutazione riproducibile da un comando.

## Fase 5 — Modello completo e ciclo di apprendimento

Prompt: `docs/prompts/fase-5.md`

- Sotto-modelli (allenatore, forza, rischio infortunio) e modello finale.
- Agenti `news-extractor`, `press-sentiment`, `matchday-reviewer` con golden set.
- Previsioni a T-24h e T-1h salvate prima del fischio.
- Report settimanale di calibrazione e CLV.

Criteri di completamento:

- [ ] Ogni variabile attiva ha un report di valutazione che ne giustifica l'attivazione.
- [ ] Agente `news-extractor` con precisione ≥ 0,90 sul golden set.
- [ ] 4 settimane di previsioni live salvate senza eccezioni al trigger temporale.

## Fase 6 — API e area amministrativa

Prompt: `docs/prompts/fase-6.md`. Riferimenti: ADR 0008, `docs/frontend/`, `docs/security.md`.

- API FastAPI quasi solo in lettura, ruolo `sap_api`, schema `app` per utenti, sessioni, tentativi di accesso e audit.
- Accesso per due utenti amministratori: argon2id, TOTP obbligatorio, sessioni lato server; utenze create da terminale con `sap admin create` (i nomi li fornisce Nico, le password le digita ciascun admin).
- Frontend in `frontend/` dal riferimento `docs/frontend/riferimento-design.md`, con gli adattamenti di `docs/frontend/README.md` e video e immagini di contesto calcistico.
- Test di sicurezza continui in CI per ogni endpoint: autorizzazione, fuzzing dallo schema OpenAPI, analisi statica, segreti, dipendenze, scansione dinamica con ZAP, percorsi completi con Playwright.
- Staging su Cloudflare: Workers per il frontend, Tunnel e Access per l'area `/app` e l'API.

Criteri di completamento:

- [ ] Ogni endpoint ha i test di autorizzazione (401) e di validazione (422); il test che enumera le route passa e la lista pubblica è `health`, `login`, `mfa`.
- [ ] Schemathesis senza errori 5xx e senza risposte fuori schema.
- [ ] ZAP baseline e API scan senza avvisi alti.
- [ ] Playwright: accesso con TOTP, logout, scadenza della sessione, accesso negato.
- [ ] I due admin entrano in staging con credenziali create da loro da terminale.

## Fase 7 — Pentest e messa online

Prompt: `docs/prompts/fase-7.md`

- Pentest manuale sullo staging secondo `docs/security.md` (WSTG, API Security Top 10, ASVS 5.0 livello 2), con la skill `/pentest`; report conservato fuori dal repository.
- Correzioni e ritest.
- Hardening della VM: SSH solo con chiave, nessuna porta in ingresso, aggiornamenti automatici, Docker senza socket esposto.
- Messa online e sorveglianza: avvisi su accessi falliti ripetuti, errori 5xx, slot saltati.

Criteri di completamento:

- [ ] Nessuna vulnerabilità critica o alta aperta; le medie hanno un piano e una data.
- [ ] Scansione delle porte dall'esterno: nessun servizio raggiungibile oltre a Cloudflare.
- [ ] Ripristino da backup provato dopo l'hardening.
- [ ] Data del prossimo pentest fissata.
