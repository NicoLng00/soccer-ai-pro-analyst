# 0003 — Backfill e live nello stesso database

- Stato: Accettata
- Data: 2026-09-30

## Contesto

Nico vuole un database "vecchio" popolato da fonti selezionate, per addestrare subito, e uno "nuovo e vergine" alimentato dalla nostra cattura. Due database separati porterebbero due copie delle stesse entità da riconciliare per sempre.

## Decisione

Un solo database, stesse entità, stesso registro. Ogni riga dichiara `mode` (`backfill` o `live`). Due ruoli Postgres con Row Level Security: `sap_live` inserisce solo righe `live`, `sap_backfill` solo `backfill`. Le funzioni `obs.as_of_*` accettano un filtro sui modi.

## Conseguenze

- Il dataset "vergine" è una vista: `mode = 'live'`.
- Nessuna riconciliazione tra database.
- Un bug nel backfill non può contaminare le righe live, e viceversa.
