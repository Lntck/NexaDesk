from typing import Sequence, cast

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import ProjectRole
from app.models import Project, ProjectMember, Task

SORT_FIELDS = {"created_at", "name", "key"}


class ProjectCRUD:
    """Project row data access."""

    async def create_project(self, session: AsyncSession, project: Project) -> Project:
        """Persist a new project.

        Args:
            session: active database session.
            project: project to persist.

        Returns:
            Project: the persisted project.
        """
        session.add(project)
        await session.flush()
        return project

    async def get_by_id(self, session: AsyncSession, project_id: int) -> Project | None:
        """Return one project by primary key.

        Args:
            session: active database session.
            project_id: project id to look up.

        Returns:
            Project | None: the project or None.
        """
        stmt = select(Project).where(Project.id == project_id)
        result = await session.scalar(stmt)
        return result

    async def get_by_key(self, session: AsyncSession, key: str) -> Project | None:
        """Return one project by its key.

        Args:
            session: active database session.
            key: project key to look up.

        Returns:
            Project | None: the project or None.
        """
        stmt = select(Project).where(Project.key == key)
        result = await session.scalar(stmt)
        return result

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
        stmt = (
            select(Project, ProjectMember.role)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(ProjectMember.user_id == user_id)
        )
        stmt = self._apply_filters(stmt, search, archived)
        stmt = stmt.order_by(*self._order_by(sort))
        stmt = stmt.limit(limit).offset(offset)
        rows = await session.execute(stmt)
        return cast(Sequence[tuple[Project, ProjectRole]], rows.all())

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
        stmt = (
            select(func.count())
            .select_from(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(ProjectMember.user_id == user_id)
        )
        stmt = self._apply_filters(stmt, search, archived)
        return int(await session.scalar(stmt) or 0)

    async def count_members(self, session: AsyncSession, project_id: int) -> int:
        """Count memberships of a project.

        Args:
            session: active database session.
            project_id: project to inspect.

        Returns:
            int: number of project members.
        """
        stmt = (
            select(func.count())
            .select_from(ProjectMember)
            .where(ProjectMember.project_id == project_id)
        )
        return int(await session.scalar(stmt) or 0)

    async def count_tasks(self, session: AsyncSession, project_id: int) -> int:
        """Count live tasks of a project.

        Args:
            session: active database session.
            project_id: project to inspect.

        Returns:
            int: number of live tasks.
        """
        stmt = (
            select(func.count())
            .select_from(Task)
            .where(Task.project_id == project_id, Task.deleted_at.is_(None))
        )
        return int(await session.scalar(stmt) or 0)

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
        stmt = select(Project).where(Project.id == project_id).with_for_update()
        result = await session.scalar(stmt)
        return result

    async def update(self, session: AsyncSession, project: Project) -> Project:
        """Flush pending changes of a project row.

        Args:
            session: active database session.
            project: project to flush.

        Returns:
            Project: the same project instance.
        """
        await session.flush()
        return project

    @staticmethod
    def _apply_filters(stmt, search: str | None, archived: bool | None):
        """Restrict a project listing statement by search and archive filters.

        Args:
            stmt: select statement to filter.
            search: optional substring filter on key and name.
            archived: archive filter, None excludes archived projects.

        Returns:
            the filtered select statement.
        """
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(Project.key.ilike(pattern), Project.name.ilike(pattern))
            )
        stmt = stmt.where(Project.is_archived.is_(archived is True))
        return stmt

    @staticmethod
    def _order_by(sort: str):
        """Build order-by expressions for a validated sort key.

        Args:
            sort: sort key with optional "-" prefix.

        Returns:
            tuple: order-by expressions.
        """
        field = sort[1:] if sort.startswith("-") else sort
        column = getattr(Project, field)
        return (
            (column.desc(), Project.id)
            if sort.startswith("-")
            else (
                column.asc(),
                Project.id,
            )
        )
