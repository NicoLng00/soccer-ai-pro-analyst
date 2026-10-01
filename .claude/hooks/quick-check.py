#!/usr/bin/env python3
"""Stop: quick quality gate before Claude ends its turn.

Runs only when Python files changed since HEAD. On failure exits 2, so Claude keeps
working on the fix. `stop_hook_active` prevents loops: the second consecutive stop
is always allowed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

TIMEOUT_S = 240


def run(cmd: list[str], cwd: str) -> tuple[bool, str]:
    try:
        res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT_S, check=False)
    except subprocess.TimeoutExpired:
        return False, f"{' '.join(cmd)}: timeout dopo {TIMEOUT_S}s"
    out = (res.stdout + res.stderr).strip().splitlines()
    return res.returncode == 0, "\n".join(out[-25:])


def main() -> None:
    payload = json.load(sys.stdin)
    if payload.get("stop_hook_active"):
        sys.exit(0)

    project = os.environ.get("CLAUDE_PROJECT_DIR", payload.get("cwd", "."))
    if not shutil.which("uv") or not os.path.exists(os.path.join(project, "pyproject.toml")):
        sys.exit(0)

    changed = subprocess.run(
        ["git", "status", "--porcelain", "--", "*.py"],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    if not changed:
        sys.exit(0)

    checks = [
        ["uv", "run", "--quiet", "ruff", "check", "."],
        ["uv", "run", "--quiet", "mypy", "src"],
        ["uv", "run", "--quiet", "pytest", "-q", "-x", "-m", "not integration and not slow"],
    ]
    failures = []
    for cmd in checks:
        ok, tail = run(cmd, project)
        if not ok:
            failures.append(f"$ {' '.join(cmd[3:])}\n{tail}")

    if failures:
        print(
            "Controllo rapido fallito, correggi prima di chiudere:\n\n" + "\n\n".join(failures),
            file=sys.stderr,
        )
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
