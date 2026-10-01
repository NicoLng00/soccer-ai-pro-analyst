#!/usr/bin/env python3
"""PreToolUse (Edit|Write|MultiEdit|NotebookEdit): protect secrets, data and committed migrations.

Exit 2 blocks the tool call; stderr is shown to Claude as the reason. Any internal error also
exits 2 (fail closed).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import NoReturn


def block(reason: str) -> NoReturn:
    print(reason, file=sys.stderr)
    sys.exit(2)


def main() -> None:
    payload = json.load(sys.stdin)
    tool_input = payload.get("tool_input", {})
    raw_path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not isinstance(raw_path, str) or not raw_path:
        block("guard-files: payload senza percorso, bloccato per sicurezza.")

    path = Path(raw_path).resolve()
    # The template is env.example (no leading dot): every .env* file is a secrets file,
    # inside or outside the project.
    if path.name.startswith(".env"):
        block("File di segreti: non si modifica da Claude Code. Chiedi a Nico.")

    project = Path(os.environ.get("CLAUDE_PROJECT_DIR", payload.get("cwd", "."))).resolve()
    try:
        rel = path.relative_to(project)
    except ValueError:
        sys.exit(0)
    rel_posix = rel.as_posix()

    if rel_posix.startswith(("data/", "secrets/")):
        block(f"{rel_posix}: i dati non si modificano a mano. Passa dalla pipeline.")

    if rel_posix.startswith("migrations/versions/") and path.exists():
        try:
            tracked = subprocess.run(
                ["git", "-C", str(project), "cat-file", "-e", f"HEAD:{rel_posix}"],
                capture_output=True,
                check=False,
            )
        except OSError:
            # Fail closed: without git we cannot tell whether the migration is committed.
            block(f"{rel_posix}: git non disponibile, impossibile verificare se è già committata.")
        if tracked.returncode == 0:
            block(
                f"{rel_posix} è una migrazione già committata e non si modifica. "
                "Crea una nuova migrazione (skill nuova-migrazione)."
            )

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Fail closed: a guard that crashes must block, not let the edit through.
        print(f"guard-files: errore interno, modifica bloccata: {exc!r}", file=sys.stderr)
        sys.exit(2)
