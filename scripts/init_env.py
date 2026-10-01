"""Create .env from env.example with random passwords (development and the production VM).

Every placeholder `cambia-<nome>` becomes a random URL-safe password; the same placeholder
gets the same password everywhere (POSTGRES_PASSWORD and the password inside
SAP_DB_URL_ADMIN stay in step). Comments, order and the other values are kept. No password
is ever printed. An existing .env is replaced only with --force, after a backup copy.

Standard library only: it runs with a bare python3, before `uv sync`.

    uv run python scripts/init_env.py            # crea .env
    uv run python scripts/init_env.py --force    # sostituisce .env, con copia di riserva
"""

from __future__ import annotations

import argparse
import os
import re
import secrets
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER = re.compile(r"\bcambia-[a-z0-9-]+\b")
# 32 bytes of entropy; token_urlsafe uses only [A-Za-z0-9_-], safe in URLs and unquoted in .env.
PASSWORD_BYTES = 32


def render(template: str) -> tuple[str, int]:
    """The template with every placeholder replaced, and how many distinct placeholders there were."""
    passwords: dict[str, str] = {}

    def password_for(match: re.Match[str]) -> str:
        return passwords.setdefault(match.group(0), secrets.token_urlsafe(PASSWORD_BYTES))

    return PLACEHOLDER.sub(password_for, template), len(passwords)


def _write_private(path: Path, text: str) -> None:
    """Write atomically, LF line endings, readable by the owner only where the OS allows it."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    if os.name == "posix":
        tmp.chmod(0o600)
    tmp.replace(path)


def init_env(template: Path, output: Path, *, force: bool) -> str:
    """Create `output` from `template`; return a message without secrets."""
    if not template.is_file():
        msg = f"modello non trovato: {template}"
        raise FileNotFoundError(msg)
    text, count = render(template.read_text(encoding="utf-8-sig").replace("\r\n", "\n"))
    backup_note = ""
    if output.exists():
        if not force:
            msg = f"{output} esiste già: usa --force per sostituirlo (ne resta una copia di riserva)"
            raise FileExistsError(msg)
        stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
        backup = output.with_name(f"{output.name}.bak-{stamp}")
        shutil.copy2(output, backup)
        if os.name == "posix":
            backup.chmod(0o600)
        backup_note = f"; copia di riserva: {backup.name}"
    _write_private(output, text)
    return f"creato {output.name} da {template.name}: {count} password generate{backup_note}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Crea .env da env.example con password casuali.")
    parser.add_argument("--template", type=Path, default=ROOT / "env.example")
    parser.add_argument("--output", type=Path, default=ROOT / ".env")
    parser.add_argument("--force", action="store_true", help="sostituisce un .env esistente")
    args = parser.parse_args(argv)
    try:
        print(init_env(args.template, args.output, force=args.force))
    except (FileExistsError, FileNotFoundError) as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
