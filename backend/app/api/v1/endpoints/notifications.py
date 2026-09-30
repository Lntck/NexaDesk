from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.schemas import CurrentUser
from app.dependencies import get_db_session, get_notification_service
from app.schemas import NotificationRead, PageParams, Paginated
from app.services import NotificationService

router = APIRouter(tags=["Notifications"])


@router.get("/notifications", response_model=Paginated[NotificationRead])
async def list_notifications(
    page: PageParams = Depends(),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: NotificationService = Depends(get_notification_service),
    read: bool | None = Query(None),
):
    """List notifications of the current user, newest first.

    Args:
        page: pagination parameters.
        current_user: authenticated caller.
        session: active database session.
        service: notification domain service.
        read: False returns only unread notifications, True only read
            ones, omitted returns everything.

    Returns:
        Paginated[NotificationRead]: one page of notifications.
    """
    return await service.list_notifications(session, current_user.id, page, read)


@router.post("/notifications/{notification_id}/read", response_model=NotificationRead)
async def mark_notification_read(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: NotificationService = Depends(get_notification_service),
    notification_id: int = Path(...),
):
    """Mark one notification of the current user as read.

    Marking an already read notification is a no-op.

    Args:
        current_user: authenticated caller.
        session: active database session.
        service: notification domain service.
        notification_id: notification to mark.

    Returns:
        NotificationRead: the updated notification.
    """
    return await service.mark_read(session, current_user.id, notification_id)


@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_read(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: NotificationService = Depends(get_notification_service),
):
    """Mark every unread notification of the current user as read.

    Args:
        current_user: authenticated caller.
        session: active database session.
        service: notification domain service.

    Returns:
        None: the response carries no body.
    """
    return await service.mark_all_read(session, current_user.id)
