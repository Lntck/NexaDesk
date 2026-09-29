from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import ProjectRole


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