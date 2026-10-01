# Registro delle variabili

La fonte di verità è `registry/variables.yaml`. Questo file spiega le regole; l'elenco sta nel YAML.

## Ciclo di vita

1. **Proposta.** Una variabile nasce da un'idea di Nico, da un'ipotesi dell'agente di revisione (`ml.variable_proposal`) o da un'analisi. Si aggiunge al YAML con `status: experimental`.
2. **Implementazione.** Adapter o derivazione, test point-in-time, riga in `docs/sources.md` se usa una fonte nuova. Procedura: skill `nuova-variabile`.
3. **Valutazione.** Si confronta il modello con e senza la variabile con validazione temporale (walk-forward) su almeno due stagioni mai viste. Criterio: miglioramento del log-loss oltre il rumore stimato con bootstrap, e nessun peggioramento della calibrazione.
4. **Attivazione.** `experimental` → `active` con riga in `obs.variable_status_log` che punta al report di valutazione.
5. **Dismissione.** `active` → `retired` se smette di aiutare o se la fonte si rompe. Le osservazioni restano.

Nessuna variabile si aggiunge per spiegare una singola partita.

## Campi che contano di più

- **`knowable_rule`** stabilisce quando il valore è conoscibile. È ciò che protegge dal leakage.
- **`backfill_policy`**:
  - `allowed`: la conoscibilità storica è certa (es. un risultato è noto a fine partita).
  - `rule`: nel backfill il limite inferiore di `known_period` si ricostruisce con `knowable_rule` e `knowledge_basis = 'rule'`.
  - `excluded`: nel backfill non esiste una ricostruzione affidabile (es. notizie di infortunio): la variabile non entra nelle feature pre-partita addestrate sullo storico. Si addestra solo sui dati live.
- **`temporal_kind`** decide come `obs.as_of_*` sceglie la riga (vedi `docs/data-model.md`).

## Relazione con il catalogo del documento di progetto

Il catalogo su claude.ai ha una riga per concetto (44 righe). Nel YAML un concetto può diventare più codici: "Punti, posizione e differenza reti" diventa tre variabili numeriche. I fatti strutturati (risultati, formazioni, trasferimenti, mandati, quote) vivono in tabelle `ref` e `mkt`, e nel registro compaiono solo le variabili che ne derivano.

## Convenzioni per i codici

`<entità>.<nome>` in snake_case inglese: `team.elo`, `match_team.rest_days`, `person.xg_per90`. L'entità nel codice coincide con `entity_kind`, salvo `coach.*` che usa `entity_kind: person`.
