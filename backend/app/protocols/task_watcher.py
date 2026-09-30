from typing import Protocol, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TaskWatcher


class TaskWatcherCRUDProtocol(Protocol):
    """Data access for task watcher subscriptions."""

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
        ...

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
        ...

    async def list_for_task(
        self, session: AsyncSession, task_id: int
    ) -> Sequence[TaskWatcher]:
        """Return all watchers of a task ordered by subscription time.

        Args:
            session: active database session.
            task_id: task to inspect.

        Returns:
            Sequence[TaskWatcher]: subscriptions with their users loaded.
        """
        ...

    async def count_for_task(self, session: AsyncSession, task_id: int) -> int:
        """Count the watchers of a task.

        Args:
            session: active database session.
            task_id: task to inspect.

        Returns:
            int: number of subscriptions.
        """
        ...

    async def remove(self, session: AsyncSession, watcher: TaskWatcher) -> None:
        """Delete one task watcher subscription.

        Args:
            session: active database session.
            watcher: subscription to delete.
        """
        ...
