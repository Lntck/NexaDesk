from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import resolve_role
from app.enums import ActivityEventType, ProjectRole
from app.exceptions import (
    TaskNotFound,
    UserNotFound,
)
from app.models import Task, TaskWatcher, User
from app.protocols import (
    ActivityLogProtocol,
    ProjectMemberCRUDProtocol,
    TaskCRUDProtocol,
    TaskWatcherCRUDProtocol,
    UserCRUDProtocol,
)
from app.schemas import UserBrief, WatcherRead
from app.utils import utcnow


class WatcherService:
    """Task watcher subscriptions.

    Watch and unwatch are idempotent commands (docs/api-endpoints.md, 30) and
    never modify the task itself, so they stay available on archived projects.
    """

    def __init__(
        self,
        watcher_crud: TaskWatcherCRUDProtocol,
        task_crud: TaskCRUDProtocol,
        member_crud: ProjectMemberCRUDProtocol,
        user_crud: UserCRUDProtocol,
        activity: ActivityLogProtocol,
    ):
        """Attach storage implementations.

        Args:
            watcher_crud: task watcher subscription storage.
            task_crud: task storage used to resolve the task scope.
            member_crud: membership storage used for permission checks.
            user_crud: user storage used to resolve accounts.
            activity: activity history recorder.
        """
        self.watcher_crud = watcher_crud
        self.task_crud = task_crud
        self.member_crud = member_crud
        self.user_crud = user_crud
        self.activity = activity

    async def list_watchers(
        self, session: AsyncSession, actor_id: int, task_id: int
    ) -> list[WatcherRead]:
        """List the watchers of a task, oldest subscription first.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            task_id: task to inspect.

        Returns:
            list[WatcherRead]: watcher subscriptions.

        Raises:
            TaskNotFound: when the task is missing or the caller is not a
                member of its project.
        """
        task, _ = await self._load_task(session, task_id, actor_id)
        watchers = await self.watcher_crud.list_for_task(session, task.id)
        return [self._read(watcher) for watcher in watchers]

    async def watch(
        self, session: AsyncSession, actor_id: int, task_id: int
    ) -> WatcherRead:
        """Subscribe the caller to task changes.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            task_id: task to watch.

        Returns:
            WatcherRead: the caller subscription.

        Raises:
            TaskNotFound: when the task is missing or the caller is not a
                member of its project.
            UserNotFound: when no account has the caller id.
        """
        task, _ = await self._load_task(session, task_id, actor_id)

        existing = await self.watcher_crud.get(session, task.id, actor_id)
        if existing is not None:
            return self._read(existing)

        user = await self._get_user(session, actor_id)
        watcher = await self.watcher_crud.add_watcher(
            session,
            TaskWatcher(task_id=task.id, user_id=user.id, created_at=utcnow()),
        )
        watcher.user = user
        await self.activity.record(
            session,
            ActivityEventType.WATCHER_ADDED,
            actor_id,
            project_id=task.project_id,
            task_id=task.id,
            data={"user_id": user.id, "username": user.username, "task_key": task.key},
        )
        return self._read(watcher)

    async def unwatch(self, session: AsyncSession, actor_id: int, task_id: int) -> None:
        """Unsubscribe the caller from task changes.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            task_id: task to stop watching.

        Raises:
            TaskNotFound: when the task is missing or the caller is not a
                member of its project.
        """
        task, _ = await self._load_task(session, task_id, actor_id)

        watcher = await self.watcher_crud.get(session, task.id, actor_id)
        if watcher is None:
            return

        user = await self._get_user(session, actor_id)
        await self.watcher_crud.remove(session, watcher)
        await self.activity.record(
            session,
            ActivityEventType.WATCHER_REMOVED,
            actor_id,
            project_id=task.project_id,
            task_id=task.id,
            data={"user_id": user.id, "username": user.username, "task_key": task.key},
        )

    async def remove_watcher(
        self, session: AsyncSession, actor_id: int, task_id: int, user_id: int
    ) -> None:
        """Remove one watcher from a task.

        A watcher may always remove himself, project admins may remove anyone.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            task_id: task to update.
            user_id: watcher to remove.

        Raises:
            TaskNotFound: when the task is missing or the caller is not a
                member of its project.
            AccessDenied: when the caller may not remove the watcher.
            UserNotFound: when the watcher account is missing.
        """
        task, role = await self._load_task(session, task_id, actor_id)
        if user_id != actor_id:
            resolve_role(role, ProjectRole.ADMIN, missing=TaskNotFound)

        watcher = await self.watcher_crud.get(session, task.id, user_id)
        if watcher is None:
            return

        user = await self._get_user(session, user_id)
        await self.watcher_crud.remove(session, watcher)
        await self.activity.record(
            session,
            ActivityEventType.WATCHER_REMOVED,
            actor_id,
            project_id=task.project_id,
            task_id=task.id,
            data={"user_id": user.id, "username": user.username, "task_key": task.key},
        )

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
    def _read(watcher: TaskWatcher) -> WatcherRead:
        """Compose one watcher response.

        Args:
            watcher: subscription to render.

        Returns:
            WatcherRead: subscription with the user brief.
        """
        user = watcher.user
        return WatcherRead(
            user=UserBrief(id=user.id, username=user.username),
            created_at=watcher.created_at,
        )
