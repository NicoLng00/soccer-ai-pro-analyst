# Lettore dei file d'ambiente (.env) per gli script bash. Si include con `source`.
#
# Il file non viene mai eseguito: ogni riga KEY=VALUE si interpreta come testo, con la stessa
# semantica di python-dotenv (usato da core/config.py) tranne le sequenze di escape tra
# virgolette doppie, così bash e Python vedono gli stessi valori. Gestisce BOM UTF-8 all'inizio, a capo CRLF, ultima riga senza a capo, prefisso
# `export`, virgolette singole o doppie, commenti e righe vuote. Con chiavi ripetute vince
# l'ultima occorrenza.

# Righe normalizzate: BOM e CR tolti, ultima riga letta anche senza a capo.
_dotenv_lines() {
  local line first=1
  while IFS= read -r line || [[ -n "$line" ]]; do
    if ((first)); then
      line="${line#$'\xef\xbb\xbf'}"
      first=0
    fi
    printf '%s\n' "${line%$'\r'}"
  done <"$1"
}

# Coppie "chiave<TAB>valore", una per assegnazione, nell'ordine del file.
_dotenv_pairs() {
  local line key value re='^[[:space:]]*(export[[:space:]]+)?([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*=[[:space:]]*(.*)$'
  while IFS= read -r line; do
    [[ "$line" =~ $re ]] || continue
    key="${BASH_REMATCH[2]}"
    value="${BASH_REMATCH[3]}"
    if [[ "$value" =~ ^\"(.*)\"[[:space:]]*(#.*)?$ || "$value" =~ ^\'(.*)\'[[:space:]]*(#.*)?$ ]]; then
      value="${BASH_REMATCH[1]}"
    else
      value="${value%%[[:space:]]#*}"
      value="${value%"${value##*[![:space:]]}"}"
    fi
    printf '%s\t%s\n' "$key" "$value"
  done < <(_dotenv_lines "$1")
}

# Chiavi definite nel file, una per riga, senza ripetizioni.
dotenv_keys() {
  _dotenv_pairs "$1" | cut -f1 | sort -u
}

# Valore di una chiave (ultima occorrenza); stringa vuota se assente.
dotenv_get() {
  local key value result=""
  while IFS=$'\t' read -r key value; do
    [[ "$key" == "$2" ]] && result="$value"
  done < <(_dotenv_pairs "$1")
  printf '%s' "$result"
}

# Esporta ogni chiave del file nell'ambiente della shell corrente, senza eseguire il file.
dotenv_export() {
  local key value
  while IFS=$'\t' read -r key value; do
    export "$key=$value"
  done < <(_dotenv_pairs "$1")
}

# Confronta il file con il modello: stampa solo nomi, mai valori. Esce con 1 se una chiave che
# nel modello ha un valore manca o è vuota nel file. Le chiavi ripetute sono un avviso.
dotenv_check() {
  local file="$1" template="$2" key value keys status=0
  keys="$(_dotenv_pairs "$file" | cut -f1)"
  while IFS= read -r key; do
    [[ -n "$key" ]] && echo "attenzione: $key compare più volte in $file (vale l'ultima)" >&2
  done < <(printf '%s\n' "$keys" | sort | uniq -d)
  while IFS=$'\t' read -r key value; do
    [[ -z "$value" ]] && continue
    if ! printf '%s\n' "$keys" | grep -qx "$key"; then
      echo "manca in $file: $key" >&2
      status=1
    elif [[ -z "$(dotenv_get "$file" "$key")" ]]; then
      echo "vuota in $file: $key" >&2
      status=1
    fi
  done < <(_dotenv_pairs "$template")
  return "$status"
}
