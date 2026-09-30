from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ActivityEvent


class ActivityCRUD:
    """Append-only activity history data access."""

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
        session.add(event)
        await session.flush()
        return event

    async def list_for_project(
        self, session: AsyncSession, project_id: int, limit: int, offset: int
    ) -> list[ActivityEvent]:
        """Return one page of project history, newest first.

        Args:
            session: active database session.
            project_id: project to inspect.
            limit: page size.
            offset: rows to skip.

        Returns:
            list[ActivityEvent]: history entries ordered newest first.
        """
        stmt = (
            select(ActivityEvent)
            .where(ActivityEvent.project_id == project_id)
            .order_by(ActivityEvent.created_at.desc(), ActivityEvent.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await session.scalars(stmt)).all())

    async def count_for_project(self, session: AsyncSession, project_id: int) -> int:
        """Count history entries of a project.

        Args:
            session: active database session.
            project_id: project to inspect.

        Returns:
            int: number of history entries.
        """
        stmt = (
            select(func.count())
            .select_from(ActivityEvent)
            .where(ActivityEvent.project_id == project_id)
        )
        return int(await session.scalar(stmt) or 0)

    async def list_for_task(
        self, session: AsyncSession, task_id: int, limit: int, offset: int
    ) -> list[ActivityEvent]:
        """Return one page of task history, newest first.

        Args:
            session: active database session.
            task_id: task to inspect.
            limit: page size.
            offset: rows to skip.

        Returns:
            list[ActivityEvent]: history entries ordered newest first.
        """
        stmt = (
            select(ActivityEvent)
            .where(ActivityEvent.task_id == task_id)
            .order_by(ActivityEvent.created_at.desc(), ActivityEvent.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await session.scalars(stmt)).all())

    async def count_for_task(self, session: AsyncSession, task_id: int) -> int:
        """Count history entries of a task.

        Args:
            session: active database session.
            task_id: task to inspect.

        Returns:
            int: number of history entries.
        """
        stmt = (
            select(func.count())
            .select_from(ActivityEvent)
            .where(ActivityEvent.task_id == task_id)
        )
        return int(await session.scalar(stmt) or 0)

    async def list_events_after(
        self, session: AsyncSession, project_id: int, after_id: str, limit: int
    ) -> list[ActivityEvent]:
        """Return project history entries newer than one event id.

        Event ids are UUIDv7 values, so id order equals creation order
        and the query doubles as the SSE replay cursor.

        Args:
            session: active database session.
            project_id: project to inspect.
            after_id: exclusive lower bound, the last id the client saw.
            limit: maximum number of rows to return.

        Returns:
            list[ActivityEvent]: history entries ordered oldest first.
        """
        stmt = (
            select(ActivityEvent)
            .where(
                ActivityEvent.project_id == project_id,
                ActivityEvent.id > after_id,
            )
            .order_by(ActivityEvent.id.asc())
            .limit(limit)
        )
        return list((await session.scalars(stmt)).all())
