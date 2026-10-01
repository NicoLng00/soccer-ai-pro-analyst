# Modello dei dati

Specifica a livello di colonna dello schema v1. Le migrazioni Alembic la implementano; quando cambia lo schema si aggiorna prima questo file.

## Convenzioni

- **Schemi**: `ops` (funzionamento, mutabile), `ref` (entità e fatti strutturati), `obs` (registro e osservazioni), `mkt` (quote), `ml` (modelli, previsioni, valutazioni), `app` (area amministrativa, fase 6).
- **Chiavi**: `id bigint GENERATED ALWAYS AS IDENTITY`; `smallint` per tabelle piccole di dominio. Chiavi naturali con `UNIQUE` sulle entità e sulle tabelle operative, con `EXCLUDE … known_period WITH &&` sulle tabelle di fatti.
- **Tempo**: sempre `timestamptz` in UTC; date calcistiche `date`; periodi `daterange` o `tstzrange` con limite superiore aperto per "ancora valido".
- **Niente null** in `ref`, `obs`, `mkt`, `ml`: ogni colonna è `NOT NULL`. In `ops` i null sono ammessi solo dove indicato.
- **Insiemi chiusi**: `text` con `CHECK (col IN (...))`, non tipi `ENUM` (più semplici da migrare).
- **Estensioni**: `btree_gist` per i vincoli di esclusione.

### Colonne di provenienza e conoscenza

Tutte le tabelle di fatti (`ref` tranne le entità pure, `obs`, `mkt`, `ml.prediction`) includono:

