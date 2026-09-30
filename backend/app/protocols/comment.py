from typing import Protocol, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Comment


class CommentCRUDProtocol(Protocol):
    """Data access for task comments."""

    async def create_comment(self, session: AsyncSession, comment: Comment) -> Comment:
        """Persist a new comment.

        Args:
            session: active database session.
            comment: comment to persist.

        Returns:
            Comment: the persisted comment.
        """
        ...

    async def get_by_id(self, session: AsyncSession, comment_id: int) -> Comment | None:
        """Return one live comment by id.

        Args:
            session: active database session.
            comment_id: comment id to look up.

        Returns:
            Comment | None: the comment or None when missing or deleted.
        """
        ...

    async def list_for_task(
        self, session: AsyncSession, task_id: int, limit: int, offset: int
    ) -> Sequence[Comment]:
        """Return one page of live task comments, oldest first.

        Args:
            session: active database session.
            task_id: task to inspect.
            limit: page size.
            offset: rows to skip.

        Returns:
            Sequence[Comment]: comments ordered oldest first.
        """
        ...

    async def count_for_task(self, session: AsyncSession, task_id: int) -> int:
        """Count live comments of a task.

        Args:
            session: active database session.
            task_id: task to inspect.

        Returns:
            int: number of live comments.
        """
        ...

    async def update(self, session: AsyncSession, comment: Comment) -> Comment:
        """Flush pending changes of a comment row.

        Args:
            session: active database session.
            comment: comment to flush.

        Returns:
            Comment: the same comment instance.
        """
        ...

    async def soft_delete(self, session: AsyncSession, comment: Comment) -> Comment:
        """Mark a comment as deleted, keeping the row for history.

        Args:
            session: active database session.
            comment: comment to hide.

        Returns:
            Comment: the same comment instance.
        """
        ...
