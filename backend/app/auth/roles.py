from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import ProjectRole
from app.exceptions import AccessDenied, AppException, ProjectNotFound
from app.protocols.membership import ProjectMembershipProtocol


def resolve_role(
    role: ProjectRole | None,
    required: ProjectRole,
    missing: type[AppException] = ProjectNotFound,
) -> ProjectRole:
    """Validate membership and a minimum project role.

    Args:
        role: role held by the caller, None when not a member.
        required: minimal project role accepted for the action.
        missing: exception raised when the caller is not a member.

    Returns:
        ProjectRole: the verified role of the caller.

    Raises:
        AppException: when the caller is not a member of the project.
        AccessDenied: when the member role is below the required one.
    """
    if role is None:
        raise missing()
    if role.level < required.level:
        raise AccessDenied()
    return role


async def load_role(
    membership: ProjectMembershipProtocol,
    session: AsyncSession,
    project_id: int,
    user_id: int,
    missing: type[AppException] = ProjectNotFound,
) -> ProjectRole:
    """Return the project role of a user or raise when he is not a member.

    Args:
        membership: lookup returning the user role in the project.
        session: active database session.
        project_id: project to inspect.
        user_id: user whose role is resolved.
        missing: exception raised when the user is not a member.

    Returns:
        ProjectRole: the role held by the user.

    Raises:
        AppException: when the user is not a member of the project.
    """
    role = await membership.get_project_role(session, project_id, user_id)
    return resolve_role(role, ProjectRole.VIEWER, missing)
