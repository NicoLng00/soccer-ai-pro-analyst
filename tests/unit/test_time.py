from datetime import UTC, datetime, timedelta, timezone

import pytest

from soccer_analyst.core.time import ensure_utc, utc_now


def test_utc_now_is_aware() -> None:
    now = utc_now()
    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)


def test_ensure_utc_converts_offsets() -> None:
    rome_summer = timezone(timedelta(hours=2))
    value = datetime(2026, 10, 18, 20, 45, tzinfo=rome_summer)
    assert ensure_utc(value) == datetime(2026, 10, 18, 18, 45, tzinfo=UTC)


def test_ensure_utc_rejects_naive() -> None:
    with pytest.raises(ValueError, match="naive"):
        ensure_utc(datetime(2026, 10, 18, 20, 45))  # noqa: DTZ001
