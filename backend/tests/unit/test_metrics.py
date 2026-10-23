"""Unit tests for the metrics helpers and the business metric hooks."""

import pytest
from fakeredis.aioredis import FakeRedis
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core import Settings
from app.core.metrics import (
    is_excluded_path,
    observe_auth_attempt,
    observe_comment_created,
    observe_notification_created,
    observe_task_created,
    observe_task_transition,
    render_metrics,
    route_template,
    set_active_sse_streams,
    set_overdue_tasks,
    transition_direction,
)
from app.events.streams import ConnectionManager
from app.exceptions import (
    InvalidCredentials,
    InvalidTransition,
    TaskNotFound,
    TokenInvalidError,
    register_exception_handlers,
)
from app.schemas import CommentCreate, TaskAssign, TaskCreate, TaskTransition
from app.services import AuthService, UserService
from tests.fakes import FakeUserCRUD
from tests.fakes.world import build_world


def sample(name: str, labels: dict[str, str] | None = None) -> float:
    """Read one sample of the shared metrics registry.

    Args:
        name: metric name.
        labels: label values identifying the series.

    Returns:
        float: sample value, 0.0 when the series is not registered yet.
    """
    return REGISTRY.get_sample_value(name, labels or {}) or 0.0


def test_render_metrics_defaults_to_openmetrics():
    payload, content_type = render_metrics("")

    assert content_type.startswith("application/openmetrics-text")
    assert b"nexadesk_tasks_created" in payload
    assert payload.endswith(b"# EOF\n")


def test_render_metrics_wildcard_accept_uses_openmetrics():
    _, content_type = render_metrics("*/*")

    assert content_type.startswith("application/openmetrics-text")


def test_render_metrics_prefers_openmetrics_when_both_accepted():
    accept = (
        "application/openmetrics-text;version=1.0.0,"
        "text/plain;version=0.0.4;q=0.5,*/*;q=0.1"
    )
    _, content_type = render_metrics(accept)

    assert content_type.startswith("application/openmetrics-text")


def test_render_metrics_serves_classic_text_on_explicit_accept():
    payload, content_type = render_metrics("text/plain; version=0.0.4")

    assert content_type.startswith("text/plain")
    assert b"nexadesk_tasks_created" in payload
    assert not payload.endswith(b"# EOF\n")


@pytest.mark.parametrize(
    "from_position,to_position,expected",
    [
        (1, 2, "forward"),
        (2, 1, "backward"),
        (2, 2, "same"),
        (None, 2, "unknown"),
        (1, None, "unknown"),
        (None, None, "unknown"),
    ],
)
def test_transition_direction(from_position, to_position, expected):
    assert transition_direction(from_position, to_position) == expected


def test_observe_task_created_labels_priority():
    before = sample("nexadesk_tasks_created_total", {"priority": "HIGH"})

    observe_task_created("HIGH")

    delta = sample("nexadesk_tasks_created_total", {"priority": "HIGH"}) - before
    assert delta == 1.0


def test_observe_task_transition_labels_direction_and_result():
    before = sample(
        "nexadesk_tasks_transitions_total",
        {"direction": "backward", "result": "success"},
    )

    observe_task_transition(3, 1, "success")

    delta = (
        sample(
            "nexadesk_tasks_transitions_total",
            {"direction": "backward", "result": "success"},
        )
        - before
    )
    assert delta == 1.0


def test_observe_comment_created_labels_has_mentions():
    before_true = sample("nexadesk_comments_created_total", {"has_mentions": "true"})
    before_false = sample("nexadesk_comments_created_total", {"has_mentions": "false"})

    observe_comment_created(True)
    observe_comment_created(False)

    assert (
        sample("nexadesk_comments_created_total", {"has_mentions": "true"})
        - (before_true)
        == 1.0
    )
    assert (
        sample("nexadesk_comments_created_total", {"has_mentions": "false"})
        - (before_false)
        == 1.0
    )


def test_observe_notification_created_labels_type():
    labels = {"type": "comment.mentioned"}
    before = sample("nexadesk_notifications_created_total", labels)

    observe_notification_created("comment.mentioned")

    assert sample("nexadesk_notifications_created_total", labels) - before == 1.0


