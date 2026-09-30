from typing import Protocol, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TaskLabel


class TaskLabelCRUDProtocol(Protocol):
    """Data access for task label attachments."""

    async def attach(self, session: AsyncSession, relation: TaskLabel) -> TaskLabel:
        """Persist a new task label attachment.

        Args:
            session: active database session.
            relation: attachment to persist.

        Returns:
            TaskLabel: the persisted attachment.
        """
        ...

    async def get(
        self, session: AsyncSession, task_id: int, label_id: int
    ) -> TaskLabel | None:
        """Return one task label attachment.

        Args:
            session: active database session.
            task_id: task to inspect.
            label_id: label to look for.

        Returns:
            TaskLabel | None: the attachment or None.
        """
        ...

    async def list_for_task(
        self, session: AsyncSession, task_id: int
    ) -> Sequence[TaskLabel]:
        """Return all label attachments of a task.

        Args:
            session: active database session.
            task_id: task to inspect.

        Returns:
            Sequence[TaskLabel]: attachments with their labels loaded.
        """
        ...

    async def detach(self, session: AsyncSession, relation: TaskLabel) -> None:
        """Delete one task label attachment.

        Args:
            session: active database session.
            relation: attachment to delete.
        """
        ...

    async def delete_for_label(self, session: AsyncSession, label_id: int) -> None:
        """Delete every attachment of one label.

        Args:
            session: active database session.
            label_id: label being removed from the project.
        """
        ...
