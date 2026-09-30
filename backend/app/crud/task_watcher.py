from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TaskWatcher


class TaskWatcherCRUD:
    """Task watcher subscription row data access."""

    async def add_watcher(
        self, session: AsyncSession, watcher: TaskWatcher
    ) -> TaskWatcher:
        """Persist a new task watcher subscription.

        Args:
            session: active database session.
            watcher: subscription to persist.

        Returns:
            TaskWatcher: the persisted subscription.
        """
        session.add(watcher)
        await session.flush()
        return watcher

    async def get(
        self, session: AsyncSession, task_id: int, user_id: int
    ) -> TaskWatcher | None:
        """Return one task watcher subscription.

        Args:
            session: active database session.
            task_id: task to inspect.
            user_id: watcher to look for.

        Returns:
            TaskWatcher | None: the subscription or None.
        """
        stmt = select(TaskWatcher).where(
            TaskWatcher.task_id == task_id, TaskWatcher.user_id == user_id
        )
        result = await session.scalar(stmt)
        return result

    async def list_for_task(
        self, session: AsyncSession, task_id: int
    ) -> list[TaskWatcher]:
        """Return all watchers of a task ordered by subscription time.

        Args:
            session: active database session.
            task_id: task to inspect.

        Returns:
            list[TaskWatcher]: subscriptions with their users loaded.
        """
        stmt = (
            select(TaskWatcher)
            .where(TaskWatcher.task_id == task_id)
            .order_by(TaskWatcher.created_at, TaskWatcher.user_id)
        )
        return list((await session.scalars(stmt)).all())

    async def count_for_task(self, session: AsyncSession, task_id: int) -> int:
        """Count the watchers of a task.

        Args:
            session: active database session.
            task_id: task to inspect.

        Returns:
            int: number of subscriptions.
        """
        stmt = (
            select(func.count())
            .select_from(TaskWatcher)
            .where(TaskWatcher.task_id == task_id)
        )
        return int(await session.scalar(stmt) or 0)

    async def remove(self, session: AsyncSession, watcher: TaskWatcher) -> None:
        """Delete one task watcher subscription.

        Args:
            session: active database session.
            watcher: subscription to delete.
        """
        await session.delete(watcher)
        await session.flush()
