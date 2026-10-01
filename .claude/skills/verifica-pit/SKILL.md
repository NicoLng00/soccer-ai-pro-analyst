---
name: verifica-pit
description: Checklist point-in-time per individuare leakage in feature, derivazioni, snapshot, modelli, adapter e agenti. Usala prima di chiudere qualsiasi modifica che produce o legge dati usati da un modello.
user-invocable: true
---

# Checklist point-in-time

Per ogni modifica, rispondi a ogni domanda con "sì", "no" o "non pertinente", citando file e riga.

## Letture

1. Ogni lettura di fatti o osservazioni passa da `obs.as_of_*` o filtra `known_period @> as_of`?
2. Le finestre temporali si chiudono strettamente prima dell'evento da prevedere?
3. Gli aggregati di stagione (medie, classifiche, forme) sono calcolati fino ad `as_of` e non sull'intera stagione?
4. Normalizzazioni, encoder e scaler sono stimati solo su dati di addestramento precedenti al periodo di test?

## Tempo

5. Tutti gli orari sono UTC con timezone esplicita? Il fuso della fonte è dichiarato nel parser?
6. Un cambio di orario della partita genera una nuova versione e non sovrascrive?
7. Le formazioni catturate dopo il calcio d'inizio sono scartate o marcate?

## Backfill

8. Le variabili con `backfill_policy: excluded` sono assenti dalle feature addestrate sullo storico?
9. Le regole di conoscibilità (`knowledge_basis = 'rule'`) corrispondono a `knowable_rule` nel registro?
10. Le quote `closing` non sono mai feature per previsioni a T-24h o T-1h?

## Agenti

11. Il `known_period` di un fatto estratto da una notizia parte dall'orario di pubblicazione, non da quello di elaborazione?
12. L'output di un agente entra solo come osservazione sperimentale, mai direttamente in una previsione?

## Test

13. Esiste un test `pit` che fallirebbe se il punto più rischioso di questa modifica usasse il futuro?

Ogni "no" è un problema da correggere prima del commit.
