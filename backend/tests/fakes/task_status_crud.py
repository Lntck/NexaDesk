from app.models import TaskStatus
from app.utils import utcnow

from .domain import DomainStore


class FakeTaskStatusCRUD:
    """In-memory stand-in for TaskStatusCRUD used in unit tests."""

    def __init__(self, store: DomainStore):
        """Attach the shared in-memory tables.

        Args:
            store: shared domain tables.
        """
        self.store = store

    async def create_status(self, session, status: TaskStatus) -> TaskStatus:
        """Store a new board status and assign an id.

        Args:
            session: unused session placeholder.
            status: status to store.

        Returns:
            TaskStatus: the stored status with assigned id.
        """
        status.id = self.store.status_seq
        self.store.status_seq += 1
        status.created_at = status.created_at or utcnow()
        status.updated_at = status.updated_at or utcnow()
        self.store.statuses[status.id] = status
        return status

    async def get_by_id(
        self, session, project_id: int, status_id: int
    ) -> TaskStatus | None:
        """Return one status of a project.

        Args:
            session: unused session placeholder.
            project_id: owning project.
            status_id: status id to look up.

        Returns:
            TaskStatus | None: the status or None.
        """
        status = self.store.statuses.get(status_id)
        if status is None or status.project_id != project_id:
            return None
        return status

    async def get_by_key(self, session, project_id: int, key: str) -> TaskStatus | None:
        """Return one status of a project by its key.

        Args:
            session: unused session placeholder.
            project_id: owning project.
            key: status key to look up.

        Returns:
            TaskStatus | None: the status or None.
        """
        for status in self.store.statuses.values():
            if status.project_id == project_id and status.key == key:
                return status
        return None

    async def list_by_project(self, session, project_id: int) -> list[TaskStatus]:
        """Return all statuses of a project ordered by board position.

        Args:
            session: unused session placeholder.
            project_id: owning project.

        Returns:
            list[TaskStatus]: statuses in board order.
        """
        statuses = [
            status
            for status in self.store.statuses.values()
            if status.project_id == project_id
        ]
        statuses.sort(key=lambda status: (status.position, status.id))
        return statuses

    async def count_tasks(self, session, status_id: int) -> int:
        """Count live tasks holding the given status.

        Args:
            session: unused session placeholder.
            status_id: status to inspect.

        Returns:
            int: number of live tasks in the status.
        """
        return len(
            [
                task
                for task in self.store.tasks.values()
                if task.status_id == status_id and task.deleted_at is None
            ]
        )

    async def next_position(self, session, project_id: int) -> int:
        """Return the board position following the last status.

        Args:
            session: unused session placeholder.
            project_id: owning project.

        Returns:
            int: free position at the end of the board.
        """
        positions = [
            status.position
            for status in self.store.statuses.values()
            if status.project_id == project_id
        ]
        return (max(positions) if positions else 0) + 1

    async def update(self, session, status: TaskStatus) -> TaskStatus:
        """Flush pending changes of a status row.

        Args:
            session: unused session placeholder.
            status: status to flush.

        Returns:
            TaskStatus: the same status instance.
        """
        return status

    async def delete(self, session, status: TaskStatus) -> None:
        """Delete a status row.

        Args:
            session: unused session placeholder.
            status: status to delete.
        """
        self.store.statuses.pop(status.id, None)
