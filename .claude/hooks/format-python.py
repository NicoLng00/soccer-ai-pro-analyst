#!/usr/bin/env python3
"""PostToolUse (Edit|Write|MultiEdit): format and lint the edited Python file.

Exit 2 feeds remaining lint errors back to Claude; exit 0 otherwise.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> None:
    payload = json.load(sys.stdin)
    raw_path = payload.get("tool_input", {}).get("file_path", "")
    path = Path(raw_path)
    if path.suffix != ".py" or not path.exists():
        sys.exit(0)

    runner = ["uv", "run", "--quiet", "ruff"] if shutil.which("uv") else ["ruff"]
    if not shutil.which(runner[0]):
        sys.exit(0)

    subprocess.run([*runner, "format", str(path)], capture_output=True, check=False)
    subprocess.run([*runner, "check", "--fix", str(path)], capture_output=True, check=False)
    result = subprocess.run(
        [*runner, "check", "--output-format", "concise", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"ruff segnala ancora problemi in {path.name}:\n{result.stdout.strip()}", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
