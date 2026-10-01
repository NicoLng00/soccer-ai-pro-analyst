"""scripts/claude.sh: the Claude Code session sees SAP_ENV and SAP_DB_URL_READONLY, no other secret."""

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
from dotenv_cases import CASES, VALUES, write_case

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "claude.sh"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="serve bash")

READONLY_URL = "postgresql://sap_readonly:ro-pw-value@localhost:5432/sap"
# Values defined in the env file on top of the template, in the forms people write by hand.
EXTRA_LINES = [
    "SAP_ENV=dev",
    f'SAP_DB_URL_READONLY="{READONLY_URL}"',
    'SAP_TOTP_ENCRYPTION_KEY="totp-key-value"',
    "export SAP_GEMINI_API_KEY=gemini-key-value",
    "POSTGRES_PASSWORD=pg-pw-value\r",
]
# Secrets already exported in the shell that launches the script.
INHERITED = {
    "SAP_DB_URL_ADMIN": "postgresql://postgres:inherited-admin-pw@localhost/sap",
    "SAP_RAW_SECRET_ACCESS_KEY": "inherited-s3-secret",
    "POSTGRES_PASSWORD": "inherited-pg-pw",
}


def template_values() -> dict[str, str]:
    values = {}
    for line in (ROOT / "env.example").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


@pytest.fixture
def fake_claude(tmp_path: Path) -> Path:
    fake = tmp_path / "fake-claude"
    fake.write_text('#!/usr/bin/env bash\nprintf "ARGS=%s\\n" "$*"\nenv\n', encoding="utf-8", newline="\n")
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return fake


def launch(env_file: Path, fake: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, **INHERITED, SAP_ENV_FILE=str(env_file), SAP_CLAUDE_BIN=str(fake), KEEP_ME="1")
    return subprocess.run(  # noqa: S603
        [str(BASH), str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def session_env(output: str) -> dict[str, str]:
    pairs = (line.split("=", 1) for line in output.splitlines() if "=" in line)
    return {key: value for key, value in pairs}


def test_session_gets_no_secret(tmp_path: Path, fake_claude: Path) -> None:
    template = (ROOT / "env.example").read_text(encoding="utf-8")
    env_file = tmp_path / "test.env"
    env_file.write_text(template + "\n" + "\n".join(EXTRA_LINES) + "\n", encoding="utf-8", newline="")

    result = launch(env_file, fake_claude, "--resume", "x")
    assert result.returncode == 0, result.stderr
    seen = session_env(result.stdout)

    assert seen["SAP_ENV"] == "dev"
    assert seen["SAP_DB_URL_READONLY"] == READONLY_URL
    assert seen["ARGS"] == "--resume x"
    assert seen["KEEP_ME"] == "1"
    assert {k for k in seen if k.startswith("SAP_")} == {"SAP_ENV", "SAP_DB_URL_READONLY"}

    defined = set(template_values()) | {line.split("=", 1)[0].removeprefix("export ") for line in EXTRA_LINES}
    leaked_keys = (defined & set(seen)) - {"SAP_ENV", "SAP_DB_URL_READONLY"}
    assert not leaked_keys

    secrets = [v for k, v in template_values().items() if v and k not in {"SAP_ENV", "SAP_DB_URL_READONLY"}]
    secrets += ["totp-key-value", "gemini-key-value", "pg-pw-value", *INHERITED.values()]
    leaked_values = [s for s in secrets if s in result.stdout]
    assert not leaked_values


@pytest.mark.parametrize("case", CASES)
def test_every_file_layout_gives_the_same_session(case: str, tmp_path: Path, fake_claude: Path) -> None:
    result = launch(write_case(tmp_path, case), fake_claude)
    assert result.returncode == 0, result.stderr
    seen = session_env(result.stdout)
    assert seen["SAP_ENV"] == VALUES["SAP_ENV"]
    assert seen["SAP_DB_URL_READONLY"] == VALUES["SAP_DB_URL_READONLY"]
    assert "SAP_DB_URL_OWNER" not in seen
    assert "SAP_DB_URL_REGISTRY" not in seen
    assert "pw-owner" not in result.stdout
    assert "pw-reg" not in result.stdout


def test_missing_env_file_stops_the_launch(tmp_path: Path, fake_claude: Path) -> None:
    result = launch(tmp_path / "missing.env", fake_claude)
    assert result.returncode == 1
    assert "ARGS=" not in result.stdout


def test_missing_readonly_url_stops_the_launch(tmp_path: Path, fake_claude: Path) -> None:
    env_file = tmp_path / "test.env"
    env_file.write_text("SAP_ENV=dev\n", encoding="utf-8")
    result = launch(env_file, fake_claude)
    assert result.returncode == 1
    assert "SAP_DB_URL_READONLY" in result.stderr
