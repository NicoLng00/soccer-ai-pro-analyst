#!/usr/bin/env python3
"""PreToolUse (Edit|Write|MultiEdit|NotebookEdit): protect secrets, data and committed migrations.

Exit 2 blocks the tool call; stderr is shown to Claude as the reason.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def block(reason: str) -> None:
    print(reason, file=sys.stderr)
    sys.exit(2)


def main() -> None:
    payload = json.load(sys.stdin)
    tool_input = payload.get("tool_input", {})
    raw_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not raw_path:
        sys.exit(0)

    project = Path(os.environ.get("CLAUDE_PROJECT_DIR", payload.get("cwd", "."))).resolve()
    path = Path(raw_path).resolve()
    try:
        rel = path.relative_to(project)
    except ValueError:
        sys.exit(0)
    rel_posix = rel.as_posix()

    if rel.name.startswith(".env") and rel.name != ".env.example":
        block("File di segreti: non si modifica da Claude Code. Chiedi a Nico.")

    if rel_posix.startswith(("data/", "secrets/")):
        block(f"{rel_posix}: i dati non si modificano a mano. Passa dalla pipeline.")

    if rel_posix.startswith("migrations/versions/") and path.exists():
        tracked = subprocess.run(
            ["git", "-C", str(project), "cat-file", "-e", f"HEAD:{rel_posix}"],
            capture_output=True,
            check=False,
        )
        if tracked.returncode == 0:
            block(
                f"{rel_posix} è una migrazione già committata e non si modifica. "
                "Crea una nuova migrazione (skill nuova-migrazione)."
            )

    sys.exit(0)


if __name__ == "__main__":
    main()
