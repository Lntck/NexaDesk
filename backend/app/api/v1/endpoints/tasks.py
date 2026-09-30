from datetime import date

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import RequireRole
from app.auth.schemas import CurrentUser
from app.dependencies import (
    get_db_session,
    get_if_match_version,
    get_task_service,
)
from app.enums import Priority, Role
from app.schemas import (
    BoardRead,
    PageParams,
    Paginated,
    TaskAssign,
    TaskAssignRead,
    TaskCreate,
    TaskListItem,
    TaskPatch,
    TaskPositionRead,
    TaskRead,
    TaskReorder,
    TaskTransition,
    TaskTransitionRead,
)
from app.services import TaskService

router = APIRouter(tags=["Tasks"])


@router.get("/projects/{project_id}/tasks", response_model=Paginated[TaskListItem])
async def list_tasks(
    current_user: CurrentUser = Depends(RequireRole(Role.USER)),
    session: AsyncSession = Depends(get_db_session),
    service: TaskService = Depends(get_task_service),
    project_id: int = Path(...),
    page: PageParams = Depends(),
    search: str | None = None,
    status_key: str | None = Query(default=None, alias="status"),
    priority: Priority | None = None,
    assignee_id: int | None = None,
    creator_id: int | None = None,
    due_before: date | None = None,
    due_after: date | None = None,
    sort: str | None = None,
):
    """List and filter project tasks.

    Args:
        current_user: authenticated caller.
        session: active database session.
        service: task domain service.
        project_id: project to inspect.
        page: pagination parameters.
        search: substring filter on title and description.
        status_key: status key filter.
        priority: priority filter.
        assignee_id: assignee filter.
        creator_id: creator filter.
        due_before: due date upper bound.
        due_after: due date lower bound.
        sort: sort key from the collection whitelist.

    Returns:
        Paginated[TaskListItem]: one page of task cards.
    """
    return await service.list_tasks(
        session,
        current_user.id,
        project_id,
        page,
        search,
        status_key,
        priority,
        assignee_id,
        creator_id,
        due_before,
        due_after,
        sort,
    )


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    data: TaskCreate,
    current_user: CurrentUser = Depends(RequireRole(Role.USER)),
    session: AsyncSession = Depends(get_db_session),
    service: TaskService = Depends(get_task_service),
    project_id: int = Path(...),
):
    """Create a task in a project.

    Args:
        data: validated task creation payload.
        current_user: authenticated caller.
        session: active database session.
        service: task domain service.
        project_id: project to extend.

    Returns:
        TaskRead: the created task.
    """
    return await service.create_task(session, current_user.id, project_id, data)


@router.get("/projects/{project_id}/board", response_model=BoardRead)
async def get_board(
    current_user: CurrentUser = Depends(RequireRole(Role.USER)),
    session: AsyncSession = Depends(get_db_session),
    service: TaskService = Depends(get_task_service),
    project_id: int = Path(...),
    limit_per_column: int = Query(default=50, ge=1, le=100),
):
    """Return tasks grouped by board column.

    Args:
        current_user: authenticated caller.
        session: active database session.
        service: task domain service.
        project_id: project to render.
        limit_per_column: maximum number of cards per column.

    Returns:
        BoardRead: board columns with cards and has_more flags.
    """
    return await service.get_board(
        session, current_user.id, project_id, limit_per_column
    )


@router.get("/tasks/{task_id}", response_model=TaskRead)
async def get_task(
    current_user: CurrentUser = Depends(RequireRole(Role.USER)),
    session: AsyncSession = Depends(get_db_session),
    service: TaskService = Depends(get_task_service),
    task_id: int = Path(...),
):
    """Get a single task.

    Args:
        current_user: authenticated caller.
        session: active database session.
        service: task domain service.
        task_id: task to read.

    Returns:
        TaskRead: the task with its current version.
    """
    return await service.get_task(session, current_user.id, task_id)


