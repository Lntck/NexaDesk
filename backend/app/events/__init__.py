"""Domain event publishing hook.

The publisher contract is a seam between domain services and delivery
backends (Redis Pub/Sub now, transactional outbox later). Services build
events, the publisher takes care of delivery.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class DomainEvent:
    """Immutable domain event passed to an EventPublisher.

    Attributes:
        type: event type key, e.g. "task.status_changed".
        project_id: project the event belongs to, None for global events.
        task_id: task the event belongs to, None when not task scoped.
        actor_id: id of the user who caused the event.
        data: free-form payload with event specific attributes.
    """

    type: str
    project_id: int | None = None
    task_id: int | None = None
    actor_id: int | None = None
    data: dict[str, Any] = field(default_factory=dict)


class EventPublisher(Protocol):
    """Delivery backend for domain events."""

    async def publish(self, event: DomainEvent) -> None:
        """Publish one domain event.

        Args:
            event: event to deliver.
        """
        ...


class NoopPublisher:
    """EventPublisher placeholder used before delivery is wired.

    Keeps service code free from delivery details and allows the outbox
    implementation to be introduced without touching domain services.
    """

    async def publish(self, event: DomainEvent) -> None:
        """Accept and drop the event.

        Args:
            event: event that would be delivered.
        """
        return None
