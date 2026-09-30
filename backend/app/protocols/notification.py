from datetime import datetime
from typing import Protocol, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import NotificationType
from app.models import Notification


class NotificationCRUDProtocol(Protocol):
    """Data access for user notifications."""

    async def create(
        self, session: AsyncSession, notification: Notification
    ) -> Notification:
        """Persist one notification.

        Args:
            session: active database session.
            notification: notification to persist.

        Returns:
            Notification: the persisted notification.
        """
        ...

    async def get_by_id(
        self, session: AsyncSession, notification_id: int
    ) -> Notification | None:
        """Return one notification by primary key.

        Args:
            session: active database session.
            notification_id: notification to look up.

        Returns:
            Notification | None: the notification or None.
        """
        ...

    async def get_for_comment(
        self,
        session: AsyncSession,
        user_id: int,
        comment_id: int,
        notification_type: NotificationType,
    ) -> Notification | None:
        """Return one notification of a user about one comment.

        Args:
            session: active database session.
            user_id: recipient to look up.
            comment_id: comment the notification refers to.
            notification_type: notification type to match.

        Returns:
            Notification | None: the notification or None.
        """
        ...

    async def list_for_user(
        self,
        session: AsyncSession,
        user_id: int,
        read: bool | None,
        limit: int,
        offset: int,
    ) -> Sequence[Notification]:
        """Return one page of user notifications, newest first.

        Args:
            session: active database session.
            user_id: recipient to inspect.
            read: True for read only, False for unread only, None for all.
            limit: page size.
            offset: rows to skip.

        Returns:
            Sequence[Notification]: notifications ordered newest first.
        """
        ...

    async def count_for_user(
        self, session: AsyncSession, user_id: int, read: bool | None
    ) -> int:
        """Count user notifications.

        Args:
            session: active database session.
            user_id: recipient to inspect.
            read: True for read only, False for unread only, None for all.

        Returns:
            int: number of matching notifications.
        """
        ...

    async def update(
        self, session: AsyncSession, notification: Notification
    ) -> Notification:
        """Persist changes of one notification.

        Args:
            session: active database session.
            notification: notification to update.

        Returns:
            Notification: the updated notification.
        """
        ...

    async def mark_all_read(
        self, session: AsyncSession, user_id: int, read_at: datetime
    ) -> int:
        """Mark every unread notification of one user as read.

        Args:
            session: active database session.
            user_id: recipient to update.
            read_at: timestamp stored as the read moment.

        Returns:
            int: number of notifications marked as read.
        """
        ...
