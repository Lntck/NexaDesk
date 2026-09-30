from app.models import ActivityEvent

from .domain import DomainStore


class FakeActivityCRUD:
    """In-memory stand-in for ActivityCRUD used in unit tests."""

    def __init__(self, store: DomainStore):
        """Attach the shared in-memory tables.

        Args:
            store: shared domain tables.
        """
        self.store = store

    async def create_event(self, session, event: ActivityEvent) -> ActivityEvent:
        """Store one activity event.

        Args:
            session: unused session placeholder.
            event: event to store.

        Returns:
            ActivityEvent: the stored event.
        """
        self.store.events[event.id] = event
        return event

    async def list_for_project(
        self, session, project_id: int, limit: int, offset: int
    ) -> list[ActivityEvent]:
        """Return one page of project history, newest first.

        Args:
            session: unused session placeholder.
            project_id: project to inspect.
            limit: page size.
            offset: rows to skip.

        Returns:
            list[ActivityEvent]: history entries ordered newest first.
        """
        events = self._sorted(
            [
                event
                for event in self.store.events.values()
                if event.project_id == project_id
            ]
        )
        return events[offset : offset + limit]

    async def count_for_project(self, session, project_id: int) -> int:
        """Count history entries of a project.

        Args:
            session: unused session placeholder.
            project_id: project to inspect.

        Returns:
            int: number of history entries.
        """
        return len(
            [
                event
                for event in self.store.events.values()
                if event.project_id == project_id
            ]
        )

    async def list_for_task(
        self, session, task_id: int, limit: int, offset: int
    ) -> list[ActivityEvent]:
        """Return one page of task history, newest first.

        Args:
            session: unused session placeholder.
            task_id: task to inspect.
            limit: page size.
            offset: rows to skip.

        Returns:
            list[ActivityEvent]: history entries ordered newest first.
        """
        events = self._sorted(
            [event for event in self.store.events.values() if event.task_id == task_id]
        )
        return events[offset : offset + limit]

    async def count_for_task(self, session, task_id: int) -> int:
        """Count history entries of a task.

        Args:
            session: unused session placeholder.
            task_id: task to inspect.

        Returns:
            int: number of history entries.
        """
        return len(
            [event for event in self.store.events.values() if event.task_id == task_id]
        )

    async def list_events_after(
        self, session, project_id: int, after_id: str, limit: int
    ) -> list[ActivityEvent]:
        """Return project history entries newer than one event id.

        Args:
            session: unused session placeholder.
            project_id: project to inspect.
            after_id: exclusive lower bound, the last id the client saw.
            limit: maximum number of rows to return.

        Returns:
            list[ActivityEvent]: history entries ordered oldest first.
        """
        events = [
            event
            for event in self.store.events.values()
            if event.project_id == project_id and event.id > after_id
        ]
        events.sort(key=lambda event: event.id)
        return events[:limit]

    @staticmethod
    def _sorted(events: list[ActivityEvent]) -> list[ActivityEvent]:
        """Order history entries newest first.

        Args:
            events: entries to order.

        Returns:
            list[ActivityEvent]: entries ordered by creation time and id.
        """
        return sorted(
            events, key=lambda event: (event.created_at, event.id), reverse=True
        )
