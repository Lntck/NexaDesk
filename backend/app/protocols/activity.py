from typing import Any, Protocol, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import ActivityEventType
from app.models import ActivityEvent


class ActivityCRUDProtocol(Protocol):
    """Data access for the append-only activity history."""

    async def create_event(
        self, session: AsyncSession, event: ActivityEvent
    ) -> ActivityEvent:
        """Persist one activity event.

        Args:
            session: active database session.
            event: event to persist.

        Returns:
            ActivityEvent: the persisted event.
        """
        ...

    async def list_for_project(
        self, session: AsyncSession, project_id: int, limit: int, offset: int
    ) -> Sequence[ActivityEvent]:
        """Return one page of project history, newest first.

        Args:
            session: active database session.
            project_id: project to inspect.
            limit: page size.
            offset: rows to skip.

        Returns:
            Sequence[ActivityEvent]: history entries ordered newest first.
        """
        ...

    async def count_for_project(self, session: AsyncSession, project_id: int) -> int:
        """Count history entries of a project.

        Args:
            session: active database session.
            project_id: project to inspect.

        Returns:
            int: number of history entries.
        """
        ...

    async def list_for_task(
        self, session: AsyncSession, task_id: int, limit: int, offset: int
    ) -> Sequence[ActivityEvent]:
        """Return one page of task history, newest first.

        Args:
            session: active database session.
            task_id: task to inspect.
            limit: page size.
            offset: rows to skip.

        Returns:
            Sequence[ActivityEvent]: history entries ordered newest first.
        """
        ...

    async def count_for_task(self, session: AsyncSession, task_id: int) -> int:
        """Count history entries of a task.

        Args:
            session: active database session.
            task_id: task to inspect.

        Returns:
            int: number of history entries.
        """
        ...


class ActivityLogProtocol(Protocol):
    """Recording seam for the immutable activity history."""

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
        ...
