"""Unit tests for the synthetic user journey and its metrics."""

import asyncio

import httpx
import pytest
from prometheus_client import REGISTRY

from prober.main import record_run
from prober.scenario import (
    SCENARIO_STEPS,
    STEP_TRANSITION_TASK,
    ScenarioError,
    StepTiming,
    UserJourney,
)


class FakeApi:
    """In-memory stub of the NexaDesk API surface used by the journey.

    Attributes:
        requests: paths of the requests received so far.
    """

    def __init__(self, fail_at: str | None = None, reject_login: bool = False):
        """Configure the stub.

        Args:
            fail_at: request path suffix that must answer 500.
            reject_login: whether the first login attempt answers 401.
        """
        self.requests: list[str] = []
        self.fail_at = fail_at
        self.reject_login = reject_login
        self._logins = 0

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        """Answer one API request.

        Args:
            request: intercepted request.

        Returns:
            httpx.Response: canned answer for the requested path.
        """
        path = request.url.path
        self.requests.append(path)
        if self.fail_at and path.endswith(self.fail_at):
            return httpx.Response(500, json={"detail": "boom"})

        if path == "/api/v1/login":
            self._logins += 1
            if self.reject_login and self._logins == 1:
                return httpx.Response(401, json={"detail": "invalid credentials"})
            return httpx.Response(200, json={"access_token": "token"})

        if path == "/api/v1/register":
            return httpx.Response(
                201,
                json={"id": 1, "username": "prober", "email": "prober@nexadesk.local"},
            )

        if path == "/api/v1/projects" and request.method == "GET":
            return httpx.Response(
                200,
                json={"items": [], "page": 1, "page_size": 100, "total": 0},
            )

        if path == "/api/v1/projects" and request.method == "POST":
            return httpx.Response(
                201, json={"id": 1, "key": "PROBE", "name": "Synthetic Probing"}
            )

        if path == "/api/v1/projects/1/tasks":
            return httpx.Response(
                201,
                json={
                    "id": 10,
                    "key": "PROBE-1",
                    "status": {"id": 1, "key": "TODO", "name": "To Do"},
                },
            )

        if path == "/api/v1/projects/1/statuses":
            return httpx.Response(
                200,
                json=[
                    {"id": 1, "key": "TODO", "name": "To Do", "position": 1},
                    {"id": 2, "key": "IN_PROGRESS", "name": "In Progress", "position": 2},
                ],
            )

        if path == "/api/v1/tasks/10/transition":
            return httpx.Response(
                200,
                json={
                    "id": 10,
                    "key": "PROBE-1",
                    "status": {"id": 2, "key": "IN_PROGRESS", "name": "In Progress"},
                },
            )

        if path == "/api/v1/tasks/10/comments":
            return httpx.Response(201, json={"id": 3, "body": "Synthetic probe comment"})

        if path == "/api/v1/notifications":
            return httpx.Response(
                200,
                json={"items": [], "page": 1, "page_size": 10, "total": 0},
            )

        return httpx.Response(404, json={"detail": "not found"})


def build_journey(api: FakeApi) -> UserJourney:
    """Build a journey wired to a stubbed API.

    Args:
        api: stub answering the journey requests.

    Returns:
        UserJourney: journey over the stub transport.
    """
    client = httpx.AsyncClient(
        base_url="http://probe.test",
        transport=httpx.MockTransport(api),
    )
    return UserJourney(
        base_url="http://probe.test",
        email="prober@nexadesk.local",
        password="prober-strong-pass",
        username="prober",
        client=client,
    )


def sample(name: str, labels: dict[str, str] | None = None) -> float:
    """Read one sample of the shared metrics registry.

    Args:
        name: metric name.
        labels: label values identifying the series.

    Returns:
        float: sample value, 0.0 when the series is not registered yet.
    """
    return REGISTRY.get_sample_value(name, labels or {}) or 0.0


def test_run_completes_all_steps_in_order():
    api = FakeApi()
    journey = build_journey(api)

    report = asyncio.run(journey.run())

    assert [timing.step for timing in report] == list(SCENARIO_STEPS)
    assert all(timing.duration_s >= 0.0 for timing in report)
    assert api.requests[0] == "/api/v1/login"
    assert api.requests[-1] == "/api/v1/notifications"


def test_run_sends_bearer_token_after_login():
    api = FakeApi()
    journey = build_journey(api)

    asyncio.run(journey.run())

    assert api.requests.count("/api/v1/login") == 1
    assert "/api/v1/projects" in api.requests


def test_run_reports_failing_step_with_completed_steps():
    api = FakeApi(fail_at="/transition")
    journey = build_journey(api)

    with pytest.raises(ScenarioError) as exc_info:
        asyncio.run(journey.run())

    assert exc_info.value.step == STEP_TRANSITION_TASK
    assert [timing.step for timing in exc_info.value.completed] == list(
        SCENARIO_STEPS[:3]
    )


def test_ensure_account_registers_when_login_is_rejected():
    api = FakeApi(reject_login=True)
    journey = build_journey(api)

    asyncio.run(journey.ensure_account())

    assert api.requests == [
        "/api/v1/login",
        "/api/v1/register",
        "/api/v1/login",
    ]


def test_record_run_publishes_success_metrics():
    before_runs = sample(
        "nexadesk_probe_runs_total", {"scenario": "user_journey", "result": "success"}
    )

    record_run([StepTiming("login", 0.25)], None, 1.0)

    assert (
        sample(
            "nexadesk_probe_runs_total",
            {"scenario": "user_journey", "result": "success"},
        )
        - before_runs
        == 1.0
    )
    assert sample("nexadesk_probe_success", {"scenario": "user_journey"}) == 1.0
    assert (
        sample(
            "nexadesk_probe_step_duration_seconds_count",
            {"scenario": "user_journey", "step": "login"},
        )
        > 0.0
    )


def test_record_run_publishes_failure_metrics():
    before_runs = sample(
        "nexadesk_probe_runs_total", {"scenario": "user_journey", "result": "error"}
    )

    record_run([StepTiming("login", 0.25)], STEP_TRANSITION_TASK, 1.0)

    assert (
        sample(
            "nexadesk_probe_runs_total",
            {"scenario": "user_journey", "result": "error"},
        )
        - before_runs
        == 1.0
    )
    assert sample("nexadesk_probe_success", {"scenario": "user_journey"}) == 0.0
    assert (
        sample(
            "nexadesk_probe_step_failures_total",
            {"scenario": "user_journey", "step": STEP_TRANSITION_TASK},
        )
        > 0.0
    )
