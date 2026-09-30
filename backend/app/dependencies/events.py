from app.events import EventPublisher, NoopPublisher


def get_event_publisher() -> EventPublisher:
    """Return the publisher used by domain services.

    A Redis backed publisher lands with the outbox work; until then events
    are accepted and dropped so services can already share the same seam.

    Returns:
        EventPublisher: placeholder publisher implementation.
    """
    return NoopPublisher()
