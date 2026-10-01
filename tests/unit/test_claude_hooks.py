"""The Claude Code guard hooks are part of the safety net: they get tests like any code."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[2] / ".claude" / "hooks"


def run_hook(
    name: str,
    payload: dict[str, object] | str,
    project: Path | None = None,
    path: str | None = None,
) -> subprocess.CompletedProcess[str]:
    # The real environment (git must be on PATH, also on Windows), with CLAUDE_PROJECT_DIR
    # pointing at the test project instead of the session that runs the tests.
    env = dict(os.environ)
    env.pop("CLAUDE_PROJECT_DIR", None)
    if project is not None:
        env["CLAUDE_PROJECT_DIR"] = str(project)
    if path is not None:
        env["PATH"] = path
    return subprocess.run(  # noqa: S603
        [sys.executable, str(HOOKS / name)],
        input=payload if isinstance(payload, str) else json.dumps(payload),
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
        "cat .env.local",
        "cat .env.example",
        # PowerShell
        "Get-Content .env",
        "gc .env.production",
        "type .env",
        "Remove-Item -Recurse -Force src",
        "ri -r migrations",
        "rm -Recurse data",
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
        "cat env.example",
        "Remove-Item -Force reports/quality/old.md",
        "Remove-Item -Recurse .pytest_cache",
    ],
)
def test_guard_bash_allows(command: str) -> None:
    result = run_hook("guard-bash.py", {"tool_input": {"command": command}})
    assert result.returncode == 0, (command, result.stderr)


@pytest.mark.parametrize("hook", ["guard-bash.py", "guard-files.py"])
def test_guards_fail_closed_on_malformed_input(hook: str, tmp_path: Path) -> None:
    result = run_hook(hook, "{not json", tmp_path)
    assert result.returncode == 2
    assert "errore interno" in result.stderr


@pytest.mark.parametrize("name", [".env", ".env.local", ".env.example", ".env.production"])
def test_guard_files_blocks_env(name: str, tmp_path: Path) -> None:
    result = run_hook("guard-files.py", {"tool_input": {"file_path": str(tmp_path / name)}}, tmp_path)
    assert result.returncode == 2


def test_guard_files_allows_env_template(tmp_path: Path) -> None:
    result = run_hook(
        "guard-files.py", {"tool_input": {"file_path": str(tmp_path / "env.example")}}, tmp_path
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

    result = run_hook(
        "guard-files.py",
        {"tool_input": {"file_path": str(migration)}},
        tmp_path,
        path=str(tmp_path / "no-git-here"),
    )
    assert result.returncode == 2
    assert "git non disponibile" in result.stderr
