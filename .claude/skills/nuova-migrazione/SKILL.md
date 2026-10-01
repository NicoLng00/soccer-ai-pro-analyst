---
name: nuova-migrazione
description: Regole per creare una migrazione Alembic in SoccerAnalystPro. Usala ogni volta che serve cambiare lo schema del database.
paths: "migrations/**, src/soccer_analyst/db/**"
---

# Nuova migrazione

## Prima

1. Aggiorna `docs/data-model.md` con la modifica. La specifica viene prima del codice.
2. Controlla che la modifica rispetti i principi di `CLAUDE.md`: niente null in `ref`, `obs`, `mkt`, `ml`; colonne di provenienza e conoscenza sulle tabelle di fatti; `CHECK` sugli insiemi chiusi; vincoli di esclusione con `known_period &&` dove servono.

## Scrittura

- `uv run alembic revision -m "<descrizione breve in inglese>"`. Autogenerate solo come bozza, da rileggere riga per riga.
- Mai modificare una migrazione già committata: un hook lo impedisce. Si crea una migrazione nuova.
- SQL esplicito (`op.execute`) per vincoli di esclusione, trigger, funzioni, RLS e grant.
- Una nuova tabella di fatti include sempre: `known_period tstzrange NOT NULL`, `knowledge_basis`, `mode`, `source_id`, `origin_kind`, `origin_id`, `recorded_at`, indice GiST su `known_period`, policy RLS per `sap_live` e `sap_backfill`, grant a `sap_readonly`.
- `downgrade` completo e simmetrico.

## Verifica

```bash
uv run pytest -m integration -k "migration or schema" -q
```

Il test di integrazione applica `upgrade head`, poi `downgrade base`, poi di nuovo `upgrade head` su un Postgres 18 pulito, e verifica che non esistano colonne nullable negli schemi di fatti.

Poi revisione dello `schema-guardian`.
