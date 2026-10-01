---
name: avvia-fase
description: Avvia una fase della roadmap caricando il suo prompt e proponendo un piano. Solo su richiesta esplicita di Nico.
disable-model-invocation: true
argument-hint: "[numero-fase]"
arguments: fase
---

## Stato del repository

!`git status --short | head -20`
!`git log --oneline -5`
!`grep -m1 "Fase corrente" docs/roadmap.md`

## Istruzioni

1. Leggi `docs/prompts/fase-$fase.md` per intero e i documenti che indica.
2. Controlla che i criteri di completamento della fase precedente in `docs/roadmap.md` siano spuntati. Se non lo sono, fermati e dillo a Nico.
3. Entra in plan mode e proponi il piano della fase diviso in blocchi. Per ogni blocco: obiettivo, file toccati, test che lo verificano, revisore da coinvolgere.
4. Aspetta l'approvazione prima di scrivere codice.
5. Crea un branch `fase-$fase/<nome-blocco>` per il primo blocco approvato.
