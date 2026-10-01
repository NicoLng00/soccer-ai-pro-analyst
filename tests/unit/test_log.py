import io
import json
from collections.abc import Iterator

import pytest
import structlog

from soccer_analyst.core.log import bound_contextvars, configure_logging, get_logger


@pytest.fixture
def stream() -> Iterator[io.StringIO]:
    buffer = io.StringIO()
    configure_logging("INFO", stream=buffer)
    yield buffer
    structlog.reset_defaults()


def lines(buffer: io.StringIO) -> list[dict[str, object]]:
    return [json.loads(line) for line in buffer.getvalue().splitlines()]


def test_one_json_event_per_line(stream: io.StringIO) -> None:
    log = get_logger("test")
    log.info("first", rows=3)
    log.warning("second")
    events = lines(stream)
    assert [e["event"] for e in events] == ["first", "second"]
    assert events[0]["rows"] == 3
    assert events[0]["logger"] == "test"
    assert str(events[0]["timestamp"]).endswith("Z")


def test_job_run_id_is_bound_inside_the_context(stream: io.StringIO) -> None:
    log = get_logger("test")
    with bound_contextvars(job_run_id=42):
        log.info("inside")
    log.info("outside")
    inside, outside = lines(stream)
    assert inside["job_run_id"] == 42
    assert "job_run_id" not in outside


def test_level_filters_debug(stream: io.StringIO) -> None:
    get_logger("test").debug("hidden")
    assert lines(stream) == []
