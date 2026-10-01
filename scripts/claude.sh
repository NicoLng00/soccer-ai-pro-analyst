#!/usr/bin/env bash
# Avvia Claude Code con il minimo indispensabile dell'ambiente: SAP_ENV e
# SAP_DB_URL_READONLY (per il server MCP postgres-ro di .mcp.json). Nessun altro segreto
# entra nella sessione: le variabili definite nel file e ogni SAP_* già esportata nella
# shell vengono tolte. In sviluppo i processi Python leggono .env da soli (core/config.py).
#
# Il file non viene eseguito: si leggono solo le due righe che servono.
#
# Uso: ./scripts/claude.sh [argomenti di claude]
# Per i test: SAP_ENV_FILE sceglie il file, SAP_CLAUDE_BIN il programma da avviare.
set -euo pipefail
cd "$(dirname "$0")/.."

env_file="${SAP_ENV_FILE:-.env}"
claude_bin="${SAP_CLAUDE_BIN:-claude}"
if [[ ! -f "$env_file" ]]; then
  echo "Manca $env_file: esegui 'cp env.example .env' e cambia le password." >&2
  exit 1
fi

# Lettore condiviso con dev-up.sh: BOM, CRLF e ultima riga senza a capo gestiti.
# shellcheck source=lib/dotenv.sh
source scripts/lib/dotenv.sh

sap_env="$(dotenv_get "$env_file" SAP_ENV)"
readonly_url="$(dotenv_get "$env_file" SAP_DB_URL_READONLY)"
if [[ -z "$sap_env" || -z "$readonly_url" ]]; then
  echo "$env_file deve definire SAP_ENV e SAP_DB_URL_READONLY." >&2
  exit 1
fi

# Ogni chiave del file e ogni SAP_* ereditata esce dalla sessione.
while IFS= read -r name; do
  unset "$name" 2>/dev/null || true
done < <(
  {
    dotenv_keys "$env_file"
    compgen -e | grep -E '^SAP_' || true
  } | sort -u
)

export SAP_ENV="$sap_env"
export SAP_DB_URL_READONLY="$readonly_url"
exec "$claude_bin" "$@"
