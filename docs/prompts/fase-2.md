# Fase 2 — Backfill

## Prima di iniziare

Leggi `docs/sources.md`, `docs/data-quality.md`, `docs/decisions/0005-fonti-per-dato.md` e la skill `nuova-fonte`. Proponi il piano in plan mode.

## Obiettivo

Lo storico ricostruito dalla nostra pipeline: top 5 campionati dal 2014/15, Serie A dal 2005/06, coppe europee per le squadre seguite. Ogni riga con `mode = 'backfill'` e `knowledge_basis` corretto.

## Ordine degli adapter

1. `football_data`: risultati, statistiche, quote pre-chiusura e chiusura. Attenzione: date `dd/mm/yy` e `dd/mm/yyyy`, orari UK, colonne che cambiano tra stagioni, codifiche diverse.
2. `openfootball`: seconda fonte dei risultati per il controllo 3.
3. `curation`: partite a tavolino, sospese e rigiocate, penalizzazioni, rivalità, stadi. Parti dai casi elencati in `docs/data-quality.md`.
4. `understat`: tiri, xG, xA. Salva subito una copia locale completa dello storico.
5. `transfermarkt_ds`: formazioni, presenze, eventi, trasferimenti, allenatori, spettatori, valori di mercato. Prima dell'import, controllo 6.
6. `open_meteo`: archivio delle previsioni dal 2021.
7. `wikidata`: stadi, poi verifica manuale in curatela.

## Riconciliazione delle entità

- Chiave esatta, poi regole (alias noti), poi fuzzy con soglia. Sotto soglia: `ops.entity_map_review`.
- Mai creare due entità per la stessa squadra o persona: meglio una revisione manuale in più.

## Orchestrazione

Asset Dagster partizionati per `competition_season`, un asset per fonte e livello (raw, clean). Asset check = controlli di `docs/data-quality.md`. Il backfill si lancia con la skill `backfill-stagione`.

## Revisioni

- `leakage-auditor` su ogni regola di conoscibilità del backfill.
- `data-quality-analyst` dopo ogni stagione importata.
- `schema-guardian` se servono migrazioni.

## Fatto quando

Criteri della Fase 2 in `docs/roadmap.md` spuntati, con `reports/quality/backfill-v1.md`.
