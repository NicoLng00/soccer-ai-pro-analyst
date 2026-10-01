"""scripts/lib/dotenv.sh: the env-file reader of dev-up.sh and claude.sh."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from dotenv import dotenv_values
from dotenv_cases import CASES, VALUES, write_case

from soccer_analyst.core.config import load_database_settings

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "scripts" / "lib" / "dotenv.sh"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="serve bash")


def bash(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [str(BASH), "-c", f'set -euo pipefail; source "$0"; {script}', str(LIB), *args],
        capture_output=True,
        encoding="utf-8",
        check=False,
    )


def read_with_bash(path: Path, keys: list[str]) -> dict[str, str]:
    script = 'f="$1"; shift; for k in "$@"; do printf "%s=%s\\0" "$k" "$(dotenv_get "$f" "$k")"; done'
    result = bash(script, str(path), *keys)
    assert result.returncode == 0, result.stderr
    return dict(item.split("=", 1) for item in result.stdout.split("\0") if item)


def exported_by_bash(path: Path) -> dict[str, str]:
    result = bash('dotenv_export "$1"; env -0', str(path))
    assert result.returncode == 0, result.stderr
    pairs = (item.split("=", 1) for item in result.stdout.split("\0") if "=" in item)
    return {key: value for key, value in pairs if key in VALUES}


@pytest.mark.parametrize("case", CASES)
def test_get_reads_every_layout(case: str, tmp_path: Path) -> None:
    path = write_case(tmp_path, case)
    assert read_with_bash(path, list(VALUES)) == VALUES


@pytest.mark.parametrize("case", CASES)
def test_export_reads_every_layout(case: str, tmp_path: Path) -> None:
    # dev-up.sh exports with dotenv_export: no CR, no BOM, last line included.
    assert exported_by_bash(write_case(tmp_path, case)) == VALUES


@pytest.mark.parametrize("case", CASES)
def test_keys_lists_every_layout(case: str, tmp_path: Path) -> None:
    result = bash('dotenv_keys "$1"', str(write_case(tmp_path, case)))
    assert result.stdout.split() == sorted(VALUES)


@pytest.mark.parametrize("case", CASES)
def test_python_reads_the_same_values(case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # core/config.py must see what dev-up.sh exports.
    write_case(tmp_path, case, name=".env")
    monkeypatch.chdir(tmp_path)
    for name in [n for n in os.environ if n.upper().startswith("SAP_")]:
        monkeypatch.delenv(name)
    monkeypatch.setenv("SAP_ENV", "dev")
    db = load_database_settings()
    for role in ("owner", "readonly", "registry"):
        assert db.libpq_url(role).get_secret_value() == VALUES[f"SAP_DB_URL_{role.upper()}"]


RICH = """# commento
export SAP_A=valore-a
SAP_B = "con spazi # non è un commento"
SAP_C='virgolette singole'
SAP_D=senza virgolette # commento in linea
SAP_E=
SAP_F=prima
SAP_F=seconda

SAP_G=a=b=c
"""


def test_syntax_matches_python_dotenv(tmp_path: Path) -> None:
    path = tmp_path / "rich.env"
    path.write_text(RICH, encoding="utf-8")
    expected = {k: v or "" for k, v in dotenv_values(path).items()}
    assert read_with_bash(path, list(expected)) == expected
    assert expected["SAP_F"] == "seconda"
    assert expected["SAP_D"] == "senza virgolette"


def test_file_is_never_executed(tmp_path: Path) -> None:
    marker = tmp_path / "eseguito"
    path = tmp_path / "evil.env"
    path.write_text(f"touch {marker.as_posix()}\nSAP_X=$(touch {marker.as_posix()})\n", encoding="utf-8")
    result = bash('dotenv_export "$1"; printf "%s" "$SAP_X"', str(path))
    assert result.returncode == 0, result.stderr
    assert not marker.exists()
    assert result.stdout == f"$(touch {marker.as_posix()})"


def test_check_reports_names_only(tmp_path: Path) -> None:
    template = tmp_path / "template.env"
    template.write_text("SAP_ENV=dev\nSAP_A=x\nSAP_B=y\nSAP_OPTIONAL=\n", encoding="utf-8")
    env = tmp_path / "local.env"
    env.write_text("SAP_ENV=dev\nSAP_B=\nSAP_ENV=dev\nSAP_SECRET=valore-segreto\n", encoding="utf-8")
    result = bash('dotenv_check "$1" "$2"', str(env), str(template))
    assert result.returncode == 1
    assert f"manca in {env}: SAP_A" in result.stderr
    assert f"vuota in {env}: SAP_B" in result.stderr
    assert "SAP_ENV compare più volte" in result.stderr
    assert "SAP_OPTIONAL" not in result.stderr
    assert "valore-segreto" not in result.stderr + result.stdout


@pytest.mark.parametrize("case", CASES)
def test_check_accepts_every_layout(case: str, tmp_path: Path) -> None:
    template = write_case(tmp_path, "lf", name="template.env")
    result = bash('dotenv_check "$1" "$2"', str(write_case(tmp_path, case)), str(template))
    assert result.returncode == 0, result.stderr
