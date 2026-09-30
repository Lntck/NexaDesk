from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import NotificationType
from app.models import Notification


class NotificationCRUD:
    """User notification row data access."""

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
        session.add(notification)
        await session.flush()
        return notification

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
        stmt = select(Notification).where(Notification.id == notification_id)
        result: Notification | None = await session.scalar(stmt)
        return result

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
        stmt = select(Notification).where(
            Notification.user_id == user_id,
            Notification.comment_id == comment_id,
            Notification.type == notification_type,
        )
        result: Notification | None = await session.scalar(stmt)
        return result

    async def list_for_user(
        self,
        session: AsyncSession,
        user_id: int,
        read: bool | None,
        limit: int,
        offset: int,
    ) -> list[Notification]:
        """Return one page of user notifications, newest first.

        Args:
            session: active database session.
            user_id: recipient to inspect.
            read: True for read only, False for unread only, None for all.
            limit: page size.
            offset: rows to skip.

        Returns:
            list[Notification]: notifications ordered newest first.
        """
        stmt = self._for_user(user_id, read)
        stmt = (
            stmt.order_by(Notification.created_at.desc(), Notification.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await session.scalars(stmt)).all())

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
        stmt = select(func.count()).select_from(
            self._for_user(user_id, read).subquery()
        )
        return int(await session.scalar(stmt) or 0)

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
        await session.flush()
        return notification

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
        stmt = select(Notification).where(
            Notification.user_id == user_id, Notification.read_at.is_(None)
        )
        notifications = list((await session.scalars(stmt)).all())
        for notification in notifications:
            notification.read_at = read_at
        await session.flush()
        return len(notifications)

    @staticmethod
    def _for_user(user_id: int, read: bool | None):
        """Build the base select of one user notification collection.

        Args:
            user_id: recipient to inspect.
            read: True for read only, False for unread only, None for all.

        Returns:
            Select: statement filtered by recipient and read state.
        """
        stmt = select(Notification).where(Notification.user_id == user_id)
        if read is True:
            stmt = stmt.where(Notification.read_at.is_not(None))
        elif read is False:
            stmt = stmt.where(Notification.read_at.is_(None))
        return stmt
