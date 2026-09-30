from fastapi import Depends

from app.core import Settings, get_settings
from app.crud import (
    ProjectCRUD,
    ProjectMemberCRUD,
    TaskCRUD,
    TaskStatusCRUD,
    UserCRUD,
)
from app.services import (
    AuthService,
    ProjectService,
    TaskService,
    TaskStatusService,
    UserService,
)

from .crud import (
    get_member_crud,
    get_project_crud,
    get_status_crud,
    get_task_crud,
    get_user_crud,
)


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
) -> ProjectService:
    """Return the project domain service.

    Args:
        project_crud: project storage.
        member_crud: membership storage.
        status_crud: board status storage.
        user_crud: user storage.

    Returns:
        ProjectService: project, membership and ownership management.
    """
    return ProjectService(project_crud, member_crud, status_crud, user_crud)


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
) -> TaskService:
    """Return the task domain service.

    Args:
        task_crud: task storage.
        project_crud: project storage.
        member_crud: membership storage.
        status_crud: board status storage.
        user_crud: user storage.

    Returns:
        TaskService: task lifecycle, workflow and board ordering.
    """
    return TaskService(task_crud, project_crud, member_crud, status_crud, user_crud)
