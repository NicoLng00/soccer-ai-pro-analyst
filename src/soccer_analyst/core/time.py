"""Time helpers. Every datetime in the system is timezone-aware UTC."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current instant as an aware UTC datetime."""
    return datetime.now(tz=UTC)


def ensure_utc(value: datetime) -> datetime:
    """Convert an aware datetime to UTC; reject naive datetimes."""
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        msg = f"naive datetime not allowed: {value!r}"
        raise ValueError(msg)
    return value.astimezone(UTC)
