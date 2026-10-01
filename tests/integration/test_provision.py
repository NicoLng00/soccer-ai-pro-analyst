import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from soccer_analyst.core.config import DatabaseSettings, to_sqlalchemy_url
from soccer_analyst.db.provision import APP_ROLES, provision_roles

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def provisioned(db_settings: DatabaseSettings) -> list[str]:
    return provision_roles(db_settings)


def test_every_role_is_created(provisioned: list[str]) -> None:
    assert {f"create role sap_{role}" for role in APP_ROLES} <= set(provisioned)


def test_provisioning_is_idempotent(provisioned: list[str], db_settings: DatabaseSettings) -> None:
    again = provision_roles(db_settings)
    assert {f"alter role sap_{role}" for role in APP_ROLES} <= set(again)


@pytest.mark.parametrize("role", APP_ROLES)
def test_every_role_logs_in_with_its_password(
    provisioned: list[str], db_settings: DatabaseSettings, role: str
) -> None:
    with psycopg.connect(db_settings.libpq_url(role).get_secret_value()) as conn:
        user, tz = conn.execute("SELECT current_user, current_setting('TimeZone')").fetchone() or ("", "")
    assert (user, tz) == (f"sap_{role}", "UTC")


def test_database_belongs_to_owner_and_public_cannot_create(
    provisioned: list[str], db_settings: DatabaseSettings
) -> None:
    with psycopg.connect(db_settings.libpq_url("admin").get_secret_value()) as conn:
        owner = conn.execute(
            "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = current_database()"
        ).fetchone()
        public_create = conn.execute("SELECT has_schema_privilege('sap_live', 'public', 'CREATE')").fetchone()
        public_connect = conn.execute(
            "SELECT has_database_privilege('sap_live', current_database(), 'CONNECT')"
        ).fetchone()
    assert owner == ("sap_owner",)
    assert public_create == (False,)
    assert public_connect == (True,)


def test_passwords_never_reach_the_server_log(
    provisioned: list[str], db_settings: DatabaseSettings, postgres: PostgresContainer
) -> None:
    # The container runs with log_statement=all: only the session settings keep passwords out.
    with psycopg.connect(db_settings.libpq_url("admin").get_secret_value()) as conn:
        conn.execute("SELECT 'log-marker-provision'")
    stdout, stderr = postgres.get_logs()
    log = (stdout + stderr).decode("utf-8", errors="replace")
    assert "log-marker-provision" in log  # other sessions are logged: the check below means something
    for role in APP_ROLES:
        password = to_sqlalchemy_url(db_settings.libpq_url(role), role).password
        assert password
        assert password not in log
