#!/usr/bin/env python3
"""SessionStart: inject project state as context (stdout becomes context for Claude)."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


def sh(cmd: list[str], cwd: Path) -> str:
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    return res.stdout.strip()


def main() -> None:
    project = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
    lines = ["## Stato di SoccerAnalystPro all'avvio della sessione"]

    roadmap = project / "docs" / "roadmap.md"
    if roadmap.exists():
        match = re.search(r"^Fase corrente:\s*(\d+)", roadmap.read_text(encoding="utf-8"), re.M)
        if match:
            phase = match.group(1)
            lines.append(f"- Fase corrente: {phase} (prompt: docs/prompts/fase-{phase}.md)")

    branch = sh(["git", "branch", "--show-current"], project)
    if branch:
        lines.append(f"- Branch: {branch}")
    dirty = sh(["git", "status", "--porcelain"], project)
    lines.append(f"- Modifiche non committate: {len(dirty.splitlines()) if dirty else 0} file")
    last = sh(["git", "log", "-3", "--format=%h %s"], project)
    if last:
        lines.append("- Ultimi commit:\n" + "\n".join(f"  - {line}" for line in last.splitlines()))

    versions = sorted((project / "migrations" / "versions").glob("*.py"))
    if versions:
        lines.append(f"- Ultima migrazione: {versions[-1].name}")

    reports = sorted((project / "reports" / "quality").glob("*.md"))
    if reports:
        lines.append(f"- Ultimo report di qualità: reports/quality/{reports[-1].name}")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
