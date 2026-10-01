#!/usr/bin/env bash
# Avvia l'ambiente di sviluppo: Postgres 18 + SeaweedFS (S3), ruoli, bucket, migrazioni.
# Idempotente: si può rilanciare quando serve.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo "Manca .env: esegui 'uv run python scripts/init_env.py'." >&2
  exit 1
fi
# .env si legge come testo, non si esegue (BOM, CRLF e ultima riga senza a capo gestiti).
# shellcheck source=lib/dotenv.sh
source scripts/lib/dotenv.sh
if ! dotenv_check .env env.example; then
  echo "Correggi .env confrontandolo con env.example (sopra solo i nomi, mai i valori)." >&2
  exit 1
fi
dotenv_export .env

docker compose up -d --wait postgres
docker compose up -d s3

uv run python scripts/provision_roles.py
uv run python scripts/ensure_bucket.py

if [[ -f migrations/env.py ]]; then
  uv run alembic upgrade head
else
  echo "Nessuna migrazione ancora: lo schema si crea nella fase 0."
fi

echo "Pronto. Postgres su 127.0.0.1:5432, S3 su ${SAP_RAW_ENDPOINT_URL}."
