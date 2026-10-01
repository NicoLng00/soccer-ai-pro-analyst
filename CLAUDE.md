# SoccerAnalystPro

Sistema che raccoglie dati calcistici point-in-time, li valida e produce per ogni partita le probabilità di 1X2, Goal/NoGoal e Over/Under 2.5, la quota equa e l'edge rispetto al mercato. Obiettivo iniziale: Serie A. Progetto di Nico; si lavora in italiano, il codice è in inglese.

## Principi non negoziabili

Dettagli in `docs/architecture.md`. Se un compito sembra richiedere di violarne uno, fermati e chiedi.

1. **Point-in-time.** Ogni fatto ha `known_period`: il limite inferiore è quando era conoscibile nel mondo. Una feature all'istante T legge solo `known_period @> T`.
2. **Append-only nel contenuto.** Mai `UPDATE` di valori o `DELETE` su `ref`, `obs`, `mkt`, `ml.prediction`. L'unica modifica ammessa è chiudere `known_period`, con riga in `ops.correction_log`.
3. **Provenienza.** Ogni riga ha `source_id`, `mode` (`live`/`backfill`), `knowledge_basis`, origine.
4. **Niente null** in `ref`, `obs`, `mkt`, `ml`. Un dato mancante è una riga che non esiste.
5. **Deterministico.** Nessun LLM nel percorso che produce una previsione. Seed fissi, versioni registrate.
6. **Fonti isolate.** Un adapter per fonte, contratto Pydantic che fallisce in modo esplicito.
7. **Valutazione sulla calibrazione**, su centinaia di partite. Mai aggiungere una variabile per spiegare una partita.

## Mappa del repository

| Percorso | Contenuto |
|---|---|
| `src/soccer_analyst/core/` | Configurazione, tempo, log, errori |
| `src/soccer_analyst/db/` | Modelli SQLAlchemy, query, funzioni point-in-time |
| `src/soccer_analyst/sources/<fonte>/` | `client.py`, `contracts.py`, `parser.py`, `mapping.py` |
| `src/soccer_analyst/ingest/` | Raw store, riconciliazione delle entità |
| `src/soccer_analyst/quality/` | Controlli e soglie |
| `src/soccer_analyst/features/` | Derivazioni e snapshot |
| `src/soccer_analyst/models/`, `evaluation/` | Modelli e valutazione |
| `src/soccer_analyst/agents/` | Agenti LLM runtime e provider |
| `src/soccer_analyst/orchestration/` | Definizioni Dagster (involucri sottili, niente logica di dominio) |
| `src/soccer_analyst/api/` | API FastAPI dell'area amministrativa (fase 6) |
| `src/soccer_analyst/cli.py` | CLI `sap`, compresa la gestione delle utenze (`sap admin`) |
| `frontend/` | Pagina d'ingresso e area `/app`: Vite, React 19, TypeScript, Tailwind v4 (fase 6) |
| `migrations/` | Alembic |
| `registry/` | `sources.yaml`, `variables.yaml`: fonte di verità di fonti e variabili |
| `curation/` | Dati curati a mano (tavolino, penalizzazioni, stadi, rivalità) |
| `docs/` | Architettura, modello dei dati, fonti, qualità, sicurezza, frontend, agenti, roadmap, ADR, prompt di fase |
| `reports/` | Report generati (qualità, valutazione, giornate) |

## Comandi

```bash
uv sync                                   # dipendenze
./scripts/dev-up.sh                       # Postgres 18 + SeaweedFS (S3) in Docker, ruoli, bucket
uv run alembic upgrade head               # schema
uv run sap registry sync                  # carica registry/*.yaml
uv run pytest -m "not integration"        # test veloci
uv run pytest -m integration              # test con Postgres in container
uv run ruff check . && uv run ruff format --check .
uv run mypy src
uv run dagster dev -m soccer_analyst.orchestration.definitions
```

## Come si lavora

- **Fasi.** La fase corrente è in `docs/roadmap.md`. Ogni fase parte con `/avvia-fase N` e un piano in plan mode approvato da Nico.
- **Documentazione prima del codice.** Se cambia lo schema, aggiorna prima `docs/data-model.md`; se cambia una fonte, `docs/sources.md`; una decisione importante diventa un ADR in `docs/decisions/`.
- **Revisori.** Usa i subagent di `.claude/agents/`: `schema-guardian` dopo modifiche a migrazioni o `db/`; `leakage-auditor` dopo modifiche a feature, modelli, regole di conoscibilità, adapter; `ml-evaluator` prima di attivare una variabile o un modello; `data-quality-analyst` dopo un backfill; `security-reviewer` dopo modifiche ad API, frontend, autenticazione, CI o deploy.
- **Procedure.** Skill `nuova-fonte`, `nuova-variabile`, `nuova-migrazione`, `nuovo-endpoint`, `backfill-stagione`, `verifica-pit`, `pentest` (solo su richiesta di Nico).
- **Branch e commit.** Un branch per blocco di lavoro; commit piccoli con messaggi in italiano all'imperativo ("Aggiungi adapter football_data"). Mai commit su `main` direttamente.

## Convenzioni di codice

- Python 3.12, tipizzazione completa, mypy strict. Niente `Any` senza commento che lo giustifichi.
- Tempo: sempre `datetime` con timezone UTC (`core/time.py`). Mai `datetime.now()` senza tz; nei test il tempo si inietta.
- SQL: SQLAlchemy Core per le query pesanti, SQL esplicito per vincoli e funzioni. Nessuna query costruita concatenando stringhe.
- Errori: eccezioni tipizzate in `core/errors.py`; un contratto violato solleva `ContractViolation` con fonte e payload.
- Log: structlog, un evento per riga, sempre con `job_run_id` quando esiste.
- Test: ogni adapter ha fixture reali in `tests/fixtures/<fonte>/`; ogni variabile derivata ha un test point-in-time; i test che toccano il database sono `integration`.
- Configurazione e segreti solo da variabili d'ambiente (`core/config.py`).

## Mai

- Leggere o modificare `.env` o file di segreti.
- Modificare una migrazione già committata: se ne crea una nuova.
- Scrivere nel database con il ruolo proprietario fuori dalle migrazioni.
- Usare statistiche di football-data non normalizzate per stagione (ADR 0005), o Pinnacle dopo il 23/07/2025 come riferimento.
- Inserire dati di terze parti nel repository (fixture minime per i test escluse).
- Dichiarare finito un blocco senza aver eseguito i comandi di verifica.
- Scrivere credenziali reali in codice, test, log, report o chat: le utenze si creano da terminale con `sap admin create`.
- Aggiungere un endpoint senza `require_admin` e senza test di autorizzazione, o mostrare nel frontend testo esterno come HTML.
- Lanciare strumenti di scansione o attacco (nmap, ffuf, nuclei, sqlmap, ZAP) contro qualcosa che non sia l'ambiente locale o lo staging del perimetro.

## Documenti da leggere quando servono

- `docs/architecture.md`: principi, componenti, orchestrazione, deploy
- `docs/data-model.md`: schema a livello di colonna
- `docs/sources.md` e `docs/data-quality.md`: fonti, difetti noti, controlli
- `docs/variables.md` e `registry/variables.yaml`: registro delle variabili
- `docs/agents.md`: subagent, skill, hook, agenti runtime
- `docs/security.md`: difese, utenze, test di sicurezza, pentest
- `docs/frontend/`: riferimento di design, adattamenti, pagine dell'area amministrativa
- `docs/roadmap.md` e `docs/prompts/`: fasi e criteri di completamento
