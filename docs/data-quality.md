# Qualità dei dati

Ogni import passa questi controlli. Sono asset check di Dagster; ogni esito si scrive anche in `ops.quality_check_result`. Un `fail` blocca gli asset a valle; un `warn` apre una segnalazione ma non blocca.

| # | Controllo | Regola | Esito se violato |
|---|---|---|---|
| 1 | Completezza stagione | Campionato a 20 squadre: 380 partite, ogni incrocio casa-trasferta una volta, 38 partite per squadra. Coppe: numero di partite atteso per fase | `fail` |
| 2 | Coerenza interna | Esito coerente con i gol; primo tempo ≤ finale; tiri in porta ≤ tiri; gol ricostruiti dai tiri di Understat = gol del risultato | `fail` sulla riga, che resta fuori |
| 3 | Concordanza tra fonti | Risultato finale e data confrontati su almeno due fonti | `fail` sulla riga; la riga va in `ops.entity_map_review` o in curatela |
| 4 | Stabilità delle serie | Media per stagione di ogni statistica di squadra; salto rispetto alla media delle 3 stagioni precedenti oltre la soglia (proposta iniziale: 15%) | `warn`; la serie di quella stagione non entra nelle feature finché non si decide |
| 5 | Sanità delle quote | Prezzo > 1; margine del bookmaker 1X2 tra 0% e 15%; nessuna quota Pinnacle dopo il 23/07/2025 | `fail` sulla quota |
| 6 | Conteggi Transfermarkt | Partite, presenze e formazioni per stagione e competizione confrontate con football-data; minuti per squadra e partita intorno a 990 | `fail` sulla stagione se mancano partite; `warn` sui minuti |
| 7 | Casi speciali | Partite a tavolino, sospese e rigiocate, penalizzazioni: solo da `curation/*.yaml` | `fail` se una fonte riporta un caso non curato |
| 8 | Point-in-time | Nessuna feature usa righe con `known_period` che inizia dopo l'`as_of` dello snapshot | `fail` sempre; è un bug |
| 9 | Slot saltati | Ogni riga di `ops.expected_slot` passata ha un `ops.job_run` corrispondente | `warn` a 15 minuti di ritardo, `fail` a 60 |

Le soglie sono proposte iniziali: si tarano sul backfill e si fissano in `src/soccer_analyst/quality/thresholds.py` con un commento che spiega da dove vengono.

## Casi già noti

- Sassuolo-Pescara 2016/17: 2-1 sul campo, 0-3 omologato.
- Verona-Roma 2020/21: 0-0 sul campo, 3-0 omologato.
- Juventus-Napoli 2020/21: non giocata il 4 ottobre 2020, giocata il 7 aprile 2021 (2-1).
- Fiorentina-Inter 2024/25: sospesa il 1° dicembre 2024, giocata il 6 febbraio 2025 (3-0). Primo tempo discordante tra le fonti.
- Juventus 2022/23: penalizzazione di 10 punti.
- Differenze di primo tempo da arbitrare con una terza fonte: Sampdoria-Milan 2014/15, Sassuolo-Cagliari 2020/21, Fiorentina-Inter 2024/25.

## Regime, non errore

Dal 2019/20 le vittorie in casa in Serie A non superano il 42,4%; dal 2005/06 al 2018/19 erano scese sotto il 43% una sola volta. Il vantaggio del campo si stima per periodo, non come costante.
