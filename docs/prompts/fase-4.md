# Fase 4 — Variabili derivate e baseline

## Prima di iniziare

Leggi `docs/variables.md`, `registry/variables.yaml`, la skill `nuova-variabile` e `docs/decisions/0002-modello-bitemporale.md`. Proponi il piano in plan mode.

## Obiettivo

Le variabili derivate deterministiche e un modello di riferimento onesto, contro cui misurare tutto il resto.

## Blocchi di lavoro

1. **Derivazioni.** Elo, classifica prima della partita (da risultati `official` e penalizzazioni), forma, rendimento casa e trasferta, riposo, km, partite negli ultimi 14 e 30 giorni, squalifiche e diffide dai cartellini con il regolamento della competizione, minuti dei giocatori. Ogni derivazione è una funzione pura su un input `as_of`, registrata in `ops.derivation_run`.
2. **Snapshot delle feature.** `features/build.py`: dato un `as_of` e un insieme di variabili, costruisce la matrice per le partite e la salva in `ml.feature_snapshot`.
3. **Baseline.** Dixon-Coles con pesatura temporale esponenziale e vantaggio del campo stimato per periodo (vedi "Regime, non errore" in `docs/data-quality.md`). Output: distribuzione dei gol, da cui 1X2, Goal/NoGoal, Over/Under 2.5.
4. **Valutazione.** Walk-forward per giornata: addestra fino alla giornata k, prevedi k+1. Metriche: log-loss, Brier, RPS, calibrazione (ECE e grafico), CLV contro la chiusura. Intervalli con bootstrap.
5. **Report.** `sap evaluate --model baseline --scope ITA-SA/2023-24,ITA-SA/2024-25` produce `reports/evaluation/<modello>-<data>.md`.

## Vincoli

- Nessun uso di statistiche di football-data con cambi di definizione non normalizzati (ADR 0005).
- Seed fissi; versioni in `ml.model_version`.

## Revisioni

- `leakage-auditor` su ogni derivazione e sulla costruzione degli snapshot.
- `ml-evaluator` sul protocollo di valutazione prima di leggere i numeri.

## Fatto quando

Criteri della Fase 4 in `docs/roadmap.md` spuntati.
