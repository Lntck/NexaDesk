"""Dedicated metrics endpoint and the background gauge snapshots.

The endpoint is served by its own embedded HTTP server on a separate port so
that the monitoring system reaches the instances without passing through the
public routing. The endpoint carries no authentication on purpose: access
control is a network level concern of the deployment.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING

import uvicorn

from app.core.logger import logger
from app.core.metrics import METRICS_PATH, render_metrics, set_overdue_tasks
from app.crud import TaskCRUD
from app.utils import utcnow

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send

    from app.db import DatabaseClient
    from app.protocols import TaskCRUDProtocol

SNAPSHOT_INTERVAL_S = 60.0

_NOT_FOUND_BODY = b'{"detail":"Not Found","code":"not_found"}'


class MetricsApp:
    """Minimal ASGI application that serves GET /metrics."""

    def __init__(self) -> None:
        """Bind the application to the shared metrics registry."""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Serve the metrics payload and answer everything else with 404.

        Args:
            scope: ASGI connection scope.
            receive: ASGI receive callable.
            send: ASGI send callable.

        Returns:
            None
        """
        if scope["type"] != "http":
            return
        method = scope.get("method", "")
        if method not in ("GET", "HEAD") or scope.get("path") != METRICS_PATH:
            await self._respond(send, 404, _NOT_FOUND_BODY, "application/json")
            return

        payload, content_type = render_metrics(self._accept(scope))
        body = payload if method == "GET" else b""
        await self._respond(send, 200, body, content_type, len(payload))

    @staticmethod
    def _accept(scope: Scope) -> str:
        """Read the Accept header of the scrape request.

        Args:
            scope: ASGI connection scope.

        Returns:
            str: decoded header value, empty when absent.
        """
        for raw_key, raw_value in scope.get("headers", ()):
            if raw_key.lower() == b"accept":
                return str(raw_value.decode("latin-1"))
        return ""

    @staticmethod
    async def _respond(
        send: Send,
        status_code: int,
        body: bytes,
        content_type: str,
        content_length: int | None = None,
    ) -> None:
        """Write one complete HTTP response.

        Args:
            send: ASGI send callable.
            status_code: HTTP status code.
            body: response body.
            content_type: value of the Content-Type header.
            content_length: body length to advertise, defaults to the real
                one so that HEAD answers keep the payload size.

        Returns:
            None
        """
        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": [
                    (b"content-type", content_type.encode("latin-1")),
                    (b"content-length", str(content_length or len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


class _EmbeddedServer(uvicorn.Server):
    """Uvicorn server that leaves process signals to the outer server."""

    @contextlib.contextmanager
    def capture_signals(self):
        """Skip signal capture so the main server keeps owning shutdown.

        Yields:
            None: control to the serving loop.
        """
        yield


class MetricsServer:
    """Embedded HTTP server exposing the metrics endpoint on its own port."""

    def __init__(self, app: ASGIApp, host: str, port: int) -> None:
        """Build the embedded server.

        Args:
            app: ASGI application to serve.
            host: interface to bind.
            port: port to bind.
        """
        self._server = _EmbeddedServer(
            uvicorn.Config(
                app=app,
                host=host,
                port=port,
                log_config=None,
                access_log=False,
                lifespan="off",
            )
        )
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start serving in the background.

        Returns:
            None
        """
        self._task = asyncio.create_task(self._server.serve())

    async def stop(self) -> None:
        """Stop serving and wait until the server exits.

        Returns:
            None
        """
        if self._task is None:
            return
        self._server.should_exit = True
        await self._task
        self._task = None


class OverdueTasksSnapshot:
    """Periodic refresh of the overdue tasks gauge from the database."""

    def __init__(
        self,
        db: DatabaseClient,
        task_crud: TaskCRUDProtocol | None = None,
        interval_s: float = SNAPSHOT_INTERVAL_S,
    ) -> None:
        """Attach the database client and the refresh policy.

        Args:
            db: database client providing sessions.
            task_crud: task row storage, defaults to the real one.
            interval_s: pause between two snapshots.
        """
        self.db = db
        self.task_crud = task_crud or TaskCRUD()
        self.interval_s = interval_s

    async def run(self) -> None:
        """Refresh the gauge every interval until cancelled.

        Returns:
            None
        """
        while True:
            await self.refresh()
            await asyncio.sleep(self.interval_s)

    async def refresh(self) -> None:
        """Read the overdue task count and publish it as a gauge value.

        A failed read keeps the last published value: the monitoring system
        then sees the snapshot as stale rather than as a drop to zero.

        Returns:
            None
        """
        try:
            async with self.db.session_factory() as session:
                count = await self.task_crud.count_overdue(session, utcnow().date())
        except Exception as exc:
            logger.warning(
                "overdue tasks snapshot failed",
                **{"error.type": type(exc).__name__, "error.message": str(exc)},
            )
            return
        set_overdue_tasks(count)
