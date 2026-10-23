"""Prometheus metrics registry and observation helpers.

The registry is the shared Prometheus one: the client library adds process
and garbage collector collectors and the payload is rendered in OpenMetrics
for the monitoring system, which polls the instances and stores the samples
centrally.
"""

from typing import Any, Mapping

from prometheus_client import REGISTRY, Counter, Gauge, Histogram, Info
from prometheus_client.exposition import choose_encoder

METRICS_PATH = "/metrics"
UNMATCHED_ROUTE = "unmatched"

# Request metrics leave out scrapes and probes: they would distort the rows.
EXCLUDED_PATH_PREFIXES = (METRICS_PATH, "/health")

OPENMETRICS_ACCEPT = "application/openmetrics-text; version=1.0.0; charset=utf-8"

DURATION_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Completed HTTP requests by method, route template and status code.",
    ["method", "route", "status"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds by method and route template.",
    ["method", "route"],
    buckets=DURATION_BUCKETS,
)
HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently being processed by method.",
    ["method"],
)
APP_INFO = Info("app", "Application build information.")

TASKS_CREATED_TOTAL = Counter(
    "nexadesk_tasks_created_total",
    "Tasks created by priority.",
    ["priority"],
)
TASKS_TRANSITIONS_TOTAL = Counter(
    "nexadesk_tasks_transitions_total",
    "Task status change attempts by board direction and outcome.",
    ["direction", "result"],
)
COMMENTS_CREATED_TOTAL = Counter(
    "nexadesk_comments_created_total",
    "Comments created on tasks by presence of resolved mentions.",
    ["has_mentions"],
)
NOTIFICATIONS_CREATED_TOTAL = Counter(
    "nexadesk_notifications_created_total",
    "Notifications created for users by notification type.",
    ["type"],
)
AUTH_ATTEMPTS_TOTAL = Counter(
    "nexadesk_auth_attempts_total",
    "Authentication attempts by outcome.",
    ["result"],
)
SSE_STREAMS_ACTIVE = Gauge(
    "nexadesk_sse_streams_active",
    "Server-sent event streams currently open.",
)
TASKS_OVERDUE = Gauge(
    "nexadesk_tasks_overdue",
    "Live tasks whose due date has passed, refreshed from the database.",
)


def set_app_info(service: str, version: str) -> None:
    """Publish the build information of the running instance.

    Args:
        service: service name label value.
        version: service version label value.

    Returns:
        None
    """
    APP_INFO.info({"service": service, "version": version})


def is_excluded_path(path: str) -> bool:
    """Tell whether a request path is left out of the request metrics.

    Args:
        path: request path.

    Returns:
        bool: True for scrapes and probes, False otherwise.
    """
    return path.startswith(EXCLUDED_PATH_PREFIXES)


def route_template(scope: Mapping[str, Any]) -> str:
    """Pick the low-cardinality route label of one request.

    The matched FastAPI route carries its template, e.g.
    /api/v1/tasks/{task_id}. Requests that matched no route collapse into
    a single label value so that probing random paths cannot inflate the
    metric.

    Args:
        scope: ASGI connection scope of the finished request.

    Returns:
        str: route template or the unmatched placeholder.
    """
    route = scope.get("route")
    return getattr(route, "path", None) or UNMATCHED_ROUTE


def transition_direction(from_position: int | None, to_position: int | None) -> str:
    """Map two board positions to the direction label of a transition.

    Args:
        from_position: position of the current status, None when unknown.
        to_position: position of the target status, None when unknown.

    Returns:
        str: forward, backward, same or unknown.
    """
    if from_position is None or to_position is None:
        return "unknown"
    if to_position > from_position:
        return "forward"
    if to_position < from_position:
        return "backward"
    return "same"


def observe_task_created(priority: str) -> None:
    """Count one created task.

    Args:
        priority: task priority label value.

    Returns:
        None
    """
    TASKS_CREATED_TOTAL.labels(priority=priority).inc()


def observe_task_transition(
    from_position: int | None, to_position: int | None, result: str
) -> None:
    """Count one task status change attempt whatever its outcome.

    Args:
        from_position: position of the current status, None when the task
            was never loaded.
        to_position: position of the target status, None when the target
            was never resolved.
        result: outcome label value: success, conflict or error.

    Returns:
        None
    """
    TASKS_TRANSITIONS_TOTAL.labels(
        direction=transition_direction(from_position, to_position),
        result=result,
    ).inc()


def observe_comment_created(has_mentions: bool) -> None:
    """Count one comment created on a task.

    Args:
        has_mentions: whether the comment body resolved to real mentions.

    Returns:
        None
    """
    COMMENTS_CREATED_TOTAL.labels(has_mentions=str(has_mentions).lower()).inc()


def observe_notification_created(notification_type: str) -> None:
    """Count one notification created for a user.

    Args:
        notification_type: notification type label value.

    Returns:
        None
    """
    NOTIFICATIONS_CREATED_TOTAL.labels(type=notification_type).inc()


def observe_auth_attempt(result: str) -> None:
    """Count one authentication attempt.

    Args:
        result: outcome label value: success, invalid_credentials,
            invalid_token, rate_limited or error.

    Returns:
        None
    """
    AUTH_ATTEMPTS_TOTAL.labels(result=result).inc()


def set_active_sse_streams(count: int) -> None:
    """Publish the number of open realtime streams.

    Args:
        count: streams registered right now.

    Returns:
        None
    """
    SSE_STREAMS_ACTIVE.set(count)


def set_overdue_tasks(count: int) -> None:
    """Publish the overdue task count taken from the last snapshot.

    Args:
        count: live tasks with a due date in the past.

    Returns:
        None
    """
    TASKS_OVERDUE.set(count)


def render_metrics(accept: str = "") -> tuple[bytes, str]:
    """Render the registry for one scrape request.

    OpenMetrics 1.0.0 is the default representation. An Accept header that
    explicitly prefers the classic Prometheus text format negotiates that
    format instead, so plain curl output and older scrapers keep working.

    Args:
        accept: value of the request Accept header, empty when absent.

    Returns:
        tuple[bytes, str]: payload and its content type.
    """
    accept = accept or ""
    encoder, content_type = choose_encoder(accept)
    if "application/openmetrics-text" not in accept and "text/plain" not in accept:
        encoder, content_type = choose_encoder(OPENMETRICS_ACCEPT)
    return encoder(REGISTRY), content_type