| Colonna | Tipo | Significato |
|---|---|---|
| `known_period` | `tstzrange` | Da quando il fatto è conoscibile nel mondo (limite inferiore) a quando è stato sostituito o ritrattato (limite superiore, aperto se attuale) |
| `knowledge_basis` | `text` | Come è stato stabilito il limite inferiore: `captured` (catturato da noi), `publication` (orario di pubblicazione della fonte), `rule` (regola del registro, solo backfill), `post_event` (noto solo dopo l'evento) |
| `mode` | `text` | `live` o `backfill` |
| `source_id` | `smallint` → `ops.source` | Fonte |
| `origin_kind` | `text` | `raw` (da `ops.parse_run`) o `derivation` (da `ops.derivation_run`) |
| `origin_id` | `bigint` | Id della riga d'origine; un trigger verifica che esista nella tabella indicata da `origin_kind` |
| `recorded_at` | `timestamptz DEFAULT now()` | Quando la riga è entrata nel nostro database |

Regole:

- Un fatto nuovo si inserisce con `known_period = tstzrange(t_conoscibile, NULL)`.
- Una correzione chiude il `known_period` della riga precedente all'istante della correzione e inserisce la nuova. Una ritrattazione chiude senza inserire. In entrambi i casi si scrive in `ops.correction_log`, sempre tramite `ops.close_known_period` (sotto).
- La lettura all'istante T filtra `known_period @> T`.
- `mode` è vincolato dalla Row Level Security: il ruolo `sap_live` può inserire solo `mode = 'live'`, `sap_backfill` solo `mode = 'backfill'`.

Vincoli comuni a ogni tabella di fatti:

- `CHECK (NOT isempty(known_period) AND NOT lower_inf(known_period) AND lower_inc(known_period) AND NOT upper_inc(known_period))`: limite inferiore finito e incluso, superiore escluso o aperto.
- `CHECK (knowledge_basis <> 'rule' OR mode = 'backfill')`: la conoscibilità ricostruita da regola esiste solo nel backfill.
- Le chiavi naturali sono vincoli `EXCLUDE (… WITH =, known_period WITH &&)`, mai `UNIQUE`: con `UNIQUE` una correzione (chiudi e reinserisci la stessa chiave) sarebbe impossibile.
- Indice GiST su `known_period`.

### Append-only applicato dal database

- `sap_live` e `sap_backfill` hanno `UPDATE` solo sulla colonna `known_period` (grant per colonna) e nessun `DELETE`.
- Un trigger `BEFORE UPDATE` ammette solo la chiusura: il limite inferiore non cambia, il superiore passa da aperto a un istante maggiore o uguale all'inferiore; ogni altra modifica è un errore.
- Trigger `BEFORE DELETE` (per riga) e `BEFORE TRUNCATE` (per istruzione) che rifiutano sempre, anche per il proprietario. Le migrazioni di `downgrade` eliminano le tabelle, non le righe.
- `ops.close_known_period(p_table regclass, p_row_id bigint, p_at timestamptz, p_action text, p_reason text, p_job_run_id bigint)`: chiude il `known_period` della riga e scrive `ops.correction_log` nella stessa transazione.
  - `SECURITY INVOKER`: gira con i permessi e la RLS di chi la chiama.
  - Accetta solo tabelle di un elenco chiuso (le tabelle di fatti di `ref`, `obs`, `mkt` e `ml.prediction`, confrontate come `regclass`); qualsiasi altra tabella è un errore.
  - Costruisce l'`UPDATE` con `format('%I.%I', …)` sui nomi presi dal catalogo, mai concatenando testo dell'utente; i valori passano come parametri (`EXECUTE … USING`).
  - Errore se la riga non esiste, è già chiusa o se `p_at` precede l'inizio del suo `known_period`.

## ops

| Tabella | Colonne principali | Vincoli e note |
|---|---|---|
| `ops.source` | `id smallint`, `code text`, `name text`, `kind text` (`file`, `api`, `scrape`, `rss`, `manual`, `derived`, `agent`), `priority smallint`, `license_note text`, `terms_url text`, `status text` (`active`, `testing`, `disabled`), `created_at` | `code` univoco. Popolata da `registry/sources.yaml` con `sap registry sync`. `priority`: con più fonti per la stessa variabile vince il valore più basso, a parità l'`id` più basso |
| `ops.raw_ingest` | `id`, `source_id`, `request_key text` (URL o percorso), `object_key text` (chiave R2), `sha256 char(64)`, `byte_size int`, `content_type text`, `first_fetched_at timestamptz` | Univoca su `(source_id, sha256)` |
| `ops.fetch_log` | `id`, `raw_ingest_id`, `fetched_at`, `http_status smallint`, `job_run_id` → `ops.job_run` | Un evento per download, anche se il contenuto è già noto: prova di quando l'informazione era disponibile. Ogni download avviene dentro un job |
| `ops.parse_run` | `id`, `raw_ingest_id`, `parser_name`, `parser_version`, `started_at`, `finished_at`, `status` (`success`, `failed`), `rows_emitted int`, `error_count int` | Riparsare = nuova riga, nuove versioni dei fatti |
| `ops.job_run` | `id`, `job_name`, `scheduled_for`, `started_at`, `finished_at` (null finché `running`), `status` (`running`, `success`, `failed`, `partial`), `rows_in`, `rows_out`, `git_sha`, `message text DEFAULT ''` | Scritta all'avvio con `status = 'running'`, così l'id esiste per `fetch_log`, `correction_log` e i log; aggiornata nel `finally` con stato finale, `finished_at` e contatori. `CHECK ((status = 'running') = (finished_at IS NULL))`. Un crash (processo ucciso) lascia la riga `running`: il controllo degli slot la tratta come fallita oltre il timeout del job. `scheduled_for` vale `started_at` per i job lanciati a mano; `git_sha` vale `'unknown'` se non disponibile |
| `ops.expected_slot` | `id`, `job_name`, `subject_key text` (es. `match:4812`, `global`), `scheduled_for`, `created_at`, `cancelled boolean DEFAULT false` | Univoca su `(job_name, subject_key, scheduled_for)`. Base del controllo "slot saltati" |
| `ops.entity_map` | `id`, `source_id`, `entity_kind`, `source_key text`, `entity_id bigint`, `method` (`exact`, `rule`, `fuzzy`, `manual`), `confidence numeric(4,3)`, `decided_at`, `decided_by text` | Univoca su `(source_id, entity_kind, source_key, decided_at)`; vale la decisione più recente |
| `ops.entity_map_review` | `id`, `source_id`, `entity_kind`, `source_key`, `candidates jsonb`, `status` (`open`, `resolved`), `created_at`, `resolved_at` (null ammesso) | Coda di revisione manuale sotto la soglia di confidenza |
| `ops.derivation_run` | `id`, `derivation_name`, `code_version`, `params_hash`, `started_at`, `finished_at`, `status`, `rows_out` | Origine delle variabili derivate |
| `ops.correction_log` | `id`, `table_name`, `row_id`, `action` (`superseded`, `retracted`), `reason text`, `acted_at`, `job_run_id` → `ops.job_run` | Ogni chiusura di `known_period`, scritta da `ops.close_known_period` |
| `ops.quality_check_result` | `id`, `check_name`, `subject text`, `run_at`, `status` (`pass`, `warn`, `fail`), `metric numeric`, `threshold numeric`, `details jsonb` | Storia dei controlli, indipendente da Dagster |
| `ops.news_item` | `id`, `source_id`, `url text`, `title text`, `published_at`, `first_seen_at`, `language text`, `raw_ingest_id` | Univoca su `url`. Nessun testo integrale nel database |
| `ops.llm_call` | `id`, `agent_name`, `agent_version`, `provider`, `model`, `prompt_sha256`, `input_ref text`, `output jsonb`, `output_valid boolean`, `started_at`, `latency_ms`, `input_tokens`, `output_tokens`, `cost_usd numeric(10,6)` | Ogni chiamata di un agente runtime, per riproducibilità e costi |

## ref: entità

| Tabella | Colonne | Vincoli e note |
|---|---|---|
| `ref.area` | `id smallint`, `code text` (ISO 3166-1 alpha-2, `EU`, `WORLD`), `name`, `kind` (`country`, `continent`, `world`) | `code` univoco |
| `ref.competition` | `id smallint`, `code text` (es. `ITA-SA`, `UEFA-CL`), `name`, `area_id`, `kind` (`league`, `cup`, `supercup`, `international`), `tier smallint`, `gender` (`men`, `women`) | `code` univoco |
| `ref.season` | `id smallint`, `code text` (es. `2026-27`), `period daterange` | `code` univoco |
| `ref.competition_season` | `id`, `competition_id`, `season_id`, `period daterange`, `format` (`round_robin`, `knockout`, `mixed`) | Univoca su `(competition_id, season_id)`. È la partizione degli asset Dagster |
| `ref.team` | `id`, `kind` (`club`, `national`, `placeholder`), `canonical_name`, `short_name`, `area_id` | `placeholder` per "svincolato", "settore giovanile", "ritirato" nei trasferimenti |
| `ref.venue` | `id`, `canonical_name`, `city`, `area_id`, `lat double precision`, `lon double precision` | Si crea solo con coordinate verificate; la capienza è un'osservazione |
| `ref.person` | `id`, `canonical_name`, `created_at` | Una persona sola anche se cambia ruolo. Data di nascita, piede, altezza sono osservazioni |
| `ref.rivalry` | `id`, `team_low_id`, `team_high_id`, `name`, `intensity smallint` (1-3) | `CHECK (team_low_id < team_high_id)`; curata in `curation/rivalries.yaml` |

## ref: fatti

Tutte con le colonne di provenienza e conoscenza.

| Tabella | Colonne | Vincoli e note |
|---|---|---|
| `ref.match` | `id`, `competition_season_id`, `stage text` (es. `regular`, `round_of_16`), `round_label text` (es. `Giornata 5`), `home_team_id`, `away_team_id`, `replay_seq smallint DEFAULT 0` | Identità della partita. Orario, stadio, stato sono osservazioni. `replay_seq`: 0 per la partita originale, 1, 2… per le ripetizioni ordinate dagli organi sportivi. Chiave naturale: `EXCLUDE (competition_season_id =, stage =, home_team_id =, away_team_id =, replay_seq =, known_period &&)`. `CHECK (home_team_id <> away_team_id)`, `CHECK (replay_seq >= 0)` |
| `ref.match_team` | `id`, `match_id`, `side` (`home`, `away`), `team_id` | Esclusione su `(match_id, side)` con `known_period` sovrapposto. Entità del livello partita |
| `ref.match_result` | `id`, `match_id`, `kind` (`half_time`, `full_time_on_field`, `after_extra_time`, `penalties`, `official`), `home_goals smallint`, `away_goals smallint`, `decided_by` (`played`, `awarded`, `replayed`) | Esclusione su `(match_id, kind, source_id)` con `known_period` sovrapposto. `full_time_on_field` per i modelli, `official` per la classifica |
| `ref.lineup_entry` | `id`, `match_team_id`, `person_id`, `role` (`starter`, `bench`) | Esclusione su `(match_team_id, person_id)` con `known_period` sovrapposto. Conoscibile circa 60 minuti prima; nel backfill `knowledge_basis = 'rule'` |
| `ref.participation` | `id`, `match_team_id`, `person_id`, `minute_in smallint`, `minute_out smallint`, `minutes_played smallint` | Esclusione su `(match_team_id, person_id)` con `known_period` sovrapposto. `post_event` |
| `ref.match_event` | `id`, `match_id`, `match_team_id`, `person_id`, `kind` (`goal`, `own_goal`, `penalty_goal`, `penalty_missed`, `yellow`, `second_yellow`, `red`, `sub_in`, `sub_out`), `minute smallint`, `stoppage smallint DEFAULT 0` | Eventi senza persona nota non si registrano qui |
| `ref.referee_assignment` | `id`, `match_id`, `person_id`, `role` (`referee`, `var`, `assistant`, `fourth`) | Esclusione su `(match_id, person_id)` con `known_period` sovrapposto. `knowledge_basis = 'publication'` quando la designazione ha una data |
| `ref.squad_membership` | `id`, `person_id`, `team_id`, `scope` (`club`, `national`), `valid_period daterange` | `EXCLUDE (person_id =, scope =, valid_period &&, known_period &&)` |
| `ref.coach_tenure` | `id`, `person_id`, `team_id`, `role` (`head_coach`, `caretaker`), `valid_period daterange` | `EXCLUDE (team_id =, role =, valid_period &&, known_period &&)` |
| `ref.transfer` | `id`, `person_id`, `from_team_id`, `to_team_id`, `kind` (`permanent`, `loan`, `loan_return`, `free`), `announced_at`, `effective_date` | Esclusione su `(person_id, to_team_id, effective_date)` con `known_period` sovrapposto. Mai voci di mercato. Il prezzo è un'osservazione, spesso assente |
| `ref.standing_adjustment` | `id`, `competition_season_id`, `team_id`, `points smallint` (negativo = penalizzazione), `effective_date`, `reason text` | Classifica = risultati `official` + penalizzazioni |

## obs

### `obs.variable` (registro)

Popolato da `registry/variables.yaml`, versionato nel repository. È metadato, non un fatto: si aggiorna solo con `sap registry sync`, che scrive con il ruolo `sap_registry`, secondo queste regole:

- `code`, `dtype` ed `entity_kind` sono immutabili: cambiarli è un errore (si crea una variabile nuova).
- Un cambio di `level`, `kind`, `unit`, `temporal_kind`, `knowable_rule` o `backfill_policy` richiede `version` incrementata.
- `status`, `feasibility` e `description` cambiano liberamente; ogni cambio di `status` scrive `obs.variable_status_log`, e il passaggio ad `active` richiede un riferimento all'evidenza (`--evidence`, il report di valutazione).
- Una variabile tolta dallo YAML è un errore: non si cancella, si mette `retired`.
- Le stesse regole valgono per `ops.source` (`code` immutabile, nessuna cancellazione: si mette `disabled`).

| Colonna | Tipo | Valori |
|---|---|---|
| `id` | `smallint` | |
| `code` | `text` univoco | es. `team.elo`, `match_team.rest_days` |
| `level` | `text` | `macro`, `match`, `micro` |
| `entity_kind` | `text` | `competition_season`, `team`, `person`, `venue`, `match`, `match_team` |
| `kind` | `text` | `raw`, `derived`, `model` |
| `dtype` | `text` | `num`, `cat`, `bool`, `json` |
| `unit` | `text` | es. `km`, `giorni`, `adimensionale` |
| `temporal_kind` | `text` | `state` (vale da `valid_at` fino al valore successivo), `event` (accade a `valid_at`), `attribute` (valore unico dell'entità) |
| `knowable_rule` | `text` | `post_match`, `kickoff_minus_60m`, `publication`, `announcement`, `static`, `pre_match` |
| `backfill_policy` | `text` | `allowed`, `rule` (conoscibilità ricostruita da `knowable_rule`), `excluded` (nessuna feature pre-partita sul backfill) |
| `feasibility` | `text` | `collectable`, `to_test`, `approximable`, `deferred` |
| `status` | `text` | `experimental`, `active`, `retired` |
| `version` | `smallint` | Incrementa se cambia la definizione |
| `description` | `text` | In italiano |

I cambi di `status` si registrano in `obs.variable_status_log (variable_id, from_status, to_status, changed_at, evidence_ref text)`.

### Osservazioni tipizzate

Quattro tabelle con le stesse colonne, cambia solo il tipo di `value`: `obs.obs_num` (`double precision`), `obs.obs_cat` (`text`), `obs.obs_bool` (`boolean`), `obs.obs_json` (`jsonb`). Nessuna colonna di valore nullable.

| Colonna | Tipo |
|---|---|
| `id` | `bigint` |
| `variable_id` | `smallint` → `obs.variable` |
| `entity_kind` | `text` |
| `entity_id` | `bigint` |
| `valid_at` | `timestamptz` |
| `value` | tipo della tabella |
| colonne di provenienza e conoscenza | vedi sopra |

- Un trigger verifica che `dtype` ed `entity_kind` coincidano con il registro e che l'entità esista.
- `EXCLUDE (variable_id =, entity_kind =, entity_id =, valid_at =, source_id =, known_period &&)`.
- Indici: `(variable_id, entity_id, valid_at DESC)` e GiST su `known_period`.
- `obs.observation` è una vista `UNION ALL` delle quattro, con `value` convertito in `jsonb`, per ispezione.

### Lettura point-in-time

Funzioni SQL, una per tipo, stessa firma:

```sql
obs.as_of_num(
    p_variable text,
    p_as_of timestamptz,
    p_modes text[] DEFAULT '{live,backfill}',
    p_sources text[] DEFAULT NULL          -- codici di ops.source; NULL = tutte le fonti
) RETURNS TABLE (entity_kind text, entity_id bigint, valid_at timestamptz, value double precision, source_id smallint)
```

Le righe candidate sono quelle della variabile con `known_period @> p_as_of`, `valid_at <= p_as_of`, `mode = ANY(p_modes)` e, se `p_sources` non è `NULL`, fonte in `p_sources`. Semantica per `temporal_kind`:

- `state` e `attribute`: per ogni entità una riga, quella con `valid_at` più recente. A parità di `valid_at` vince la fonte con `priority` più bassa, poi con `id` più basso.
- `event`: per ogni entità tutte le righe, una sola per ogni `valid_at`: quella della fonte con `priority` più bassa, poi con `id` più basso.

Le funzioni sono `STABLE` e deterministiche: stesso contenuto e stessi argomenti, stesso risultato. La vista `obs.current_*` è il caso `p_as_of = now()`.

Test obbligatori (fase 0):

- Una riga inserita con `known_period` che inizia dopo T non compare mai in `as_of(T)`; una correzione chiusa a T2 compare in `as_of(T1 < T2)` e non in `as_of(T3 > T2)`.
- Test di proprietà (Hypothesis): su insiemi casuali di osservazioni (più entità, fonti con priorità, modi, correzioni e ritrattazioni) e istanti casuali, ogni funzione `as_of_*` restituisce esattamente ciò che restituisce un'implementazione di riferimento in Python scritta da questa specifica, per ogni combinazione di `p_modes` e `p_sources`.

## mkt

| Tabella | Colonne | Vincoli e note |
|---|---|---|
| `mkt.bookmaker` | `id smallint`, `code`, `name`, `is_exchange boolean`, `is_sharp boolean` | `code` univoco |
| `mkt.market` | `code text` PK (`1x2`, `ou_2.5`, `btts`), `outcomes text[]` | La linea sta nel codice: nessun null. Righe inserite dalla migrazione: `1x2` → `{home,draw,away}`, `ou_2.5` → `{over,under}`, `btts` → `{yes,no}`. Un trigger verifica che ogni `outcome` di `odds_quote`, `prediction_prob` e `prediction_edge` appartenga agli `outcomes` del suo mercato |
| `mkt.odds_quote` | `id`, `match_id`, `bookmaker_id`, `market_code`, `outcome`, `price numeric(8,3)`, `quoted_at`, `quote_kind` (`snapshot`, `opening`, `pre_closing`, `closing`) + provenienza e conoscenza | `CHECK (price > 1)`. Esclusione su `(match_id, bookmaker_id, market_code, outcome, quote_kind, quoted_at, source_id)` con `known_period` sovrapposto. Per football-data: `pre_closing` con `quoted_at` da regola (venerdì o martedì pomeriggio), `closing` con `quoted_at` al calcio d'inizio. Pinnacle esclusa dopo il 23/07/2025 |

## ml

| Tabella | Colonne | Vincoli e note |
|---|---|---|
| `ml.model_version` | `id`, `name`, `version`, `git_sha`, `params jsonb`, `feature_set_hash`, `train_window tstzrange`, `trained_at`, `status` (`experimental`, `active`, `retired`) | Univoca su `(name, version)` |
| `ml.feature_snapshot` | `id`, `match_id`, `as_of`, `feature_set_hash`, `features jsonb`, `created_at` | Una feature mancante è una chiave assente, mai un null |
| `ml.prediction` | `id`, `model_version_id`, `match_id`, `horizon` (`T-24h`, `T-1h`), `as_of`, `feature_snapshot_id`, `created_at DEFAULT now()` + provenienza | Mai modificata. Trigger "previsione prima del calcio d'inizio", con il calcio d'inizio letto da `match.kickoff_at` tramite `obs.as_of_json` (nessun calcio d'inizio noto = errore). `live`: `created_at` è forzato a `now()`, `as_of <= created_at` e `created_at` precede il calcio d'inizio noto ad `as_of`. `backfill` (previsioni rigiocate sullo storico): `as_of` precede sia il calcio d'inizio noto ad `as_of` sia quello noto oggi (`now()`), così un rinvio scoperto dopo non rende valida una previsione fatta a partita già giocata |
| `ml.prediction_prob` | `prediction_id`, `market_code`, `outcome`, `probability numeric(6,5)`, `fair_odds numeric(8,3)` | Chiave `(prediction_id, market_code, outcome)`. La somma per mercato è 1 entro 1e-4: trigger di vincolo `DEFERRABLE INITIALLY DEFERRED`, controllato al commit |
| `ml.prediction_edge` | `prediction_id`, `market_code`, `outcome`, `bookmaker_id`, `price`, `edge numeric(7,4)` | Edge = probabilità × quota − 1 |
| `ml.evaluation` | `id`, `model_version_id`, `scope text`, `metric` (`log_loss`, `brier`, `rps`, `ece`, `clv`), `value`, `n_matches`, `computed_at` | |
| `ml.variable_proposal` | `id`, `proposed_by` (`agent:matchday-reviewer`, `human`), `created_at`, `title`, `rationale`, `evidence jsonb` | Ipotesi di nuove variabili; nessuna si attiva da sola |
| `ml.variable_proposal_decision` | `proposal_id`, `decision` (`accepted`, `rejected`), `decided_by` (FK `app.admin_user`), `decided_at`, `note` | Decisione umana, presa dall'area amministrativa. `accepted` vuol dire "da valutare": l'attivazione passa comunque da `docs/variables.md` |

## app

Utenti, sessioni e audit dell'area amministrativa (ADR 0008, `docs/security.md`). È l'unico schema, insieme a `ops`, in cui sono ammessi null: contiene stati operativi (una sessione revocata o no), non fatti calcistici.

| Tabella | Colonne | Vincoli e note |
|---|---|---|
| `app.admin_user` | `id smallint`, `username`, `email`, `password_hash`, `totp_secret_enc bytea`, `totp_confirmed_at`, `created_at`, `password_changed_at`, `disabled_at` (null se attivo) | `username` univoco, `CHECK (username ~ '^[a-z0-9._-]{3,32}$')`; `password_hash` argon2id; il segreto TOTP è cifrato con `SAP_TOTP_ENCRYPTION_KEY`. Scrivibile solo da `sap_useradmin` |
| `app.session` | `id`, `user_id`, `token_hash bytea`, `created_at`, `last_seen_at`, `mfa_passed_at` (null finché il TOTP non è confermato), `idle_expires_at`, `absolute_expires_at`, `revoked_at`, `ip inet`, `user_agent` | `token_hash` univoco (SHA-256 del token: il token in chiaro vive solo nel cookie). Una sessione senza `mfa_passed_at` non dà accesso a nessun endpoint protetto |
| `app.login_attempt` | `id`, `at`, `ip inet`, `username_tried`, `outcome` (`ok`, `bad_credentials`, `locked`, `bad_totp`) | Base per il limite di tentativi e il blocco progressivo. Pulizia oltre i 90 giorni |
| `app.audit_log` | `id`, `at`, `actor` (`user:<id>`, `cli`, `system`), `action`, `target`, `details jsonb`, `ip inet` | Sola aggiunta: un trigger blocca `UPDATE` e `DELETE`. Mai password, codici, cookie o token in `details` |

## Ruoli Postgres

| Ruolo | Permessi |
|---|---|
| `sap_owner` | Proprietario dello schema; solo migrazioni |
| `sap_live` | `SELECT` su `ref`, `obs`, `mkt`, `ml`; `INSERT` su fatti e osservazioni con `mode = 'live'` e sulle entità di `ref` e `mkt` (che non hanno `mode`); `UPDATE` solo della colonna `known_period`; `SELECT`, `INSERT`, `UPDATE` sulle tabelle operative di `ops` tranne `ops.source`; mai `DELETE`. Sul registro (`ops.source`, `obs.variable`, `obs.variable_status_log`) solo `SELECT` |
| `sap_backfill` | Come `sap_live` ma `mode = 'backfill'` |
| `sap_registry` | Solo per `sap registry sync`: `SELECT`, `INSERT`, `UPDATE` su `ops.source` e `obs.variable`; `SELECT`, `INSERT` su `obs.variable_status_log`. Nessun altro permesso |
| `sap_readonly` | `SELECT` su tutto tranne `app`; usato dal server MCP di Claude Code e dalle analisi |
| `sap_api` | Ruolo dell'API: `SELECT` su `ref`, `obs`, `mkt`, `ml` e sulle tabelle di stato di `ops`; `INSERT` su `ml.variable_proposal_decision`; `SELECT`, `INSERT`, `UPDATE` su `app.session` e `app.login_attempt`; `INSERT` su `app.audit_log`; `SELECT` su `app.admin_user` senza poterlo modificare |
| `sap_useradmin` | Solo per i comandi `sap admin` da terminale: `SELECT`, `INSERT`, `UPDATE` su `app.admin_user`, `UPDATE` di `revoked_at` su `app.session`, `INSERT` su `app.audit_log`. Il container dell'API non ne conosce la password |
