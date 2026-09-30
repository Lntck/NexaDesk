from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import ProjectRole
from app.models import ProjectMember


class ProjectMemberCRUD:
    """Project membership row data access."""

    async def get_project_role(
        self, session: AsyncSession, project_id: int, user_id: int
    ) -> ProjectRole | None:
        """Return the role of the user in the project, None when not a member.

        Args:
            session: active database session.
            project_id: project to inspect.
            user_id: user whose role is looked up.

        Returns:
            ProjectRole | None: member role or None.
        """
        stmt = select(ProjectMember.role).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
        result = await session.scalar(stmt)
        return result

    async def create_member(
        self, session: AsyncSession, member: ProjectMember
    ) -> ProjectMember:
        """Persist a new membership row.

        Args:
            session: active database session.
            member: membership to persist.

        Returns:
            ProjectMember: the persisted membership.
        """
        session.add(member)
        await session.flush()
        return member

    async def get_member(
        self, session: AsyncSession, project_id: int, user_id: int
    ) -> ProjectMember | None:
        """Return one membership row.

        Args:
            session: active database session.
            project_id: project to inspect.
            user_id: member to look up.

        Returns:
            ProjectMember | None: the membership or None.
        """
        stmt = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
        result = await session.scalar(stmt)
        return result

    async def list_members(
        self, session: AsyncSession, project_id: int
    ) -> Sequence[ProjectMember]:
        """Return all memberships of a project.

        Args:
            session: active database session.
            project_id: project to inspect.

        Returns:
            Sequence[ProjectMember]: memberships ordered by user id.
        """
        stmt = (
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.user_id)
        )
        return (await session.scalars(stmt)).all()

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

    async def update_role(
        self, session: AsyncSession, member: ProjectMember, role: ProjectRole
    ) -> ProjectMember:
        """Change the role stored in a membership row.

        Args:
            session: active database session.
            member: membership to update.
            role: new project role.

        Returns:
            ProjectMember: the updated membership.
        """
        member.role = role
        await session.flush()
        return member

    async def remove_member(self, session: AsyncSession, member: ProjectMember) -> None:
        """Delete a membership row.

        Args:
            session: active database session.
            member: membership to delete.
        """
        await session.delete(member)
        await session.flush()
