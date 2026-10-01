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


def _connect(dsn: str) -> None:
    password = "local-pw-value"  # noqa: S105 - fake value that must not reach the log
    msg = f"connessione fallita per {dsn} ({len(password)})"
    raise RuntimeError(msg)


def test_exceptions_never_log_local_variables(stream: io.StringIO) -> None:
    try:
        _connect("postgresql://sap_live:url-pw-value@localhost/sap")
    except RuntimeError:
        get_logger("test").exception("errore")
    output = stream.getvalue()
    assert "errore" in output
    assert "RuntimeError" in output
    assert "local-pw-value" not in output
    assert "url-pw-value" not in output


def test_sensitive_keys_are_masked_at_any_depth(stream: io.StringIO) -> None:
    get_logger("test").info(
        "evento",
        password="pw-1",  # noqa: S106 - fake value
        api_key="key-2",
        details={"session_token": "tok-3", "rows": 4, "nested": [{"Authorization": "Bearer abc"}]},
    )
    (event,) = lines(stream)
    output = stream.getvalue()
    for secret in ("pw-1", "key-2", "tok-3", "Bearer abc"):
        assert secret not in output
    assert event["password"] == "***"  # noqa: S105 - the mask, not a secret
    assert event["details"] == {"session_token": "***", "rows": 4, "nested": [{"Authorization": "***"}]}


def test_url_passwords_are_masked_in_any_string(stream: io.StringIO) -> None:
    get_logger("test").info("connessione a postgresql://sap_api:s3cr3t@db:5432/sap", target="s3://k:v@host/b")
    output = stream.getvalue()
    assert "s3cr3t" not in output
    assert "postgresql://sap_api:***@db:5432/sap" in output
    assert "s3://k:***@host/b" in output
