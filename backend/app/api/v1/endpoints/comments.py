from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.schemas import CurrentUser
from app.dependencies import get_comment_service, get_db_session
from app.schemas import CommentCreate, CommentPatch, CommentRead, PageParams, Paginated
from app.services import CommentService

router = APIRouter(tags=["Comments"])


@router.get("/tasks/{task_id}/comments", response_model=Paginated[CommentRead])
async def list_comments(
    page: PageParams = Depends(),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: CommentService = Depends(get_comment_service),
    task_id: int = Path(...),
):
    """List live comments of a task, oldest first.

    Args:
        page: pagination parameters.
        current_user: authenticated caller.
        session: active database session.
        service: comment domain service.
        task_id: task to inspect.

    Returns:
        Paginated[CommentRead]: one page of comments.
    """
    return await service.list_comments(session, current_user.id, task_id, page)


@router.post(
    "/tasks/{task_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    data: CommentCreate,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: CommentService = Depends(get_comment_service),
    task_id: int = Path(...),
):
    """Create a comment on a task.

    Args:
        data: validated comment creation payload.
        current_user: authenticated caller.
        session: active database session.
        service: comment domain service.
        task_id: task to comment on.

    Returns:
        CommentRead: the created comment.
    """
    return await service.create_comment(session, current_user.id, task_id, data)


@router.patch("/comments/{comment_id}", response_model=CommentRead)
async def update_comment(
    data: CommentPatch,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: CommentService = Depends(get_comment_service),
    comment_id: int = Path(...),
):
    """Update the body of a comment.

    Args:
        data: merge patch payload with editable fields.
        current_user: authenticated caller.
        session: active database session.
        service: comment domain service.
        comment_id: comment to update.

    Returns:
        CommentRead: the updated comment.
    """
    return await service.update_comment(session, current_user.id, comment_id, data)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: CommentService = Depends(get_comment_service),
    comment_id: int = Path(...),
):
    """Soft-delete a comment, keeping the activity history.

    Args:
        current_user: authenticated caller.
        session: active database session.
        service: comment domain service.
        comment_id: comment to hide.

    Returns:
        None: the response carries no body.
    """
    return await service.delete_comment(session, current_user.id, comment_id)
