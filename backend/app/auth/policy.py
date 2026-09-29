from fastapi import Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.schemas import CurrentUser
from app.dependencies.database import get_db_session
from app.enums import ProjectRole
from app.exceptions import AccessDenied, ProjectNotFound
from app.protocols.membership import ProjectMembershipProtocol


def get_project_membership() -> ProjectMembershipProtocol | None:
    """Return the project membership lookup.

    Returns:
        ProjectMembershipProtocol | None: lookup once it is wired during
        the project domain work; None before that.
    """
    return None


class RequireProjectRole:
    """Dependency enforcing project membership and a minimum project role.

    Non-members receive 404 ProjectNotFound instead of 403 so external users
    cannot discover existing projects (see docs/api-endpoints.md, 3.4).
    """

    def __init__(self, required_role: ProjectRole):
        """Configure the guard.

        Args:
            required_role: minimal project role accepted for the action.
        """
        self.required_role = required_role

    async def __call__(
        self,
        project_id: int = Path(...),
        current_user: CurrentUser = Depends(get_current_user),
        session: AsyncSession = Depends(get_db_session),
        membership: ProjectMembershipProtocol | None = Depends(get_project_membership),
    ) -> CurrentUser:
        """Validate that the caller may act inside the project.

        Args:
            project_id: id of the project being accessed.
            current_user: authenticated caller.
            session: database session used for the membership lookup.
            membership: lookup returning the caller role in the project.

        Returns:
            CurrentUser: the unchanged caller when access is granted.

        Raises:
            RuntimeError: when the membership lookup is not configured yet.
            ProjectNotFound: when the caller is not a member of the project.
            AccessDenied: when the member role is below the required one.
        """
        if membership is None:
            raise RuntimeError("Project membership lookup is not configured")

        role = await membership.get_project_role(session, project_id, current_user.id)
        if role is None:
            raise ProjectNotFound
        if role.level < self.required_role.level:
            raise AccessDenied
        return current_user