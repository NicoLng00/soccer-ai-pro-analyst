"""Create or update the Postgres roles from the SAP_DB_URL_* variables (development and CI only).

Runs as the container superuser (SAP_DB_URL_ADMIN, refused in production by core.config).
Idempotent: roles that exist get their password reset, nothing else changes. Schemas, grants,
RLS and default privileges are created by the Alembic migrations, which run as sap_owner.
"""

from __future__ import annotations

from typing import get_args

import psycopg
from psycopg import sql

from soccer_analyst.core.config import DatabaseSettings, DbRole, to_sqlalchemy_url
from soccer_analyst.core.errors import ConfigError

# Every role except the superuser, which already exists in the container.
APP_ROLES: tuple[DbRole, ...] = tuple(role for role in get_args(DbRole) if role != "admin")


def role_passwords(db: DatabaseSettings) -> dict[str, str]:
    """sap_<role> -> password, from the URLs; core.config already checks user and query."""
    passwords = {}
    for role in APP_ROLES:
        variable = f"SAP_DB_URL_{role.upper()}"
        password = to_sqlalchemy_url(db.libpq_url(role), variable).password
        if not password:
            msg = f"{variable}: manca la password nell'URL"
            raise ConfigError(msg)
        passwords[f"sap_{role}"] = password
    return passwords


def provision_roles(db: DatabaseSettings) -> list[str]:
    """Create or update every application role; return what was done, one line per action."""
    passwords = role_passwords(db)
    done = []
    with psycopg.connect(db.libpq_url("admin").get_secret_value(), autocommit=True) as conn:
        # CREATE/ALTER ROLE ... PASSWORD carries the password in clear: keep it out of the server log.
        conn.execute("SET log_statement = 'none'")
        conn.execute("SET log_min_duration_statement = -1")
        conn.execute("SET log_min_error_statement = 'panic'")
        for role, password in passwords.items():
            exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
            verb = "ALTER" if exists else "CREATE"
            conn.execute(
                sql.SQL("{} ROLE {} LOGIN PASSWORD {}").format(
                    sql.SQL(verb), sql.Identifier(role), sql.Literal(password)
                )
            )
            conn.execute(sql.SQL("ALTER ROLE {} SET timezone = 'UTC'").format(sql.Identifier(role)))
            done.append(f"{verb.lower()} role {role}")

        dbname = conn.info.dbname
        database = sql.Identifier(dbname)
        others = sql.SQL(", ").join(sql.Identifier(r) for r in passwords if r != "sap_owner")
        conn.execute(sql.SQL("ALTER DATABASE {} OWNER TO sap_owner").format(database))
        conn.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(database))
        conn.execute(sql.SQL("GRANT CONNECT, TEMPORARY ON DATABASE {} TO {}").format(database, others))
        conn.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        done.append(f"database {dbname}: owner sap_owner, connect per gli altri ruoli")
    return done
