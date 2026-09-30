from typing import Protocol, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import ProjectRole
from app.models import Project


class ProjectCRUDProtocol(Protocol):
    """Data access for project rows."""

    async def create_project(self, session: AsyncSession, project: Project) -> Project:
        """Persist a new project.

        Args:
            session: active database session.
            project: project to persist.

        Returns:
            Project: the persisted project.
        """
        ...

    async def get_by_id(self, session: AsyncSession, project_id: int) -> Project | None:
        """Return one project by primary key.

        Args:
            session: active database session.
            project_id: project id to look up.

        Returns:
            Project | None: the project or None.
        """
        ...

    async def get_by_key(self, session: AsyncSession, key: str) -> Project | None:
        """Return one project by its key.

        Args:
            session: active database session.
            key: normalized project key.

        Returns:
            Project | None: the project or None.
        """
        ...

    async def list_for_user(
        self,
        session: AsyncSession,
        user_id: int,
        search: str | None,
        archived: bool | None,
        sort: str,
        limit: int,
        offset: int,
    ) -> Sequence[tuple[Project, ProjectRole]]:
        """Return one page of projects the user belongs to.

        Args:
            session: active database session.
            user_id: member whose projects are listed.
            search: optional substring filter on key and name.
            archived: archive filter, None excludes archived projects.
            sort: validated sort key with optional "-" prefix.
            limit: page size.
            offset: rows to skip.

        Returns:
            Sequence[tuple[Project, ProjectRole]]: project with the caller role.
        """
        ...

    async def count_for_user(
        self,
        session: AsyncSession,
        user_id: int,
        search: str | None,
        archived: bool | None,
    ) -> int:
        """Count projects matching a user project listing filter.

        Args:
            session: active database session.
            user_id: member whose projects are counted.
            search: optional substring filter on key and name.
            archived: archive filter, None excludes archived projects.

        Returns:
            int: total number of matching projects.
        """
        ...

    async def count_members(self, session: AsyncSession, project_id: int) -> int:
        """Count memberships of a project.

        Args:
            session: active database session.
            project_id: project to inspect.

        Returns:
            int: number of project members.
        """
        ...

    async def count_tasks(self, session: AsyncSession, project_id: int) -> int:
        """Count live tasks of a project.

        Args:
            session: active database session.
            project_id: project to inspect.

        Returns:
            int: number of live tasks.
        """
        ...

    async def lock_by_id(
        self, session: AsyncSession, project_id: int
    ) -> Project | None:
        """Load a project row under a FOR UPDATE lock.

        Args:
            session: active database session.
            project_id: project id to lock.

        Returns:
            Project | None: the locked project or None.
        """
        ...

    async def update(self, session: AsyncSession, project: Project) -> Project:
        """Flush pending changes of a project row.

        Args:
            session: active database session.
            project: project to flush.

        Returns:
            Project: the same project instance.
        """
        ...
