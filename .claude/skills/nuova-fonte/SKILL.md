---
name: nuova-fonte
description: Procedura per integrare o riparare l'adapter di una fonte dati (client, contratto Pydantic, parser, mapping delle entità, fixture, test, controlli di qualità). Usala ogni volta che si aggiunge o modifica codice in src/soccer_analyst/sources/.
argument-hint: "[codice-fonte]"
arguments: fonte
paths: "src/soccer_analyst/sources/**, tests/fixtures/**"
---

# Nuova fonte: `$fonte`

## 1. Specifica

- Leggi la voce di `$fonte` in `docs/sources.md` e in `registry/sources.yaml`. Se manca, scrivila prima: cosa copre, accesso, limiti, condizioni d'uso, difetti noti, conoscibilità.
- Elenca le variabili di `registry/variables.yaml` che la fonte alimenta. Una fonte senza variabili non entra (principio 6).

## 2. Struttura del pacchetto

```
src/soccer_analyst/sources/$fonte/
  __init__.py
  client.py      # scarica e salva nel raw store; nessuna trasformazione
  contracts.py   # modelli Pydantic del payload grezzo
  parser.py      # payload validato -> righe tipizzate (dataclass o Pydantic)
  mapping.py     # chiavi della fonte -> entità canoniche via ops.entity_map
tests/fixtures/$fonte/   # payload reali minimi
tests/unit/sources/test_$fonte.py
```

## 3. Client

- Solo `httpx` con timeout espliciti e retry con `tenacity` (backoff esponenziale, massimo tentativi configurato).
- Ogni risposta passa da `ingest.raw_store.put(...)`: payload su R2, riga in `ops.raw_ingest`, evento in `ops.fetch_log`.
- Contatore di chiamate e limite dalla configurazione. Superato il limite, errore esplicito.

## 4. Contratto prima del parser

- Modelli Pydantic stretti. Risposta vuota, campo mancante o tipo inatteso → `ContractViolation` con fonte, chiave della richiesta e percorso del campo.
- Nessun valore di ripiego: un dato assente non diventa zero né stringa vuota.
- Test: ogni fixture valida; almeno una fixture corrotta che deve fallire.

## 5. Parser

- Funzione pura: payload validato → righe. Nessun accesso al database.
- Ogni riga porta `valid_at`, limite inferiore di `known_period`, `knowledge_basis`, `mode` secondo `registry/variables.yaml` (`knowable_rule`, `backfill_policy`).
- Date e orari convertiti in UTC con il fuso della fonte dichiarato esplicitamente.

## 6. Mapping delle entità

- Ordine: chiave esatta già mappata, alias noti, fuzzy con soglia di confidenza.
- Sotto soglia: riga in `ops.entity_map_review` e stop per quell'entità. Mai creare un doppione.

## 7. Qualità

- Aggiungi i controlli di `docs/data-quality.md` pertinenti come asset check e in `quality/`.
- Aggiorna la sezione "Difetti noti" di `docs/sources.md` con ciò che scopri.

## 8. Verifica

```bash
uv run ruff check src tests && uv run mypy src
uv run pytest tests/unit/sources/test_$fonte.py -q
```

Poi chiedi la revisione del `leakage-auditor` sulle regole di conoscibilità.
