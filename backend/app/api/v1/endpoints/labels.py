from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.policy import RequireProjectRole
from app.auth.schemas import CurrentUser
from app.dependencies import get_db_session, get_label_service
from app.enums import ProjectRole
from app.schemas import LabelCreate, LabelPatch, LabelRead
from app.services import LabelService

router = APIRouter(tags=["Labels"])


@router.get("/projects/{project_id}/labels", response_model=list[LabelRead])
async def list_labels(
    current_user: CurrentUser = Depends(RequireProjectRole(ProjectRole.VIEWER)),
    session: AsyncSession = Depends(get_db_session),
    service: LabelService = Depends(get_label_service),
    project_id: int = Path(...),
):
    """List project labels.

    Args:
        current_user: authenticated project member.
        session: active database session.
        service: label domain service.
        project_id: project to inspect.

    Returns:
        list[LabelRead]: labels of the project ordered by name.
    """
    return await service.list_labels(session, current_user.id, project_id)


@router.post(
    "/projects/{project_id}/labels",
    response_model=LabelRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_label(
    data: LabelCreate,
    current_user: CurrentUser = Depends(RequireProjectRole(ProjectRole.ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    service: LabelService = Depends(get_label_service),
    project_id: int = Path(...),
):
    """Create a project label.

    Args:
        data: validated label creation payload.
        current_user: authenticated project owner or admin.
        session: active database session.
        service: label domain service.
        project_id: project to extend.

    Returns:
        LabelRead: the created label.
    """
    return await service.create_label(session, current_user.id, project_id, data)


@router.patch("/projects/{project_id}/labels/{label_id}", response_model=LabelRead)
async def update_label(
    data: LabelPatch,
    current_user: CurrentUser = Depends(RequireProjectRole(ProjectRole.ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    service: LabelService = Depends(get_label_service),
    project_id: int = Path(...),
    label_id: int = Path(...),
):
    """Update label metadata.

    Args:
        data: merge patch payload with editable fields.
        current_user: authenticated project owner or admin.
        session: active database session.
        service: label domain service.
        project_id: project owning the label.
        label_id: label to update.

    Returns:
        LabelRead: the updated label.
    """
    return await service.update_label(
        session, current_user.id, project_id, label_id, data
    )


@router.delete(
    "/projects/{project_id}/labels/{label_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_label(
    current_user: CurrentUser = Depends(RequireProjectRole(ProjectRole.ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    service: LabelService = Depends(get_label_service),
    project_id: int = Path(...),
    label_id: int = Path(...),
):
    """Delete a label and detach it from every task.

    Args:
        current_user: authenticated project owner or admin.
        session: active database session.
        service: label domain service.
        project_id: project owning the label.
        label_id: label to delete.

    Returns:
        None: the response carries no body.
    """
    return await service.delete_label(session, current_user.id, project_id, label_id)


@router.post(
    "/tasks/{task_id}/labels/{label_id}",
    response_model=LabelRead,
    status_code=status.HTTP_201_CREATED,
)
async def attach_label(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: LabelService = Depends(get_label_service),
    task_id: int = Path(...),
    label_id: int = Path(...),
):
    """Attach a project label to a task.

    Args:
        current_user: authenticated caller.
        session: active database session.
        service: label domain service.
        task_id: task to extend.
        label_id: label to attach.

    Returns:
        LabelRead: the attached label.
    """
    return await service.attach_label(session, current_user.id, task_id, label_id)


@router.delete(
    "/tasks/{task_id}/labels/{label_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def detach_label(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: LabelService = Depends(get_label_service),
    task_id: int = Path(...),
    label_id: int = Path(...),
):
    """Remove a label from a task.

    Args:
        current_user: authenticated caller.
        session: active database session.
        service: label domain service.
        task_id: task to update.
        label_id: label to remove.

    Returns:
        None: the response carries no body.
    """
    return await service.detach_label(session, current_user.id, task_id, label_id)
