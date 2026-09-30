from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from app.enums import ActivityEventType

if TYPE_CHECKING:
    from app.models import ActivityEvent


class EventActor(BaseModel):
    """Author of a realtime event as seen by connected clients."""

    id: int
    username: str


class RealtimeEvent(BaseModel):
    """Wire envelope of one realtime event delivered over SSE.

    The envelope is the ``data:`` payload of the SSE frame and carries the
    common fields from docs/api-endpoints.md, section 21: opaque id, event
    type, project and task scope, actor, timestamp and the event specific
    attributes under ``data``.
    """

    id: str
    type: ActivityEventType
    project_id: int | None = None
    task_id: int | None = None
    actor: EventActor | None = None
    timestamp: datetime
    data: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_activity(cls, event: ActivityEvent) -> RealtimeEvent:
        """Build an envelope from a stored activity history entry.

        Used by the SSE replay path: rows already carry the actor, so the
        envelope is assembled without extra lookups.

        Args:
            event: immutable activity history entry.

        Returns:
            RealtimeEvent: envelope matching the stored entry.
        """
        actor = None
        if event.actor is not None:
            actor = EventActor(id=event.actor.id, username=event.actor.username)
        elif event.actor_id is not None:
            actor = EventActor(id=event.actor_id, username="")
        return cls(
            id=event.id,
            type=event.type,
            project_id=event.project_id,
            task_id=event.task_id,
            actor=actor,
            timestamp=event.created_at,
            data=dict(event.data or {}),
        )