def test_observe_auth_attempt_labels_result():
    labels = {"result": "rate_limited"}
    before = sample("nexadesk_auth_attempts_total", labels)

    observe_auth_attempt("rate_limited")

    assert sample("nexadesk_auth_attempts_total", labels) - before == 1.0


def test_set_active_sse_streams_publishes_value():
    set_active_sse_streams(3)

    assert sample("nexadesk_sse_streams_active") == 3.0


def test_set_overdue_tasks_publishes_value():
    set_overdue_tasks(5)

    assert sample("nexadesk_tasks_overdue") == 5.0


def test_route_template_uses_matched_pattern():
    scope = {"route": type("Route", (), {"path": "/api/v1/tasks/{task_id}"})()}

    assert route_template(scope) == "/api/v1/tasks/{task_id}"


def test_route_template_falls_back_to_placeholder():
    assert route_template({}) == "unmatched"


@pytest.mark.parametrize(
    "path,excluded",
    [
        ("/metrics", True),
        ("/health", True),
        ("/health/ready", True),
        ("/api/v1/tasks", False),
        ("/", False),
    ],
)
def test_is_excluded_path(path, excluded):
    assert is_excluded_path(path) is excluded


@pytest.mark.asyncio
async def test_create_task_counts_priority():
    world = await build_world()
    before = sample("nexadesk_tasks_created_total", {"priority": "CRITICAL"})

    await world.task_service.create_task(
        None,
        3,
        1,
        TaskCreate(title="Urgent fix", priority="CRITICAL"),
    )

    delta = sample("nexadesk_tasks_created_total", {"priority": "CRITICAL"}) - before
    assert delta == 1.0


@pytest.mark.asyncio
async def test_transition_counts_forward_success():
    world = await build_world()
    card = await world.task_service.create_task(
        None, 3, 1, TaskCreate(title="Card", status_id=1)
    )
    labels = {"direction": "forward", "result": "success"}
    before = sample("nexadesk_tasks_transitions_total", labels)

    await world.task_service.transition(None, 3, card.id, TaskTransition(status_id=2))

    assert sample("nexadesk_tasks_transitions_total", labels) - before == 1.0


@pytest.mark.asyncio
async def test_transition_counts_backward_success():
    world = await build_world()
    card = await world.task_service.create_task(
        None, 3, 1, TaskCreate(title="Card", status_id=2)
    )
    labels = {"direction": "backward", "result": "success"}
    before = sample("nexadesk_tasks_transitions_total", labels)

    await world.task_service.transition(None, 3, card.id, TaskTransition(status_id=1))

    assert sample("nexadesk_tasks_transitions_total", labels) - before == 1.0


@pytest.mark.asyncio
async def test_transition_counts_conflict_on_invalid_move():
    world = await build_world()
    card = await world.task_service.create_task(
        None, 3, 1, TaskCreate(title="Card", status_id=1)
    )
    labels = {"direction": "forward", "result": "conflict"}
    before = sample("nexadesk_tasks_transitions_total", labels)

    with pytest.raises(InvalidTransition):
        await world.task_service.transition(
            None, 3, card.id, TaskTransition(status_id=4)
        )

    assert sample("nexadesk_tasks_transitions_total", labels) - before == 1.0


@pytest.mark.asyncio
async def test_transition_counts_error_on_missing_task():
    world = await build_world()
    labels = {"direction": "unknown", "result": "error"}
    before = sample("nexadesk_tasks_transitions_total", labels)

    with pytest.raises(TaskNotFound):
        await world.task_service.transition(None, 3, 999, TaskTransition(status_id=1))

    assert sample("nexadesk_tasks_transitions_total", labels) - before == 1.0


@pytest.mark.asyncio
async def test_comment_counts_has_mentions():
    world = await build_world()
    card = await world.task_service.create_task(
        None, 3, 1, TaskCreate(title="Card", status_id=1)
    )
    before_true = sample("nexadesk_comments_created_total", {"has_mentions": "true"})
    before_false = sample("nexadesk_comments_created_total", {"has_mentions": "false"})

    await world.comment_service.create_comment(
        None, 3, card.id, CommentCreate(body="Please look, @owner")
    )
    await world.comment_service.create_comment(
        None, 3, card.id, CommentCreate(body="No mentions here")
    )

    assert (
        sample("nexadesk_comments_created_total", {"has_mentions": "true"})
        - before_true
        == 1.0
    )
    assert (
        sample("nexadesk_comments_created_total", {"has_mentions": "false"})
        - before_false
        == 1.0
    )


