# 0002 — Modello bitemporale con known_period

- Stato: Accettata
- Data: 2026-09-30

## Contesto

Il primo nemico dei modelli sportivi è il leakage: usare in una previsione un'informazione che a quell'istante non esisteva. Serve anche poter rigiocare ogni previsione passata.

## Decisione

Ogni fatto ha un tempo di validità e un `known_period tstzrange`. Il limite inferiore è l'istante in cui il fatto è diventato conoscibile nel mondo; il superiore resta aperto finché una versione successiva o una ritrattazione non lo chiude. È l'unica modifica ammessa sulle righe di fatti. `knowledge_basis` dichiara come è stato stabilito il limite inferiore (`captured`, `publication`, `rule`, `post_event`).

## Conseguenze

- La lettura all'istante T è `known_period @> T`, indicizzabile con GiST.
- I vincoli di esclusione impediscono due versioni sovrapposte dello stesso fatto.
- Nel backfill la conoscibilità è ricostruita da regole (`knowledge_basis = 'rule'`): le variabili senza regola affidabile sono escluse dalle feature pre-partita addestrate sullo storico.
- Serve l'estensione `btree_gist`.
