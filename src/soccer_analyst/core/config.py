"""Configuration from environment variables only: no .env parsing, no defaults for secrets.

Each concern has its own settings class, so a process asks only for what it uses: Alembic
needs SAP_DB_URL_OWNER and nothing else. A missing or malformed variable raises ConfigError
naming the variable; secrets are SecretStr and never appear in repr or str.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

from soccer_analyst.core.errors import ConfigError

DbRole = Literal["owner", "live", "backfill", "registry", "readonly", "api", "useradmin", "admin"]

LIBPQ_SCHEMES = {"postgresql", "postgres"}
SQLALCHEMY_DRIVER = "postgresql+psycopg"


class Environment(StrEnum):
    DEV = "dev"
    CI = "ci"
    PROD = "prod"


class AppSettings(BaseSettings):
    """SAP_ENV: where the code is running."""

    model_config = SettingsConfigDict(env_prefix="SAP_", extra="ignore", frozen=True)

    env: Environment


class DatabaseSettings(BaseSettings):
    """SAP_DB_URL_<ROLE>: one libpq URL per Postgres role.

    Every URL is optional at load time and required when used: `libpq_url("live")` fails if
    SAP_DB_URL_LIVE is not set, so each process needs only its own role (the API container
    gets only SAP_DB_URL_API). The user in the URL must be the role's own user: a URL that
    points a low-privilege role at another user is a configuration error. `admin` (the
    container superuser) exists only in development and CI.
    """

    model_config = SettingsConfigDict(env_prefix="SAP_DB_URL_", extra="ignore", frozen=True)

    owner: SecretStr | None = None
    live: SecretStr | None = None
    backfill: SecretStr | None = None
    registry: SecretStr | None = None
    readonly: SecretStr | None = None
    api: SecretStr | None = None
    useradmin: SecretStr | None = None
    admin: SecretStr | None = None

    def libpq_url(self, role: DbRole) -> SecretStr:
        """The URL as written in the environment, for psycopg and pg tools."""
        variable = f"SAP_DB_URL_{role.upper()}"
        value: SecretStr | None = getattr(self, role)
        if value is None or not value.get_secret_value():
            msg = f"variabile mancante: {variable}"
            raise ConfigError(msg)
        if role != "admin":
            user = to_sqlalchemy_url(value, variable).username
            if user != f"sap_{role}":
                msg = f"{variable}: l'utente deve essere sap_{role}, trovato {user!r}"
                raise ConfigError(msg)
        return value

    def sqlalchemy_url(self, role: DbRole) -> URL:
        """The URL converted to the postgresql+psycopg dialect. URL hides the password in repr."""
        return to_sqlalchemy_url(self.libpq_url(role), f"SAP_DB_URL_{role.upper()}")


class RawStoreSettings(BaseSettings):
    """SAP_RAW_*: S3-compatible raw store (Cloudflare R2 in production, SeaweedFS in development)."""

    model_config = SettingsConfigDict(env_prefix="SAP_RAW_", extra="ignore", frozen=True)

    endpoint_url: str
    region: str = "auto"
    bucket: str
    access_key_id: SecretStr
    secret_access_key: SecretStr


def to_sqlalchemy_url(libpq_url: SecretStr, variable: str) -> URL:
    """Convert a libpq URI (postgresql://user:pass@host:port/db?opts) to SQLAlchemy psycopg form."""
    try:
        url = make_url(libpq_url.get_secret_value())
    except ArgumentError as exc:
        msg = f"{variable}: non è un URL libpq (postgresql://utente:password@host:porta/database)"
        raise ConfigError(msg) from exc
    if url.drivername not in LIBPQ_SCHEMES:
        msg = f"{variable}: schema {url.drivername!r} non ammesso, usa postgresql://"
        raise ConfigError(msg)
    if not url.username or not url.database:
        msg = f"{variable}: l'URL deve indicare utente e database"
        raise ConfigError(msg)
    return url.set(drivername=SQLALCHEMY_DRIVER)


def _missing_variables(exc: ValidationError, prefix: str) -> str:
    names = sorted(f"{prefix}{'_'.join(str(p) for p in err['loc']).upper()}" for err in exc.errors())
    return ", ".join(names)


def load_app_settings() -> AppSettings:
    try:
        return AppSettings()
    except ValidationError as exc:
        msg = f"variabili mancanti o non valide: {_missing_variables(exc, 'SAP_')}"
        raise ConfigError(msg) from exc


def load_database_settings() -> DatabaseSettings:
    return DatabaseSettings()


def load_raw_store_settings() -> RawStoreSettings:
    try:
        return RawStoreSettings()
    except ValidationError as exc:
        msg = f"variabili mancanti o non valide: {_missing_variables(exc, 'SAP_RAW_')}"
        raise ConfigError(msg) from exc
