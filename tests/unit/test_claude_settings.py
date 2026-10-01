"""Permissions in .claude/settings.json and .mcp.json are part of the safety net: test them."""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SETTINGS = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
PERMISSIONS = SETTINGS["permissions"]
# Tool names accepted by the settings schema (json.schemastore.org/claude-code-settings.json).
RULE = re.compile(
    r"^(Bash|PowerShell|Read|Edit|Write|MultiEdit|NotebookEdit|WebFetch|WebSearch)(\([^)]+\))?$"
)


@pytest.mark.parametrize("kind", ["allow", "ask", "deny"])
def test_every_rule_is_well_formed(kind: str) -> None:
    malformed = [rule for rule in PERMISSIONS[kind] if not RULE.match(rule)]
    assert not malformed


@pytest.mark.parametrize("tool", ["Read", "Edit"])
@pytest.mark.parametrize("pattern", ["**/.env", "**/.env.*", "**/.envrc"])
def test_secret_files_are_denied_at_any_depth(tool: str, pattern: str) -> None:
    assert f"{tool}({pattern})" in PERMISSIONS["deny"]


@pytest.mark.parametrize("tool", ["Edit", "Write"])
@pytest.mark.parametrize("path", ["./.claude/**", "./.github/workflows/**"])
def test_changes_to_guards_and_workflows_ask_first(tool: str, path: str) -> None:
    assert f"{tool}({path})" in PERMISSIONS["ask"]


@pytest.mark.parametrize("kind", ["ask", "deny"])
def test_every_bash_rule_also_covers_powershell(kind: str) -> None:
    rules = set(PERMISSIONS[kind])
    bash = [r.removeprefix("Bash(") for r in rules if r.startswith("Bash(")]
    assert bash
    missing = [f"PowerShell({spec}" for spec in bash if f"PowerShell({spec}" not in rules]
    assert not missing


def test_force_push_is_denied() -> None:
    for shell in ("Bash", "PowerShell"):
        assert f"{shell}(git push --force *)" in PERMISSIONS["deny"]
        assert f"{shell}(git push -f *)" in PERMISSIONS["deny"]


def test_hooks_declare_bash() -> None:
    # The commands use bash syntax ("$CLAUDE_PROJECT_DIR", || exit 2): never let them run in pwsh.
    hooks = [hook for entries in SETTINGS["hooks"].values() for entry in entries for hook in entry["hooks"]]
    assert hooks
    assert all(hook.get("shell") == "bash" for hook in hooks)


def test_mcp_servers_are_pinned() -> None:
    servers = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]
    for name, server in servers.items():
        if server["command"] == "uvx":
            package = server["args"][0]
            assert re.search(r"(@|==)\d+\.\d+\.\d+$", package), f"{name}: {package} senza versione"
