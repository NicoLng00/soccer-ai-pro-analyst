"""Create or update the database roles from the SAP_DB_URL_* variables.

Runs as the container superuser (SAP_DB_URL_ADMIN) in development and CI only.
Idempotent: roles that exist get their password reset, nothing else changes.
Schemas, grants, RLS and default privileges are created by the Alembic migrations,
which run as sap_owner.
"""

from __future__ import annotations

import os
import sys
from urllib.parse import unquote, urlsplit

import psycopg
from psycopg import sql

ROLES = {
    "SAP_DB_URL_OWNER": "sap_owner",
    "SAP_DB_URL_LIVE": "sap_live",
    "SAP_DB_URL_BACKFILL": "sap_backfill",
    "SAP_DB_URL_READONLY": "sap_readonly",
    "SAP_DB_URL_API": "sap_api",
    "SAP_DB_URL_USERADMIN": "sap_useradmin",
}


def env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        sys.exit(f"Variabile mancante: {name}")
    return value


def password_for(var: str, role: str) -> str:
    parts = urlsplit(env(var))
    if parts.username != role:
        sys.exit(f"{var}: l'utente dell'URL deve essere {role}, trovato {parts.username!r}")
    if not parts.password:
        sys.exit(f"{var}: manca la password nell'URL")
    return unquote(parts.password)


def main() -> None:
    admin_url = env("SAP_DB_URL_ADMIN")
    passwords = {role: password_for(var, role) for var, role in ROLES.items()}

    with psycopg.connect(admin_url, autocommit=True) as conn:
        dbname = conn.info.dbname
        for role, password in passwords.items():
            exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
            verb = "ALTER" if exists else "CREATE"
            conn.execute(
                sql.SQL("{} ROLE {} LOGIN PASSWORD {}").format(
                    sql.SQL(verb), sql.Identifier(role), sql.Literal(password)
                )
            )
            conn.execute(sql.SQL("ALTER ROLE {} SET timezone = 'UTC'").format(sql.Identifier(role)))
            print(f"{verb.lower()} role {role}")

        db = sql.Identifier(dbname)
        conn.execute(sql.SQL("ALTER DATABASE {} OWNER TO sap_owner").format(db))
        conn.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(db))
        conn.execute(
            sql.SQL(
                "GRANT CONNECT, TEMPORARY ON DATABASE {} "
                "TO sap_live, sap_backfill, sap_readonly, sap_api, sap_useradmin"
            ).format(db)
        )
        conn.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        print(f"database {dbname}: owner sap_owner, connect per gli altri ruoli")


if __name__ == "__main__":
    main()
