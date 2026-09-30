from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.policy import RequireProjectRole
from app.auth.schemas import CurrentUser
from app.dependencies import (
    get_db_session,
    get_project_service,
)
from app.enums import ProjectRole
from app.schemas import MemberAdd, MemberList, MemberRead, MemberRolePatch
from app.services import ProjectService

router = APIRouter(prefix="/projects/{project_id}/members", tags=["Members"])


@router.get("", response_model=MemberList)
async def list_members(
    current_user: CurrentUser = Depends(RequireProjectRole(ProjectRole.VIEWER)),
    session: AsyncSession = Depends(get_db_session),
    service: ProjectService = Depends(get_project_service),
    project_id: int = Path(...),
):
    """List project members.

    Args:
        current_user: authenticated project member.
        session: active database session.
        service: project domain service.
        project_id: project to inspect.

    Returns:
        MemberList: membership rows ordered by user id.
    """
    return await service.list_members(session, current_user.id, project_id)


@router.post("", response_model=MemberRead, status_code=status.HTTP_201_CREATED)
async def add_member(
    data: MemberAdd,
    current_user: CurrentUser = Depends(RequireProjectRole(ProjectRole.ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    service: ProjectService = Depends(get_project_service),
    project_id: int = Path(...),
):
    """Add an existing user to a project.

    Args:
        data: command payload with the user and his role.
        current_user: authenticated project owner or admin.
        session: active database session.
        service: project domain service.
        project_id: project to extend.

    Returns:
        MemberRead: the created membership.
    """
    return await service.add_member(session, current_user.id, project_id, data)


@router.patch("/{user_id}", response_model=MemberRead)
async def change_member_role(
    data: MemberRolePatch,
    current_user: CurrentUser = Depends(RequireProjectRole(ProjectRole.ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    service: ProjectService = Depends(get_project_service),
    project_id: int = Path(...),
    user_id: int = Path(...),
):
    """Change a project member role.

    Args:
        data: command payload with the new role.
        current_user: authenticated project owner or admin.
        session: active database session.
        service: project domain service.
        project_id: project to manage.
        user_id: member whose role changes.

    Returns:
        MemberRead: the updated membership.
    """
    return await service.change_member_role(
        session, current_user.id, project_id, user_id, data
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    current_user: CurrentUser = Depends(RequireProjectRole(ProjectRole.ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    service: ProjectService = Depends(get_project_service),
    project_id: int = Path(...),
    user_id: int = Path(...),
):
    """Remove a project member.

    Args:
        current_user: authenticated project owner or admin.
        session: active database session.
        service: project domain service.
        project_id: project to manage.
        user_id: member to remove.

    Returns:
        None: the response carries no body.
    """
    return await service.remove_member(session, current_user.id, project_id, user_id)
