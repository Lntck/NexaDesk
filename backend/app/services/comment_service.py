from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import ActivityEventType, ProjectRole, Role
from app.exceptions import (
    AccessDenied,
    ArchivedCollection,
    CommentNotFound,
    TaskNotFound,
    UserNotFound,
    ValidationFailed,
)
from app.models import Comment, Task, User
from app.protocols import (
    ActivityLogProtocol,
    CommentCRUDProtocol,
    ProjectMemberCRUDProtocol,
    TaskCRUDProtocol,
    UserCRUDProtocol,
)
from app.schemas import (
    CommentCreate,
    CommentPatch,
    CommentRead,
    PageParams,
    Paginated,
    UserBrief,
)
from app.utils import utcnow

MENTION_PATTERN = re.compile(r"(?<!\w)@([A-Za-z0-9_]+)")


class CommentService:
    """Task discussion management with mention parsing."""

    def __init__(
        self,
        comment_crud: CommentCRUDProtocol,
        task_crud: TaskCRUDProtocol,
        member_crud: ProjectMemberCRUDProtocol,
        user_crud: UserCRUDProtocol,
        activity: ActivityLogProtocol,
    ):
        """Attach storage implementations.

        Args:
            comment_crud: comment row storage.
            task_crud: task storage used to resolve the task scope.
            member_crud: membership storage used for permission checks.
            user_crud: user storage used to resolve authors and mentions.
            activity: activity history recorder.
        """
        self.comment_crud = comment_crud
        self.task_crud = task_crud
        self.member_crud = member_crud
        self.user_crud = user_crud
        self.activity = activity

    async def list_comments(
        self,
        session: AsyncSession,
        actor_id: int,
        task_id: int,
        page: PageParams,
    ) -> Paginated[CommentRead]:
        """List live comments of a task, oldest first.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            task_id: task to inspect.
            page: pagination parameters.

        Returns:
            Paginated[CommentRead]: one page of comments.

        Raises:
            TaskNotFound: when the task is missing or the caller is not a
                member of its project.
        """
        task, _ = await self._load_task(session, task_id, actor_id)
        comments = await self.comment_crud.list_for_task(
            session, task.id, page.page_size, page.offset
        )
        total = await self.comment_crud.count_for_task(session, task.id)
        return Paginated(
            items=[self._read(comment) for comment in comments],
            page=page.page,
            page_size=page.page_size,
            total=total,
        )

    async def create_comment(
        self,
        session: AsyncSession,
        actor_id: int,
        task_id: int,
        data: CommentCreate,
    ) -> CommentRead:
        """Create a comment on a task.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            task_id: task to comment on.
            data: validated comment creation payload.

        Returns:
            CommentRead: the created comment.

        Raises:
            TaskNotFound: when the task is missing or the caller is not a
                member of its project.
            AccessDenied: when the caller cannot comment.
            ArchivedCollection: when the project is archived.
            ValidationFailed: when the body is empty.
        """
        task = await self._get_commentable_task(session, task_id, actor_id)
        self._ensure_non_empty(data.body)

        now = utcnow()
        comment = await self.comment_crud.create_comment(
            session,
            Comment(
                task_id=task.id,
                author_id=actor_id,
                body=data.body,
                created_at=now,
                updated_at=now,
            ),
        )
        comment.author = await self._get_user(session, actor_id)
        mentions = await self._resolve_mentions(session, data.body, actor_id)
        await self.activity.record(
            session,
            ActivityEventType.COMMENT_CREATED,
            actor_id,
            project_id=task.project_id,
            task_id=task.id,
            data={
                "comment_id": comment.id,
                "task_key": task.key,
                "mentioned_user_ids": [user.id for user in mentions],
            },
        )
        await self._record_mentions(session, task, comment, mentions)
        return self._read(comment)

    async def update_comment(
        self,
        session: AsyncSession,
        actor_id: int,
        comment_id: int,
        data: CommentPatch,
    ) -> CommentRead:
        """Update the body of a comment.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            comment_id: comment to update.
            data: merge patch payload with editable fields.

        Returns:
            CommentRead: the updated comment.

        Raises:
            CommentNotFound: when the comment is missing or deleted.
            TaskNotFound: when the comment belongs to a foreign task.
            AccessDenied: when the caller cannot edit the comment.
            ArchivedCollection: when the project is archived.
            ValidationFailed: when the body is cleared or empty.
        """
        comment, task = await self._load_comment(session, comment_id, actor_id)
        self._ensure_writable(task)

        changes = data.changes()
        if "body" not in changes:
            return self._read(comment)
        if changes["body"] is None:
            raise ValidationFailed("Comment body cannot be cleared")

        body = str(changes["body"])
        self._ensure_non_empty(body)
        comment.body = body
        comment.updated_at = utcnow()
        await self.comment_crud.update(session, comment)
        mentions = await self._resolve_mentions(session, body, actor_id)
        await self.activity.record(
            session,
            ActivityEventType.COMMENT_UPDATED,
            actor_id,
            project_id=task.project_id,
            task_id=task.id,
            data={
                "comment_id": comment.id,
                "task_key": task.key,
                "mentioned_user_ids": [user.id for user in mentions],
            },
        )
        await self._record_mentions(session, task, comment, mentions)
        return self._read(comment)

    async def delete_comment(
        self, session: AsyncSession, actor_id: int, comment_id: int
    ) -> None:
        """Soft-delete a comment, keeping the activity history.

        Global admins may moderate archived projects, everyone else is
        blocked by the archive guard.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            comment_id: comment to hide.

        Raises:
            CommentNotFound: when the comment is missing or deleted.
            TaskNotFound: when the comment belongs to a foreign task.
            AccessDenied: when the caller cannot delete the comment.
            ArchivedCollection: when the project is archived.
        """
        comment, task = await self._load_comment(session, comment_id, actor_id)
        if not await self._is_global_admin(session, actor_id):
            self._ensure_writable(task)

        await self.comment_crud.soft_delete(session, comment)
        await self.activity.record(
            session,
            ActivityEventType.COMMENT_DELETED,
            actor_id,
            project_id=task.project_id,
            task_id=task.id,
            data={"comment_id": comment.id, "task_key": task.key},
        )

    async def _get_commentable_task(
        self, session: AsyncSession, task_id: int, actor_id: int
    ) -> Task:
        """Load a task the caller may comment on.

        Args:
            session: active database session.
            task_id: task to load.
            actor_id: id of the authenticated user.

        Returns:
            Task: the task row.

        Raises:
            TaskNotFound: when the task is missing or the caller is not a
                member of its project.
            AccessDenied: when the caller cannot comment.
            ArchivedCollection: when the project is archived.
        """
        task, role = await self._load_task(session, task_id, actor_id)
        if role.level < ProjectRole.MEMBER.level:
            raise AccessDenied()
        self._ensure_writable(task)
        return task

    async def _load_task(
        self, session: AsyncSession, task_id: int, actor_id: int
    ) -> tuple[Task, ProjectRole]:
        """Load a task together with the caller project role.

        Args:
            session: active database session.
            task_id: task to load.
            actor_id: id of the authenticated user.

        Returns:
            tuple[Task, ProjectRole]: the task and the caller role.

        Raises:
            TaskNotFound: when the task is missing or the caller is not a
                member of its project.
        """
        task = await self.task_crud.get_by_id(session, task_id)
        if task is None:
            raise TaskNotFound()
        role = await self.member_crud.get_project_role(
            session, task.project_id, actor_id
        )
        if role is None:
            raise TaskNotFound()
        return task, role

    async def _load_comment(
        self, session: AsyncSession, comment_id: int, actor_id: int
    ) -> tuple[Comment, Task]:
        """Load a comment with its task and enforce the moderation policy.

        The comment author, project admins and global admins may edit and
        delete comments (docs/api-endpoints.md, 15).

        Args:
            session: active database session.
            comment_id: comment to load.
            actor_id: id of the authenticated user.

        Returns:
            tuple[Comment, Task]: the comment and its task.

        Raises:
            CommentNotFound: when the comment is missing or deleted.
            TaskNotFound: when the comment belongs to a foreign task.
            AccessDenied: when the caller is neither the author nor a
                moderator.
        """
        comment = await self.comment_crud.get_by_id(session, comment_id)
        if comment is None:
            raise CommentNotFound()
        task, role = await self._load_task(session, comment.task_id, actor_id)

        is_moderator = role.level >= ProjectRole.ADMIN.level or (
            await self._is_global_admin(session, actor_id)
        )
        if comment.author_id != actor_id and not is_moderator:
            raise AccessDenied()
        return comment, task

    async def _resolve_mentions(
        self, session: AsyncSession, body: str, actor_id: int
    ) -> list[User]:
        """Resolve the accounts mentioned in a comment body.

        Unknown usernames and self-mentions are ignored.

        Args:
            session: active database session.
            body: comment body to scan.
            actor_id: id of the comment author.

        Returns:
            list[User]: mentioned accounts in order of appearance.
        """
        mentions: list[User] = []
        for username in self._mentioned_usernames(body):
            user = await self.user_crud.get_by_username(session, username)
            if user is None or user.id == actor_id:
                continue
            mentions.append(user)
        return mentions

    async def _record_mentions(
        self,
        session: AsyncSession,
        task: Task,
        comment: Comment,
        mentions: list[User],
    ) -> None:
        """Record a mention event for every mentioned account.

        Args:
            session: active database session.
            task: task owning the comment.
            comment: comment whose body was saved.
            mentions: accounts mentioned in the comment body.
        """
        for user in mentions:
            await self.activity.record(
                session,
                ActivityEventType.COMMENT_MENTIONED,
                comment.author_id,
                project_id=task.project_id,
                task_id=task.id,
                data={
                    "comment_id": comment.id,
                    "task_key": task.key,
                    "user_id": user.id,
                    "username": user.username,
                },
            )

    @staticmethod
    def _mentioned_usernames(body: str) -> list[str]:
        """Extract unique mentioned usernames from a comment body.

        Args:
            body: comment body to scan.

        Returns:
            list[str]: mentioned usernames in order of appearance.
        """
        found: list[str] = []
        for username in MENTION_PATTERN.findall(body):
            if username not in found:
                found.append(username)
        return found

    @staticmethod
    def _ensure_non_empty(body: str) -> None:
        """Reject blank comment bodies.

        Args:
            body: body to validate.

        Raises:
            ValidationFailed: when the body holds no visible content.
        """
        if not body.strip():
            raise ValidationFailed("Comment body cannot be empty")

    @staticmethod
    def _ensure_writable(task: Task) -> None:
        """Reject comment writes on archived projects.

        Args:
            task: task owning the comment.

        Raises:
            ArchivedCollection: when the project is archived.
        """
        if task.project.is_archived:
            raise ArchivedCollection()

    async def _is_global_admin(self, session: AsyncSession, actor_id: int) -> bool:
        """Check whether the caller holds the global admin role.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.

        Returns:
            bool: True for global admins.
        """
        user = await self.user_crud.get_by_id(session, actor_id)
        return user is not None and user.role == Role.ADMIN

    async def _get_user(self, session: AsyncSession, user_id: int) -> User:
        """Load a user account by id.

        Args:
            session: active database session.
            user_id: user to load.

        Returns:
            User: the user account.

        Raises:
            UserNotFound: when no user has the given id.
        """
        user = await self.user_crud.get_by_id(session, user_id)
        if user is None:
            raise UserNotFound()
        return user

    @staticmethod
    def _read(comment: Comment) -> CommentRead:
        """Compose one comment response.

        Args:
            comment: comment to render.

        Returns:
            CommentRead: comment with the author brief.
        """
        author = comment.author
        return CommentRead(
            id=comment.id,
            task_id=comment.task_id,
            author=UserBrief(id=author.id, username=author.username),
            body=comment.body,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
        )
