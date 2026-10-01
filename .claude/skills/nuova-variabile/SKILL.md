---
name: nuova-variabile
description: Procedura per aggiungere o modificare una variabile del registro (voce in registry/variables.yaml, derivazione, test point-in-time, documentazione). Usala ogni volta che si tocca registry/variables.yaml o src/soccer_analyst/features/.
argument-hint: "[codice-variabile]"
arguments: codice
paths: "registry/variables.yaml, src/soccer_analyst/features/**"
---

# Nuova variabile: `$codice`

## 1. Voce del registro

Aggiungi o modifica la voce in `registry/variables.yaml` con tutti i campi. Regole:

- `code` nel formato `<entità>.<nome>` (vedi `docs/variables.md`).
- `status: experimental`. Solo `ml-evaluator` può giustificare il passaggio ad `active`.
- `knowable_rule` e `backfill_policy` pensati per primi: quando è conoscibile questo valore nel mondo reale? Esiste una regola affidabile per ricostruirlo nel passato? Se no, `backfill_policy: excluded`.
- Se cambia la definizione di una variabile esistente, incrementa `version`.

## 2. Derivazione (se `kind` è `derived` o `model`)

- Funzione pura in `src/soccer_analyst/features/` con firma che riceve un `as_of: datetime` e legge solo tramite `obs.as_of_*` o query che filtrano `known_period @> as_of`.
- Esecuzione registrata in `ops.derivation_run`; le righe prodotte hanno `origin_kind = 'derivation'`.
- Finestre temporali: l'estremo superiore è strettamente prima dell'evento da prevedere.

## 3. Test point-in-time (obbligatori, marcati `pit`)

- Un dato conoscibile dopo `as_of` non cambia il valore calcolato ad `as_of`.
- Una correzione successiva non cambia il valore calcolato prima della correzione.
- Caso limite: dato conoscibile esattamente all'istante `as_of`.

## 4. Documentazione

- Se la variabile usa una fonte nuova, aggiorna `docs/sources.md`.
- Nessuna modifica al catalogo del documento di progetto: se ne occupa Nico.

## 5. Verifica

```bash
uv run sap registry sync --dry-run
uv run pytest -m pit -q
```

Poi revisione del `leakage-auditor`. Per l'attivazione, report di valutazione e revisione dell'`ml-evaluator`.
