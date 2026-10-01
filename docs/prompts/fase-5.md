# Fase 5 — Modello completo e ciclo di apprendimento

## Prima di iniziare

Leggi `docs/agents.md`, `docs/decisions/0006-agenti-llm-ai-margini.md`, `docs/variables.md` e l'ultimo report della baseline. Proponi il piano in plan mode.

## Obiettivo

Il modello completo, le previsioni live salvate prima del fischio e il ciclo che trasforma gli errori in ipotesi valutate.

## Blocchi di lavoro

1. **Sotto-modelli.** Profilo dell'allenatore al netto della rosa (con shrinkage), forza offensiva e difensiva da xG, rischio infortunio, impatto del giocatore. Ognuno produce variabili `kind: model` con la propria valutazione.
2. **Modello finale.** Gradient boosting (LightGBM) sulle feature attive, con la baseline Dixon-Coles come feature o come prior; calibrazione isotonica o di Platt valutata a parte. Esperimenti tracciati in MLflow.
3. **Previsioni live.** A T-24h e T-1h: snapshot, previsione, probabilità, quota equa, edge. Il trigger rifiuta previsioni dopo il calcio d'inizio.
4. **Agenti runtime** (Pydantic AI, provider da configurazione):
   - `news-extractor` con golden set di almeno 200 titoli etichettati a mano in `tests/golden/news-extractor/`;
   - `press-sentiment`;
   - `matchday-reviewer`: passo deterministico, poi report e proposte in `ml.variable_proposal`.
5. **Report settimanale.** Calibrazione e CLV delle ultime settimane, confronto con la baseline, stato delle proposte di variabili.

## Vincoli

- Nessun LLM nel percorso della previsione (ADR 0006).
- Una variabile passa ad `active` solo con il report di `ml-evaluator`.

## Revisioni

- `ml-evaluator` su ogni modello e ogni attivazione.
- `leakage-auditor` sugli agenti: l'orario di pubblicazione di una notizia è il suo `known_period`, mai l'orario di elaborazione se è precedente.

## Fatto quando

Criteri della Fase 5 in `docs/roadmap.md` spuntati.
