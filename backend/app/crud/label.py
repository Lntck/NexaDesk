from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Label


class LabelCRUD:
    """Project label row data access."""

    async def create_label(self, session: AsyncSession, label: Label) -> Label:
        """Persist a new project label.

        Args:
            session: active database session.
            label: label to persist.

        Returns:
            Label: the persisted label.
        """
        session.add(label)
        await session.flush()
        return label

    async def get_by_id(
        self, session: AsyncSession, project_id: int, label_id: int
    ) -> Label | None:
        """Return one label of a project.

        Args:
            session: active database session.
            project_id: owning project.
            label_id: label id to look up.

        Returns:
            Label | None: the label or None.
        """
        stmt = select(Label).where(Label.id == label_id, Label.project_id == project_id)
        result = await session.scalar(stmt)
        return result

    async def get_by_name(
        self, session: AsyncSession, project_id: int, name: str
    ) -> Label | None:
        """Return one label of a project by its name, case-insensitively.

        Args:
            session: active database session.
            project_id: owning project.
            name: label name to look up.

        Returns:
            Label | None: the label or None.
        """
        stmt = select(Label).where(
            Label.project_id == project_id,
            func.lower(Label.name) == name.lower(),
        )
        result = await session.scalar(stmt)
        return result

    async def list_by_project(
        self, session: AsyncSession, project_id: int
    ) -> list[Label]:
        """Return all labels of a project ordered by name.

        Args:
            session: active database session.
            project_id: project to inspect.

        Returns:
            list[Label]: labels ordered by name.
        """
        stmt = (
            select(Label)
            .where(Label.project_id == project_id)
            .order_by(func.lower(Label.name), Label.id)
        )
        return list((await session.scalars(stmt)).all())

    async def update(self, session: AsyncSession, label: Label) -> Label:
        """Flush pending changes of a label row.

        Args:
            session: active database session.
            label: label to flush.

        Returns:
            Label: the same label instance.
        """
        await session.flush()
        return label

    async def delete(self, session: AsyncSession, label: Label) -> None:
        """Delete a label row.

        Args:
            session: active database session.
            label: label to delete.
        """
        await session.delete(label)
        await session.flush()
