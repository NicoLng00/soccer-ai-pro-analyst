"""scripts/init_env.py: .env from env.example with random passwords, never printed."""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import dotenv_values
from pydantic import SecretStr

from soccer_analyst.core.config import to_sqlalchemy_url

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "init_env.py"
TEMPLATE = ROOT / "env.example"
BASH = shutil.which("bash")
PLACEHOLDER = re.compile(r"\bcambia-[a-z0-9-]+\b")


def run(output: Path, *extra: str, template: Path = TEMPLATE) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), "--template", str(template), "--output", str(output), *extra],
        capture_output=True,
        encoding="utf-8",
        # Through a pipe Windows would encode the messages (già) in the ANSI code page.
        env=dict(os.environ, PYTHONUTF8="1"),
        check=False,
    )


@pytest.fixture
def created(tmp_path: Path) -> tuple[Path, subprocess.CompletedProcess[str]]:
    output = tmp_path / ".env"
    result = run(output)
    assert result.returncode == 0, result.stderr
    return output, result


def test_every_placeholder_is_replaced(created: tuple[Path, subprocess.CompletedProcess[str]]) -> None:
    output, _ = created
    assert PLACEHOLDER.search(TEMPLATE.read_text(encoding="utf-8"))
    assert not PLACEHOLDER.search(output.read_text(encoding="utf-8"))


def test_same_placeholder_same_password(created: tuple[Path, subprocess.CompletedProcess[str]]) -> None:
    values = dotenv_values(created[0])
    admin = to_sqlalchemy_url(SecretStr(values["SAP_DB_URL_ADMIN"] or ""), "SAP_DB_URL_ADMIN")
    assert admin.password == values["POSTGRES_PASSWORD"]


def test_different_placeholders_different_passwords(
    created: tuple[Path, subprocess.CompletedProcess[str]],
) -> None:
    values = dotenv_values(created[0])
    roles = ["OWNER", "LIVE", "BACKFILL", "REGISTRY", "READONLY", "API", "USERADMIN"]
    passwords = [to_sqlalchemy_url(SecretStr(values[f"SAP_DB_URL_{r}"] or ""), r).password for r in roles]
    passwords += [values["POSTGRES_PASSWORD"], values["SAP_RAW_SECRET_ACCESS_KEY"]]
    assert len(set(passwords)) == len(passwords)
    assert all(p and len(p) >= 40 and re.fullmatch(r"[A-Za-z0-9_-]+", p) for p in passwords)


def test_everything_else_is_kept(created: tuple[Path, subprocess.CompletedProcess[str]]) -> None:
    template_lines = TEMPLATE.read_text(encoding="utf-8").splitlines()
    output_lines = created[0].read_text(encoding="utf-8").splitlines()
    assert len(output_lines) == len(template_lines)
    for before, after in zip(template_lines, output_lines, strict=True):
        if not PLACEHOLDER.search(before):
            assert after == before
    values = dotenv_values(created[0])
    assert values["SAP_ENV"] == "dev"
    assert values["SAP_RAW_ACCESS_KEY_ID"] == "sap-dev"
    assert values["SAP_GEMINI_API_KEY"] == ""


def test_users_still_match_their_roles(created: tuple[Path, subprocess.CompletedProcess[str]]) -> None:
    values = dotenv_values(created[0])
    for key, value in values.items():
        if key.startswith("SAP_DB_URL_") and key != "SAP_DB_URL_ADMIN":
            role = key.removeprefix("SAP_DB_URL_").lower()
            assert to_sqlalchemy_url(SecretStr(value or ""), key).username == f"sap_{role}"


def test_no_password_is_printed(created: tuple[Path, subprocess.CompletedProcess[str]]) -> None:
    output, result = created
    printed = result.stdout + result.stderr
    assert "password generate" in printed
    secrets = [v for v in dotenv_values(output).values() if v and len(v) >= 40]
    assert secrets
    for value in secrets:
        assert value not in printed
        password = value.rsplit(":", 1)[-1].split("@", 1)[0]
        assert password not in printed


def test_output_is_utf8_lf_without_bom(created: tuple[Path, subprocess.CompletedProcess[str]]) -> None:
    data = created[0].read_bytes()
    assert not data.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" not in data
    assert data.endswith(b"\n")


@pytest.mark.skipif(os.name != "posix", reason="permessi POSIX")
def test_output_is_private(created: tuple[Path, subprocess.CompletedProcess[str]]) -> None:
    assert created[0].stat().st_mode & 0o777 == 0o600


@pytest.mark.skipif(BASH is None, reason="serve bash")
def test_dev_up_accepts_the_result(created: tuple[Path, subprocess.CompletedProcess[str]]) -> None:
    lib = ROOT / "scripts" / "lib" / "dotenv.sh"
    result = subprocess.run(  # noqa: S603
        [str(BASH), "-c", 'source "$0"; dotenv_check "$1" "$2"', str(lib), str(created[0]), str(TEMPLATE)],
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_existing_env_is_kept_without_force(tmp_path: Path) -> None:
    output = tmp_path / ".env"
    output.write_text("SAP_ENV=dev\n", encoding="utf-8")
    result = run(output)
    assert result.returncode == 1
    assert "--force" in result.stderr
    assert output.read_text(encoding="utf-8") == "SAP_ENV=dev\n"


def test_force_replaces_with_a_backup(tmp_path: Path) -> None:
    output = tmp_path / ".env"
    output.write_text("SAP_ENV=dev\nPOSTGRES_PASSWORD=vecchia\n", encoding="utf-8")
    result = run(output, "--force")
    assert result.returncode == 0, result.stderr
    backups = list(tmp_path.glob(".env.bak-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "SAP_ENV=dev\nPOSTGRES_PASSWORD=vecchia\n"
    assert backups[0].name in result.stdout
    assert dotenv_values(output)["POSTGRES_PASSWORD"] != "vecchia"  # noqa: S105 - fake value


def test_each_run_draws_new_passwords(tmp_path: Path) -> None:
    first, second = tmp_path / "a.env", tmp_path / "b.env"
    assert run(first).returncode == 0
    assert run(second).returncode == 0
    assert dotenv_values(first)["POSTGRES_PASSWORD"] != dotenv_values(second)["POSTGRES_PASSWORD"]


def test_template_with_bom_and_crlf(tmp_path: Path) -> None:
    template = tmp_path / "template"
    template.write_bytes(b"\xef\xbb\xbfSAP_ENV=dev\r\nPOSTGRES_PASSWORD=cambia-x\r\n")
    output = tmp_path / ".env"
    assert run(output, template=template).returncode == 0
    data = output.read_bytes()
    assert data.startswith(b"SAP_ENV=dev\nPOSTGRES_PASSWORD=")
    assert b"cambia-x" not in data


def test_missing_template_fails(tmp_path: Path) -> None:
    result = run(tmp_path / ".env", template=tmp_path / "missing")
    assert result.returncode == 1
    assert "modello non trovato" in result.stderr
