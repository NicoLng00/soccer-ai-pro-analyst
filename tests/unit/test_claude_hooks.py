"""The Claude Code guard hooks are part of the safety net: they get tests like any code."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / ".claude" / "hooks"


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


def git_repo(base: Path, branch: str) -> Path:
    repo = base / branch
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", branch, str(repo)], check=True)  # noqa: S603, S607
    return repo


@pytest.fixture(scope="module")
def feature_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return git_repo(tmp_path_factory.mktemp("repos"), "feature")


@pytest.fixture(scope="module")
def main_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return git_repo(tmp_path_factory.mktemp("repos"), "main")


def run_bash_guard(command: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return run_hook("guard-bash.py", {"tool_input": {"command": command}, "cwd": str(cwd)})


@pytest.mark.parametrize(
    "command",
    [
        # SQL and Alembic
        "psql -c 'DELETE FROM obs.obs_num WHERE id = 3'",
        "psql -c 'drop table ref.match'",
        "psql -c 'TRUNCATE TABLE mkt.odds_quote'",
        'psql -c "UPDATE ref.match SET home_team_id = 2"',
        "uv run alembic downgrade base",
        # git
        "git push --force origin main",
        "git push -f",
        "git push origin +fase-0/x",
        "git push origin HEAD:main",
        "git push origin fase-0/x:refs/heads/main",
        "git reset --hard HEAD~3",
        "git clean -d -f",
        "git clean -fdx",
        # recursive deletion
        "rm -rf src",
        "rm -rf .ruff_cache src",
        "rm -r -f data",
        "sudo rm --recursive migrations",
        "rm -rf tmp/../src",
        "rm -rf /tmp/../home/nico",
        "true & rm -rf src",
        "(rm -rf src)",
        "ls | xargs rm -rf",
        "bash -c 'rm -rf src'",
        "find . -name '*.py' -delete",
        "Remove-Item -Recurse -Force src",
        "ri -r migrations",
        "rm -Recurse data",
        "& { Remove-Item -Recurse src }",
        "cmd /c rd /s /q src",
        # secret files, read as arguments
        "cat .env",
        "cat .env.local",
        "cat .env.example",
        "cat .envrc",
        "cat config/.env",
        "cat C:\\proj\\.env",
        "cat .e*",
        "source .env",
        "set -a; . .env; set +a",
        "echo $(cat .env)",
        "ls\ncat .env",
        "cat < .env",
        "echo x > .env",
        "uv run --env-file .env python x.py",
        "uv run --env-file=.env python x.py",
        "bash -c 'cat .env'",
        "Get-Content .env",
        "Get-Content -Path .env",
        "gc .env.production",
        "type .env",
    ],
)
def test_guard_bash_blocks(command: str, feature_repo: Path) -> None:
    result = run_bash_guard(command, feature_repo)
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
        "rm -rf /tmp/sap-test",
        "rm -f reports/quality/old.md",
        "Remove-Item -Force reports/quality/old.md",
        "Remove-Item -Recurse .pytest_cache",
        "git push origin fix-f",
        "git push -u origin fase-0/schema",
        "git push --follow-tags origin fase-0/schema",
        "git clean -n",
        # .env mentioned in text, not read as a file
        "git commit -m 'Rinomina .env.example'",
        'git commit -m "Leggi (cat .env) nel testo" -m "secondo paragrafo"',
        "grep -rn '\\.env\\.example' docs",
        "echo 'il modello è env.example'",
        "cat env.example",
    ],
)
def test_guard_bash_allows(command: str, feature_repo: Path) -> None:
    result = run_bash_guard(command, feature_repo)
    assert result.returncode == 0, (command, result.stderr)


@pytest.mark.parametrize("command", ["git commit -m 'x'", "git push", "git push -u origin HEAD"])
def test_guard_bash_blocks_commit_and_push_on_main(command: str, main_repo: Path) -> None:
    result = run_bash_guard(command, main_repo)
    assert result.returncode == 2, command
    assert "main" in result.stderr


def test_guard_bash_follows_git_dash_c_to_main(main_repo: Path, feature_repo: Path) -> None:
    result = run_bash_guard(f"git -C {main_repo.as_posix()} commit -m x", feature_repo)
    assert result.returncode == 2


def test_guard_bash_allows_commit_on_a_branch(feature_repo: Path) -> None:
    assert run_bash_guard("git commit -m 'Aggiungi x'", feature_repo).returncode == 0


@pytest.mark.parametrize("hook", ["guard-bash.py", "guard-files.py"])
def test_guards_fail_closed_on_malformed_input(hook: str, tmp_path: Path) -> None:
    result = run_hook(hook, "{not json", tmp_path)
    assert result.returncode == 2
    assert "errore interno" in result.stderr


@pytest.mark.parametrize(
    ("hook", "tool_input"),
    [
        ("guard-bash.py", {}),
        ("guard-bash.py", {"command": ["cat", ".env"]}),
        ("guard-files.py", {}),
        ("guard-files.py", {"file_path": ""}),
    ],
)
def test_guards_fail_closed_without_the_expected_field(
    hook: str, tool_input: dict[str, object], tmp_path: Path
) -> None:
    result = run_hook(hook, {"tool_input": tool_input}, tmp_path)
    assert result.returncode == 2
    assert "payload senza" in result.stderr


@pytest.mark.parametrize("name", [".env", ".env.local", ".env.example", ".env.production", ".envrc"])
def test_guard_files_blocks_env(name: str, tmp_path: Path) -> None:
    result = run_hook("guard-files.py", {"tool_input": {"file_path": str(tmp_path / name)}}, tmp_path)
    assert result.returncode == 2


def test_guard_files_blocks_env_outside_the_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "frontend" / ".env.local"
    result = run_hook("guard-files.py", {"tool_input": {"file_path": str(outside)}}, project)
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


# ------------------------------------------------------------------ wiring in settings.json


def guard_hooks() -> dict[str, tuple[str, str]]:
    """Guard script name -> (matcher, command) as configured in .claude/settings.json."""
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    found: dict[str, tuple[str, str]] = {}
    for entry in settings["hooks"]["PreToolUse"]:
        for hook in entry["hooks"]:
            for name in ("guard-bash.py", "guard-files.py"):
                if name in hook["command"]:
                    found[name] = (entry["matcher"], hook["command"])
    return found


def test_guards_are_wired_to_every_shell_and_edit_tool() -> None:
    hooks = guard_hooks()
    assert set(hooks["guard-bash.py"][0].split("|")) >= {"Bash", "PowerShell"}
    assert set(hooks["guard-files.py"][0].split("|")) >= {"Edit", "Write", "MultiEdit", "NotebookEdit"}


BASH = shutil.which("bash")


@pytest.mark.skipif(BASH is None or shutil.which("uv") is None, reason="servono bash e uv")
@pytest.mark.parametrize("name", ["guard-bash.py", "guard-files.py"])
@pytest.mark.parametrize("broken", ["payload", "uv-missing"])
def test_configured_guard_command_blocks_on_failure(name: str, broken: str) -> None:
    _, command = guard_hooks()[name]
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(ROOT))
    if broken == "uv-missing":
        env["PATH"] = str(ROOT / "no-uv-here")
    result = subprocess.run(  # noqa: S603
        [str(BASH), "-c", command],
        input="{not json",
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 2, result.stderr
