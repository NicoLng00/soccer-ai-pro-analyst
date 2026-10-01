#!/usr/bin/env python3
"""PreToolUse (Bash|PowerShell): block destructive commands on data, history, secrets and filesystem.

Exit 2 blocks the command; stderr is shown to Claude as the reason. Any internal error, or a
payload without a command, also exits 2 (fail closed).

SQL rules look at the text, wherever it appears (psql -c '...'). Every other rule looks at the
parsed command: the command line is split with shlex into simple commands at ; & | ( ) { } $( `
and newlines, quotes respected, so a commit message that mentions a file is just an argument.
This is a guard against mistakes, not a sandbox: a determined bypass is always possible.
Covered by tests/unit/test_claude_hooks.py: add a test case with every new rule.
"""

from __future__ import annotations

import fnmatch
import json
import os
import posixpath
import re
import shlex
import subprocess
import sys
from typing import NoReturn

FACT_SCHEMAS = r"(ref|obs|mkt|ml)\."

TEXT_RULES: list[tuple[re.Pattern[str], str]] = [
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
        re.compile(r"\balembic\s+downgrade\b", re.I),
        "Downgrade di Alembic: consentito solo nei test. Chiedi conferma a Nico.",
    ),
]

PUNCTUATION = ";&|()<>`{}\n"
# Wrappers that run the command that follows them.
PREFIXES = {"sudo", "doas", "command", "env", "exec", "nohup", "nice", "time", "xargs"}
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# Shells whose -c / -Command / /c argument is itself a command line.
SHELLS = {"bash", "sh", "zsh", "dash", "pwsh", "powershell", "cmd"}
SHELL_COMMAND_FLAGS = {"-c", "-command", "/c"}

# Commands that read, copy, move or load the files they receive as arguments.
READERS = {
    "cat", "tac", "nl", "less", "more", "head", "tail", "grep", "egrep", "fgrep", "rg", "ag",
    "sed", "awk", "gawk", "cut", "sort", "uniq", "diff", "cmp", "comm", "paste", "od", "xxd",
    "hexdump", "strings", "base64", "source", ".", "cp", "mv", "ln", "scp", "rsync", "tar",
    "zip", "gzip", "bat", "view", "vi", "vim", "nano", "code", "tee", "dd", "openssl", "iconv",
    "get-content", "gc", "type", "select-string", "sls", "copy-item", "cpi", "copy",
    "move-item", "mi", "move", "import-csv",
}  # fmt: skip
SECRET_SAMPLES = (".env", ".env.local", ".envrc")

# Targets that a recursive delete may remove: caches, build output, temporary folders.
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
# PowerShell and cmd names for recursive deletion (-Recurse, -r, /s).
WINDOWS_REMOVE = {"remove-item", "ri", "rmdir", "rd", "del", "erase"}

PROTECTED_BRANCHES = {"main"}
GIT_OPTIONS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}


def block(reason: str) -> NoReturn:
    print(reason, file=sys.stderr)
    sys.exit(2)


# --------------------------------------------------------------------------- parsing


def _tokens(command: str) -> list[str]:
    lex = shlex.shlex(command, posix=True, punctuation_chars=PUNCTUATION)
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""
    try:
        return list(lex)
    except ValueError:
        # Unbalanced quotes: fall back to a plain split, still cut at the separators.
        return re.findall(r"[;&|()<>`{}\n]+|[^\s;&|()<>`{}]+", command)


def _is_separator(token: str) -> bool:
    return bool(token) and all(c in PUNCTUATION for c in token)


def split_commands(command: str) -> tuple[list[list[str]], list[str]]:
    """Simple commands (argv lists, wrappers removed) and redirection targets.

    The command line is parsed twice, as written and with backslashes turned into slashes,
    so that Windows paths (C:\\x\\.env) are seen as paths too.
    """
    commands: list[list[str]] = []
    redirects: list[str] = []
    for variant in {command, command.replace("\\", "/")}:
        current: list[str] = []
        after_redirect = False
        for token in _tokens(variant):
            if _is_separator(token):
                if current:
                    commands.append(current)
                current = []
                after_redirect = "<" in token or ">" in token
                continue
            if after_redirect:
                redirects.append(token)
                after_redirect = False
                continue
            current.append(token)
        if current:
            commands.append(current)
    return [_strip_prefixes(argv) for argv in commands if argv], redirects


def _strip_prefixes(argv: list[str]) -> list[str]:
    while argv and (argv[0] in PREFIXES or ASSIGNMENT.match(argv[0])):
        argv = argv[1:]
    return argv


def command_name(argv: list[str]) -> str:
    name = posixpath.basename(argv[0].replace("\\", "/")).lower()
    return name.removesuffix(".exe")


# --------------------------------------------------------------------------- secrets


def is_secret_path(token: str) -> bool:
    """`.env`, `.env.*` or `.envrc`, at any depth, also as a glob that expands to one of them."""
    for candidate in (token, token.split("=", 1)[1] if "=" in token else ""):
        name = posixpath.basename(candidate.replace("\\", "/").rstrip("/"))
        if not name.startswith("."):
            continue
        if name in {".env", ".envrc"} or name.startswith(".env."):
            return True
        # bash expands a glob to dotfiles only when it starts with a dot.
        if any(c in name for c in "*?[") and any(fnmatch.fnmatchcase(s, name) for s in SECRET_SAMPLES):
            return True
    return False


def secret_file_violation(argv: list[str]) -> bool:
    name = command_name(argv)
    args = argv[1:]
    if name in READERS and any(is_secret_path(a) for a in args if not a.startswith("-")):
        return True
    # uv run --env-file .env, docker run --env-file=.env: load the secrets into a process.
    for i, arg in enumerate(args):
        if arg == "--env-file" and i + 1 < len(args) and is_secret_path(args[i + 1]):
            return True
        if arg.startswith("--env-file=") and is_secret_path(arg):
            return True
    return False


