from typing import Any, Protocol, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task


class TaskCRUDProtocol(Protocol):
    """Data access for tasks and their board ordering."""

    async def create_task(self, session: AsyncSession, task: Task) -> Task:
        """Persist a new task.

        Args:
            session: active database session.
            task: task to persist.

        Returns:
            Task: the persisted task.
        """
        ...

    async def get_by_id(self, session: AsyncSession, task_id: int) -> Task | None:
        """Return one live task by primary key.

        Args:
            session: active database session.
            task_id: task id to look up.

        Returns:
            Task | None: the task or None when missing or soft-deleted.
        """
        ...

    async def list_for_project(
        self,
        session: AsyncSession,
        project_id: int,
        filters: dict[str, Any],
        sort: str,
        limit: int,
        offset: int,
    ) -> Sequence[Task]:
        """Return one page of live project tasks matching the filters.

        Args:
            session: active database session.
            project_id: owning project.
            filters: supported keys: search, status, priority, assignee_id,
                creator_id, due_before, due_after.
            sort: validated sort key with optional "-" prefix.
            limit: page size.
            offset: rows to skip.

        Returns:
            Sequence[Task]: matching tasks in sort order.
        """
        ...

    async def count_for_project(
        self, session: AsyncSession, project_id: int, filters: dict[str, Any]
    ) -> int:
        """Count live project tasks matching the filters.

        Args:
            session: active database session.
            project_id: owning project.
            filters: same keys as in list_for_project.

        Returns:
            int: total number of matching tasks.
        """
        ...

    async def list_in_status(
        self,
        session: AsyncSession,
        project_id: int,
        status_id: int,
        limit: int | None,
    ) -> Sequence[Task]:
        """Return the first cards of one board column ordered by rank.

        Args:
            session: active database session.
            project_id: owning project.
            status_id: board column to read.
            limit: maximum number of cards, None returns the full column.

        Returns:
            Sequence[Task]: cards of the column.
        """
        ...

    async def count_in_status(
        self, session: AsyncSession, project_id: int, status_id: int
    ) -> int:
        """Count live tasks in one board column.

        Args:
            session: active database session.
            project_id: owning project.
            status_id: board column to count.

        Returns:
            int: number of live tasks in the column.
        """
        ...

    async def next_rank(
        self, session: AsyncSession, project_id: int, status_id: int
    ) -> int:
        """Return the rank following the last card of a board column.

        Args:
            session: active database session.
            project_id: owning project.
            status_id: board column to inspect.

        Returns:
            int: free rank at the end of the column.
        """
        ...

    async def renumber_column(
        self, session: AsyncSession, project_id: int, status_id: int
    ) -> None:
        """Reassign dense ranks 1..n inside one board column.

        Args:
            session: active database session.
            project_id: owning project.
            status_id: board column to normalize.
        """
        ...

    async def update(self, session: AsyncSession, task: Task) -> Task:
        """Flush pending changes of a task row.

        Args:
            session: active database session.
            task: task to flush.

        Returns:
            Task: the same task instance.
        """
        ...
