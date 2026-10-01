"""Env files in every byte layout an editor can produce, shared by the shell-reader tests."""

from pathlib import Path

BOM = "﻿"
# The first line is a key (a BOM would corrupt it) and the last line is a key (a missing final
# newline would drop it with a naive reader).
VALUES = {
    "SAP_DB_URL_OWNER": "postgresql://sap_owner:pw-owner@localhost:5432/sap",
    "SAP_ENV": "dev",
    "SAP_DB_URL_READONLY": "postgresql://sap_readonly:pw-ro@localhost:5432/sap",
    "SAP_DB_URL_REGISTRY": "postgresql://sap_registry:pw-reg@localhost:5432/sap",
}
LINES = [f"{key}={value}" for key, value in VALUES.items()]

CASES = {
    "lf": "\n".join(LINES) + "\n",
    "senza-a-capo-finale": "\n".join(LINES),
    "crlf": "\r\n".join(LINES) + "\r\n",
    "bom": BOM + "\n".join(LINES) + "\n",
    "bom-crlf-senza-a-capo-finale": BOM + "\r\n".join(LINES),
}


def write_case(folder: Path, case: str, name: str = "test.env") -> Path:
    path = folder / name
    path.write_bytes(CASES[case].encode("utf-8"))
    return path
