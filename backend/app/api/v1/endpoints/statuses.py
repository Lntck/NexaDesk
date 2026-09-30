from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.policy import RequireProjectRole
from app.auth.schemas import CurrentUser
from app.dependencies import (
    get_db_session,
    get_status_service,
)
from app.enums import ProjectRole
from app.schemas import TaskStatusCreate, TaskStatusPatch, TaskStatusRead
from app.services import TaskStatusService

router = APIRouter(prefix="/projects/{project_id}/statuses", tags=["Statuses"])


@router.get("", response_model=list[TaskStatusRead])
async def list_statuses(
    current_user: CurrentUser = Depends(RequireProjectRole(ProjectRole.VIEWER)),
    session: AsyncSession = Depends(get_db_session),
    service: TaskStatusService = Depends(get_status_service),
    project_id: int = Path(...),
):
    """List project task statuses.

    Args:
        current_user: authenticated project member.
        session: active database session.
        service: board status domain service.
        project_id: project to inspect.

    Returns:
        list[TaskStatusRead]: statuses in board order.
    """
    return await service.list_statuses(session, current_user.id, project_id)


@router.post("", response_model=TaskStatusRead, status_code=status.HTTP_201_CREATED)
async def create_status(
    data: TaskStatusCreate,
    current_user: CurrentUser = Depends(RequireProjectRole(ProjectRole.ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    service: TaskStatusService = Depends(get_status_service),
    project_id: int = Path(...),
):
    """Create a custom board status.

    Args:
        data: validated status creation payload.
        current_user: authenticated project owner or admin.
        session: active database session.
        service: board status domain service.
        project_id: project to extend.

    Returns:
        TaskStatusRead: the created status.
    """
    return await service.create_status(session, current_user.id, project_id, data)


@router.patch("/{status_id}", response_model=TaskStatusRead)
async def update_status(
    data: TaskStatusPatch,
    current_user: CurrentUser = Depends(RequireProjectRole(ProjectRole.ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    service: TaskStatusService = Depends(get_status_service),
    project_id: int = Path(...),
    status_id: int = Path(...),
):
    """Update status metadata or board position.

    Args:
        data: merge patch payload with editable fields.
        current_user: authenticated project owner or admin.
        session: active database session.
        service: board status domain service.
        project_id: project owning the status.
        status_id: status to update.

    Returns:
        TaskStatusRead: the updated status.
    """
    return await service.update_status(
        session, current_user.id, project_id, status_id, data
    )


@router.delete("/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_status(
    current_user: CurrentUser = Depends(RequireProjectRole(ProjectRole.ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    service: TaskStatusService = Depends(get_status_service),
    project_id: int = Path(...),
    status_id: int = Path(...),
):
    """Delete a board status that holds no tasks.

    Args:
        current_user: authenticated project owner or admin.
        session: active database session.
        service: board status domain service.
        project_id: project owning the status.
        status_id: status to delete.

    Returns:
        None: the response carries no body.
    """
    return await service.delete_status(session, current_user.id, project_id, status_id)
