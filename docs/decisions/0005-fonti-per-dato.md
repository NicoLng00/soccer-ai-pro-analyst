# 0005 — Una fonte di riferimento per ogni dato storico

- Stato: Accettata
- Data: 2026-09-30

## Contesto

La verifica del 30 settembre 2026 ha mostrato che football-data.co.uk è affidabile sui risultati ma non sulle statistiche: i tiri del 2018/19–2020/21 vengono da una fonte diversa. Pinnacle è inaffidabile dal 23 luglio 2025.

## Decisione

- Risultati e date: football_data, con openfootball come seconda fonte obbligatoria.
- Tiri, xG, xA: understat.
- Statistiche di squadra di football_data (corner, falli, cartellini): solo normalizzate dentro la stagione.
- Quote storiche: football_data; riferimento di chiusura Pinnacle fino al 2024/25, poi media di mercato o Betfair Exchange.
- Casi speciali (tavolino, sospensioni, penalizzazioni): solo curatela manuale.

## Conseguenze

- La priorità delle fonti sta in `registry/sources.yaml`.
- Il controllo di stabilità delle serie (`docs/data-quality.md`, controllo 4) protegge dai cambi futuri.
