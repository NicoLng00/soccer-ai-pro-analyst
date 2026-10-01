# Fase 0 — Fondamenta

## Prima di iniziare

Leggi, in quest'ordine: `CLAUDE.md`, `docs/architecture.md`, `docs/data-model.md`, `docs/decisions/0001`–`0004`, la sezione Fase 0 di `docs/roadmap.md`. Poi entra in plan mode e proponi un piano diviso in blocchi, ciascuno chiudibile con un commit verde.

## Obiettivo

Un repository che chiunque clona e porta a "database pronto, schema v1 applicato, test verdi" con tre comandi. Nessun dato calcistico ancora.

## Blocchi di lavoro

1. **Tooling.** Il kit contiene già `pyproject.toml`, `uv.lock`, `.pre-commit-config.yaml` e `.github/workflows/ci.yml`: verificali, non riscriverli. `uv sync` deve funzionare da zero. mypy in modalità strict su `src/`. Attiva pre-commit (`uv run pre-commit install`). Sicurezza della catena: gitleaks in pre-commit e in CI, pip-audit in CI, Dependabot. Gli hook di guardia di Claude Code bloccano anche quando falliscono (un'eccezione diventa exit 2) e coprono ogni tool di shell.
2. **Ambiente di sviluppo.** Già presenti: `docker-compose.yml` (Postgres 18 e SeaweedFS come S3 locale), `scripts/dev-up.sh`, `scripts/provision_roles.py`, `scripts/ensure_bucket.py`, `env.example` (il modello delle variabili non comincia con un punto: ogni file `.env*` è un segreto). Provali da zero (volumi cancellati) e correggi ciò che non funziona. Ogni nuova variabile d'ambiente va in `env.example` con un commento.
3. **Configurazione.** `src/soccer_analyst/core/config.py` con `pydantic-settings`: URL del database per ruolo, credenziali R2, ambiente. Nessun default per i segreti.
4. **Schema v1.** Migrazioni Alembic che implementano `docs/data-model.md` per intero: schemi, estensione `btree_gist`, tabelle, `CHECK`, vincoli di esclusione, indici, trigger (validazione del registro nelle osservazioni, origine esistente, previsione prima del calcio d'inizio, somma delle probabilità), ruoli e Row Level Security. Una migrazione per schema logico, in ordine: `ops`, `ref`, `obs`, `mkt`, `ml`, ruoli e RLS. SQL esplicito dove SQLAlchemy non esprime il vincolo.
5. **Funzioni point-in-time.** `obs.as_of_num`, `as_of_cat`, `as_of_bool`, `as_of_json` con la semantica per `temporal_kind`. Viste `obs.current_*` e `obs.observation`.
6. **Registro.** `sap registry sync` (Typer) carica `registry/sources.yaml` e `registry/variables.yaml` in modo idempotente; i cambi di `status` scrivono `obs.variable_status_log`.
7. **Raw store e job.** `ingest/raw_store.py` (put su R2 o SeaweedFS con chiave derivata da fonte, data e SHA-256; registrazione in `ops.raw_ingest` e `ops.fetch_log`). Decoratore o context manager `tracked_job` che scrive `ops.job_run` nel `finally`.
8. **Dagster minimo.** `orchestration/definitions.py` con un asset di prova che usa il raw store e un asset check. Misura la memoria di webserver + daemon a riposo e annotala nell'ADR 0004.
9. **Backup.** `scripts/backup.sh` (pg_dump compresso su R2 o SeaweedFS) e `scripts/restore.sh`; prova di ripristino su un database nuovo.

## Vincoli

- Principi di `docs/architecture.md` non negoziabili. Se un requisito sembra impossibile senza violarne uno, fermati e chiedi.
- Niente codice di dominio in questa fase: nessun adapter, nessuna feature.
- Ogni migrazione deve avere un `downgrade` funzionante.
- Test di integrazione con testcontainers (Postgres 18), marcati `integration`; tra questi `test_migrations_from_zero` (upgrade, downgrade, upgrade). Il job `integration` della CI prova inoltre ruoli e migrazioni sul servizio Postgres del runner.
- Alembic legge `SAP_DB_URL_OWNER` in forma libpq e la converte al dialetto `postgresql+psycopg` in `core/config.py`.

## Revisioni obbligatorie

- Dopo il blocco 4 e dopo il blocco 5: `schema-guardian`.
- Dopo il blocco 5: `leakage-auditor` sui test point-in-time.

## Fatto quando

Tutti i criteri della Fase 0 in `docs/roadmap.md` sono spuntati, ciascuno con il comando che lo verifica riportato nel PR. Aggiorna `Fase corrente: 1` in `docs/roadmap.md` solo dopo l'approvazione di Nico.
