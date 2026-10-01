"""The Claude Code guard hooks are part of the safety net: they get tests like any code."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[2] / ".claude" / "hooks"


def run_hook(
    name: str, payload: dict[str, object], project: Path | None = None
) -> subprocess.CompletedProcess[str]:
    # Minimal environment, but with the real PATH: guard-files needs git, which on Windows
    # does not live in /usr/bin.
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    if project is not None:
        env["CLAUDE_PROJECT_DIR"] = str(project)
    return subprocess.run(  # noqa: S603
        [sys.executable, str(HOOKS / name)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


@pytest.mark.parametrize(
    "command",
    [
        "psql -c 'DELETE FROM obs.obs_num WHERE id = 3'",
        "psql -c 'drop table ref.match'",
        "psql -c 'TRUNCATE TABLE mkt.odds_quote'",
        'psql -c "UPDATE ref.match SET home_team_id = 2"',
        "git push --force origin main",
        "git reset --hard HEAD~3",
        "rm -rf src",
        "rm -rf .ruff_cache src",
        "rm -r -f data",
        "sudo rm --recursive migrations",
        "git push -f",
        "source .env",
        "set -a; . .env; set +a",
        "uv run alembic downgrade base",
        "cat .env",
    ],
)
def test_guard_bash_blocks(command: str) -> None:
    result = run_hook("guard-bash.py", {"tool_input": {"command": command}})
    assert result.returncode == 2, command
    assert result.stderr.strip()


@pytest.mark.parametrize(
    "command",
    [
        "uv run pytest -q",
        'psql -c "UPDATE obs.obs_num SET known_period = tstzrange(lower(known_period), now())"',
        "psql -c 'SELECT count(*) FROM ref.match'",
        "rm -rf .pytest_cache",
        "rm -rf tmp/ .ruff_cache build",
        "rm -f reports/quality/old.md",
        "git push origin fix-f",
        "git push origin fase-0/schema",
        "cat .env.example",
    ],
)
def test_guard_bash_allows(command: str) -> None:
    result = run_hook("guard-bash.py", {"tool_input": {"command": command}})
    assert result.returncode == 0, (command, result.stderr)


def test_guard_files_blocks_env(tmp_path: Path) -> None:
    result = run_hook("guard-files.py", {"tool_input": {"file_path": str(tmp_path / ".env")}}, tmp_path)
    assert result.returncode == 2


def test_guard_files_allows_env_example(tmp_path: Path) -> None:
    result = run_hook(
        "guard-files.py", {"tool_input": {"file_path": str(tmp_path / ".env.example")}}, tmp_path
    )
    assert result.returncode == 0


def test_guard_files_blocks_committed_migration(tmp_path: Path) -> None:
    versions = tmp_path / "migrations" / "versions"
    versions.mkdir(parents=True)
    migration = versions / "0001_ops.py"
    migration.write_text("revision = '0001'\n")
    git = ["git", "-C", str(tmp_path), "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run([*git, "init", "-q"], check=True)  # noqa: S603
    subprocess.run([*git, "add", "."], check=True)  # noqa: S603
    subprocess.run([*git, "commit", "-qm", "init"], check=True)  # noqa: S603

    result = run_hook("guard-files.py", {"tool_input": {"file_path": str(migration)}}, tmp_path)
    assert result.returncode == 2
    assert "nuova migrazione" in result.stderr

    new_migration = versions / "0002_ref.py"
    result = run_hook("guard-files.py", {"tool_input": {"file_path": str(new_migration)}}, tmp_path)
    assert result.returncode == 0


def test_guard_files_fails_closed_without_git(tmp_path: Path) -> None:
    versions = tmp_path / "migrations" / "versions"
    versions.mkdir(parents=True)
    migration = versions / "0001_ops.py"
    migration.write_text("revision = '0001'\n")

    result = subprocess.run(  # noqa: S603
        [sys.executable, str(HOOKS / "guard-files.py")],
        input=json.dumps({"tool_input": {"file_path": str(migration)}}),
        capture_output=True,
        text=True,
        env={"PATH": str(tmp_path / "no-git-here"), "CLAUDE_PROJECT_DIR": str(tmp_path)},
        check=False,
    )
    assert result.returncode == 2
    assert "git non disponibile" in result.stderr
