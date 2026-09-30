from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.schemas import CurrentUser
from app.dependencies import get_db_session, get_watcher_service
from app.schemas import WatcherRead
from app.services import WatcherService

router = APIRouter(tags=["Watchers"])


@router.get("/tasks/{task_id}/watchers", response_model=list[WatcherRead])
async def list_watchers(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: WatcherService = Depends(get_watcher_service),
    task_id: int = Path(...),
):
    """List the watchers of a task.

    Args:
        current_user: authenticated caller.
        session: active database session.
        service: watcher domain service.
        task_id: task to inspect.

    Returns:
        list[WatcherRead]: watcher subscriptions.
    """
    return await service.list_watchers(session, current_user.id, task_id)


@router.post("/tasks/{task_id}/watch", response_model=WatcherRead)
async def watch_task(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: WatcherService = Depends(get_watcher_service),
    task_id: int = Path(...),
):
    """Subscribe the caller to task changes.

    Args:
        current_user: authenticated caller.
        session: active database session.
        service: watcher domain service.
        task_id: task to watch.

    Returns:
        WatcherRead: the caller subscription.
    """
    return await service.watch(session, current_user.id, task_id)


@router.post("/tasks/{task_id}/unwatch", status_code=status.HTTP_204_NO_CONTENT)
async def unwatch_task(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: WatcherService = Depends(get_watcher_service),
    task_id: int = Path(...),
):
    """Unsubscribe the caller from task changes.

    Args:
        current_user: authenticated caller.
        session: active database session.
        service: watcher domain service.
        task_id: task to stop watching.

    Returns:
        None: the response carries no body.
    """
    return await service.unwatch(session, current_user.id, task_id)


@router.delete(
    "/tasks/{task_id}/watchers/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_watcher(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: WatcherService = Depends(get_watcher_service),
    task_id: int = Path(...),
    user_id: int = Path(...),
):
    """Remove one watcher from a task.

    Args:
        current_user: authenticated caller.
        session: active database session.
        service: watcher domain service.
        task_id: task to update.
        user_id: watcher to remove.

    Returns:
        None: the response carries no body.
    """
    return await service.remove_watcher(session, current_user.id, task_id, user_id)
