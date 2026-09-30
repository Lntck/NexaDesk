from app.crud import ProjectCRUD, ProjectMemberCRUD, TaskCRUD, TaskStatusCRUD, UserCRUD


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
