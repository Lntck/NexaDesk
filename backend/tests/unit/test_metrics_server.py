"""Unit tests for the dedicated metrics endpoint and the gauge snapshots."""

import asyncio
import socket

import httpx
import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app.core.metrics import set_overdue_tasks
from app.core.metrics_server import MetricsApp, MetricsServer, OverdueTasksSnapshot


def sample(name: str, labels: dict[str, str] | None = None) -> float:
    """Read one sample of the shared metrics registry.

    Args:
        name: metric name.
        labels: label values identifying the series.

    Returns:
        float: sample value, 0.0 when the series is not registered yet.
    """
    return REGISTRY.get_sample_value(name, labels or {}) or 0.0


class StubSession:
    """Async context manager standing in for one database session."""

    async def __aenter__(self):
        """Enter the session placeholder.

        Returns:
            None: the session carries no state.
        """
        return None

    async def __aexit__(self, *exc):
        """Leave the session placeholder.

        Args:
            *exc: ignored exception info.

        Returns:
            bool: False so that exceptions keep propagating.
        """
        return False


class StubDB:
    """Database client stub handing out placeholder sessions."""

    def session_factory(self):
        """Open one placeholder session.

        Returns:
            StubSession: session placeholder.
        """
        return StubSession()


class FailingDB:
    """Database client stub whose sessions never open."""

    def session_factory(self):
        """Refuse to open a session.

        Raises:
            ConnectionError: always.
        """
        raise ConnectionError("database is down")


class StubTaskCRUD:
    """Task storage stub with a fixed overdue count."""

    def __init__(self, count: int):
        """Store the count to report.

        Args:
            count: overdue tasks the stub reports.
        """
        self.count = count
        self.seen_today = None

    async def count_overdue(self, session, today) -> int:
        """Report the configured overdue count.

        Args:
            session: unused session placeholder.
            today: current date passed by the snapshot.

        Returns:
            int: configured overdue count.
        """
        self.seen_today = today
        return self.count


def test_metrics_endpoint_serves_openmetrics_by_default():
    client = TestClient(MetricsApp())

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/openmetrics-text")
    assert b"nexadesk_tasks_overdue" in response.content
    assert response.content.endswith(b"# EOF\n")


def test_metrics_endpoint_negotiates_classic_text():
    client = TestClient(MetricsApp())

    response = client.get("/metrics", headers={"Accept": "text/plain; version=0.0.4"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert not response.content.endswith(b"# EOF\n")


def test_metrics_endpoint_answers_head_without_body():
    client = TestClient(MetricsApp())

    response = client.head("/metrics")

    assert response.status_code == 200
    assert response.content == b""
    assert int(response.headers["content-length"]) > 0


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/"),
        ("get", "/other"),
        ("post", "/metrics"),
    ],
)
def test_metrics_endpoint_rejects_everything_else(method, path):
    client = TestClient(MetricsApp())

    response = getattr(client, method)(path)

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found", "code": "not_found"}


def test_snapshot_refresh_publishes_overdue_count():
    task_crud = StubTaskCRUD(7)
    snapshot = OverdueTasksSnapshot(StubDB(), task_crud=task_crud, interval_s=0)

    asyncio.run(snapshot.refresh())

    assert sample("nexadesk_tasks_overdue") == 7.0
    assert task_crud.seen_today is not None


def test_snapshot_refresh_keeps_last_value_on_failure():
    set_overdue_tasks(4)
    snapshot = OverdueTasksSnapshot(FailingDB(), interval_s=0)

    asyncio.run(snapshot.refresh())

    assert sample("nexadesk_tasks_overdue") == 4.0


@pytest.mark.asyncio
async def test_metrics_server_serves_on_its_own_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]

    server = MetricsServer(MetricsApp(), "127.0.0.1", port)
    await server.start()
    try:
        async with httpx.AsyncClient() as client:
            for _ in range(40):
                try:
                    response = await client.get(f"http://127.0.0.1:{port}/metrics")
                    break
                except httpx.ConnectError:
                    await asyncio.sleep(0.05)
            else:
                pytest.fail("metrics server did not start")
    finally:
        await server.stop()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/openmetrics-text")
