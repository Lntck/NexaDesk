"""Unit tests for the request metrics middleware."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app.core.middleware import MetricsMiddleware


def sample(name: str, labels: dict[str, str] | None = None) -> float:
    """Read one sample of the shared metrics registry.

    Args:
        name: metric name.
        labels: label values identifying the series.

    Returns:
        float: sample value, 0.0 when the series is not registered yet.
    """
    return REGISTRY.get_sample_value(name, labels or {}) or 0.0


def build_client(raise_server_exceptions: bool = False) -> TestClient:
    """Build a test client over an app wrapped in the metrics middleware.

    Args:
        raise_server_exceptions: whether the client re-raises handler errors.

    Returns:
        TestClient: client instrumented with MetricsMiddleware.
    """
    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/items/{item_id}")
    async def get_item(item_id: int):
        return {"id": item_id}

    @app.get("/boom")
    async def boom():
        raise RuntimeError("boom")

    return TestClient(app, raise_server_exceptions=raise_server_exceptions)


def test_request_recorded_by_route_template():
    client = build_client()
    counter_labels = {
        "method": "GET",
        "route": "/items/{item_id}",
        "status": "200",
    }
    histogram_labels = {"method": "GET", "route": "/items/{item_id}"}
    before_counter = sample("http_requests_total", counter_labels)
    before_duration = sample("http_request_duration_seconds_count", histogram_labels)

    response = client.get("/items/42")

    assert response.status_code == 200
    assert sample("http_requests_total", counter_labels) - before_counter == 1.0
    assert (
        sample("http_request_duration_seconds_count", histogram_labels)
        - before_duration
        == 1.0
    )


def test_unmatched_requests_collapse_into_placeholder():
    client = build_client()
    labels = {"method": "GET", "route": "unmatched", "status": "404"}
    before = sample("http_requests_total", labels)

    response = client.get("/missing")

    assert response.status_code == 404
    assert sample("http_requests_total", labels) - before == 1.0


def test_server_errors_recorded():
    client = build_client()
    labels = {"method": "GET", "route": "/boom", "status": "500"}
    before = sample("http_requests_total", labels)

    response = client.get("/boom")

    assert response.status_code == 500
    assert sample("http_requests_total", labels) - before == 1.0


def test_in_progress_gauge_returns_to_zero():
    client = build_client()
    labels = {"method": "GET"}
    before = sample("http_requests_in_progress", labels)

    client.get("/items/7")

    assert sample("http_requests_in_progress", labels) - before == 0.0


@pytest.mark.parametrize("path", ["/metrics", "/health/live", "/health/ready"])
def test_scrapes_and_probes_are_excluded(path):
    client = build_client()
    before = sample("http_requests_total", {"method": "GET", "route": "unmatched"})

    client.get(path)

    delta = (
        sample("http_requests_total", {"method": "GET", "route": "unmatched"}) - before
    )
    assert delta == 0.0
