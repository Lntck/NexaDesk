from app.models import Comment
from app.utils import utcnow

from .domain import DomainStore


class FakeCommentCRUD:
    """In-memory stand-in for CommentCRUD used in unit tests."""

    def __init__(self, store: DomainStore):
        """Attach the shared in-memory tables.

        Args:
            store: shared domain tables.
        """
        self.store = store

    async def create_comment(self, session, comment: Comment) -> Comment:
        """Store a new comment and assign an id.

        Args:
            session: unused session placeholder.
            comment: comment to store.

        Returns:
            Comment: the stored comment with assigned id.
        """
        comment.id = self.store.comment_seq
        self.store.comment_seq += 1
        comment.deleted_at = None
        comment.created_at = comment.created_at or utcnow()
        comment.updated_at = comment.updated_at or utcnow()
        self.store.comments[comment.id] = comment
        return comment

    async def get_by_id(self, session, comment_id: int) -> Comment | None:
        """Return one live comment by id.

        Args:
            session: unused session placeholder.
            comment_id: comment id to look up.

        Returns:
            Comment | None: the comment or None when missing or deleted.
        """
        comment = self.store.comments.get(comment_id)
        if comment is None or comment.deleted_at is not None:
            return None
        return comment

    async def list_for_task(
        self, session, task_id: int, limit: int, offset: int
    ) -> list[Comment]:
        """Return one page of live task comments, oldest first.

        Args:
            session: unused session placeholder.
            task_id: task to inspect.
            limit: page size.
            offset: rows to skip.

        Returns:
            list[Comment]: comments ordered oldest first.
        """
        comments = self._sorted(
            [
                comment
                for comment in self.store.comments.values()
                if comment.task_id == task_id and comment.deleted_at is None
            ]
        )
        return comments[offset : offset + limit]

    async def count_for_task(self, session, task_id: int) -> int:
        """Count live comments of a task.

        Args:
            session: unused session placeholder.
            task_id: task to inspect.

        Returns:
            int: number of live comments.
        """
        return len(
            [
                comment
                for comment in self.store.comments.values()
                if comment.task_id == task_id and comment.deleted_at is None
            ]
        )

    async def update(self, session, comment: Comment) -> Comment:
        """Flush pending changes of a comment row.

        Args:
            session: unused session placeholder.
            comment: comment to flush.

        Returns:
            Comment: the same comment instance.
        """
        return comment

    async def soft_delete(self, session, comment: Comment) -> Comment:
        """Mark a comment as deleted, keeping the row for history.

        Args:
            session: unused session placeholder.
            comment: comment to hide.

        Returns:
            Comment: the same comment instance.
        """
        comment.deleted_at = comment.deleted_at or utcnow()
        return comment

    @staticmethod
    def _sorted(comments: list[Comment]) -> list[Comment]:
        """Order comments oldest first.

        Args:
            comments: comments to order.

        Returns:
            list[Comment]: comments ordered by creation time and id.
        """
        return sorted(comments, key=lambda comment: (comment.created_at, comment.id))
