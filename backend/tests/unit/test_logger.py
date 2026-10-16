"""Unit tests for structured JSON logging and the request logging middleware."""

import hashlib
import json
import logging
import re
from uuid import UUID

import pytest
import structlog
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.logger import configure_logging, logger
from app.core.middleware import RequestLoggingMiddleware

TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


@pytest.fixture()
def json_logs(capfd):
    """Configure JSON logging and expose captured file descriptors.

    Args:
        capfd: pytest capture fixture for file descriptors.

    Yields:
        capfd: capture fixture with the JSON pipeline active.
    """
    configure_logging("DEBUG")
    structlog.contextvars.clear_contextvars()
    yield capfd
    structlog.contextvars.clear_contextvars()


def parse_records(capfd) -> list[dict]:
    """Parse every JSON log line from the captured output.

    Args:
        capfd: pytest capture fixture holding the output.

    Returns:
        list: parsed log records in emission order.
    """
    lines = [line for line in capfd.readouterr().out.splitlines() if line.strip()]
    return [json.loads(line) for line in lines]


def find_record(capfd, message: str) -> dict:
    """Parse the captured output and pick one record by its message.

    Args:
        capfd: pytest capture fixture holding the output.
        message: message identifying the wanted record.

    Returns:
        dict: the matching log record.

    Raises:
        AssertionError: when no record carries the message.
    """
    matches = [r for r in parse_records(capfd) if r.get("message") == message]
    assert matches, f"no log record with message {message!r}"
    return matches[-1]


def build_app() -> FastAPI:
    """Build a minimal app wrapped in the request logging middleware.

    Returns:
        FastAPI: application with one API route and one health route.
    """
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/api/ping")
    async def ping():
        """Answer a plain JSON payload.

        Returns:
            dict: static response body.
        """
        return {"ok": True}

    @app.get("/health/live")
    async def health():
        """Answer the liveness probe.

        Returns:
            dict: static response body.
        """
        return {"ok": True}

    return app


def test_record_has_checklist_fields(json_logs):
    """Every record carries the agreed observability fields."""
    logger.info("hello")
    record = find_record(json_logs, "hello")

    assert record["message"] == "hello"
    assert record["level"] == "INFO"
    assert record["severity_number"] == 9
    assert TIMESTAMP_RE.match(record["timestamp"])
    assert record["service.name"] == "nexadesk-backend"
    assert record["service.version"]
    assert record["deployment.environment.name"]
    assert record["host.name"]
    assert record["k8s.pod.name"]
    assert record["logger"] == "nexadesk"


@pytest.mark.parametrize(
    ("method", "level", "severity"),
    [
        ("debug", "DEBUG", 5),
        ("info", "INFO", 9),
        ("warning", "WARNING", 13),
        ("error", "ERROR", 17),
        ("critical", "CRITICAL", 21),
    ],
)
def test_level_and_severity_mapping(json_logs, method, level, severity):
    """Each log method maps to the agreed level name and severity number."""
    getattr(logger, method)("event")
    record = find_record(json_logs, "event")

    assert record["level"] == level
    assert record["severity_number"] == severity


def test_foreign_logger_record_is_json(json_logs):
    """Records from stdlib loggers such as uvicorn are rendered as JSON too."""
    logging.getLogger("uvicorn.error").info("Application startup complete.")
    record = find_record(json_logs, "Application startup complete.")

    assert record["message"] == "Application startup complete."
    assert record["logger"] == "uvicorn.error"
    assert record["level"] == "INFO"
    assert record["severity_number"] == 9


def test_request_context_fields_are_attached(json_logs):
    """Request and trace identifiers bound in context reach every record."""
    structlog.contextvars.bind_contextvars(
        request_id="req-42", trace_id="0af7651916cd43dd8448eb211c80319c"
    )
    logger.info("inside request")
    record = find_record(json_logs, "inside request")

    assert record["request_id"] == "req-42"
    assert record["trace_id"] == "0af7651916cd43dd8448eb211c80319c"


def test_secret_values_are_scrubbed(json_logs):
    """Secret-looking keys and strings never reach the log line."""
    logger.info(
        "connecting with token=abc123",
        password="qwerty",
        api_key="k-123",
        authorization="Bearer xyz",
        database_url="postgresql+asyncpg://user:supers3cret@db:5432/x",
    )
    raw = json_logs.readouterr().out
    records = [json.loads(line) for line in raw.strip().splitlines() if line.strip()]
    record = [r for r in records if "password" in r][-1]

    assert "qwerty" not in raw
    assert "k-123" not in raw
    assert "supers3cret" not in raw
    assert "abc123" not in raw
    assert record["password"] == "***"
    assert record["api_key"] == "***"
    assert record["authorization"] == "***"
    assert record["database_url"] == "***"
    assert "***" in record["message"]


def test_session_id_is_hashed(json_logs):
    """Session identifiers are replaced by a stable hash."""
    logger.info("replay", session_id="sess-9")
    record = find_record(json_logs, "replay")

    assert record["session_id"] == hashlib.sha256(b"sess-9").hexdigest()


def test_card_number_in_message_is_masked(json_logs):
    """Card numbers in free text are reduced to first6last4."""
    logger.info("paid with 4242 4242 4242 4242")
    find_record(json_logs, "paid with 424242****4242")


def test_exception_fields_are_structured(json_logs):
    """Exceptions land in error.message and error.stack instead of exc_info."""
    try:
        raise ValueError("boom")
    except ValueError:
        logger.exception("failed to save")
    record = find_record(json_logs, "failed to save")

    assert record["level"] == "ERROR"
    assert record["error.type"] == "ValueError"
    assert record["error.message"] == "boom"
    assert "ValueError: boom" in record["error.stack"]
    assert "exc_info" not in record


def test_access_log_fields_and_request_id_header(json_logs):
    """One access event is logged per request with the correlation fields."""
    client = TestClient(build_app())
    response = client.get("/api/ping", headers={"X-Request-Id": "req-42"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-42"
    record = find_record(json_logs, "http request completed")

    assert record["message"] == "http request completed"
    assert record["method"] == "GET"
    assert record["path"] == "/api/ping"
    assert record["status_code"] == 200
    assert isinstance(record["duration_ms"], (int, float))
    assert record["request_id"] == "req-42"
    assert record["trace_id"]


def test_access_log_uses_traceparent_trace_id(json_logs):
    """The trace id is taken from a valid W3C traceparent header."""
    trace_id = "0af7651916cd43dd8448eb211c80319c"
    client = TestClient(build_app())
    client.get(
        "/api/ping",
        headers={"traceparent": f"00-{trace_id}-b7ad6d7b1f2e3d4c-01"},
    )
    record = find_record(json_logs, "http request completed")

    assert record["trace_id"] == trace_id


def test_access_log_generates_identifiers_when_headers_absent(json_logs):
    """Missing headers still produce a request id and a trace id."""
    client = TestClient(build_app())
    response = client.get("/api/ping")

    assert UUID(response.headers["x-request-id"])
    record = find_record(json_logs, "http request completed")

    assert record["request_id"] == response.headers["x-request-id"]
    assert re.match(r"^[0-9a-f]{32}$", record["trace_id"])


def test_health_requests_are_not_logged(json_logs):
    """Probe traffic does not pollute the access log."""
    client = TestClient(build_app())
    response = client.get("/health/live")

    assert response.status_code == 200
    records = parse_records(json_logs)
    assert not [r for r in records if r.get("message") == "http request completed"]
