# Infrastruttura agentica

Due livelli con regole diverse. Nello sviluppo gli agenti scrivono codice sotto controllo di test, hook e revisori. A runtime gli agenti LLM lavorano solo ai margini e non toccano mai il percorso deterministico che produce una previsione.

## 1. Sviluppo con Claude Code

### Flusso di lavoro

1. Ogni fase parte con `/avvia-fase N`: Claude legge `docs/prompts/fase-N.md`, entra in plan mode e propone il piano.
2. Nico approva il piano. Si lavora su un branch per blocco di lavoro.
3. Claude implementa. Gli hook formattano e controllano a ogni modifica.
4. Prima di chiudere un blocco, i revisori pertinenti (sotto) esaminano il diff. I problemi bloccanti si correggono prima del commit.
5. Il blocco si chiude quando il criterio di completamento in `docs/roadmap.md` è verificato con un comando riproducibile.

### Subagent (`.claude/agents/`)

| Agente | Modello | Quando | Cosa fa |
|---|---|---|---|
| `schema-guardian` | opus | Dopo ogni modifica a `migrations/` o `src/soccer_analyst/db/` | Confronta con `docs/data-model.md` e i principi: niente null, `known_period`, RLS, vincoli di esclusione, reversibilità della migrazione. Solo lettura |
| `leakage-auditor` | opus | Dopo ogni modifica a feature, modelli, regole di conoscibilità, adapter | Cerca ogni modo in cui un'informazione futura può entrare in una feature o in un addestramento. Esegue i test point-in-time |
| `source-adapter-engineer` | sonnet | Per costruire o riparare un adapter | Segue la skill `nuova-fonte`: contratto, parser, mapping, test con fixture reali, controlli di qualità |
| `data-quality-analyst` | sonnet | Dopo un backfill o quando un controllo fallisce | Interroga il database in sola lettura via MCP, indaga le anomalie, scrive un report in `reports/quality/` |
| `ml-evaluator` | opus | Prima di attivare una variabile o un modello | Verifica validazione temporale, confronto con la quota di chiusura, significatività; boccia i miglioramenti dentro il rumore |
| `security-reviewer` | opus | Dopo modifiche ad API, frontend, `sap admin`, header, CORS, CI o deploy, e prima di ogni deploy | Cerca falle di autenticazione, autorizzazione, input, sessioni, segreti e configurazione secondo `docs/security.md` (ASVS 5.0 livello 2, API Top 10). Solo lettura |
| `security-reviewer` | opus | Dopo modifiche ad API, frontend, `sap admin`, header, CORS, CI o deploy, e prima di ogni deploy | Cerca falle di autenticazione, autorizzazione, input, sessioni, segreti e configurazione secondo `docs/security.md` (ASVS 5.0 livello 2, API Top 10). Solo lettura |

### Skill (`.claude/skills/`)

| Skill | Invocazione | Scopo |
|---|---|---|
| `avvia-fase` | solo `/avvia-fase N` | Carica il prompt della fase e parte in plan mode |
| `nuova-fonte` | automatica o `/nuova-fonte codice` | Procedura completa per un adapter |
| `nuova-variabile` | automatica o `/nuova-variabile codice` | Registro, derivazione, test point-in-time, documentazione |
| `nuova-migrazione` | automatica | Regole per le migrazioni Alembic |
| `backfill-stagione` | solo `/backfill-stagione competizione stagione` | Backfill di una partizione con controlli e report |
| `verifica-pit` | automatica | Checklist point-in-time, caricata anche dal `leakage-auditor` |
| `nuovo-endpoint` | automatica o `/nuovo-endpoint GET /api/...` | Endpoint con autorizzazione, limiti, test 401 e 422, fuzzing, revisione di sicurezza |
| `pentest` | solo `/pentest prepara`, `testa`, `report`, `ritest` | Campagna di pentest sullo staging condotta da Nico, report fuori dal repository |
| `nuovo-endpoint` | automatica o `/nuovo-endpoint GET /api/...` | Endpoint con autorizzazione, limiti, test 401 e 422, fuzzing, revisione di sicurezza |
| `pentest` | solo `/pentest prepara|testa|report|ritest` | Campagna di pentest sullo staging condotta da Nico, report fuori dal repository |

### Hook (`.claude/settings.json`)

