---
name: backfill-stagione
description: Esegue il backfill di una partizione competizione-stagione con controlli di qualità e report. Solo su richiesta esplicita.
disable-model-invocation: true
argument-hint: "[competizione] [stagione]  es. ITA-SA 2024-25"
arguments: competizione stagione
---

# Backfill `$competizione` `$stagione`

## Stato attuale della partizione

!`uv run sap partition status $competizione $stagione 2>&1 | tail -20`

## Procedura

1. Verifica che il ruolo usato sia `sap_backfill` (variabile `SAP_DB_URL_BACKFILL`).
2. Lancia gli asset della partizione in ordine di dipendenza:
   `uv run dagster asset materialize -m soccer_analyst.orchestration.definitions --partition "$competizione/$stagione" --select "tag:layer=raw+"`
   Se Dagster non è ancora disponibile, usa `uv run sap backfill $competizione $stagione`.
3. Leggi l'esito degli asset check. Per ogni `fail`, fermati: non proseguire con le partizioni successive.
4. Svuota la coda `ops.entity_map_review` della partizione prima di passare alla successiva.
5. Chiedi al `data-quality-analyst` il report della partizione.

## Output

Una riga in `reports/quality/backfill-log.md`: data, partizione, righe per tabella, controlli (pass, warn, fail), revisioni aperte, link al report.
