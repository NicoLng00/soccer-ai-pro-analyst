# Curatela manuale

Fatti che nessuna fonte automatica riporta in modo affidabile. Ogni file è un payload grezzo come gli altri: il loader della fase 1 lo registra in `ops.raw_ingest` (fonte `curation`), quindi ogni riga caricata ha provenienza e hash.

## Regole

- **Solo fonti ufficiali**: comunicati del Giudice sportivo e della Lega, decisioni della Corte federale d'appello e del Collegio di garanzia del CONI, siti ufficiali dei club. Niente indiscrezioni.
- **`evidence`**: elenco di URL o riferimenti al comunicato (numero e data). Vuoto finché la voce non è verificata.
- **`verified: false`** vuol dire che la voce è un appunto da controllare. Il loader carica solo le voci `verified: true` e segnala le altre nel report di qualità.
- **`known_from`**: il momento in cui il fatto è diventato pubblico (data del comunicato), non la data della partita. È il limite inferiore di `known_period`. Una decisione poi ribaltata resta nel file: la nuova decisione è una voce nuova con il proprio `known_from`, e il loader chiude il `known_period` della precedente.
- Le date sono in formato ISO 8601; gli orari, se servono, in UTC.

## File

| File | Tabella di destinazione | Contenuto |
|---|---|---|
| `awarded_matches.yaml` | `ref.match_result` (`official`, `decided_by`) | Partite con risultato omologato diverso da quello del campo |
| `standing_adjustments.yaml` | `ref.standing_adjustment` | Penalizzazioni in classifica |
| `rescheduled_matches.yaml` | `ref.match` (stato e nuova data) | Partite non disputate, rinviate o ripetute per decisione degli organi |
| `crowd_restrictions.yaml` | `obs` (`match.crowd_restriction`) | Porte chiuse e limiti di capienza per periodo |
| `rivalries.yaml` | `ref.rivalry` | Derby e rivalità con intensità 1–3 |
| `venues.yaml` | `ref.venue` | Stadi: coordinate, capienza, superficie |
