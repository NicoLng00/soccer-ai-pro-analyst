# 0007 — Hosting gratuito: VM Oracle, R2, GitHub Actions

- Stato: Accettata; la scelta tra VM e Neon resta da confermare
- Data: 2026-09-30

## Contesto

Vincolo principale: solo risorse gratuite, verificate e misurate. Vercel Hobby è solo per uso non commerciale e ha cron giornalieri.

## Decisione

- VM Arm Oracle Always Free (2 OCPU, 12 GB, 200 GB) per Postgres, Dagster e codice.
- Cloudflare R2 (10 GB gratuiti, egress gratuito) per payload grezzi e backup.
- GitHub Actions per CI e sorveglianza oraria.
- Alternativa se la VM non è disponibile: Neon (0,5 GB) per il core e i dati live, storico pesante in Parquet su R2.

## Conseguenze

- Oracle può recuperare una VM inattiva: cache di Postgres dimensionata per superare le soglie, backup notturni, installazione riproducibile da script.
- Nei repository pubblici GitHub disattiva i workflow programmati dopo 60 giorni senza attività: il repository resta attivo con i commit del lavoro normale; il controllo orario lo segnala se succede.
