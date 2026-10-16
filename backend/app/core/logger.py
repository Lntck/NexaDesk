"""Structured JSON logging for the backend.

Every record leaves the process as a single JSON line on stdout carrying the
agreed observability fields: timestamp, level, severity_number, message,
service identity, request correlation identifiers and error details. Values
that may hold secrets or payment data are scrubbed before rendering.
"""

import hashlib
import logging
import os
import re
import socket
import sys
import traceback
from datetime import datetime, timezone
from typing import Any

import structlog

from app.core.constants import SERVICE_NAME, SERVICE_VERSION

SEVERITY_BY_LEVEL: dict[str, int] = {
    "TRACE": 1,
    "DEBUG": 5,
    "INFO": 9,
    "WARNING": 13,
    "ERROR": 17,
    "CRITICAL": 21,
}

LEVEL_ALIASES: dict[str, str] = {
    "WARN": "WARNING",
    "FATAL": "CRITICAL",
    "EXCEPTION": "ERROR",
    "MSG": "INFO",
    "NOTICE": "INFO",
}

REDACTED = "***"

SENSITIVE_KEY_MARKERS: tuple[str, ...] = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "database_url",
    "private_key",
    "credential",
)

SENSITIVE_KEYS: frozenset[str] = frozenset(
    {"cvv", "cvc", "pin", "pan", "card_number", "cardnumber"}
)

HASHED_KEYS: frozenset[str] = frozenset({"session_id", "sessionid"})

_URI_CREDENTIALS_RE = re.compile(
    r"((?:[a-z][a-z0-9+.-]*)://[^:/\s@]+):([^@\s]+)@", re.IGNORECASE
)
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{3,}\.[A-Za-z0-9_-]{3,}\.[A-Za-z0-9_-]{3,}")
_KEY_VALUE_RE = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|authorization)"
    r"(\s*[=:]\s*)([^\s,;&]+)"
)
_PAN_CANDIDATE_RE = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")


def _env(name: str, default: str) -> str:
    """Read an environment variable with a fallback.

    Args:
        name: environment variable name.
        default: value used when the variable is not set.

    Returns:
        str: configured or default value.
    """
    return os.environ.get(name, default)


def hash_identifier(value: Any) -> str:
    """Hash an identifier so logs can correlate without exposing the raw value.

    Args:
        value: identifier to hash.

    Returns:
        str: sha256 hex digest of the identifier.
    """
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _luhn(digits: str) -> bool:
    """Check a digit string with the Luhn algorithm.

    Args:
        digits: candidate card number digits.

    Returns:
        bool: True when the digits form a valid payment card number.
    """
    total = 0
    for index, char in enumerate(reversed(digits)):
        digit = int(char)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _mask_pan(match: re.Match[str]) -> str:
    """Mask a card number candidate down to first6last4.

    Args:
        match: regex match holding the candidate number.

    Returns:
        str: masked number when the candidate passes the Luhn check,
        otherwise the untouched text.
    """
    raw = match.group(0)
    digits = re.sub(r"\D", "", raw)
    if 13 <= len(digits) <= 19 and _luhn(digits):
        return f"{digits[:6]}****{digits[-4:]}"
    return raw


def scrub_text(value: str) -> str:
    """Scrub secret-looking substrings out of a free-form string.

    Masks connection string credentials, bearer tokens, JWTs, inline
    key/value secrets and reduces card numbers to first6last4.

    Args:
        value: text to scrub.

    Returns:
        str: scrubbed text.
    """
    text = _URI_CREDENTIALS_RE.sub(lambda m: f"{m.group(1)}:{REDACTED}@", value)
    text = _BEARER_RE.sub(f"Bearer {REDACTED}", text)
    text = _JWT_RE.sub(REDACTED, text)
    text = _KEY_VALUE_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}", text)
    return _PAN_CANDIDATE_RE.sub(_mask_pan, text)