@pytest.mark.asyncio
async def test_assignment_counts_notification_type():
    world = await build_world()
    card = await world.task_service.create_task(
        None, 1, 1, TaskCreate(title="Card", status_id=1)
    )
    labels = {"type": "task.assigned"}
    before = sample("nexadesk_notifications_created_total", labels)

    await world.task_service.assign(None, 1, card.id, TaskAssign(user_id=3))

    assert sample("nexadesk_notifications_created_total", labels) - before == 1.0


@pytest.mark.asyncio
async def test_auth_attempts_counted_by_result(test_settings: Settings, dummy_session):
    service = AuthService(UserService(FakeUserCRUD()), test_settings)
    redis_client = FakeRedis()
    before_success = sample("nexadesk_auth_attempts_total", {"result": "success"})
    before_invalid = sample(
        "nexadesk_auth_attempts_total", {"result": "invalid_credentials"}
    )

    await service.auth_user(dummy_session, redis_client, "duplicate", "password")

    with pytest.raises(InvalidCredentials):
        await service.auth_user(dummy_session, redis_client, "duplicate", "wrong")

    assert (
        sample("nexadesk_auth_attempts_total", {"result": "success"}) - (before_success)
        == 1.0
    )
    assert (
        sample("nexadesk_auth_attempts_total", {"result": "invalid_credentials"})
        - before_invalid
        == 1.0
    )


@pytest.mark.asyncio
async def test_refresh_token_failure_counted_as_invalid_token(
    test_settings: Settings, dummy_session
):
    service = AuthService(UserService(FakeUserCRUD()), test_settings)
    labels = {"result": "invalid_token"}
    before = sample("nexadesk_auth_attempts_total", labels)

    with pytest.raises(TokenInvalidError):
        await service.refresh_token(dummy_session, FakeRedis(), "garbage")

    assert sample("nexadesk_auth_attempts_total", labels) - before == 1.0


def _rate_limited_app() -> FastAPI:
    """Build an app whose endpoints throttle after one request per minute.

    Returns:
        FastAPI: application with its own limiter and the contract handlers.
    """
    rate_limiter = Limiter(key_func=get_remote_address)
    app = FastAPI()
    app.state.limiter = rate_limiter
    register_exception_handlers(app)

    @app.post("/api/v1/login")
    @rate_limiter.limit("1/minute")
    async def login(request: Request):
        return {"ok": True}

    @app.post("/api/v1/tasks")
    @rate_limiter.limit("1/minute")
    async def create_task(request: Request):
        return {"ok": True}

    return app


def test_rate_limited_auth_attempt_counted():
    client = TestClient(_rate_limited_app())
    labels = {"result": "rate_limited"}
    before = sample("nexadesk_auth_attempts_total", labels)

    assert client.post("/api/v1/login").status_code == 200
    response = client.post("/api/v1/login")

    assert response.status_code == 429
    assert response.json() == {"detail": "Rate limit exceeded", "code": "rate_limited"}
    assert sample("nexadesk_auth_attempts_total", labels) - before == 1.0


def test_rate_limited_non_auth_request_not_counted():
    client = TestClient(_rate_limited_app())
    labels = {"result": "rate_limited"}
    before = sample("nexadesk_auth_attempts_total", labels)

    assert client.post("/api/v1/tasks").status_code == 200
    response = client.post("/api/v1/tasks")

    assert response.status_code == 429
    assert sample("nexadesk_auth_attempts_total", labels) - before == 0.0


def test_sse_streams_gauge_tracks_registry():
    manager = ConnectionManager()

    first = manager.register(1, 1, 10)
    manager.register(2, 1, 10)
    assert sample("nexadesk_sse_streams_active") == 2.0

    manager.unregister(first)
    assert sample("nexadesk_sse_streams_active") == 1.0
