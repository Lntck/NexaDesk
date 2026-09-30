from typing import Protocol, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TaskStatus


class TaskStatusCRUDProtocol(Protocol):
    """Data access for project board statuses."""

    async def create_status(
        self, session: AsyncSession, status: TaskStatus
    ) -> TaskStatus:
        """Persist a new board status.

        Args:
            session: active database session.
            status: status to persist.

        Returns:
            TaskStatus: the persisted status.
        """
        ...

    async def get_by_id(
        self, session: AsyncSession, project_id: int, status_id: int
    ) -> TaskStatus | None:
        """Return one status of a project.

        Args:
            session: active database session.
            project_id: owning project.
            status_id: status id to look up.

        Returns:
            TaskStatus | None: the status or None.
        """
        ...

    async def get_by_key(
        self, session: AsyncSession, project_id: int, key: str
    ) -> TaskStatus | None:
        """Return one status of a project by its key.

        Args:
            session: active database session.
            project_id: owning project.
            key: status key to look up.

        Returns:
            TaskStatus | None: the status or None.
        """
        ...

    async def list_by_project(
        self, session: AsyncSession, project_id: int
    ) -> Sequence[TaskStatus]:
        """Return all statuses of a project ordered by board position.

        Args:
            session: active database session.
            project_id: owning project.

        Returns:
            Sequence[TaskStatus]: statuses in board order.
        """
        ...

    async def count_tasks(self, session: AsyncSession, status_id: int) -> int:
        """Count live tasks holding the given status.

        Args:
            session: active database session.
            status_id: status to inspect.

        Returns:
            int: number of live tasks in the status.
        """
        ...

    async def next_position(self, session: AsyncSession, project_id: int) -> int:
        """Return the board position following the last status of a project.

        Args:
            session: active database session.
            project_id: owning project.

        Returns:
            int: free position at the end of the board.
        """
        ...

    async def update(self, session: AsyncSession, status: TaskStatus) -> TaskStatus:
        """Flush pending changes of a status row.

        Args:
            session: active database session.
            status: status to flush.

        Returns:
            TaskStatus: the same status instance.
        """
        ...

    async def delete(self, session: AsyncSession, status: TaskStatus) -> None:
        """Delete a status row.

        Args:
            session: active database session.
            status: status to delete.
        """
        ...
