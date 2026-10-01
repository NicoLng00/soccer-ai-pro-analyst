# Fase 3 — Cattura live

## Prima di iniziare

Leggi `docs/architecture.md` (Orchestrazione), `docs/agents.md` (agente `quality-triage`), `reports/sources/budget.md`. Proponi il piano in plan mode.

## Obiettivo

Da ora in poi ogni informazione pre-partita viene catturata nel momento in cui esiste, con `mode = 'live'` e `knowledge_basis = 'captured'` o `'publication'`.

## Blocchi di lavoro

1. **Calendario.** Import del calendario (API-Football) come osservazioni `match.kickoff_at` e `match.status`; ogni cambio di orario è una nuova versione.
2. **Slot.** Da ogni orario generare `ops.expected_slot`: quote a T-24h, T-1h e chiusura; formazioni a T-60 e T-30 minuti; meteo a T-6h e T-1h. Un cambio di orario annulla e rigenera gli slot.
3. **Sensori Dagster.** Un sensore ogni minuto lancia i job degli slot scaduti; idempotenza per `(job_name, subject_key, scheduled_for)`.
4. **Quote.** Snapshot della Serie A (1X2, Over/Under 2.5) da The Odds API entro il budget; Goal/NoGoal da OddsPapi se la fase 1 l'ha approvato.
5. **Formazioni e indisponibili.** Da API-Football, con `known_period` dal momento della cattura.
6. **Notizie.** Lettura periodica dei feed RSS approvati; solo `ops.news_item`, nessuna estrazione ancora.
7. **Sorveglianza.** Controllo 9 (slot saltati) come asset check e come workflow orario su GitHub Actions; notifica Telegram (bot gratuito) a Nico.
8. **Agente `quality-triage`.** Riassume ogni mattina i controlli falliti della notte. Output tipizzato, chiamate in `ops.llm_call`.

## Vincoli

- Mai sovrascrivere: ogni snapshot è una riga nuova.
- Il budget di chiamate è un limite rigido nel codice, non una speranza.

## Revisioni

- `leakage-auditor` sulla gestione dei tempi (fuso orario, cambi di orario, formazioni catturate dopo il calcio d'inizio).

## Fatto quando

Criteri della Fase 3 in `docs/roadmap.md` spuntati.
