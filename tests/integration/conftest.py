"""Postgres in a throwaway container for the integration tests (testcontainers).

The image is the one in docker-compose.yml, so development, tests and CI run the same version.
Passwords are generated per session: nothing here is a real credential.
"""

import secrets
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml
from pydantic import SecretStr
from testcontainers.community.postgres import PostgresContainer

from soccer_analyst.core.config import DatabaseSettings
from soccer_analyst.db.provision import APP_ROLES

ROOT = Path(__file__).resolve().parents[2]


def compose_image(service: str) -> str:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    image: str = compose["services"][service]["image"]
    return image


@pytest.fixture(scope="session", autouse=True)
def ci_environment() -> Iterator[None]:
    # SAP_ENV=ci: the superuser URL is allowed and the developer's .env is never read.
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("SAP_ENV", "ci")
        yield


@pytest.fixture(scope="session")
def postgres() -> Iterator[PostgresContainer]:
    container = PostgresContainer(
        compose_image("postgres"),
        username="postgres",
        password=secrets.token_urlsafe(16),
        dbname="sap",
        driver=None,
    ).with_command("postgres -c timezone=UTC -c log_statement=all")
    with container:
        yield container


@pytest.fixture(scope="session")
def db_settings(postgres: PostgresContainer) -> DatabaseSettings:
    host = postgres.get_container_host_ip()
    port = postgres.get_exposed_port(5432)
    urls = {
        role: SecretStr(f"postgresql://sap_{role}:{secrets.token_urlsafe(16)}@{host}:{port}/sap")
        for role in APP_ROLES
    }
    urls["admin"] = SecretStr(f"postgresql://postgres:{postgres.password}@{host}:{port}/sap")
    return DatabaseSettings(**urls)
