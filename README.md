# SoccerAnalystPro

Sistema che raccoglie dati calcistici point-in-time, li valida e produce per ogni partita le probabilità di **1X2**, **Goal/NoGoal** e **Over/Under 2.5**, la quota equa e l'edge rispetto al mercato. Obiettivo iniziale: Serie A, con i dati dei top 5 campionati e delle coppe europee.

Il sistema impara dagli errori sulla calibrazione di centinaia di partite, non inseguendo la singola partita sbagliata.

## Requisiti

- [uv](https://docs.astral.sh/uv/) (installa da sé Python 3.12)
- Docker con Compose
- [Claude Code](https://code.claude.com/docs) per lavorare con gli agenti del repository

## Avvio

```bash
git clone https://github.com/NicoLng00/soccer-ai-pro-analyst.git && cd soccer-ai-pro-analyst
uv sync
uv run python scripts/init_env.py  # .env da env.example con password casuali, mai stampate
./scripts/dev-up.sh                # Postgres 18 + SeaweedFS (S3), ruoli, bucket
uv run sap registry validate       # registro di fonti e variabili
uv run pytest                      # unitari e di integrazione (testcontainers, serve Docker)
uv run pre-commit install
```

Per lavorare con Claude Code avvia la sessione con lo script, dalla radice del repository:

```bash
./scripts/claude.sh
```

Non esportare `.env` nella shell da cui parte Claude Code: ogni comando che Claude esegue vedrebbe tutti i segreti. Lo script passa alla sessione solo `SAP_ENV` e `SAP_DB_URL_READONLY` (per il server MCP in sola lettura). In sviluppo (`SAP_ENV=dev`) i processi Python leggono `.env` da soli tramite `core/config.py`, ciascuno solo la sezione che gli serve.

Poi, nella sessione: `/avvia-fase 0`.

## Come è organizzato il lavoro con gli agenti

| Pezzo | Dove | A cosa serve |
|---|---|---|
| Istruzioni di progetto | `CLAUDE.md` | Principi, comandi, convenzioni, cosa non fare mai |
| Fasi | `docs/roadmap.md`, `docs/prompts/fase-N.md` | Un prompt per fase con blocchi, vincoli e criteri di completamento |
| Subagent revisori | `.claude/agents/` | `schema-guardian`, `leakage-auditor`, `ml-evaluator`, `security-reviewer` (sola lettura); `source-adapter-engineer`, `data-quality-analyst` |
| Skill | `.claude/skills/` | Procedure ripetibili: avvio fase, nuova fonte, nuova variabile, nuova migrazione, nuovo endpoint, backfill, verifica point-in-time, pentest |
| Hook | `.claude/hooks/`, `.claude/settings.json` | Bloccano segreti, dati, migrazioni committate, SQL distruttivo; formattano; controllano prima di chiudere il turno |
| MCP | `.mcp.json` | Postgres in sola lettura (ruolo `sap_readonly`) per ispezionare i dati |
| Agenti runtime | `docs/agents.md`, ADR 0006 | LLM solo ai margini: notizie, sentiment, revisione della giornata. Mai nel calcolo della previsione |

## Documentazione

- `docs/architecture.md` — principi, livelli dei dati, componenti, deploy
- `docs/data-model.md` — schema a livello di colonna
- `docs/sources.md`, `docs/data-quality.md` — fonti, difetti noti, controlli
- `docs/variables.md`, `registry/` — registro delle variabili e delle fonti
- `docs/agents.md` — infrastruttura agentica di sviluppo e runtime
- `docs/security.md` — difese, utenze amministrative, test di sicurezza, pentest
- `docs/frontend/` — riferimento di design e area amministrativa
- `docs/decisions/` — decisioni architetturali (ADR)
- `curation/` — fatti curati a mano da fonti ufficiali

## Dati

Il repository contiene codice, registro e curatela. I dati di terze parti non entrano mai nel repository: stanno nel raw store (Cloudflare R2 in produzione, SeaweedFS in sviluppo) e nel database.