| Evento | Script | Effetto |
|---|---|---|
| `SessionStart` | `session-context.py` | Inietta fase corrente, branch, ultima migrazione, controlli falliti recenti |
| `PreToolUse` su `Edit`/`Write` | `guard-files.py` | Blocca modifiche a `.env*`, a `data/` e alle migrazioni già committate |
| `PreToolUse` su `Bash` | `guard-bash.py` | Blocca `DROP`, `TRUNCATE`, `DELETE` su schemi di fatti, `git push --force`, `rm -rf` fuori da `tmp/` |
| `PostToolUse` su `Edit`/`Write` | `format-python.py` | `ruff format` e `ruff check --fix` sul file; gli errori residui tornano a Claude |
| `Stop` | `quick-check.py` | Lint, type check e test unitari veloci; se falliscono Claude continua a correggere |

Oltre agli hook, i permessi di `.claude/settings.json` chiedono conferma a Nico prima di ogni strumento di scansione o attacco (nmap, ffuf, nuclei, sqlmap, ZAP, testssl.sh) e prima di installare pacchetti npm.

Oltre agli hook, i permessi di `.claude/settings.json` chiedono conferma a Nico prima di ogni strumento di scansione o attacco (nmap, ffuf, nuclei, sqlmap, ZAP, testssl.sh) e prima di installare pacchetti npm.

### MCP (`.mcp.json`)

- `postgres-ro`: Postgres MCP Pro in modalità `restricted` con il ruolo `sap_readonly`. Serve ai subagent per ispezionare dati e piani di esecuzione senza poter scrivere.

## 2. Agenti runtime

### Regole

- **Mai nel percorso della previsione.** Un agente produce osservazioni (con `source = agent_news` e `status: experimental` nel registro) o report. Il modello le usa solo dopo la normale valutazione.
- **Output tipizzato.** Ogni agente dichiara un modello Pydantic di output. Un output che non valida si scarta e si registra.
- **Tracciabilità.** Ogni chiamata va in `ops.llm_call` con agente, versione, modello, hash del prompt, token, costo.
- **Valutazione prima dell'attivazione.** Ogni agente ha un golden set etichettato a mano in `tests/golden/<agente>/`. Soglia minima prima di usarne l'output: precisione 0,90 sui fatti estratti.
- **Provider sostituibile.** Interfaccia unica in `src/soccer_analyst/agents/providers.py`. Default: Gemini Flash-Lite sul piano gratuito (i testi inviati sono pubblici: il piano gratuito può usarli per migliorare i prodotti Google). Alternative configurabili senza toccare gli agenti.
- **Costi e limiti.** Lavorazione a lotti, cache per SHA-256 dell'input, budget giornaliero di chiamate in configurazione.

### Agenti

| Agente | Input | Output | Fase |
|---|---|---|---|
| `news-extractor` | Titolo, sommario RSS, testata, orario | `NewsFacts`: persona, squadra, tipo di fatto (`injury`, `recovery`, `suspension`, `probable_starter`, `coach_under_pressure`, `other`), stato, confidenza, frase di evidenza | 5 |
| `press-sentiment` | Titoli del giorno per squadra e allenatore | Punteggio da -1 a 1 per squadra, da 0 a 1 di pressione per allenatore | 5 |
| `matchday-reviewer` | Metriche deterministiche della giornata (calibrazione, contributi al log-loss, CLV), fatti estratti dalle notizie attorno alle partite più sorprendenti | Report in italiano in `reports/matchdays/` e proposte in `ml.variable_proposal` | 5 |
| `quality-triage` | Controlli falliti della notte | Riassunto per Nico con causa probabile e azione suggerita | 3 |

### "Perché il Milan ha pareggiato?"

Il `matchday-reviewer` risponde a questa domanda senza cadere nell'overfitting:

1. Un passo deterministico calcola, per ogni partita, quanto è costata al modello (contributo al log-loss) e se la sorpresa rientra nel previsto (una probabilità del 27% si avvera circa una volta su quattro).
2. Per le partite davvero anomale su più giornate, l'agente legge i fatti estratti dalle notizie e le variabili disponibili e formula ipotesi.
3. Ogni ipotesi diventa una proposta in `ml.variable_proposal`, con evidenze. Nessuna si attiva da sola: passa dalla valutazione di `docs/variables.md`.

### Orchestrazione degli agenti

Gli agenti runtime sono asset Dagster come gli altri: hanno input dichiarati, partizioni, controlli e storia. Framework: Pydantic AI per output tipizzati e provider intercambiabili.
