from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Comment
from app.utils import utcnow


class CommentCRUD:
    """Task comment row data access."""

    async def create_comment(self, session: AsyncSession, comment: Comment) -> Comment:
        """Persist a new comment.

        Args:
            session: active database session.
            comment: comment to persist.

        Returns:
            Comment: the persisted comment.
        """
        session.add(comment)
        await session.flush()
        return comment

    async def get_by_id(self, session: AsyncSession, comment_id: int) -> Comment | None:
        """Return one live comment by id.

        Args:
            session: active database session.
            comment_id: comment id to look up.

        Returns:
            Comment | None: the comment or None when missing or deleted.
        """
        stmt = select(Comment).where(
            Comment.id == comment_id, Comment.deleted_at.is_(None)
        )
        result = await session.scalar(stmt)
        return result

    async def list_for_task(
        self, session: AsyncSession, task_id: int, limit: int, offset: int
    ) -> list[Comment]:
        """Return one page of live task comments, oldest first.

        Args:
            session: active database session.
            task_id: task to inspect.
            limit: page size.
            offset: rows to skip.

        Returns:
            list[Comment]: comments ordered oldest first.
        """
        stmt = (
            select(Comment)
            .where(Comment.task_id == task_id, Comment.deleted_at.is_(None))
            .order_by(Comment.created_at, Comment.id)
            .limit(limit)
            .offset(offset)
        )
        return list((await session.scalars(stmt)).all())

    async def count_for_task(self, session: AsyncSession, task_id: int) -> int:
        """Count live comments of a task.

        Args:
            session: active database session.
            task_id: task to inspect.

        Returns:
            int: number of live comments.
        """
        stmt = (
            select(func.count())
            .select_from(Comment)
            .where(Comment.task_id == task_id, Comment.deleted_at.is_(None))
        )
        return int(await session.scalar(stmt) or 0)

    async def soft_delete(self, session: AsyncSession, comment: Comment) -> Comment:
        """Mark a comment as deleted, keeping the row for history.

        Args:
            session: active database session.
            comment: comment to hide.

        Returns:
            Comment: the same comment instance.
        """
        comment.deleted_at = utcnow()
        await session.flush()
        return comment

    async def update(self, session: AsyncSession, comment: Comment) -> Comment:
        """Flush pending changes of a comment row.

        Args:
            session: active database session.
            comment: comment to flush.

        Returns:
            Comment: the same comment instance.
        """
        await session.flush()
        return comment
