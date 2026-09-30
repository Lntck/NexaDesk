from typing import Protocol, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import ProjectRole
from app.models import ProjectMember


class ProjectMembershipProtocol(Protocol):
    """Lookup of the project role held by a user inside one project."""

    async def get_project_role(
        self, session: AsyncSession, project_id: int, user_id: int
    ) -> ProjectRole | None:
        """Return the role of the user in the project, None when not a member.

        Args:
            session: active database session.
            project_id: project to inspect.
            user_id: user whose role is looked up.

        Returns:
            ProjectRole | None: member role or None when the user is not
            a member of the project.
        """
        ...


class ProjectMemberCRUDProtocol(ProjectMembershipProtocol, Protocol):
    """Data access for project memberships."""

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
        ...

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
        ...

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
        ...

    async def remove_member(self, session: AsyncSession, member: ProjectMember) -> None:
        """Delete a membership row.

        Args:
            session: active database session.
            member: membership to delete.
        """
        ...
