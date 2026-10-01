---
name: nuovo-endpoint
description: Procedura per aggiungere o modificare un endpoint dell'API (route FastAPI, modelli, query, autorizzazione, limiti, test di sicurezza, schema OpenAPI). Usala ogni volta che si tocca src/soccer_analyst/api/.
argument-hint: "[metodo e percorso, es. GET /api/matches]"
paths: "src/soccer_analyst/api/**"
---

# Nuovo endpoint: $ARGUMENTS

## Prima

1. Controlla che l'endpoint sia previsto in `docs/frontend/README.md`. Se non c'è, aggiungilo lì con la motivazione prima di scrivere codice.
2. Decidi se legge o scrive. Le uniche scritture ammesse sono quelle di ADR 0008: sessioni, tentativi di accesso, audit, decisioni sulle proposte.

## Scrittura

- Router in `src/soccer_analyst/api/routes/<area>.py`. Dipendenza `require_admin` sempre, salvo i tre endpoint pubblici di `docs/security.md`.
- Modelli Pydantic di richiesta e risposta con `extra="forbid"`; limiti espliciti su ogni campo (`Field(ge=..., le=..., max_length=...)`), date con timezone, intervalli al massimo di una stagione, pagine al massimo di 200 righe.
- Query in `src/soccer_analyst/db/` con SQLAlchemy Core e parametri; mai stringhe composte con l'input.
- Il modello di risposta elenca i campi da restituire: mai una riga del database passata così com'è.
- Errori con i gestori comuni: codice, messaggio breve, nessun dettaglio interno.
- Se scrive: controllo di `Origin`, riga in `app.audit_log` con `actor`, `action`, `target`.
- Se mostra variabili di una previsione: lettura point-in-time all'istante della previsione (skill `verifica-pit`).

## Test obbligatori

In `tests/api/test_<area>.py`:

- 401 senza sessione, con sessione scaduta, con sessione revocata, con sessione senza secondo fattore;
- 422 per ogni parametro fuori limite;
- caso felice con dati di prova, controllando che la risposta non contenga campi non previsti;
- se scrive: 403 con `Origin` estraneo e riga di audit presente.

Poi:

```bash
uv run pytest -q tests/api -k "<area> or routes"
uv run pytest -q -m "not integration" -k schemathesis
```

Il test che enumera le route deve passare senza toccare la lista pubblica.

## Dopo

Revisione del `security-reviewer`.
