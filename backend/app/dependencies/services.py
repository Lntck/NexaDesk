from fastapi import Depends

from app.core import Settings, get_settings
from app.crud import (
    ActivityCRUD,
    CommentCRUD,
    LabelCRUD,
    ProjectCRUD,
    ProjectMemberCRUD,
    TaskCRUD,
    TaskLabelCRUD,
    TaskStatusCRUD,
    TaskWatcherCRUD,
    UserCRUD,
)
from app.events import ActivityLog
from app.services import (
    ActivityService,
    AuthService,
    CommentService,
    LabelService,
    ProjectService,
    TaskService,
    TaskStatusService,
    UserService,
    WatcherService,
)

from .crud import (
    get_activity_crud,
    get_comment_crud,
    get_label_crud,
    get_member_crud,
    get_project_crud,
    get_status_crud,
    get_task_crud,
    get_task_label_crud,
    get_task_watcher_crud,
    get_user_crud,
)


async def get_activity_log(
    activity_crud: ActivityCRUD = Depends(get_activity_crud),
) -> ActivityLog:
    """Return the activity history recorder.

    Args:
        activity_crud: activity history storage.

    Returns:
        ActivityLog: recorder writing the immutable activity history.
    """
    return ActivityLog(activity_crud)


async def get_user_service(
    user_crud: UserCRUD = Depends(get_user_crud),
) -> UserService:
    """Return the user account service.

    Args:
        user_crud: user storage.

    Returns:
        UserService: user account management.
    """
    return UserService(user_crud)


async def get_auth_service(
    user_service: UserService = Depends(get_user_service),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    """Return the authentication service.

    Args:
        user_service: user account management.
        settings: application settings with JWT secrets.

    Returns:
        AuthService: authentication and token management.
    """
    return AuthService(user_service, settings)


async def get_project_service(
    project_crud: ProjectCRUD = Depends(get_project_crud),
    member_crud: ProjectMemberCRUD = Depends(get_member_crud),
    status_crud: TaskStatusCRUD = Depends(get_status_crud),
    user_crud: UserCRUD = Depends(get_user_crud),
    activity: ActivityLog = Depends(get_activity_log),
) -> ProjectService:
    """Return the project domain service.

    Args:
        project_crud: project storage.
        member_crud: membership storage.
        status_crud: board status storage.
        user_crud: user storage.
        activity: activity history recorder.

    Returns:
        ProjectService: project, membership and ownership management.
    """
    return ProjectService(project_crud, member_crud, status_crud, user_crud, activity)


async def get_status_service(
    status_crud: TaskStatusCRUD = Depends(get_status_crud),
    task_crud: TaskCRUD = Depends(get_task_crud),
    project_crud: ProjectCRUD = Depends(get_project_crud),
    member_crud: ProjectMemberCRUD = Depends(get_member_crud),
) -> TaskStatusService:
    """Return the board status domain service.

    Args:
        status_crud: board status storage.
        task_crud: task storage.
        project_crud: project storage.
        member_crud: membership storage.

    Returns:
        TaskStatusService: board status management.
    """
    return TaskStatusService(status_crud, task_crud, project_crud, member_crud)


async def get_task_service(
    task_crud: TaskCRUD = Depends(get_task_crud),
    project_crud: ProjectCRUD = Depends(get_project_crud),
    member_crud: ProjectMemberCRUD = Depends(get_member_crud),
    status_crud: TaskStatusCRUD = Depends(get_status_crud),
    user_crud: UserCRUD = Depends(get_user_crud),
    comment_crud: CommentCRUD = Depends(get_comment_crud),
    task_label_crud: TaskLabelCRUD = Depends(get_task_label_crud),
    watcher_crud: TaskWatcherCRUD = Depends(get_task_watcher_crud),
    activity: ActivityLog = Depends(get_activity_log),
) -> TaskService:
    """Return the task domain service.

    Args:
        task_crud: task storage.
        project_crud: project storage.
        member_crud: membership storage.
        status_crud: board status storage.
        user_crud: user storage.
        comment_crud: comment storage used for counters.
        task_label_crud: label attachment storage used for the label list.
        watcher_crud: watcher storage used for the watchers counter.
        activity: activity history recorder.

    Returns:
        TaskService: task lifecycle, workflow and board ordering.
    """
    return TaskService(
        task_crud,
        project_crud,
        member_crud,
        status_crud,
        user_crud,
        comment_crud,
        task_label_crud,
        watcher_crud,
        activity,
    )


async def get_comment_service(
    comment_crud: CommentCRUD = Depends(get_comment_crud),
    task_crud: TaskCRUD = Depends(get_task_crud),
    member_crud: ProjectMemberCRUD = Depends(get_member_crud),
    user_crud: UserCRUD = Depends(get_user_crud),
    activity: ActivityLog = Depends(get_activity_log),
) -> CommentService:
    """Return the comment domain service.

    Args:
        comment_crud: comment storage.
        task_crud: task storage used to resolve the task scope.
        member_crud: membership storage used for permission checks.
        user_crud: user storage used to resolve authors and mentions.
        activity: activity history recorder.

    Returns:
        CommentService: task discussion management.
    """
    return CommentService(comment_crud, task_crud, member_crud, user_crud, activity)


async def get_label_service(
    label_crud: LabelCRUD = Depends(get_label_crud),
    task_label_crud: TaskLabelCRUD = Depends(get_task_label_crud),
    task_crud: TaskCRUD = Depends(get_task_crud),
    project_crud: ProjectCRUD = Depends(get_project_crud),
    member_crud: ProjectMemberCRUD = Depends(get_member_crud),
    activity: ActivityLog = Depends(get_activity_log),
) -> LabelService:
    """Return the label domain service.

    Args:
        label_crud: project label storage.
        task_label_crud: task label attachment storage.
        task_crud: task storage used to resolve the task scope.
        project_crud: project storage used for the archive check.
        member_crud: membership storage used for permission checks.
        activity: activity history recorder.

    Returns:
        LabelService: project label and task label management.
    """
    return LabelService(
        label_crud, task_label_crud, task_crud, project_crud, member_crud, activity
    )


async def get_watcher_service(
    watcher_crud: TaskWatcherCRUD = Depends(get_task_watcher_crud),
    task_crud: TaskCRUD = Depends(get_task_crud),
    member_crud: ProjectMemberCRUD = Depends(get_member_crud),
    user_crud: UserCRUD = Depends(get_user_crud),
    activity: ActivityLog = Depends(get_activity_log),
) -> WatcherService:
    """Return the watcher domain service.

    Args:
        watcher_crud: task watcher subscription storage.
        task_crud: task storage used to resolve the task scope.
        member_crud: membership storage used for permission checks.
        user_crud: user storage used to resolve accounts.
        activity: activity history recorder.

    Returns:
        WatcherService: task watcher subscription management.
    """
    return WatcherService(watcher_crud, task_crud, member_crud, user_crud, activity)


async def get_activity_service(
    activity_crud: ActivityCRUD = Depends(get_activity_crud),
    member_crud: ProjectMemberCRUD = Depends(get_member_crud),
    task_crud: TaskCRUD = Depends(get_task_crud),
) -> ActivityService:
    """Return the activity history query service.

    Args:
        activity_crud: activity history storage.
        member_crud: membership storage used for access checks.
        task_crud: task storage used to resolve task scope.

    Returns:
        ActivityService: read-only activity history view.
    """
    return ActivityService(activity_crud, member_crud, task_crud)
