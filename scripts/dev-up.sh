#!/usr/bin/env bash
# Avvia l'ambiente di sviluppo: Postgres 18 + SeaweedFS (S3), ruoli, bucket, migrazioni.
# Idempotente: si può rilanciare quando serve.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo "Manca .env: esegui 'cp .env.example .env' e cambia le password." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1091
source .env
set +a

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
