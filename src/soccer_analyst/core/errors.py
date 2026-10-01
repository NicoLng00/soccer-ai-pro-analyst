"""Typed exceptions shared by every module."""

from __future__ import annotations


class SapError(Exception):
    """Base class for every error raised by SoccerAnalystPro."""


class ConfigError(SapError):
    """A required environment variable is missing or malformed."""


class ContractViolation(SapError):  # noqa: N818 - name fixed by CLAUDE.md conventions
    """A payload from a source does not satisfy its Pydantic contract."""

    def __init__(self, source: str, detail: str, payload: object) -> None:
        super().__init__(f"{source}: {detail}")
        self.source = source
        self.detail = detail
        self.payload = payload
