"""Structured logging: structlog, JSON, one event per line, job_run_id bound through contextvars."""

from __future__ import annotations

import logging
import sys
from typing import TextIO

import structlog
from structlog.contextvars import bound_contextvars

__all__ = ["bound_contextvars", "configure_logging", "get_logger"]


def configure_logging(level: str = "INFO", stream: TextIO | None = None) -> None:
    """Configure structlog for the whole process. Call once at startup (CLI, Dagster, scripts)."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(sort_keys=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelNamesMapping()[level.upper()]),
        logger_factory=structlog.PrintLoggerFactory(file=stream or sys.stdout),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str) -> structlog.typing.FilteringBoundLogger:
    logger: structlog.typing.FilteringBoundLogger = structlog.get_logger().bind(logger=name)
    return logger
