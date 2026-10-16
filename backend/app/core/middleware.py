"""Request logging middleware.

Binds request correlation identifiers for the duration of one HTTP request,
echoes the request id back to the client and writes a single access event
with the request duration.
"""

import re
import secrets
import time
import uuid
from collections.abc import Iterable

import structlog
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logger import logger

HEALTH_PATH_PREFIX = "/health"
REQUEST_ID_HEADER = "x-request-id"
TRACEPARENT_HEADER = "traceparent"

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_TRACEPARENT_RE = re.compile(r"^[0-9a-f]{2}-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$")


def _header(scope: Scope, name: str) -> str | None:
    """Read one request header value by lowercase name.

    Args:
        scope: ASGI connection scope.
        name: lowercase header name.

    Returns:
        str | None: decoded header value or None when absent.
    """
    headers: Iterable[tuple[bytes, bytes]] = scope.get("headers", ())
    for raw_key, raw_value in headers:
        if raw_key.decode("latin-1").lower() == name:
            return raw_value.decode("latin-1")
    return None


def _pick_request_id(scope: Scope) -> str:
    """Choose the request id for one incoming request.

    A well-formed X-Request-Id header is honoured so that callers can
    correlate their own logs, otherwise a fresh uuid4 is generated.

    Args:
        scope: ASGI connection scope.

    Returns:
        str: request identifier.
    """
    candidate = _header(scope, REQUEST_ID_HEADER)
    if candidate is not None and _REQUEST_ID_RE.match(candidate):
        return candidate
    return str(uuid.uuid4())


def _pick_trace_id(scope: Scope) -> str:
    """Choose the trace id for one incoming request.

    The trace id is taken from a valid W3C traceparent header so that the
    request joins the distributed trace, otherwise a fresh one is generated.

    Args:
        scope: ASGI connection scope.

    Returns:
        str: 32 character trace identifier.
    """
    candidate = _header(scope, TRACEPARENT_HEADER)
    if candidate is not None and _TRACEPARENT_RE.match(candidate):
        return candidate.split("-")[1]
    return secrets.token_hex(16)


class RequestLoggingMiddleware:
    """ASGI middleware that logs one structured access event per request."""

    def __init__(self, app: ASGIApp) -> None:
        """Wrap an ASGI application.

        Args:
            app: application to wrap.
        """
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Bind request context, run the request and log the outcome.

        Args:
            scope: ASGI connection scope.
            receive: ASGI receive callable.
            send: ASGI send callable.

        Returns:
            None
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _pick_request_id(scope)
        trace_id = _pick_trace_id(scope)
        structlog.contextvars.bind_contextvars(request_id=request_id, trace_id=trace_id)

        status_code = 500
        started = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            """Track the response status and echo the request id.

            Args:
                message: ASGI message on its way to the client.

            Returns:
                None
            """
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = MutableHeaders(scope=message)
                headers.append("X-Request-Id", request_id)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 3)
            path = scope.get("path", "")
            if not path.startswith(HEALTH_PATH_PREFIX):
                user_id = scope.get("state", {}).get("user_id")
                logger.info(
                    "http request completed",
                    method=scope.get("method", ""),
                    path=path,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    user_id=user_id,
                )
            structlog.contextvars.clear_contextvars()