@router.patch("/tasks/{task_id}", response_model=TaskRead)
async def update_task(
    data: TaskPatch,
    current_user: CurrentUser = Depends(RequireRole(Role.USER)),
    session: AsyncSession = Depends(get_db_session),
    service: TaskService = Depends(get_task_service),
    version: int = Depends(get_if_match_version),
    task_id: int = Path(...),
):
    """Update editable task fields.

    Args:
        data: merge patch payload with editable fields.
        current_user: authenticated caller.
        session: active database session.
        service: task domain service.
        version: task version from the If-Match header.
        task_id: task to update.

    Returns:
        TaskRead: the updated task.
    """
    return await service.update_task(session, current_user.id, task_id, data, version)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    current_user: CurrentUser = Depends(RequireRole(Role.USER)),
    session: AsyncSession = Depends(get_db_session),
    service: TaskService = Depends(get_task_service),
    version: int = Depends(get_if_match_version),
    task_id: int = Path(...),
):
    """Soft-delete a task.

    Args:
        current_user: authenticated caller.
        session: active database session.
        service: task domain service.
        version: task version from the If-Match header.
        task_id: task to delete.

    Returns:
        None: the response carries no body.
    """
    return await service.delete_task(session, current_user.id, task_id, version)


@router.post("/tasks/{task_id}/transition", response_model=TaskTransitionRead)
async def transition_task(
    data: TaskTransition,
    current_user: CurrentUser = Depends(RequireRole(Role.USER)),
    session: AsyncSession = Depends(get_db_session),
    service: TaskService = Depends(get_task_service),
    task_id: int = Path(...),
):
    """Move a task to an adjacent board column.

    Args:
        data: command payload naming the target status.
        current_user: authenticated caller.
        session: active database session.
        service: task domain service.
        task_id: task to move.

    Returns:
        TaskTransitionRead: the task with its new status.
    """
    return await service.transition(session, current_user.id, task_id, data)


@router.post("/tasks/{task_id}/assign", response_model=TaskAssignRead)
async def assign_task(
    data: TaskAssign,
    current_user: CurrentUser = Depends(RequireRole(Role.USER)),
    session: AsyncSession = Depends(get_db_session),
    service: TaskService = Depends(get_task_service),
    task_id: int = Path(...),
):
    """Assign a task to a project member.

    Args:
        data: command payload naming the assignee.
        current_user: authenticated caller.
        session: active database session.
        service: task domain service.
        task_id: task to modify.

    Returns:
        TaskAssignRead: the task with its new assignee.
    """
    return await service.assign(session, current_user.id, task_id, data)


@router.post("/tasks/{task_id}/unassign", response_model=TaskAssignRead)
async def unassign_task(
    current_user: CurrentUser = Depends(RequireRole(Role.USER)),
    session: AsyncSession = Depends(get_db_session),
    service: TaskService = Depends(get_task_service),
    task_id: int = Path(...),
):
    """Remove the current assignee of a task.

    Args:
        current_user: authenticated caller.
        session: active database session.
        service: task domain service.
        task_id: task to modify.

    Returns:
        TaskAssignRead: the task without an assignee.
    """
    return await service.unassign(session, current_user.id, task_id)


@router.post("/tasks/{task_id}/reorder", response_model=TaskPositionRead)
async def reorder_task(
    data: TaskReorder,
    current_user: CurrentUser = Depends(RequireRole(Role.USER)),
    session: AsyncSession = Depends(get_db_session),
    service: TaskService = Depends(get_task_service),
    task_id: int = Path(...),
):
    """Place a card inside a board column and recalculate ranks.

    Args:
        data: command payload with the target column and neighbors.
        current_user: authenticated caller.
        session: active database session.
        service: task domain service.
        task_id: card to move.

    Returns:
        TaskPositionRead: the final position of the card.
    """
    return await service.reorder(session, current_user.id, task_id, data)
