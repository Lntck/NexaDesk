from enum import StrEnum


class NotificationType(StrEnum):
    """Reason a notification was created for its recipient."""

    TASK_ASSIGNED = "task.assigned"
    COMMENT_CREATED = "comment.created"
    COMMENT_MENTIONED = "comment.mentioned"
    TASK_STATUS_CHANGED = "task.status_changed"
    TASK_UPDATED = "task.updated"
    MEMBER_ADDED = "member.added"


class NotificationDeliveryType(StrEnum):
    """Wire type of notification frames inside a project event stream."""

    NOTIFICATION_CREATED = "notification.created"
