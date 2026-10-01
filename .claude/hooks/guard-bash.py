#!/usr/bin/env python3
"""PreToolUse (Bash): block destructive commands on data, history, secrets and filesystem.

Exit 2 blocks the command; stderr is shown to Claude as the reason.
Covered by tests/unit/test_claude_hooks.py: add a test case with every new rule.
"""

from __future__ import annotations

import json
import re
import shlex
import sys

FACT_SCHEMAS = r"(ref|obs|mkt|ml)\."

RULES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\b(drop|truncate)\s+(table|schema|database)\b", re.I),
        "DROP/TRUNCATE non ammessi da riga di comando: lo schema cambia solo con una migrazione.",
    ),
    (
        re.compile(rf"\bdelete\s+from\s+{FACT_SCHEMAS}", re.I),
        "DELETE sugli schemi di fatti viola il principio append-only: chiudi known_period.",
    ),
    (
        re.compile(rf"\bupdate\s+{FACT_SCHEMAS}\w+\s+set\s+(?!known_period\b)", re.I),
        "UPDATE sugli schemi di fatti ammesso solo sulla colonna known_period.",
    ),
    (
        re.compile(r"\bgit\s+push\b.*(?:^|\s)(?:--force(?:-with-lease)?|-f)(?:=|\s|$)", re.I),
        "Push forzato non ammesso.",
    ),
    (
        re.compile(r"\bgit\s+(reset\s+--hard|clean\s+-[a-z]*f)", re.I),
        "Comando git distruttivo: chiedi a Nico prima di eseguirlo.",
    ),
    (
        re.compile(r"\balembic\s+downgrade\b", re.I),
        "Downgrade di Alembic: consentito solo nei test. Chiedi conferma a Nico.",
    ),
    (
        re.compile(
            r"(?:\b(?:cat|less|more|head|tail|grep|sed|awk|source|cp|base64|xxd|strings)|(?:^|[;&|]\s*)\.)"
            r"\s+[^|;]*\.env(?!\.example)\b",
            re.I,
        ),
        "Lettura di file .env non ammessa.",
    ),
]

# Targets that a recursive rm may remove: caches, build output, temporary folders.
RM_ALLOWED = {
    "tmp",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    "htmlcov",
    "dist",
    "build",
    ".coverage",
}
SEGMENT_SPLIT = re.compile(r"&&|\|\||[;|\n]")


def _rm_target_allowed(target: str) -> bool:
    if target.startswith("/tmp/"):  # noqa: S108 - path comparison, not file creation
        return True
    normalized = target.removeprefix("./").rstrip("/")
    head = normalized.split("/", 1)[0]
    return normalized in RM_ALLOWED or head == "tmp" or normalized.endswith("/__pycache__")


def recursive_rm_violation(command: str) -> bool:
    """True if a segment runs a recursive rm on anything outside RM_ALLOWED."""
    for segment in SEGMENT_SPLIT.split(command):
        try:
            argv = shlex.split(segment)
        except ValueError:
            argv = segment.split()
        while argv and argv[0] in {"sudo", "command", "env"}:
            argv = argv[1:]
        if not argv or argv[0].rsplit("/", 1)[-1] != "rm":
            continue
        args = argv[1:]
        flags = [a for a in args if a.startswith("-")]
        recursive = any(
            f in {"--recursive", "-R"} or (not f.startswith("--") and "r" in f.lower()) for f in flags
        )
        if not recursive:
            continue
        targets = [a for a in args if not a.startswith("-")]
        if not targets or not all(_rm_target_allowed(t) for t in targets):
            return True
    return False


def main() -> None:
    payload = json.load(sys.stdin)
    command = payload.get("tool_input", {}).get("command", "")
    for pattern, reason in RULES:
        if pattern.search(command):
            print(reason, file=sys.stderr)
            sys.exit(2)
    if recursive_rm_violation(command):
        print("rm ricorsivo ammesso solo su cache, cartelle temporanee o di build.", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
