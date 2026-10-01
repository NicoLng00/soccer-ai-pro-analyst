"""Structured logging: structlog, JSON, one event per line, job_run_id bound through contextvars.

Secrets never reach the output (docs/security.md, point 11): tracebacks are rendered without
local variables, values under sensitive keys are masked, and passwords inside URLs
(scheme://user:password@host) are masked wherever they appear, exception messages included.
"""

from __future__ import annotations

import logging
import re
import sys
from collections.abc import MutableMapping
from typing import TextIO

import structlog
from structlog.contextvars import bound_contextvars
from structlog.tracebacks import ExceptionDictTransformer
from structlog.typing import EventDict, WrappedLogger

__all__ = ["bound_contextvars", "configure_logging", "get_logger", "redact_secrets"]

MASK = "***"
SENSITIVE_KEY = re.compile(
    r"password|passwd|secret|token|cookie|authorization|totp|api_?key|credential", re.I
)
URL_PASSWORD = re.compile(r"(?P<head>[a-z][a-z0-9+.-]*://[^:/@\s]*:)(?P<password>[^@\s]+)(?P<tail>@)", re.I)


def _scrub(value: object) -> object:
    if isinstance(value, str):
        return URL_PASSWORD.sub(rf"\g<head>{MASK}\g<tail>", value)
    if isinstance(value, MutableMapping):
        return {k: MASK if SENSITIVE_KEY.search(str(k)) else _scrub(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_scrub(v) for v in value]
    return value


def redact_secrets(_logger: WrappedLogger, _method: str, event_dict: EventDict) -> EventDict:
    """Mask sensitive keys and URL passwords, recursively, in the whole event."""
    return {k: MASK if SENSITIVE_KEY.search(k) else _scrub(v) for k, v in event_dict.items()}


def configure_logging(level: str = "INFO", stream: TextIO | None = None) -> None:
    """Configure structlog for the whole process. Call once at startup (CLI, Dagster, scripts)."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            # Never show_locals: frame locals hold passwords, URLs and tokens.
            structlog.processors.ExceptionRenderer(
                ExceptionDictTransformer(show_locals=False, use_rich=False)
            ),
            redact_secrets,
            structlog.processors.JSONRenderer(sort_keys=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelNamesMapping()[level.upper()]),
        logger_factory=structlog.PrintLoggerFactory(file=stream or sys.stdout),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str) -> structlog.typing.FilteringBoundLogger:
    logger: structlog.typing.FilteringBoundLogger = structlog.get_logger().bind(logger=name)
    return logger
