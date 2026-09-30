from fastapi import Request

from app.events import EventPublisher, NoopPublisher
from app.events.streams import ConnectionManager


def get_event_publisher(request: Request) -> EventPublisher:
    """Return the publisher used by domain services.

    The lifespan wires a Redis backed publisher on app.state; without it
    events are accepted and dropped so tests and tooling keep working.

    Args:
        request: incoming request carrying the application state.

    Returns:
        EventPublisher: publisher delivering domain events.
    """
    publisher: EventPublisher | None = getattr(request.app.state, "publisher", None)
    if publisher is None:
        return NoopPublisher()
    return publisher


def get_connection_manager(request: Request) -> ConnectionManager:
    """Return the registry of open SSE streams.

    Args:
        request: incoming request carrying the application state.

    Returns:
        ConnectionManager: connection registry shared by the process.
    """
    manager: ConnectionManager = request.app.state.connections
    return manager