# --------------------------------------------------------------------------- deletions


def _rm_target_allowed(target: str) -> bool:
    path = target.replace("\\", "/")
    if path.startswith("/tmp/"):  # noqa: S108 - path comparison, not file creation
        return posixpath.normpath(path).startswith("/tmp/")  # noqa: S108
    normalized = posixpath.normpath(path.removeprefix("./"))
    if normalized.startswith(("..", "/")):
        return False
    head = normalized.split("/", 1)[0]
    return normalized in RM_ALLOWED or head == "tmp" or normalized.endswith("/__pycache__")


def recursive_delete_violation(argv: list[str]) -> bool:
    """True for a recursive rm (or PowerShell/cmd equivalent, or find -delete) outside RM_ALLOWED."""
    name = command_name(argv)
    args = argv[1:]
    if name == "find":
        return "-delete" in args or ("-exec" in args and "rm" in args)
    if name == "rm":
        flags = [a for a in args if a.startswith("-")]
        recursive = any(
            f in {"--recursive", "-R"} or (not f.startswith("--") and "r" in f.lower()) for f in flags
        )
        targets = [a for a in args if not a.startswith("-")]
    elif name in WINDOWS_REMOVE:
        flags = [a for a in args if a.startswith("-") or re.fullmatch(r"/[A-Za-z]", a)]
        recursive = any(f.lower().startswith("-r") or f.lower() == "/s" for f in flags)
        targets = [a for a in args if a not in flags]
    else:
        return False
    if not recursive:
        return False
    return not targets or not all(_rm_target_allowed(t) for t in targets)


# --------------------------------------------------------------------------- git


def _git_subcommand(argv: list[str]) -> tuple[str, list[str], str | None]:
    i, workdir = 1, None
    while i < len(argv):
        arg = argv[i]
        if arg in GIT_OPTIONS_WITH_VALUE and i + 1 < len(argv):
            if arg == "-C":
                workdir = argv[i + 1]
            i += 2
        elif arg.startswith("-"):
            i += 1
        else:
            return arg, argv[i + 1 :], workdir
    return "", [], workdir


def current_branch(workdir: str) -> str:
    result = subprocess.run(
        ["git", "-C", workdir, "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _short_flag(flag: str, letter: str) -> bool:
    return not flag.startswith("--") and letter in flag


def _push_violation(flags: list[str], positional: list[str]) -> str | None:
    refspecs = positional[1:]  # positional[0] is the remote
    forced = any(f.startswith("--force") or _short_flag(f, "f") for f in flags)
    if forced or any(spec.startswith("+") for spec in refspecs):
        return "Push forzato non ammesso."
    for spec in refspecs:
        target = spec.split(":", 1)[1] if ":" in spec else spec
        if target.removeprefix("refs/heads/") in PROTECTED_BRANCHES:
            return "Push verso main non ammesso: si unisce con un PR."
    return None


def git_violation(argv: list[str], base_dir: str) -> str | None:
    """The reason to block a git command, or None."""
    if command_name(argv) != "git":
        return None
    sub, args, workdir = _git_subcommand(argv)
    flags = [a for a in args if a.startswith("-")]
    reason = None
    if sub == "reset" and "--hard" in flags:
        reason = "Comando git distruttivo (reset --hard): chiedi a Nico prima di eseguirlo."
    elif sub == "clean" and any(f == "--force" or _short_flag(f, "f") for f in flags):
        reason = "Comando git distruttivo (clean -f): chiedi a Nico prima di eseguirlo."
    elif sub == "push":
        reason = _push_violation(flags, [a for a in args if not a.startswith("-")])
    if reason is None and sub in {"commit", "push"}:
        branch = current_branch(os.path.join(base_dir, workdir) if workdir else base_dir)
        if branch in PROTECTED_BRANCHES:
            reason = f"git {sub} sul branch {branch} non ammesso: lavora su un branch e unisci con un PR."
    return reason


# --------------------------------------------------------------------------- main


def check(command: str, base_dir: str, depth: int = 0) -> None:
    for pattern, reason in TEXT_RULES:
        if pattern.search(command):
            block(reason)
    commands, redirects = split_commands(command)
    if any(is_secret_path(t) for t in redirects):
        block("Lettura o scrittura di file .env non ammessa.")
    for argv in commands:
        if secret_file_violation(argv):
            block("Lettura di file .env non ammessa.")
        if recursive_delete_violation(argv):
            block("Cancellazione ricorsiva ammessa solo su cache, cartelle temporanee o di build.")
        reason = git_violation(argv, base_dir)
        if reason:
            block(reason)
        if command_name(argv) in SHELLS and depth < 3:
            lowered = [a.lower() for a in argv]
            for flag in SHELL_COMMAND_FLAGS & set(lowered):
                i = lowered.index(flag)
                if i + 1 < len(argv):
                    # bash -c 'line' passes one argument; cmd /c takes the rest of the line.
                    check(
                        shlex.join(argv[i + 1 :]) if len(argv) > i + 2 else argv[i + 1], base_dir, depth + 1
                    )


def main() -> None:
    payload = json.load(sys.stdin)
    command = payload.get("tool_input", {}).get("command")
    if not isinstance(command, str):
        block("guard-bash: payload senza comando, bloccato per sicurezza.")
    base_dir = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or "."
    check(command, base_dir)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        # Fail closed: a guard that crashes must block, not let the command through.
        print(f"guard-bash: errore interno, comando bloccato: {exc!r}", file=sys.stderr)
        sys.exit(2)
