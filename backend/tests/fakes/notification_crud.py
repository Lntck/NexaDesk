from app.enums import NotificationType
from app.models import Notification

from .domain import DomainStore


class FakeNotificationCRUD:
    """In-memory stand-in for NotificationCRUD used in unit tests."""

    def __init__(self, store: DomainStore, user_crud):
        """Attach the shared in-memory tables and the user lookup.

        Args:
            store: shared domain tables.
            user_crud: user storage used to resolve notification actors.
        """
        self.store = store
        self.user_crud = user_crud

    async def create(self, session, notification: Notification) -> Notification:
        """Store a new notification and assign an id.

        Args:
            session: unused session placeholder.
            notification: notification to store.

        Returns:
            Notification: the stored notification with assigned id.
        """
        notification.id = notification.id or self.store.notification_seq
        self.store.notification_seq += 1
        self.store.notifications[notification.id] = notification
        return await self._hydrate(notification)

    async def get_by_id(self, session, notification_id: int) -> Notification | None:
        """Return one notification by primary key.

        Args:
            session: unused session placeholder.
            notification_id: notification to look up.

        Returns:
            Notification | None: the notification or None.
        """
        notification = self.store.notifications.get(notification_id)
        if notification is None:
            return None
        return await self._hydrate(notification)

    async def get_for_comment(
        self,
        session,
        user_id: int,
        comment_id: int,
        notification_type: NotificationType,
    ) -> Notification | None:
        """Return one notification of a user about one comment.

        Args:
            session: unused session placeholder.
            user_id: recipient to look up.
            comment_id: comment the notification refers to.
            notification_type: notification type to match.

        Returns:
            Notification | None: the notification or None.
        """
        for notification in self.store.notifications.values():
            if (
                notification.user_id == user_id
                and notification.comment_id == comment_id
                and notification.type == notification_type
            ):
                return await self._hydrate(notification)
        return None

    async def list_for_user(
        self,
        session,
        user_id: int,
        read: bool | None,
        limit: int,
        offset: int,
    ) -> list[Notification]:
        """Return one page of user notifications, newest first.

        Args:
            session: unused session placeholder.
            user_id: recipient to inspect.
            read: True for read only, False for unread only, None for all.
            limit: page size.
            offset: rows to skip.

        Returns:
            list[Notification]: notifications ordered newest first.
        """
        notifications = await self._for_user(session, user_id, read)
        notifications.sort(key=lambda row: (row.created_at, row.id), reverse=True)
        return notifications[offset : offset + limit]

    async def count_for_user(self, session, user_id: int, read: bool | None) -> int:
        """Count user notifications.

        Args:
            session: unused session placeholder.
            user_id: recipient to inspect.
            read: True for read only, False for unread only, None for all.

        Returns:
            int: number of matching notifications.
        """
        return len(await self._for_user(session, user_id, read))

    async def update(self, session, notification: Notification) -> Notification:
        """Persist changes of one notification.

        Args:
            session: unused session placeholder.
            notification: notification to update.

        Returns:
            Notification: the updated notification.
        """
        self.store.notifications[notification.id] = notification
        return await self._hydrate(notification)

    async def mark_all_read(self, session, user_id: int, read_at) -> int:
        """Mark every unread notification of one user as read.

        Args:
            session: unused session placeholder.
            user_id: recipient to update.
            read_at: timestamp stored as the read moment.

        Returns:
            int: number of notifications marked as read.
        """
        updated = 0
        for notification in self.store.notifications.values():
            if notification.user_id == user_id and notification.read_at is None:
                notification.read_at = read_at
                updated += 1
        return updated

    async def _for_user(
        self, session, user_id: int, read: bool | None
    ) -> list[Notification]:
        """Collect the notifications of one user matching the read state.

        Args:
            session: unused session placeholder.
            user_id: recipient to inspect.
            read: True for read only, False for unread only, None for all.

        Returns:
            list[Notification]: matching notifications in store order.
        """
        notifications = [
            notification
            for notification in self.store.notifications.values()
            if notification.user_id == user_id
        ]
        if read is True:
            notifications = [n for n in notifications if n.read_at is not None]
        elif read is False:
            notifications = [n for n in notifications if n.read_at is None]
        return [await self._hydrate(notification) for notification in notifications]

    async def _hydrate(self, notification: Notification) -> Notification:
        """Load the actor account of one notification.

        Args:
            notification: notification to inspect.

        Returns:
            Notification: the notification with its actor set.
        """
        if notification.actor is None and notification.actor_id is not None:
            notification.actor = await self.user_crud.get_by_id(
                None, notification.actor_id
            )
        return notification
