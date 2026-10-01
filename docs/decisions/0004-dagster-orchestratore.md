# 0004 — Dagster come orchestratore

- Stato: Proposta, da confermare nella fase 0
- Data: 2026-09-30

## Contesto

Servono: job legati all'orario del calcio d'inizio che cambia, backfill a partizioni riprendibili, controlli di qualità che bloccano gli asset a valle, una storia delle esecuzioni. GitHub Actions ritarda o scarta i run programmati; Vercel Hobby ha cron al massimo giornalieri.

## Decisione

Dagster OSS (webserver + daemon) sulla VM Oracle, con storage delle esecuzioni su Postgres. Asset partizionati per competizione e stagione, asset check per i controlli, sensori che leggono `ops.expected_slot` ogni minuto. Ogni job scrive anche in `ops.job_run`, indipendente da Dagster.

## Conseguenze

- Lineage e interfaccia di monitoraggio gratuiti.
- Da misurare la memoria su 12 GB condivisi con Postgres. Se è troppa, alternativa: APScheduler con la stessa `ops.expected_slot`, senza cambiare il resto del codice.
- Il codice di dominio non importa Dagster: gli asset sono involucri sottili in `src/soccer_analyst/orchestration/`.

## Misure (da compilare nella fase 0)

- Memoria a riposo di webserver + daemon:
- Memoria durante un backfill di una stagione:
