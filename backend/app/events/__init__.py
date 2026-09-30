"""Domain event publishing hook.

The publisher contract is a seam between domain services and delivery
backends (Redis Pub/Sub now, transactional outbox later). Services build
events, the publisher takes care of delivery. Events are queued on the
database session and published strictly after commit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession
from uuid_utils import uuid7

from app.models import ActivityEvent
from app.utils import utcnow

if TYPE_CHECKING:
    from app.enums import ActivityEventType
    from app.protocols.activity import ActivityCRUDProtocol

QUEUE_KEY = "domain_events"


@dataclass(frozen=True)
class DomainEvent:
    """Immutable domain event passed to an EventPublisher.

    Attributes:
        id: opaque sortable id of the matching activity entry.
        type: event type key, e.g. "task.status_changed".
        project_id: project the event belongs to, None for global events.
        task_id: task the event belongs to, None when not task scoped.
        actor_id: id of the user who caused the event.
        data: free-form payload with event specific attributes.
    """

    type: str
    id: str | None = None
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


def queue_event(session: AsyncSession | None, event: DomainEvent) -> None:
    """Attach a domain event to the session for after-commit delivery.

    Args:
        session: active database session carrying the transaction; a None
            placeholder used by unit tests skips the queueing.
        event: event to deliver once the transaction is committed.
    """
    if session is None:
        return
    session.info.setdefault(QUEUE_KEY, []).append(event)


def drain_events(session: AsyncSession | None) -> list[DomainEvent]:
    """Detach all queued domain events from the session.

    Args:
        session: database session whose transaction is already committed.

    Returns:
        list[DomainEvent]: events queued during the transaction.
    """
    if session is None:
        return []
    return list(session.info.pop(QUEUE_KEY, []))


def new_event_id() -> str:
    """Generate an opaque, lexicographically sortable event id.

    Uses UUIDv7 so the id orders by creation time and can be replayed
    directly through the SSE Last-Event-ID header.

    Returns:
        str: canonical UUIDv7 string.
    """
    return str(uuid7())


class ActivityLog:
    """Records domain changes in the append-only activity history.

    Every record lands in the current transaction and queues a matching
    DomainEvent published after commit, so the history and the realtime
    feed stay consistent.
    """

    def __init__(self, crud: ActivityCRUDProtocol):
        """Attach the activity storage.

        Args:
            crud: activity history storage.
        """
        self.crud = crud

    async def record(
        self,
        session: AsyncSession,
        event_type: ActivityEventType,
        actor_id: int | None,
        project_id: int | None = None,
        task_id: int | None = None,
        data: dict[str, Any] | None = None,
    ) -> ActivityEvent:
        """Record one domain change in the history.

        Args:
            session: active database session.
            event_type: type key of the domain change.
            actor_id: id of the user who caused the change.
            project_id: project the change belongs to.
            task_id: task the change belongs to.
            data: event specific attributes.

        Returns:
            ActivityEvent: the recorded history entry.
        """
        payload = data or {}
        event = ActivityEvent(
            id=new_event_id(),
            type=event_type,
            project_id=project_id,
            task_id=task_id,
            actor_id=actor_id,
            data=payload,
            created_at=utcnow(),
        )
        stored = await self.crud.create_event(session, event)
        queue_event(
            session,
            DomainEvent(
                id=stored.id,
                type=event_type.value,
                project_id=project_id,
                task_id=task_id,
                actor_id=actor_id,
                data=payload,
            ),
        )
        return stored
