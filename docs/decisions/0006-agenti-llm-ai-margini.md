# 0006 — Agenti LLM solo ai margini

- Stato: Accettata
- Data: 2026-09-30

## Contesto

Servono estrazione di fatti dalle notizie, sentiment e report sugli errori del modello. Un LLM nel percorso della previsione romperebbe il determinismo e renderebbe impossibile rigiocare una previsione.

## Decisione

Gli agenti runtime producono osservazioni sperimentali o report, mai previsioni. Output tipizzati con Pydantic AI, ogni chiamata in `ops.llm_call`, golden set prima dell'attivazione, provider sostituibile (default Gemini Flash-Lite sul piano gratuito).

## Conseguenze

- Le previsioni restano riproducibili: le osservazioni prodotte dagli agenti sono dati come gli altri, con `known_period`.
- Il sistema "impara dagli errori" tramite proposte di variabili valutate, non tramite modifiche automatiche.
