from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import load_role
from app.exceptions import TaskNotFound
from app.models import ActivityEvent
from app.protocols import (
    ActivityCRUDProtocol,
    ProjectMemberCRUDProtocol,
    TaskCRUDProtocol,
)
from app.schemas import ActivityEventRead, PageParams, Paginated, UserBrief


class ActivityService:
    """Read-only view over the immutable activity history."""

    def __init__(
        self,
        activity_crud: ActivityCRUDProtocol,
        member_crud: ProjectMemberCRUDProtocol,
        task_crud: TaskCRUDProtocol,
    ):
        """Attach storage implementations.

        Args:
            activity_crud: activity history storage.
            member_crud: membership storage used for access checks.
            task_crud: task storage used to resolve task scope.
        """
        self.activity_crud = activity_crud
        self.member_crud = member_crud
        self.task_crud = task_crud

    async def list_project_activity(
        self,
        session: AsyncSession,
        actor_id: int,
        project_id: int,
        page: PageParams,
    ) -> Paginated[ActivityEventRead]:
        """List project activity history, newest first.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            project_id: project to inspect.
            page: pagination parameters.

        Returns:
            Paginated[ActivityEventRead]: one page of history entries.

        Raises:
            ProjectNotFound: when the project is missing or the caller is not
                a member.
        """
        await load_role(self.member_crud, session, project_id, actor_id)
        events = await self.activity_crud.list_for_project(
            session, project_id, page.page_size, page.offset
        )
        total = await self.activity_crud.count_for_project(session, project_id)
        return Paginated(
            items=[self._read(event) for event in events],
            page=page.page,
            page_size=page.page_size,
            total=total,
        )

    async def list_task_activity(
        self,
        session: AsyncSession,
        actor_id: int,
        task_id: int,
        page: PageParams,
    ) -> Paginated[ActivityEventRead]:
        """List activity history of a single task, newest first.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            task_id: task to inspect.
            page: pagination parameters.

        Returns:
            Paginated[ActivityEventRead]: one page of history entries.

        Raises:
            TaskNotFound: when the task is missing or the caller is not a
                member of its project.
        """
        task = await self.task_crud.get_by_id(session, task_id)
        if task is None:
            raise TaskNotFound()
        await load_role(self.member_crud, session, task.project_id, actor_id)

        events = await self.activity_crud.list_for_task(
            session, task_id, page.page_size, page.offset
        )
        total = await self.activity_crud.count_for_task(session, task_id)
        return Paginated(
            items=[self._read(event) for event in events],
            page=page.page,
            page_size=page.page_size,
            total=total,
        )

    @staticmethod
    def _read(event: ActivityEvent) -> ActivityEventRead:
        """Compose one history entry response.

        Args:
            event: history entry to render.

        Returns:
            ActivityEventRead: entry with the actor brief.
        """
        actor = (
            UserBrief(id=event.actor.id, username=event.actor.username)
            if event.actor is not None
            else None
        )
        return ActivityEventRead(
            id=event.id,
            type=event.type,
            actor=actor,
            task_id=event.task_id,
            data=event.data or {},
            created_at=event.created_at,
        )
