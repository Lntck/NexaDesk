"""Unit tests for the health probes."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.health import router as health_router


class FakeService:
    """Stub of a backing service client with a configurable ping result."""

    def __init__(self, result):
        """Store the value ping() will report.

        Args:
            result: value returned by ping, or an exception to raise.
        """
        self.result = result

    async def ping(self):
        """Return the configured ping result.

        Returns:
            object: stored value when it is not an exception.

        Raises:
            Exception: when the stub was built with an exception.
        """
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def build_client(db_result=True, redis_result=True):
    """Build a test client over the health router with stubbed services.

    Args:
        db_result: result of the database ping.
        redis_result: result of the Redis ping.

    Returns:
        TestClient: client bound to a fresh app with fake backing services.
    """
    app = FastAPI()
    app.include_router(health_router, prefix="/health")
    app.state.db = FakeService(db_result)
    app.state.redis = FakeService(redis_result)
    return TestClient(app)


def test_liveness_probe_always_ok():
    """GET /health/live reports 200 without touching backing services."""
    response = build_client(db_result=ConnectionError("down")).get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_aggregate_ok():
    """GET /health reports 200 when every backing service answers."""
    response = build_client().get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "services": {"postgres": "ok", "redis": "ok"},
    }


def test_health_matches_ready():
    """GET /health answers exactly like GET /health/ready."""
    client = build_client()
    aggregate = client.get("/health")
    readiness = client.get("/health/ready")
    assert aggregate.status_code == readiness.status_code
    assert aggregate.json() == readiness.json()


def test_health_reports_database_failure():
    """GET /health reports 503 when the database ping fails."""
    response = build_client(db_result=ConnectionError("down")).get("/health")
    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "services": {"postgres": "error", "redis": "ok"},
    }


def test_health_reports_redis_failure():
    """GET /health/ready reports 503 when the Redis ping fails."""
    response = build_client(redis_result=TimeoutError("down")).get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "services": {"postgres": "ok", "redis": "error"},
    }
