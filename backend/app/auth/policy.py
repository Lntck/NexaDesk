from fastapi import Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.roles import resolve_role
from app.auth.schemas import CurrentUser
from app.dependencies.crud import get_member_crud
from app.dependencies.database import get_db_session
from app.enums import ProjectRole
from app.protocols.membership import ProjectMembershipProtocol

__all__ = ("RequireProjectRole", "get_project_membership", "resolve_role")


def get_project_membership(
    membership: ProjectMembershipProtocol = Depends(get_member_crud),
) -> ProjectMembershipProtocol:
    """Return the project membership lookup.

    Returns:
        ProjectMembershipProtocol: lookup backed by project_members rows.
    """
    return membership


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
            RuntimeError: when the membership lookup is not wired.
        """
        if membership is None:
            raise RuntimeError("Project membership lookup is not configured")
        role = await membership.get_project_role(session, project_id, current_user.id)
        resolve_role(role, self.required_role)
        return current_user
