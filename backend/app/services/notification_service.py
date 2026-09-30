"""Notification policy reacting to recorded activity.

One activity entry answers one question: who must be told about this
change? The service resolves the recipients, writes their notification
rows in the same transaction as the domain change and returns the
delivery payloads pushed to the project event stream after commit
(docs/api-endpoints.md, sections 20, 31 and 36).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import ActivityEventType, NotificationType
from app.events import NotificationDelivery
from app.exceptions import NotificationNotFound
from app.models import ActivityEvent, Notification
from app.protocols import (
    NotificationCRUDProtocol,
    ProjectCRUDProtocol,
    ProjectMemberCRUDProtocol,
    TaskCRUDProtocol,
    TaskWatcherCRUDProtocol,
    UserCRUDProtocol,
)
from app.schemas import (
    NotificationProject,
    NotificationRead,
    NotificationTask,
    PageParams,
    Paginated,
    UserBrief,
)
from app.utils import utcnow

#: Event attributes copied next to the source snapshot in notification data.
SNAPSHOT_KEYS = ("comment_id", "from", "to", "role", "fields")


class NotificationService:
    """Turns activity history entries into user notifications."""

    def __init__(
        self,
        notification_crud: NotificationCRUDProtocol,
        task_crud: TaskCRUDProtocol,
        project_crud: ProjectCRUDProtocol,
        member_crud: ProjectMemberCRUDProtocol,
        watcher_crud: TaskWatcherCRUDProtocol,
        user_crud: UserCRUDProtocol,
    ):
        """Attach storage implementations.

        Args:
            notification_crud: notification row storage.
            task_crud: task storage used for the source snapshot.
            project_crud: project storage used for the source snapshot.
            member_crud: membership storage used to keep outsiders out.
            watcher_crud: watcher storage used to resolve task subscribers.
            user_crud: user storage used to resolve the actor.
        """
        self.notification_crud = notification_crud
        self.task_crud = task_crud
        self.project_crud = project_crud
        self.member_crud = member_crud
        self.watcher_crud = watcher_crud
        self.user_crud = user_crud

    async def react(
        self, session: AsyncSession, event: ActivityEvent
    ) -> list[NotificationDelivery]:
        """Create the notifications of one recorded activity entry.

        Called by the activity log inside the transaction that made the
        change, so a rolled back change never notifies anyone. Events
        without notification rules produce nothing.

        Args:
            session: active database session.
            event: activity entry that was just recorded.

        Returns:
            list[NotificationDelivery]: one delivery per created
            notification, carrying the recipient and the rendered payload.
        """
        plans = await self._plans(session, event)
        if not plans:
            return []
        snapshot = await self._snapshot(session, event)
        actor = None
        if event.actor_id is not None:
            actor = await self.user_crud.get_by_id(session, event.actor_id)

        deliveries: list[NotificationDelivery] = []
        for notification_type, user_id in plans:
            notification = await self.notification_crud.create(
                session,
                Notification(
                    user_id=user_id,
                    actor_id=event.actor_id,
                    project_id=event.project_id,
                    task_id=event.task_id,
                    comment_id=_comment_id(event),
                    activity_event_id=event.id,
                    type=notification_type,
                    data={**snapshot, **self._event_data(event)},
                    created_at=utcnow(),
                ),
            )
            notification.actor = actor
            deliveries.append(
                NotificationDelivery(
                    user_id=user_id,
                    payload=self.render(notification).model_dump(mode="json"),
                )
            )
        return deliveries

    async def list_notifications(
        self,
        session: AsyncSession,
        user_id: int,
        page: PageParams,
        read: bool | None = None,
    ) -> Paginated[NotificationRead]:
        """List one page of user notifications, newest first.

        Args:
            session: active database session.
            user_id: id of the authenticated user.
            page: pagination parameters.
            read: True for read only, False for unread only, None for all.

        Returns:
            Paginated[NotificationRead]: one page of notifications.
        """
        notifications = await self.notification_crud.list_for_user(
            session, user_id, read, page.page_size, page.offset
        )
        total = await self.notification_crud.count_for_user(session, user_id, read)
        return Paginated(
            items=[self.render(notification) for notification in notifications],
            page=page.page,
            page_size=page.page_size,
            total=total,
        )

    async def mark_read(
        self, session: AsyncSession, user_id: int, notification_id: int
    ) -> NotificationRead:
        """Mark one notification as read.

        Marking an already read notification is a no-op, not an error.

        Args:
            session: active database session.
            user_id: id of the authenticated user.
            notification_id: notification to mark.

        Returns:
            NotificationRead: the updated notification.

        Raises:
            NotificationNotFound: when the notification is missing or
                belongs to another user.
        """
        notification = await self.notification_crud.get_by_id(session, notification_id)
        if notification is None or notification.user_id != user_id:
            raise NotificationNotFound()
        if notification.read_at is None:
            notification.read_at = utcnow()
            await self.notification_crud.update(session, notification)
        return self.render(notification)

    async def mark_all_read(self, session: AsyncSession, user_id: int) -> int:
        """Mark every unread notification of one user as read.

        Args:
            session: active database session.
            user_id: id of the authenticated user.

        Returns:
            int: number of notifications marked as read.
        """
        return await self.notification_crud.mark_all_read(session, user_id, utcnow())

    async def _plans(
        self, session: AsyncSession, event: ActivityEvent
    ) -> list[tuple[NotificationType, int]]:
        """Resolve the notification type and recipients of one entry.

        The actor is never notified about their own change and only
        current project members are notified about task changes.

        Args:
            session: active database session.
            event: activity entry to react to.

        Returns:
            list[tuple[NotificationType, int]]: one pair per recipient.
        """
        if event.type == ActivityEventType.TASK_ASSIGNED:
            notification_type = NotificationType.TASK_ASSIGNED
            candidates = [int(event.data["user_id"])]
        elif event.type == ActivityEventType.TASK_STATUS_CHANGED:
            notification_type = NotificationType.TASK_STATUS_CHANGED
            candidates = await self._watcher_ids(session, event.task_id)
        elif event.type == ActivityEventType.TASK_UPDATED:
            notification_type = NotificationType.TASK_UPDATED
            candidates = await self._watcher_ids(session, event.task_id)
        elif event.type == ActivityEventType.COMMENT_CREATED:
            notification_type = NotificationType.COMMENT_CREATED
            mentioned = {
                int(user_id) for user_id in event.data.get("mentioned_user_ids", [])
            }
            candidates = [
                user_id
                for user_id in await self._watcher_ids(session, event.task_id)
                if user_id not in mentioned
            ]
        elif event.type == ActivityEventType.COMMENT_MENTIONED:
            notification_type = NotificationType.COMMENT_MENTIONED
            candidates = [int(event.data["user_id"])]
        elif event.type == ActivityEventType.MEMBER_ADDED:
            notification_type = NotificationType.MEMBER_ADDED
            candidates = [int(event.data["user_id"])]
        else:
            return []

        members = None
        if event.task_id is not None:
            members = await self._member_ids(session, event.project_id)

        recipients: list[int] = []
        for user_id in candidates:
            if user_id == event.actor_id or user_id in recipients:
                continue
            if members is not None and user_id not in members:
                continue
            if await self._already_notified(session, event, user_id, notification_type):
                continue
            recipients.append(user_id)
        return [(notification_type, user_id) for user_id in recipients]

    async def _already_notified(
        self,
        session: AsyncSession,
        event: ActivityEvent,
        user_id: int,
        notification_type: NotificationType,
    ) -> bool:
        """Check whether a mention of this comment was already delivered.

        Saving a comment body again re-records every mention in it; only
        the first save notifies the mentioned user.

        Args:
            session: active database session.
            event: activity entry being processed.
            user_id: candidate recipient.
            notification_type: notification type being created.

        Returns:
            bool: True when the user must not be notified again.
        """
        comment_id = _comment_id(event)
        if (
            comment_id is None
            or notification_type is not NotificationType.COMMENT_MENTIONED
        ):
            return False
        existing = await self.notification_crud.get_for_comment(
            session, user_id, comment_id, notification_type
        )
        return existing is not None

    async def _watcher_ids(
        self, session: AsyncSession, task_id: int | None
    ) -> list[int]:
        """Return the watcher ids of one task in subscription order.

        Args:
            session: active database session.
            task_id: task to inspect, None yields nobody.

        Returns:
            list[int]: watcher user ids.
        """
        if task_id is None:
            return []
        watchers = await self.watcher_crud.list_for_task(session, task_id)
        return [watcher.user_id for watcher in watchers]

    async def _member_ids(
        self, session: AsyncSession, project_id: int | None
    ) -> set[int]:
        """Return the member ids of one project.

        Args:
            session: active database session.
            project_id: project to inspect, None yields nobody.

        Returns:
            set[int]: member user ids.
        """
        if project_id is None:
            return set()
        members = await self.member_crud.list_members(session, project_id)
        return {member.user_id for member in members}

    async def _snapshot(
        self, session: AsyncSession, event: ActivityEvent
    ) -> dict[str, Any]:
        """Snapshot the changed object for the notification payload.

        The snapshot keeps the notification readable after the task is
        renamed or soft-deleted.

        Args:
            session: active database session.
            event: activity entry being processed.

        Returns:
            dict[str, Any]: source keys used by the payload.
        """
        if event.task_id is not None:
            task = await self.task_crud.get_by_id(session, event.task_id)
            if task is not None:
                return {
                    "project_key": task.project.key,
                    "task_key": task.key,
                    "task_title": task.title,
                }
            return {
                "task_key": event.data.get("task_key") or event.data.get("key", ""),
            }
        if event.project_id is not None:
            project = await self.project_crud.get_by_id(session, event.project_id)
            if project is not None:
                return {"project_key": project.key}
        return {}

    @staticmethod
    def _event_data(event: ActivityEvent) -> dict[str, Any]:
        """Pick the event attributes that describe the change.

        Args:
            event: activity entry being processed.

        Returns:
            dict[str, Any]: attributes copied into notification data.
        """
        return {key: event.data[key] for key in SNAPSHOT_KEYS if key in event.data}

    @staticmethod
    def render(notification: Notification) -> NotificationRead:
        """Compose one notification response.

        Args:
            notification: notification to render.

        Returns:
            NotificationRead: notification with source and actor briefs.
        """
        data = dict(notification.data or {})
        project = None
        if notification.project_id is not None:
            project = NotificationProject(
                id=notification.project_id,
                key=str(data.get("project_key", "")),
            )
        task = None
        if notification.task_id is not None:
            task = NotificationTask(
                id=notification.task_id,
                key=str(data.get("task_key", "")),
                title=str(data.get("task_title", "")),
            )
        actor = None
        if notification.actor is not None:
            actor = UserBrief(
                id=notification.actor.id, username=notification.actor.username
            )
        return NotificationRead(
            id=notification.id,
            type=notification.type,
            project=project,
            task=task,
            actor=actor,
            data=data,
            is_read=notification.read_at is not None,
            created_at=notification.created_at,
        )


def _comment_id(event: ActivityEvent) -> int | None:
    """Return the comment id carried by an activity entry.

    Args:
        event: activity entry being processed.

    Returns:
        int | None: comment id when the entry is comment scoped.
    """
    comment_id = event.data.get("comment_id")
    return int(comment_id) if comment_id is not None else None
