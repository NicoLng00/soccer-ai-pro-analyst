# 0001 — PostgreSQL con osservazioni tipizzate

- Stato: Accettata
- Data: 2026-09-30

## Contesto

I dati devono essere flessibili (nuove variabili senza migrazioni) ma con integrità tra giocatore, club e partita. È stato valutato MongoDB.

## Decisione

PostgreSQL come unico database. Le entità stabili stanno in tabelle `ref` con colonne tutte `NOT NULL`. Tutto ciò che può mancare o cambiare è un'osservazione in quattro tabelle tipizzate (`obs.obs_num`, `obs_cat`, `obs_bool`, `obs_json`), descritta da un registro versionato (`obs.variable`). Una variabile nuova è una riga del registro, non una migrazione.

## Conseguenze

- Join e vincoli referenziali tra entità restano possibili.
- Un dato mancante è una riga che non esiste, mai un null.
- Il riferimento all'entità nelle osservazioni è polimorfico: l'integrità la garantisce un trigger, non una foreign key.
- La matrice larga per i modelli si costruisce a richiesta con `obs.as_of_*`.
