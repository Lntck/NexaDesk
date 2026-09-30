from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import load_role, resolve_role
from app.enums import ActivityEventType, ProjectRole
from app.exceptions import (
    AlreadyExists,
    ArchivedCollection,
    LabelNotFound,
    ProjectNotFound,
    TaskNotFound,
    ValidationFailed,
)
from app.models import Label, Project, Task, TaskLabel
from app.protocols import (
    ActivityLogProtocol,
    LabelCRUDProtocol,
    ProjectCRUDProtocol,
    ProjectMemberCRUDProtocol,
    TaskCRUDProtocol,
    TaskLabelCRUDProtocol,
)
from app.schemas import LabelCreate, LabelPatch, LabelRead
from app.utils import utcnow


class LabelService:
    """Project label management and task label attachments."""

    def __init__(
        self,
        label_crud: LabelCRUDProtocol,
        task_label_crud: TaskLabelCRUDProtocol,
        task_crud: TaskCRUDProtocol,
        project_crud: ProjectCRUDProtocol,
        member_crud: ProjectMemberCRUDProtocol,
        activity: ActivityLogProtocol,
    ):
        """Attach storage implementations.

        Args:
            label_crud: project label storage.
            task_label_crud: task label attachment storage.
            task_crud: task storage used to resolve the task scope.
            project_crud: project storage used for the archive check.
            member_crud: membership storage used for permission checks.
            activity: activity history recorder.
        """
        self.label_crud = label_crud
        self.task_label_crud = task_label_crud
        self.task_crud = task_crud
        self.project_crud = project_crud
        self.member_crud = member_crud
        self.activity = activity

    async def list_labels(
        self, session: AsyncSession, actor_id: int, project_id: int
    ) -> list[LabelRead]:
        """List project labels ordered by name.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            project_id: project to inspect.

        Returns:
            list[LabelRead]: labels of the project.

        Raises:
            ProjectNotFound: when the project is missing or the caller is not
                a member.
        """
        await load_role(self.member_crud, session, project_id, actor_id)
        labels = await self.label_crud.list_by_project(session, project_id)
        return [LabelRead.model_validate(label) for label in labels]

    async def create_label(
        self,
        session: AsyncSession,
        actor_id: int,
        project_id: int,
        data: LabelCreate,
    ) -> LabelRead:
        """Create a project label.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            project_id: project to extend.
            data: validated label creation payload.

        Returns:
            LabelRead: the created label.

        Raises:
            ProjectNotFound: when the project is missing or the caller is not
                a member.
            AccessDenied: when the caller cannot manage labels.
            ArchivedCollection: when the project is archived.
            AlreadyExists: when the label name is taken in the project.
        """
        resolve_role(
            await load_role(self.member_crud, session, project_id, actor_id),
            ProjectRole.ADMIN,
        )
        await self._ensure_writable_project(session, project_id)
        await self._ensure_unique_name(session, project_id, data.name)

        now = utcnow()
        label = await self.label_crud.create_label(
            session,
            Label(
                project_id=project_id,
                name=data.name,
                color=data.color,
                created_at=now,
                updated_at=now,
            ),
        )
        return LabelRead.model_validate(label)

    async def update_label(
        self,
        session: AsyncSession,
        actor_id: int,
        project_id: int,
        label_id: int,
        data: LabelPatch,
    ) -> LabelRead:
        """Update label metadata.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            project_id: project owning the label.
            label_id: label to update.
            data: merge patch payload with editable fields.

        Returns:
            LabelRead: the updated label.

        Raises:
            ProjectNotFound: when the project is missing or the caller is not
                a member.
            AccessDenied: when the caller cannot manage labels.
            ArchivedCollection: when the project is archived.
            LabelNotFound: when the label is missing.
            AlreadyExists: when the new name is taken in the project.
            ValidationFailed: when a non-nullable field is cleared.
        """
        resolve_role(
            await load_role(self.member_crud, session, project_id, actor_id),
            ProjectRole.ADMIN,
        )
        await self._ensure_writable_project(session, project_id)

        label = await self._get_label(session, project_id, label_id)
        changes = data.changes()

        if "name" in changes:
            if changes["name"] is None:
                raise ValidationFailed("Label name cannot be cleared")
            name = str(changes["name"])
            await self._ensure_unique_name(session, project_id, name, label.id)
            label.name = name
        if "color" in changes:
            if changes["color"] is None:
                raise ValidationFailed("Label color cannot be cleared")
            label.color = str(changes["color"])

        label.updated_at = utcnow()
        await self.label_crud.update(session, label)
        return LabelRead.model_validate(label)

    async def delete_label(
        self, session: AsyncSession, actor_id: int, project_id: int, label_id: int
    ) -> None:
        """Delete a label and detach it from every task.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            project_id: project owning the label.
            label_id: label to delete.

        Raises:
            ProjectNotFound: when the project is missing or the caller is not
                a member.
            AccessDenied: when the caller cannot manage labels.
            ArchivedCollection: when the project is archived.
            LabelNotFound: when the label is missing.
        """
        resolve_role(
            await load_role(self.member_crud, session, project_id, actor_id),
            ProjectRole.ADMIN,
        )
        await self._ensure_writable_project(session, project_id)

        label = await self._get_label(session, project_id, label_id)
        await self.task_label_crud.delete_for_label(session, label.id)
        await self.label_crud.delete(session, label)

    async def attach_label(
        self, session: AsyncSession, actor_id: int, task_id: int, label_id: int
    ) -> LabelRead:
        """Attach a project label to a task.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            task_id: task to extend.
            label_id: label to attach.

        Returns:
            LabelRead: the attached label.

        Raises:
            TaskNotFound: when the task is missing or the caller is not a
                member of its project.
            AccessDenied: when the caller cannot edit tasks.
            LabelNotFound: when the label is missing or belongs to another
                project.
            AlreadyExists: when the label is already attached.
            ArchivedCollection: when the project is archived.
        """
        task, role = await self._load_task(session, task_id, actor_id)
        resolve_role(role, ProjectRole.MEMBER)
        self._ensure_writable(task)

        label = await self._get_label(session, task.project_id, label_id)
        if await self.task_label_crud.get(session, task.id, label.id):
            raise AlreadyExists("Label already attached")

        await self.task_label_crud.attach(
            session,
            TaskLabel(task_id=task.id, label_id=label.id, created_at=utcnow()),
        )
        await self.activity.record(
            session,
            ActivityEventType.LABEL_ADDED,
            actor_id,
            project_id=task.project_id,
            task_id=task.id,
            data={
                "label_id": label.id,
                "label_name": label.name,
                "task_key": task.key,
            },
        )
        return LabelRead.model_validate(label)

    async def detach_label(
        self, session: AsyncSession, actor_id: int, task_id: int, label_id: int
    ) -> None:
        """Remove a label from a task.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            task_id: task to update.
            label_id: label to remove.

        Raises:
            TaskNotFound: when the task is missing or the caller is not a
                member of its project.
            AccessDenied: when the caller cannot edit tasks.
            LabelNotFound: when the label is missing or belongs to another
                project.
            ArchivedCollection: when the project is archived.
        """
        task, role = await self._load_task(session, task_id, actor_id)
        resolve_role(role, ProjectRole.MEMBER)
        self._ensure_writable(task)

        label = await self._get_label(session, task.project_id, label_id)
        relation = await self.task_label_crud.get(session, task.id, label.id)
        if relation is None:
            raise AlreadyExists("Label is not attached to the task")

        await self.task_label_crud.detach(session, relation)
        await self.activity.record(
            session,
            ActivityEventType.LABEL_REMOVED,
            actor_id,
            project_id=task.project_id,
            task_id=task.id,
            data={
                "label_id": label.id,
                "label_name": label.name,
                "task_key": task.key,
            },
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

    async def _get_label(
        self, session: AsyncSession, project_id: int, label_id: int
    ) -> Label:
        """Load one label of a project.

        Args:
            session: active database session.
            project_id: project owning the label.
            label_id: label to load.

        Returns:
            Label: the label row.

        Raises:
            LabelNotFound: when the label is missing or belongs to another
                project.
        """
        label = await self.label_crud.get_by_id(session, project_id, label_id)
        if label is None:
            raise LabelNotFound()
        return label

    async def _ensure_unique_name(
        self,
        session: AsyncSession,
        project_id: int,
        name: str,
        skip_id: int | None = None,
    ) -> None:
        """Reject label names already taken in the project.

        Args:
            session: active database session.
            project_id: project to inspect.
            name: requested label name.
            skip_id: id of the label being renamed, if any.

        Raises:
            AlreadyExists: when another label holds the name.
        """
        existing = await self.label_crud.get_by_name(session, project_id, name)
        if existing is not None and existing.id != skip_id:
            raise AlreadyExists("Label name already exists")

    async def _ensure_writable_project(
        self, session: AsyncSession, project_id: int
    ) -> Project:
        """Reject label management on archived projects.

        Args:
            session: active database session.
            project_id: project to check.

        Returns:
            Project: the project row.

        Raises:
            ProjectNotFound: when no project has the given id.
            ArchivedCollection: when the project is archived.
        """
        project = await self.project_crud.get_by_id(session, project_id)
        if project is None:
            raise ProjectNotFound()
        if project.is_archived:
            raise ArchivedCollection()
        return project

    @staticmethod
    def _ensure_writable(task: Task) -> None:
        """Reject label attachments on archived projects.

        Args:
            task: task owning the attachment.

        Raises:
            ArchivedCollection: when the project is archived.
        """
        if task.project.is_archived:
            raise ArchivedCollection()
