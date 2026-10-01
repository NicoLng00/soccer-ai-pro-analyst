# Fase 1 — Test delle fonti

## Prima di iniziare

Leggi `docs/sources.md`, `registry/sources.yaml`, `registry/variables.yaml` e la sezione Fase 1 di `docs/roadmap.md`. Proponi il piano in plan mode.

## Obiettivo

Per ogni variabile del registro con `feasibility: to_test`, una decisione basata su dati reali: fonte scelta, fonte di riserva, oppure scarto motivato.

## Blocchi di lavoro

1. **Sonde.** Uno script per fonte in `scripts/probe/` (API-Football, The Odds API, OddsPapi, football-data.org, Understat, feed RSS). Ogni sonda salva i payload in `tests/fixtures/<fonte>/` (già anonimi: sono dati pubblici) e stampa copertura, limiti residui e latenza. Le chiavi arrivano da variabili d'ambiente, mai da file.
2. **Raggiungibilità dalla VM.** Esegui le sonde anche dalla VM Oracle (Understat blocca alcuni IP di cloud). Annota l'esito.
3. **Contratti.** `sources/<fonte>/contracts.py` con modelli Pydantic stretti (`extra='forbid'` dove il formato è stabile) e test che validano ogni fixture. Una risposta vuota o con struttura inattesa deve sollevare un errore esplicito.
4. **Budget delle chiamate.** Per ogni API, chiamate al mese previste nella fase 3 contro il limite gratuito, in `reports/sources/budget.md`.
5. **Rapporto di copertura.** `reports/sources/coverage.md`: una riga per variabile `to_test` con decisione ed evidenza. Aggiorna `feasibility` in `registry/variables.yaml` di conseguenza.
6. **Curatela.** Le voci in `curation/` con `verified: false` sono appunti da controllare. Per ognuna trova il comunicato ufficiale (Giudice sportivo, Corte federale d'appello, Collegio di garanzia, Lega), compila `evidence` e `known_from`, correggi date e punteggi se servono e porta `verified: true`. Scomponi `crowd_restrictions.yaml` in periodi omogenei e compila `venues.yaml` partendo da Wikidata. Le rivalità le conferma Nico: preparagli la lista, non decidere tu l'intensità.

## Vincoli

- Rispetta i limiti delle API: un contatore locale di chiamate per sonda, stop prima del limite.
- Nessuno scraping di siti che lo vietano. Per i feed RSS, solo titolo, link, orario e sommario del feed.
- I risultati della fase aggiornano `docs/sources.md`: la documentazione deve descrivere lo stato reale.

## Revisioni

- `source-adapter-engineer` può costruire i contratti; `data-quality-analyst` rilegge il rapporto di copertura.

## Fatto quando

Criteri della Fase 1 in `docs/roadmap.md` spuntati.
