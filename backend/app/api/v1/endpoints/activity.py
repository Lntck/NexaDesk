from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.policy import RequireProjectRole
from app.auth.schemas import CurrentUser
from app.dependencies import get_activity_service, get_db_session
from app.enums import ProjectRole
from app.schemas import ActivityEventRead, PageParams, Paginated
from app.services import ActivityService

router = APIRouter(tags=["Activity"])


@router.get(
    "/projects/{project_id}/activity",
    response_model=Paginated[ActivityEventRead],
)
async def list_project_activity(
    page: PageParams = Depends(),
    current_user: CurrentUser = Depends(RequireProjectRole(ProjectRole.VIEWER)),
    session: AsyncSession = Depends(get_db_session),
    service: ActivityService = Depends(get_activity_service),
    project_id: int = Path(...),
):
    """List project activity history, newest first.

    Args:
        page: pagination parameters.
        current_user: authenticated project member.
        session: active database session.
        service: activity history query service.
        project_id: project to inspect.

    Returns:
        Paginated[ActivityEventRead]: one page of history entries.
    """
    return await service.list_project_activity(
        session, current_user.id, project_id, page
    )


@router.get(
    "/tasks/{task_id}/activity",
    response_model=Paginated[ActivityEventRead],
)
async def list_task_activity(
    page: PageParams = Depends(),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: ActivityService = Depends(get_activity_service),
    task_id: int = Path(...),
):
    """List activity history of a single task, newest first.

    Args:
        page: pagination parameters.
        current_user: authenticated caller.
        session: active database session.
        service: activity history query service.
        task_id: task to inspect.

    Returns:
        Paginated[ActivityEventRead]: one page of history entries.
    """
    return await service.list_task_activity(session, current_user.id, task_id, page)
