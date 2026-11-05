"""Unit tests for the demo fault injection state, guard and control API."""

import asyncio

import pytest
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app.api.faults import router as faults_router
from app.core import faults
from app.core.faults import FaultConfig, configure, degrade, fault_guard, fault_state
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


def build_client() -> TestClient:
    """Build a test client over an app exposing the fault control API.

    Returns:
        TestClient: client for the /internal/faults endpoints.
    """
    app = FastAPI()
    app.include_router(faults_router)
    return TestClient(app)


def build_guarded_client() -> TestClient:
    """Build a test client over an app guarded like the real API router.

    The route is mounted through include_router dependencies the same way
    main.py mounts the v1 router, so the wiring itself is under test.

    Returns:
        TestClient: client with one fault-guarded route and the metrics
        middleware around it.
    """
    sub = APIRouter()

    @sub.get("/items/{item_id}")
    async def get_item(item_id: int):
        return {"id": item_id}

    app = FastAPI()
    app.include_router(sub, dependencies=[Depends(fault_guard)])
    app.add_middleware(MetricsMiddleware)
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_fault_state():
    """Keep fault injection switched off around every test.

    Yields:
        None: the test runs with a clean state and is reset afterwards.
    """
    fault_state.reset()
    yield
    fault_state.reset()


def test_degrade_picks_error_for_error_mode():
    config = FaultConfig(mode="errors", rate=1.0)

    assert degrade(config, lambda: 0.5) == "error"
    assert degrade(FaultConfig(mode="errors", rate=0.0), lambda: 0.0) == "none"


def test_degrade_picks_latency_for_latency_mode():
    config = FaultConfig(mode="latency")

    assert degrade(config, lambda: 0.0) == "latency"
    assert degrade(config, lambda: 0.999) == "latency"


def test_degrade_mixes_error_and_latency_in_degraded_mode():
    config = FaultConfig(mode="degraded", rate=0.5)

    assert degrade(config, lambda: 0.4) == "error"
    assert degrade(config, lambda: 0.6) == "latency"


def test_degrade_is_off_by_default():
    assert degrade(FaultConfig(), lambda: 0.0) == "none"


def test_configure_clamps_values_and_updates_active_gauge():
    config = configure("errors", rate=5.0, latency_ms=-10)

    assert config == FaultConfig(mode="errors", rate=1.0, latency_ms=0)
    assert sample("nexadesk_fault_injection_active") == 1.0

    fault_state.reset()

    assert fault_state.config == FaultConfig()
    assert sample("nexadesk_fault_injection_active") == 0.0


def test_configure_falls_back_to_off_for_unknown_mode():
    assert configure("broken", rate=1.0, latency_ms=10).mode == "off"


def test_guard_raises_injected_error_and_counts_it():
    configure("errors", rate=1.0)
    before = sample("nexadesk_fault_injected_total", {"kind": "error"})

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(fault_guard())

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "injected fault"
    assert sample("nexadesk_fault_injected_total", {"kind": "error"}) - before == 1.0


def test_guard_delays_instead_of_failing_in_latency_mode(monkeypatch):
    configure("latency", latency_ms=1500)
    slept: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(faults, "_sleeper", fake_sleep)
    before = sample("nexadesk_fault_injected_total", {"kind": "latency"})

    asyncio.run(fault_guard())

    assert slept == [1.5]
    assert sample("nexadesk_fault_injected_total", {"kind": "latency"}) - before == 1.0


def test_guard_is_inert_when_off(monkeypatch):
    async def fail_sleep(seconds: float) -> None:
        raise AssertionError("must not sleep")

    monkeypatch.setattr(faults, "_sleeper", fail_sleep)

    asyncio.run(fault_guard())


def test_guarded_route_answers_503_while_injected():
    client = build_guarded_client()

    assert client.get("/items/7").status_code == 200

    configure("errors", rate=1.0)
    response = client.get("/items/7")

    assert response.status_code == 503
    assert response.json() == {"detail": "injected fault"}
    assert (
        sample(
            "http_requests_total",
            {"method": "GET", "route": "/items/{item_id}", "status": "503"},
        )
        > 0.0
    )

    fault_state.reset()

    assert client.get("/items/7").status_code == 200


def test_control_api_reads_sets_and_resets():
    client = build_client()

    assert client.get("/internal/faults").json() == {
        "mode": "off",
        "rate": 1.0,
        "latency_ms": 2000,
        "active": False,
    }

    response = client.post(
        "/internal/faults",
        json={"mode": "degraded", "rate": 0.5, "latency_ms": 300},
    )

    assert response.status_code == 200
    assert response.json() == {
        "mode": "degraded",
        "rate": 0.5,
        "latency_ms": 300,
        "active": True,
    }

    response = client.delete("/internal/faults")

    assert response.json()["active"] is False
    assert fault_state.config.mode == "off"


def test_control_api_rejects_invalid_values():
    client = build_client()

    assert client.post("/internal/faults", json={"mode": "broken"}).status_code == 422
    assert client.post("/internal/faults", json={"rate": 2.0}).status_code == 422
    assert client.post("/internal/faults", json={"latency_ms": -1}).status_code == 422
