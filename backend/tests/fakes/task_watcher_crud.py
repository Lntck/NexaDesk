from app.models import TaskWatcher

from .domain import DomainStore


class FakeTaskWatcherCRUD:
    """In-memory stand-in for TaskWatcherCRUD used in unit tests."""

    def __init__(self, store: DomainStore, user_crud):
        """Attach the shared in-memory tables and the user lookup.

        Args:
            store: shared domain tables.
            user_crud: user storage used to resolve watcher accounts.
        """
        self.store = store
        self.user_crud = user_crud

    async def add_watcher(self, session, watcher: TaskWatcher) -> TaskWatcher:
        """Store a new task watcher subscription.

        Args:
            session: unused session placeholder.
            watcher: subscription to store.

        Returns:
            TaskWatcher: the stored subscription with assigned id.
        """
        watcher.id = watcher.id or len(self.store.task_watchers) + 1
        self.store.task_watchers[(watcher.task_id, watcher.user_id)] = watcher
        return watcher

    async def get(self, session, task_id: int, user_id: int) -> TaskWatcher | None:
        """Return one task watcher subscription.

        Args:
            session: unused session placeholder.
            task_id: task to inspect.
            user_id: watcher to look for.

        Returns:
            TaskWatcher | None: the subscription or None.
        """
        return self.store.task_watchers.get((task_id, user_id))

    async def list_for_task(self, session, task_id: int) -> list[TaskWatcher]:
        """Return all watchers of a task ordered by subscription time.

        Args:
            session: unused session placeholder.
            task_id: task to inspect.

        Returns:
            list[TaskWatcher]: subscriptions with their users loaded.
        """
        watchers = [
            watcher
            for watcher in self.store.task_watchers.values()
            if watcher.task_id == task_id
        ]
        watchers.sort(key=lambda watcher: (watcher.created_at, watcher.user_id))
        for watcher in watchers:
            watcher.user = await self.user_crud.get_by_id(session, watcher.user_id)
        return watchers

    async def count_for_task(self, session, task_id: int) -> int:
        """Count the watchers of a task.

        Args:
            session: unused session placeholder.
            task_id: task to inspect.

        Returns:
            int: number of subscriptions.
        """
        return len(
            [
                watcher
                for watcher in self.store.task_watchers.values()
                if watcher.task_id == task_id
            ]
        )

    async def remove(self, session, watcher: TaskWatcher) -> None:
        """Delete one task watcher subscription.

        Args:
            session: unused session placeholder.
            watcher: subscription to delete.
        """
        self.store.task_watchers.pop((watcher.task_id, watcher.user_id), None)
