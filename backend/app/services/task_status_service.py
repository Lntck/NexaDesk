from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import load_role, resolve_role
from app.enums import ProjectRole
from app.exceptions import (
    AlreadyExists,
    ArchivedCollection,
    ProjectNotFound,
    StatusInUse,
    TaskStatusNotFound,
    ValidationFailed,
)
from app.models import TaskStatus
from app.protocols import (
    ProjectCRUDProtocol,
    ProjectMemberCRUDProtocol,
    TaskCRUDProtocol,
    TaskStatusCRUDProtocol,
)
from app.schemas import (
    TaskStatusCreate,
    TaskStatusPatch,
    TaskStatusRead,
)
from app.utils import utcnow


class TaskStatusService:
    """Board status management for one project."""

    def __init__(
        self,
        status_crud: TaskStatusCRUDProtocol,
        task_crud: TaskCRUDProtocol,
        project_crud: ProjectCRUDProtocol,
        member_crud: ProjectMemberCRUDProtocol,
    ):
        """Attach storage implementations.

        Args:
            status_crud: board status storage.
            task_crud: task storage used by the in-use check.
            project_crud: project storage used for the archive check.
            member_crud: membership storage used for permission checks.
        """
        self.status_crud = status_crud
        self.task_crud = task_crud
        self.project_crud = project_crud
        self.member_crud = member_crud

    async def list_statuses(
        self, session: AsyncSession, actor_id: int, project_id: int
    ) -> list[TaskStatusRead]:
        """List project board statuses in board order.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            project_id: project to inspect.

        Returns:
            list[TaskStatusRead]: statuses ordered by position.

        Raises:
            ProjectNotFound: when the project is missing or the caller is not
                a member.
        """
        await load_role(self.member_crud, session, project_id, actor_id)
        statuses = await self.status_crud.list_by_project(session, project_id)
        return [TaskStatusRead.model_validate(s) for s in statuses]

    async def create_status(
        self,
        session: AsyncSession,
        actor_id: int,
        project_id: int,
        data: TaskStatusCreate,
    ) -> TaskStatusRead:
        """Create a custom board status.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            project_id: project to extend.
            data: validated status creation payload.

        Returns:
            TaskStatusRead: the created status.

        Raises:
            ProjectNotFound: when the project is missing or the caller is not
                a member.
            AccessDenied: when the caller cannot manage statuses.
            ArchivedCollection: when the project is archived.
            AlreadyExists: when the status key is taken in the project.
        """
        resolve_role(
            await load_role(self.member_crud, session, project_id, actor_id),
            ProjectRole.ADMIN,
        )
        await self._ensure_writable(session, project_id)

        if await self.status_crud.get_by_key(session, project_id, data.key):
            raise AlreadyExists("Status key already exists")

        statuses = list(await self.status_crud.list_by_project(session, project_id))
        position = data.position if data.position is not None else len(statuses) + 1
        position = max(1, min(position, len(statuses) + 1))

        now = utcnow()
        status = await self.status_crud.create_status(
            session,
            TaskStatus(
                project_id=project_id,
                name=data.name,
                key=data.key,
                color=data.color,
                position=position,
                created_at=now,
                updated_at=now,
            ),
        )
        statuses.insert(position - 1, status)
        await self._renumber(session, statuses)
        return TaskStatusRead.model_validate(status)

    async def update_status(
        self,
        session: AsyncSession,
        actor_id: int,
        project_id: int,
        status_id: int,
        data: TaskStatusPatch,
    ) -> TaskStatusRead:
        """Update status metadata or board position.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            project_id: project owning the status.
            status_id: status to update.
            data: merge patch payload with editable fields.

        Returns:
            TaskStatusRead: the updated status.

        Raises:
            ProjectNotFound: when the project is missing or the caller is not
                a member.
            AccessDenied: when the caller cannot manage statuses.
            ArchivedCollection: when the project is archived.
            TaskStatusNotFound: when the status is missing.
            ValidationFailed: when a non-nullable field is cleared.
        """
        resolve_role(
            await load_role(self.member_crud, session, project_id, actor_id),
            ProjectRole.ADMIN,
        )
        await self._ensure_writable(session, project_id)

        status = await self._get_status(session, project_id, status_id)
        changes = data.changes()

        if "name" in changes:
            if changes["name"] is None:
                raise ValidationFailed("Status name cannot be cleared")
            status.name = changes["name"]
        if "color" in changes:
            if changes["color"] is None:
                raise ValidationFailed("Status color cannot be cleared")
            status.color = changes["color"]

        status.updated_at = utcnow()
        await self.status_crud.update(session, status)

        if changes.get("position") is not None:
            await self._move(session, status, int(changes["position"]))
        return TaskStatusRead.model_validate(status)

    async def delete_status(
        self, session: AsyncSession, actor_id: int, project_id: int, status_id: int
    ) -> None:
        """Delete a board status that holds no tasks.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            project_id: project owning the status.
            status_id: status to delete.

        Raises:
            ProjectNotFound: when the project is missing or the caller is not
                a member.
            AccessDenied: when the caller cannot manage statuses.
            ArchivedCollection: when the project is archived.
            TaskStatusNotFound: when the status is missing.
            StatusInUse: when live tasks still hold the status.
        """
        resolve_role(
            await load_role(self.member_crud, session, project_id, actor_id),
            ProjectRole.ADMIN,
        )
        await self._ensure_writable(session, project_id)

        status = await self._get_status(session, project_id, status_id)
        if await self.status_crud.count_tasks(session, status.id):
            raise StatusInUse()

        statuses = [
            s
            for s in await self.status_crud.list_by_project(session, project_id)
            if s.id != status.id
        ]
        await self.status_crud.delete(session, status)
        await self._renumber(session, statuses)

    async def _move(
        self, session: AsyncSession, status: TaskStatus, position: int
    ) -> None:
        """Move a status to another board position and renumber the board.

        Args:
            session: active database session.
            status: status to move.
            position: requested 1-based board position.
        """
        statuses = [
            s
            for s in await self.status_crud.list_by_project(session, status.project_id)
            if s.id != status.id
        ]
        index = max(1, min(position, len(statuses) + 1))
        statuses.insert(index - 1, status)
        await self._renumber(session, statuses)

    async def _renumber(
        self, session: AsyncSession, statuses: list[TaskStatus]
    ) -> None:
        """Assign dense board positions 1..n in the given order.

        Args:
            session: active database session.
            statuses: statuses in their target order.
        """
        for position, item in enumerate(statuses, start=1):
            item.position = position
            item.updated_at = utcnow()
            await self.status_crud.update(session, item)

    async def _ensure_writable(self, session: AsyncSession, project_id: int) -> None:
        """Reject status management on archived projects.

        Args:
            session: active database session.
            project_id: project to check.

        Raises:
            ProjectNotFound: when no project has the given id.
            ArchivedCollection: when the project is archived.
        """
        project = await self.project_crud.get_by_id(session, project_id)
        if project is None:
            raise ProjectNotFound()
        if project.is_archived:
            raise ArchivedCollection()

    async def _get_status(
        self, session: AsyncSession, project_id: int, status_id: int
    ) -> TaskStatus:
        """Load one board status of a project.

        Args:
            session: active database session.
            project_id: project owning the status.
            status_id: status to load.

        Returns:
            TaskStatus: the status row.

        Raises:
            TaskStatusNotFound: when the status is missing.
        """
        status = await self.status_crud.get_by_id(session, project_id, status_id)
        if status is None:
            raise TaskStatusNotFound()
        return status
