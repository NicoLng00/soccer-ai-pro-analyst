# Fonti

Una sezione per fonte: cosa prendiamo, come, cosa sappiamo dei suoi difetti, come la controlliamo. I difetti vengono dalla verifica del 30 settembre 2026 (sezione "Integrità dei dati storici" del documento di progetto).

Regola generale: ogni fonte è un pacchetto in `src/soccer_analyst/sources/<codice>/` con `client.py` (scaricamento), `contracts.py` (modelli Pydantic del payload), `parser.py` (payload → righe), `mapping.py` (chiavi della fonte → entità canoniche). Procedura: skill `nuova-fonte`.

## football_data — football-data.co.uk

- **Cosa**: CSV per campionato e stagione. Risultati, primo tempo, statistiche di squadra, quote 1X2 e Over/Under 2.5 di più bookmaker, pre-chiusura e chiusura.
- **Uso**: backfill di risultati e quote; controllo post-giornata.
- **Conoscibilità**: quote `pre_closing` raccolte il venerdì pomeriggio per il weekend e il martedì pomeriggio per i turni infrasettimanali (orario UK); `closing` al calcio d'inizio.
- **Difetti noti**:
  - Risultati affidabili: su 4.930 partite di Serie A confrontate con openfootball, date identiche e un solo finale diverso.
  - Partite a tavolino con criterio non uniforme: Sassuolo-Pescara 2016/17 con il risultato omologato, Verona-Roma 2020/21 con quello del campo. Si risolvono con `curation/awarded_matches.yaml`.
  - Statistiche di Serie A assenti prima del 2005/06; tiri non confrontabili tra stagioni (2018/19–2020/21 da una fonte diversa: 7,4 tiri in meno a partita di Understat).
  - Serie A: arbitro sempre vuoto, spettatori assenti.
  - Pinnacle inaffidabile dal 23 luglio 2025 e assente nel 2026/27: riferimento di chiusura = media di mercato o Betfair Exchange dopo quella data.
- **Controlli**: completezza stagione, coerenza interna, concordanza dei risultati con una seconda fonte, stabilità delle serie statistiche, sanità delle quote.

## understat — Understat

- **Cosa**: xG di squadra e tiro per tiro, xG e xA per giocatore; top 5 campionati e Russia dal 2014/15.
- **Uso**: backfill e aggiornamento il giorno dopo la partita.
- **Accesso**: endpoint JSON del sito (`/getLeagueData/{league}/{season}` e simili) con header `X-Requested-With: XMLHttpRequest`; la stagione è l'anno di inizio. Le vecchie pagine HTML rispondono 200 ma vuote.
- **Difetti noti**: blocca alcuni IP di cloud via Cloudflare; va provato dalla VM nella fase 1. Nel campione 2014/15–2020/21 stagioni complete e gol coerenti con football-data.
- **Controlli**: contratto che fallisce su risposta vuota; gol ricostruiti dai tiri uguali al risultato; copia locale completa dello storico appena scaricata.

## transfermarkt_ds — transfermarkt-datasets

- **Cosa**: 12 tabelle; ci servono partite (spettatori, allenatori), formazioni, presenze con minuti, eventi, trasferimenti, valori di mercato, giocatori.
- **Uso**: solo backfill. Aggiornamenti sospesi: fermo al 6 luglio 2026.
- **Difetti noti**: perdite silenziose in passato (66% delle presenze 2024/25 in una release, poi corretto; valutazioni regredite, poi corrette); tabella giocatori completa al 95% circa secondo un utente; valori di mercato = stime editoriali.
- **Controlli**: conteggi per stagione e competizione confrontati con football-data prima dell'import; minuti per squadra e partita intorno a 990 (11 giocatori per 90), meno in caso di espulsioni; scostamenti oltre una soglia da tarare vanno in revisione.

## open_meteo — Open-Meteo

- **Cosa**: previsioni e archivio. Per il backfill l'archivio delle previsioni (dal 2021), non la rianalisi ERA5: serve ciò che si sapeva prima della partita.
- **Condizioni**: gratuita per uso non commerciale fino a 10.000 chiamate al giorno; dati CC BY 4.0.
- **Controlli**: valori entro limiti fisici; coordinate dello stadio da `ref.venue`.

## wikidata — Wikidata

- **Cosa**: coordinate e capienza degli stadi.
- **Controlli**: gli stadi sono poche decine; si verificano a mano una volta e si fissano in `curation/venues.yaml`.

## api_football — API-Football

- **Cosa**: calendario, formazioni ufficiali, infortuni, indisponibili, arbitri, trasferimenti, allenatori.
- **Limiti**: 100 richieste al giorno; il piano gratuito limita le stagioni. Da verificare nella fase 1 che il 2026/27 sia accessibile.
- **Uso**: live.

## the_odds_api — The Odds API

- **Cosa**: quote pre-partita (h2h, totals) di bookmaker europei, Pinnacle compresa.
- **Limiti**: 500 crediti al mese; uno snapshot di tutte le partite di un campionato per un mercato e una regione costa 1 credito. Serie A, 1X2 + Over/Under, regione EU: 2 crediti per snapshot.
- **Uso**: live, snapshot allineati alle fasce orarie delle partite.

## oddspapi — OddsPapi

- **Cosa**: dichiara Goal/NoGoal nel piano gratuito. Da testare nella fase 1.

## football_data_org e openfootball

- Solo controllo incrociato di calendario e risultati.

## news_rss — testate sportive

- **Cosa**: titoli, link e orari di pubblicazione dai feed RSS (Gazzetta dello Sport, Sky Sport, Corriere dello Sport, Tuttosport e altre). Lo stato di ogni feed va verificato nella fase 1.
- **Diritti**: si conservano solo titolo, link, orario e fatti estratti; mai il testo integrale.
- **Uso**: raccolta dal primo giorno di cattura live; estrazione con l'agente notizie nella fase 5.

## curation — curatela manuale

File YAML versionati in `curation/`: partite a tavolino, penalizzazioni, rivalità, stadi, restrizioni del pubblico. Ogni file è un payload grezzo come gli altri: passa da `ops.raw_ingest`, quindi ogni riga ha provenienza.
