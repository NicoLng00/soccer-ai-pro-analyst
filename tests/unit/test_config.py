import os
import traceback
from pathlib import Path

import pytest
from pydantic import SecretStr

from soccer_analyst.core.config import (
    DbRole,
    Environment,
    load_app_settings,
    load_database_settings,
    load_raw_store_settings,
    to_sqlalchemy_url,
)
from soccer_analyst.core.errors import ConfigError

PASSWORD = "s3gr3t@/:%x"  # noqa: S105 - fake value, needs URL encoding
ENCODED = "s3gr3t%40%2F%3A%25x"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for name in list(os.environ):
        if name.upper().startswith("SAP_"):
            monkeypatch.delenv(name)
    # Every test runs in an empty folder: the real .env of the repository is never read.
    monkeypatch.chdir(tmp_path)


def write_dotenv(folder: Path, **values: str) -> None:
    lines = [f"{key}={value}" for key, value in values.items()]
    (folder / ".env").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_dotenv_is_read_in_development(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    write_dotenv(tmp_path, SAP_DB_URL_LIVE="postgresql://sap_live:from-file@localhost/sap")
    monkeypatch.setenv("SAP_ENV", "dev")
    assert load_database_settings().sqlalchemy_url("live").password == "from-file"  # noqa: S105 - fake value


@pytest.mark.parametrize("env", [None, "ci", "prod"])
def test_dotenv_is_ignored_outside_development(
    env: str | None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    write_dotenv(tmp_path, SAP_DB_URL_LIVE="postgresql://sap_live:from-file@localhost/sap")
    if env is not None:
        monkeypatch.setenv("SAP_ENV", env)
    with pytest.raises(ConfigError, match="SAP_DB_URL_LIVE"):
        load_database_settings().libpq_url("live")


def test_dotenv_never_sets_the_environment(tmp_path: Path) -> None:
    # SAP_ENV decides whether the file is read, so it must come from the process environment.
    write_dotenv(tmp_path, SAP_ENV="dev")
    with pytest.raises(ConfigError, match="SAP_ENV"):
        load_app_settings()


def test_environment_variables_win_over_dotenv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    write_dotenv(tmp_path, SAP_RAW_BUCKET="from-file", SAP_RAW_ENDPOINT_URL="http://file:8333")
    monkeypatch.setenv("SAP_ENV", "dev")
    monkeypatch.setenv("SAP_RAW_BUCKET", "from-env")
    monkeypatch.setenv("SAP_RAW_ACCESS_KEY_ID", "k")
    monkeypatch.setenv("SAP_RAW_SECRET_ACCESS_KEY", "s")
    raw = load_raw_store_settings()
    assert (raw.bucket, raw.endpoint_url) == ("from-env", "http://file:8333")


def test_each_section_loads_only_its_own_keys(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    write_dotenv(
        tmp_path,
        SAP_DB_URL_OWNER="postgresql://sap_owner:owner-pw@localhost/sap",
        SAP_RAW_ENDPOINT_URL="http://127.0.0.1:8333",
        SAP_RAW_BUCKET="sap-raw",
        SAP_RAW_ACCESS_KEY_ID="k",
        SAP_RAW_SECRET_ACCESS_KEY="s",  # noqa: S106 - fake value
    )
    monkeypatch.setenv("SAP_ENV", "dev")
    raw = load_raw_store_settings()
    assert "owner-pw" not in str(raw.model_dump())
    assert set(type(raw).model_fields) == {
        "endpoint_url",
        "region",
        "bucket",
        "access_key_id",
        "secret_access_key",
    }


def test_environment_is_required() -> None:
    with pytest.raises(ConfigError, match="SAP_ENV"):
        load_app_settings()


def test_environment_rejects_unknown_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAP_ENV", "staging")
    with pytest.raises(ConfigError, match="SAP_ENV"):
        load_app_settings()


def test_environment_reads_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAP_ENV", "ci")
    assert load_app_settings().env is Environment.CI


def test_missing_role_url_names_the_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAP_DB_URL_OWNER", "postgresql://sap_owner:x@localhost:5432/sap")
    db = load_database_settings()
    assert db.sqlalchemy_url("owner").username == "sap_owner"
    with pytest.raises(ConfigError, match="SAP_DB_URL_LIVE"):
        db.sqlalchemy_url("live")


@pytest.mark.parametrize("role", ["owner", "live", "backfill", "registry", "readonly", "api", "useradmin"])
def test_every_role_reads_its_own_variable(role: DbRole, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(f"SAP_DB_URL_{role.upper()}", f"postgresql://sap_{role}:x@localhost:5432/sap")
    assert load_database_settings().sqlalchemy_url(role).username == f"sap_{role}"


def test_role_url_must_use_the_role_user(monkeypatch: pytest.MonkeyPatch) -> None:
    # An API configured with the owner's credentials would bypass least privilege.
    monkeypatch.setenv("SAP_DB_URL_API", "postgresql://sap_owner:x@localhost:5432/sap")
    with pytest.raises(ConfigError, match="SAP_DB_URL_API: l'utente deve essere sap_api"):
        load_database_settings().sqlalchemy_url("api")


def test_admin_url_accepts_the_superuser(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAP_ENV", "dev")
    monkeypatch.setenv("SAP_DB_URL_ADMIN", "postgresql://postgres:x@localhost:5432/sap")
    assert load_database_settings().sqlalchemy_url("admin").username == "postgres"


def test_admin_url_is_refused_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAP_ENV", "prod")
    monkeypatch.setenv("SAP_DB_URL_ADMIN", "postgresql://postgres:x@localhost:5432/sap")
    with pytest.raises(ConfigError, match="non si usa in produzione"):
        load_database_settings().libpq_url("admin")


@pytest.mark.parametrize("key", ["user", "USER", "password", "passfile", "service", "options"])
def test_query_cannot_override_credentials(key: str, monkeypatch: pytest.MonkeyPatch) -> None:
    # libpq and psycopg let ?user= win over the user in the authority part.
    monkeypatch.setenv("SAP_DB_URL_API", f"postgresql://sap_api:x@localhost:5432/sap?{key}=sap_owner")
    with pytest.raises(ConfigError, match="parametri non ammessi"):
        load_database_settings().libpq_url("api")


def _traceback_text(exc: BaseException) -> str:
    return "".join(traceback.format_exception(exc))


def test_config_errors_do_not_carry_other_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAP_RAW_ENDPOINT_URL", "http://127.0.0.1:8333")
    monkeypatch.setenv("SAP_RAW_BUCKET", "sap-raw")
    monkeypatch.setenv("SAP_RAW_ACCESS_KEY_ID", "FAKEKEYID-zz9")
    with pytest.raises(ConfigError) as info:
        load_raw_store_settings()
    assert info.value.__cause__ is None
    assert info.value.__context__ is None
    assert "FAKEKEYID-zz9" not in _traceback_text(info.value)


def test_malformed_url_error_does_not_carry_the_url() -> None:
    # The value goes through a variable: the traceback prints the source line of each frame.
    dsn = SecretStr("host=localhost password=FAKEPW-zz9")
    with pytest.raises(ConfigError) as info:
        to_sqlalchemy_url(dsn, "SAP_DB_URL_LIVE")
    assert info.value.__context__ is None
    assert "FAKEPW-zz9" not in _traceback_text(info.value)


def test_empty_role_url_counts_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAP_DB_URL_READONLY", "")
    with pytest.raises(ConfigError, match="SAP_DB_URL_READONLY"):
        load_database_settings().libpq_url("readonly")


def test_libpq_url_converts_to_psycopg_dialect(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "SAP_DB_URL_LIVE", f"postgresql://sap_live:{ENCODED}@db.example:6543/sap?sslmode=require"
    )
    url = load_database_settings().sqlalchemy_url("live")
    assert url.drivername == "postgresql+psycopg"
    assert url.username == "sap_live"
    assert url.password == PASSWORD
    assert (url.host, url.port, url.database) == ("db.example", 6543, "sap")
    assert url.query == {"sslmode": "require"}
    rendered = url.render_as_string(hide_password=False)
    assert rendered == f"postgresql+psycopg://sap_live:{ENCODED}@db.example:6543/sap?sslmode=require"


def test_postgres_scheme_alias_is_accepted() -> None:
    url = to_sqlalchemy_url(SecretStr("postgres://u:p@localhost/sap"), "SAP_DB_URL_OWNER")
    assert url.drivername == "postgresql+psycopg"


@pytest.mark.parametrize(
    "value",
    [
        "host=localhost dbname=sap user=u",
        "mysql://u:p@localhost/sap",
        "postgresql+psycopg://u:p@localhost/sap",
        "postgresql://localhost/sap",
        "postgresql://u:p@localhost",
    ],
)
def test_malformed_urls_are_rejected(value: str) -> None:
    with pytest.raises(ConfigError, match="SAP_DB_URL_OWNER"):
        to_sqlalchemy_url(SecretStr(value), "SAP_DB_URL_OWNER")


def test_passwords_never_appear_in_repr_or_str(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAP_DB_URL_OWNER", f"postgresql://sap_owner:{ENCODED}@localhost/sap")
    monkeypatch.setenv("SAP_RAW_ENDPOINT_URL", "http://127.0.0.1:8333")
    monkeypatch.setenv("SAP_RAW_BUCKET", "sap-raw")
    monkeypatch.setenv("SAP_RAW_ACCESS_KEY_ID", "key-id-value")
    monkeypatch.setenv("SAP_RAW_SECRET_ACCESS_KEY", "secret-key-value")
    db = load_database_settings()
    raw = load_raw_store_settings()
    shown = " ".join([repr(db), str(db), repr(raw), str(raw), repr(db.sqlalchemy_url("owner"))])
    for secret in (PASSWORD, ENCODED, "key-id-value", "secret-key-value"):
        assert secret not in shown


def test_raw_store_requires_every_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAP_RAW_ENDPOINT_URL", "http://127.0.0.1:8333")
    monkeypatch.setenv("SAP_RAW_BUCKET", "sap-raw")
    monkeypatch.setenv("SAP_RAW_ACCESS_KEY_ID", "key-id-value")
    with pytest.raises(ConfigError, match="SAP_RAW_SECRET_ACCESS_KEY"):
        load_raw_store_settings()


def test_raw_store_region_defaults_to_auto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAP_RAW_ENDPOINT_URL", "http://127.0.0.1:8333")
    monkeypatch.setenv("SAP_RAW_BUCKET", "sap-raw")
    monkeypatch.setenv("SAP_RAW_ACCESS_KEY_ID", "key-id-value")
    monkeypatch.setenv("SAP_RAW_SECRET_ACCESS_KEY", "secret-key-value")
    assert load_raw_store_settings().region == "auto"
