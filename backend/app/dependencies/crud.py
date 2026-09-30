from app.crud import (
    ActivityCRUD,
    CommentCRUD,
    LabelCRUD,
    NotificationCRUD,
    ProjectCRUD,
    ProjectMemberCRUD,
    TaskCRUD,
    TaskLabelCRUD,
    TaskStatusCRUD,
    TaskWatcherCRUD,
    UserCRUD,
)


async def get_activity_crud() -> ActivityCRUD:
    """Return the activity history storage.

    Returns:
        ActivityCRUD: activity history row data access.
    """
    return ActivityCRUD()


async def get_comment_crud() -> CommentCRUD:
    """Return the comment storage.

    Returns:
        CommentCRUD: comment row data access.
    """
    return CommentCRUD()


async def get_user_crud() -> UserCRUD:
    """Return the user storage.

    Returns:
        UserCRUD: user row data access.
    """
    return UserCRUD()


async def get_project_crud() -> ProjectCRUD:
    """Return the project storage.

    Returns:
        ProjectCRUD: project row data access.
    """
    return ProjectCRUD()


async def get_member_crud() -> ProjectMemberCRUD:
    """Return the project membership storage.

    Returns:
        ProjectMemberCRUD: membership row data access.
    """
    return ProjectMemberCRUD()


async def get_status_crud() -> TaskStatusCRUD:
    """Return the board status storage.

    Returns:
        TaskStatusCRUD: board status row data access.
    """
    return TaskStatusCRUD()


async def get_task_crud() -> TaskCRUD:
    """Return the task storage.

    Returns:
        TaskCRUD: task row data access.
    """
    return TaskCRUD()


async def get_label_crud() -> LabelCRUD:
    """Return the project label storage.

    Returns:
        LabelCRUD: project label row data access.
    """
    return LabelCRUD()


async def get_task_label_crud() -> TaskLabelCRUD:
    """Return the task label attachment storage.

    Returns:
        TaskLabelCRUD: task label attachment row data access.
    """
    return TaskLabelCRUD()


async def get_task_watcher_crud() -> TaskWatcherCRUD:
    """Return the task watcher storage.

    Returns:
        TaskWatcherCRUD: task watcher subscription row data access.
    """
    return TaskWatcherCRUD()


async def get_notification_crud() -> NotificationCRUD:
    """Return the notification storage.

    Returns:
        NotificationCRUD: user notification row data access.
    """
    return NotificationCRUD()
