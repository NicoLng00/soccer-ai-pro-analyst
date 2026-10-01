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

# Valore di una chiave: ultima occorrenza, "export" ammesso, CR finale e virgolette esterne tolti.
value_of() {
  local line
  line="$(grep -E "^[[:space:]]*(export[[:space:]]+)?$1=" "$env_file" | tail -n 1 || true)"
  line="${line#*=}"
  line="${line%$'\r'}"
  if [[ "$line" =~ ^\"(.*)\"$ || "$line" =~ ^\'(.*)\'$ ]]; then
    line="${BASH_REMATCH[1]}"
  fi
  printf '%s' "$line"
}

sap_env="$(value_of SAP_ENV)"
readonly_url="$(value_of SAP_DB_URL_READONLY)"
if [[ -z "$sap_env" || -z "$readonly_url" ]]; then
  echo "$env_file deve definire SAP_ENV e SAP_DB_URL_READONLY." >&2
  exit 1
fi

# Ogni chiave del file e ogni SAP_* ereditata esce dalla sessione.
while IFS= read -r name; do
  unset "$name" 2>/dev/null || true
done < <(
  {
    grep -oE '^[[:space:]]*(export[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*=' "$env_file" \
      | sed -E 's/^[[:space:]]*(export[[:space:]]+)?//; s/=$//' || true
    compgen -e | grep -E '^SAP_' || true
  } | sort -u
)

export SAP_ENV="$sap_env"
export SAP_DB_URL_READONLY="$readonly_url"
exec "$claude_bin" "$@"
