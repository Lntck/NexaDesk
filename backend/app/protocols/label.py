from typing import Protocol, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Label


class LabelCRUDProtocol(Protocol):
    """Data access for project labels."""

    async def create_label(self, session: AsyncSession, label: Label) -> Label:
        """Persist a new project label.

        Args:
            session: active database session.
            label: label to persist.

        Returns:
            Label: the persisted label.
        """
        ...

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
        ...

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
        ...

    async def list_by_project(
        self, session: AsyncSession, project_id: int
    ) -> Sequence[Label]:
        """Return all labels of a project ordered by name.

        Args:
            session: active database session.
            project_id: project to inspect.

        Returns:
            Sequence[Label]: labels ordered by name.
        """
        ...

    async def update(self, session: AsyncSession, label: Label) -> Label:
        """Flush pending changes of a label row.

        Args:
            session: active database session.
            label: label to flush.

        Returns:
            Label: the same label instance.
        """
        ...

    async def delete(self, session: AsyncSession, label: Label) -> None:
        """Delete a label row.

        Args:
            session: active database session.
            label: label to delete.
        """
        ...
