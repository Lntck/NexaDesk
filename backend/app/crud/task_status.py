from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task, TaskStatus


class TaskStatusCRUD:
    """Board status row data access."""

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
        session.add(status)
        await session.flush()
        return status

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
        stmt = select(TaskStatus).where(TaskStatus.id == status_id)
        result = await session.scalar(stmt)
        return result

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
        stmt = select(TaskStatus).where(
            TaskStatus.project_id == project_id,
            TaskStatus.key == key,
        )
        result = await session.scalar(stmt)
        return result

    async def list_by_project(
        self, session: AsyncSession, project_id: int
    ) -> list[TaskStatus]:
        """Return all statuses of a project ordered by board position.

        Args:
            session: active database session.
            project_id: owning project.

        Returns:
            list[TaskStatus]: statuses in board order.
        """
        stmt = (
            select(TaskStatus)
            .where(TaskStatus.project_id == project_id)
            .order_by(TaskStatus.position, TaskStatus.id)
        )
        return list((await session.scalars(stmt)).all())

    async def count_tasks(self, session: AsyncSession, status_id: int) -> int:
        """Count live tasks holding the given status.

        Args:
            session: active database session.
            status_id: status to inspect.

        Returns:
            int: number of live tasks in the status.
        """
        stmt = (
            select(func.count())
            .select_from(Task)
            .where(Task.status_id == status_id, Task.deleted_at.is_(None))
        )
        return int(await session.scalar(stmt) or 0)

    async def next_position(self, session: AsyncSession, project_id: int) -> int:
        """Return the board position following the last status of a project.

        Args:
            session: active database session.
            project_id: owning project.

        Returns:
            int: free position at the end of the board.
        """
        stmt = select(func.coalesce(func.max(TaskStatus.position), 0)).where(
            TaskStatus.project_id == project_id
        )
        return int(await session.scalar(stmt) or 0) + 1

    async def update(self, session: AsyncSession, status: TaskStatus) -> TaskStatus:
        """Flush pending changes of a status row.

        Args:
            session: active database session.
            status: status to flush.

        Returns:
            TaskStatus: the same status instance.
        """
        await session.flush()
        return status

    async def delete(self, session: AsyncSession, status: TaskStatus) -> None:
        """Delete a status row.

        Args:
            session: active database session.
            status: status to delete.
        """
        await session.delete(status)
        await session.flush()
