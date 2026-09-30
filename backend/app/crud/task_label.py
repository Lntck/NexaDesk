from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TaskLabel


class TaskLabelCRUD:
    """Task label attachment row data access."""

    async def attach(self, session: AsyncSession, relation: TaskLabel) -> TaskLabel:
        """Persist a new task label attachment.

        Args:
            session: active database session.
            relation: attachment to persist.

        Returns:
            TaskLabel: the persisted attachment.
        """
        session.add(relation)
        await session.flush()
        return relation

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
        stmt = select(TaskLabel).where(
            TaskLabel.task_id == task_id, TaskLabel.label_id == label_id
        )
        result = await session.scalar(stmt)
        return result

    async def list_for_task(
        self, session: AsyncSession, task_id: int
    ) -> list[TaskLabel]:
        """Return all label attachments of a task ordered by label name.

        Args:
            session: active database session.
            task_id: task to inspect.

        Returns:
            list[TaskLabel]: attachments with their labels loaded.
        """
        stmt = (
            select(TaskLabel)
            .where(TaskLabel.task_id == task_id)
            .order_by(TaskLabel.label_id)
        )
        return list((await session.scalars(stmt)).all())

    async def detach(self, session: AsyncSession, relation: TaskLabel) -> None:
        """Delete one task label attachment.

        Args:
            session: active database session.
            relation: attachment to delete.
        """
        await session.delete(relation)
        await session.flush()

    async def delete_for_label(self, session: AsyncSession, label_id: int) -> None:
        """Delete every attachment of one label.

        Args:
            session: active database session.
            label_id: label being removed from the project.
        """
        await session.execute(delete(TaskLabel).where(TaskLabel.label_id == label_id))
        await session.flush()