def _scrub_value(value: Any) -> Any:
    """Scrub strings inside an arbitrary log value recursively.

    Args:
        value: scalar, list or mapping taken from an event dictionary.

    Returns:
        Any: value with every string scrubbed.
    """
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, dict):
        return {key: _scrub_pair(key, item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_scrub_value(item) for item in value]
    return value


def _scrub_pair(key: Any, value: Any) -> Any:
    """Scrub one event entry depending on its key.

    Secret-looking keys are redacted outright, session identifiers are
    hashed, everything else falls back to value scrubbing.

    Args:
        key: event dictionary key.
        value: event dictionary value.

    Returns:
        Any: safe replacement value.
    """
    lowered = str(key).lower()
    if lowered in HASHED_KEYS and value is not None:
        return hash_identifier(value)
    if lowered in SENSITIVE_KEYS or any(
        marker in lowered for marker in SENSITIVE_KEY_MARKERS
    ):
        return REDACTED if value is not None else value
    return _scrub_value(value)


def use_message_key(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Rename the structlog event key to the shared message field.

    Args:
        logger: wrapped logger instance.
        method_name: log method name.
        event_dict: event being processed.

    Returns:
        dict: event with the message key set.
    """
    if "event" in event_dict:
        event_dict["message"] = event_dict.pop("event")
    return event_dict


def add_level_fields(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add the level name and the numeric severity to the event.

    Args:
        logger: wrapped logger instance.
        method_name: log method name.
        event_dict: event being processed.

    Returns:
        dict: event with level and severity_number set.
    """
    record = event_dict.get("_record")
    raw = getattr(record, "levelname", None) or method_name or "info"
    level = LEVEL_ALIASES.get(raw.upper(), raw.upper())
    event_dict["level"] = level
    event_dict["severity_number"] = SEVERITY_BY_LEVEL.get(
        level, SEVERITY_BY_LEVEL["INFO"]
    )
    return event_dict


def add_timestamp(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add an ISO 8601 UTC timestamp with millisecond precision.

    Args:
        logger: wrapped logger instance.
        method_name: log method name.
        event_dict: event being processed.

    Returns:
        dict: event with the timestamp key set.
    """
    now = datetime.now(timezone.utc)
    event_dict["timestamp"] = (
        now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
    )
    return event_dict


def add_logger_name(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add the emitting logger name to the event.

    Args:
        logger: wrapped logger instance.
        method_name: log method name.
        event_dict: event being processed.

    Returns:
        dict: event with the logger key set when a name is known.
    """
    record = event_dict.get("_record")
    name = getattr(record, "name", None) or getattr(logger, "name", None)
    if name:
        event_dict["logger"] = name
    return event_dict


def add_error_fields(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Move exception details into error.message and error.stack.

    Args:
        logger: wrapped logger instance.
        method_name: log method name.
        event_dict: event being processed, possibly carrying exc_info.

    Returns:
        dict: event with error fields instead of the raw exc_info payload.
    """
    exc_info = event_dict.pop("exc_info", None)
    if exc_info is True:
        exc_info = sys.exc_info()
    if isinstance(exc_info, BaseException):
        exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
    if isinstance(exc_info, tuple) and exc_info[0] is not None:
        exc_type, exc_value, tb = exc_info
        event_dict["error.type"] = exc_type.__name__
        event_dict["error.message"] = str(exc_value)
        event_dict["error.stack"] = "".join(
            traceback.format_exception(exc_type, exc_value, tb)
        ).rstrip()
    elif isinstance(exc_info, str):
        event_dict["error.stack"] = exc_info

    stack_info = event_dict.pop("stack_info", None)
    if stack_info:
        event_dict["error.stack"] = stack_info
    return event_dict


def scrub_sensitive(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Scrub every value of the event before rendering.

    Args:
        logger: wrapped logger instance.
        method_name: log method name.
        event_dict: event being processed.

    Returns:
        dict: event with all values made safe for storage.
    """
    for key, value in list(event_dict.items()):
        event_dict[key] = _scrub_pair(key, value)
    return event_dict


def add_service_context(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add the service identity fields to the event.

    Args:
        logger: wrapped logger instance.
        method_name: log method name.
        event_dict: event being processed.

    Returns:
        dict: event with service and deployment fields set.
    """
    hostname = socket.gethostname()
    event_dict["service.name"] = _env("SERVICE_NAME", SERVICE_NAME)
    event_dict["service.version"] = _env("SERVICE_VERSION", SERVICE_VERSION)
    event_dict["deployment.environment.name"] = _env(
        "DEPLOYMENT_ENVIRONMENT_NAME", "local"
    )
    event_dict["host.name"] = hostname
    event_dict["k8s.pod.name"] = _env("K8S_POD_NAME", _env("HOSTNAME", hostname))
    return event_dict


class StdoutHandler(logging.StreamHandler):
    """Stream handler that writes to the current process stdout.

    The stream is resolved per record, so any later replacement of stdout
    by a supervisor or a test harness is picked up automatically.
    """

    def __init__(self) -> None:
        """Initialize the handler without pinning a stream."""
        logging.Handler.__init__(self)

    @property
    def stream(self) -> Any:
        """Return the stdout stream active at call time.

        Returns:
            Any: current sys.stdout object.
        """
        return sys.stdout

    @stream.setter
    def stream(self, value: Any) -> None:
        """Ignore stream assignment done by the base class.

        Args:
            value: ignored, the stream is resolved dynamically.

        Returns:
            None
        """
        return


def build_shared_processors() -> list:
    """Build the processor chain shared by app and foreign loggers.

    Returns:
        list: processors applied to every record before rendering.
    """
    return [
        use_message_key,
        structlog.contextvars.merge_contextvars,
        add_level_fields,
        add_timestamp,
        add_logger_name,
        add_error_fields,
        scrub_sensitive,
        add_service_context,
    ]


def configure_logging(level: str | None = None) -> None:
    """Route application and uvicorn logging into JSON lines on stdout.

    Args:
        level: root log level name, defaults to the LOG_LEVEL environment
            variable and finally to INFO.

    Returns:
        None
    """
    shared = build_shared_processors()
    structlog.configure(
        processors=shared + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(sort_keys=False),
        ],
        foreign_pre_chain=shared,
    )
    handler = StdoutHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(_resolve_level(level))

    for name in ("uvicorn", "uvicorn.error", "uvicorn.asgi"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True

    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()
    access_logger.propagate = False


def _resolve_level(level: str | None) -> int:
    """Resolve a log level name into its numeric value.

    Args:
        level: explicit level name, may be None.

    Returns:
        int: numeric logging level.

    Raises:
        ValueError: when the level name is unknown.
    """
    name = (level or _env("LOG_LEVEL", "INFO")).upper()
    value = logging.getLevelNamesMapping().get(name)
    if value is None:
        raise ValueError(f"unknown log level: {name}")
    return value


logger = structlog.get_logger("nexadesk")
