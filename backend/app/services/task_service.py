from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import load_role, resolve_role
from app.enums import ActivityEventType, Priority, ProjectRole
from app.exceptions import (
    AccessDenied,
    ArchivedCollection,
    InvalidTransition,
    PayloadError,
    ProjectNotFound,
    StaleVersion,
    TaskNotFound,
    UserNotFound,
    ValidationFailed,
)
from app.models import Project, Task, TaskStatus, User
from app.protocols import (
    ActivityLogProtocol,
    ProjectCRUDProtocol,
    ProjectMemberCRUDProtocol,
    TaskCRUDProtocol,
    TaskStatusCRUDProtocol,
    UserCRUDProtocol,
)
from app.schemas import (
    BoardCard,
    BoardColumn,
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
    TaskStatusBrief,
    TaskStatusRead,
    TaskTransition,
    TaskTransitionRead,
    UserBrief,
    check_sort,
)
from app.utils import utcnow

TASK_SORT_FIELDS = {
    "created_at",
    "updated_at",
    "title",
    "priority",
    "due_date",
    "number",
    "rank",
}
TASK_SORT_DEFAULT = "-created_at"
BOARD_LIMIT_DEFAULT = 50


class TaskService:
    """Task lifecycle, workflow and board ordering."""

    def __init__(
        self,
        task_crud: TaskCRUDProtocol,
        project_crud: ProjectCRUDProtocol,
        member_crud: ProjectMemberCRUDProtocol,
        status_crud: TaskStatusCRUDProtocol,
        user_crud: UserCRUDProtocol,
        activity: ActivityLogProtocol,
    ):
        """Attach storage implementations.

        Args:
            task_crud: task row storage.
            project_crud: project storage used for number allocation.
            member_crud: membership storage used for permission checks.
            status_crud: board status storage used for workflow validation.
            user_crud: user storage used to resolve actors and assignees.
            activity: activity history recorder.
        """
        self.task_crud = task_crud
        self.project_crud = project_crud
        self.member_crud = member_crud
        self.status_crud = status_crud
        self.user_crud = user_crud
        self.activity = activity

    async def create_task(
        self,
        session: AsyncSession,
        actor_id: int,
        project_id: int,
        data: TaskCreate,
    ) -> TaskRead:
        """Create a task in a project.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            project_id: project to extend.
            data: validated task creation payload.

        Returns:
            TaskRead: the created task.

        Raises:
            ProjectNotFound: when the project is missing or the caller is not
                a member.
            AccessDenied: when the caller cannot create tasks.
            ArchivedCollection: when the project is archived.
            PayloadError: when status, assignee or parent are semantically
                invalid.
            ValidationFailed: when the project has no board columns.
        """
        role = await load_role(self.member_crud, session, project_id, actor_id)
        resolve_role(role, ProjectRole.MEMBER)
        project = await self._get_writable_project(session, project_id)

        status = await self._resolve_status(session, project_id, data.status_id)
        assignee = await self._resolve_assignee(session, project_id, data.assignee_id)
        if data.parent_task_id is not None:
            parent = await self._resolve_parent(
                session, project_id, data.parent_task_id
            )
            parent_id = parent.id
        else:
            parent_id = None

        locked = await self.project_crud.lock_by_id(session, project_id)
        if locked is None:
            raise ProjectNotFound()
        locked.task_counter += 1
        await self.project_crud.update(session, locked)

        rank = await self.task_crud.next_rank(session, project_id, status.id)
        now = utcnow()
        task = Task(
            project_id=project_id,
            number=locked.task_counter,
            title=data.title,
            description=data.description,
            status_id=status.id,
            priority=data.priority,
            creator_id=actor_id,
            assignee_id=data.assignee_id,
            parent_task_id=parent_id,
            due_date=data.due_date,
            estimated_hours=data.estimated_hours,
            rank=rank,
            created_at=now,
            updated_at=now,
        )
        task.project = project
        task.status = status
        task.creator = await self._get_user(session, actor_id)
        task.assignee = assignee
        await self.task_crud.create_task(session, task)
        await self.activity.record(
            session,
            ActivityEventType.TASK_CREATED,
            actor_id,
            project_id=project_id,
            task_id=task.id,
            data={"key": task.key, "title": task.title},
        )
        return TaskRead.model_validate(task)

    async def list_tasks(
        self,
        session: AsyncSession,
        actor_id: int,
        project_id: int,
        page: PageParams,
        search: str | None = None,
        status: str | None = None,
        priority: Priority | None = None,
        assignee_id: int | None = None,
        creator_id: int | None = None,
        due_before: date | None = None,
        due_after: date | None = None,
        sort: str | None = None,
    ) -> Paginated[TaskListItem]:
        """List and filter project tasks.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            project_id: project to inspect.
            page: pagination parameters.
            search: substring filter on title and description.
            status: status key filter.
            priority: priority filter.
            assignee_id: assignee filter.
            creator_id: creator filter.
            due_before: due date upper bound.
            due_after: due date lower bound.
            sort: sort key from the collection whitelist.

        Returns:
            Paginated[TaskListItem]: one page of task cards.

        Raises:
            ProjectNotFound: when the project is missing or the caller is not
                a member.
            ValidationFailed: when sort is outside the collection whitelist.
        """
        await load_role(self.member_crud, session, project_id, actor_id)
        sort_value = check_sort(sort, TASK_SORT_FIELDS, TASK_SORT_DEFAULT)
        filters: dict[str, Any] = {
            "search": search,
            "status": status,
            "priority": priority,
            "assignee_id": assignee_id,
            "creator_id": creator_id,
            "due_before": due_before,
            "due_after": due_after,
        }
        tasks = await self.task_crud.list_for_project(
            session, project_id, filters, sort_value, page.page_size, page.offset
        )
        total = await self.task_crud.count_for_project(session, project_id, filters)
        return Paginated(
            items=[TaskListItem.model_validate(t) for t in tasks],
            page=page.page,
            page_size=page.page_size,
            total=total,
        )

    async def get_task(
        self, session: AsyncSession, actor_id: int, task_id: int
    ) -> TaskRead:
        """Return full task details.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            task_id: task to read.

        Returns:
            TaskRead: the task with its current version.

        Raises:
            TaskNotFound: when the task is missing or the caller is not a
                member of its project.
        """
        task, _ = await self._load_task(session, task_id, actor_id)
        return TaskRead.model_validate(task)

    async def update_task(
        self,
        session: AsyncSession,
        actor_id: int,
        task_id: int,
        data: TaskPatch,
        version: int,
    ) -> TaskRead:
        """Update editable task fields with optimistic concurrency.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            task_id: task to update.
            data: merge patch payload with editable fields.
            version: version sent in the If-Match header.

        Returns:
            TaskRead: the updated task.

        Raises:
            TaskNotFound: when the task is missing or the caller is not a
                member of its project.
            AccessDenied: when the caller cannot edit tasks.
            ArchivedCollection: when the project is archived.
            StaleVersion: when the task changed since the version was read.
            ValidationFailed: when a non-nullable field is cleared.
            PayloadError: when the parent task is semantically invalid.
        """
        task, role = await self._load_task(session, task_id, actor_id)
        resolve_role(role, ProjectRole.MEMBER)
        self._ensure_writable(task)
        self._ensure_version(task, version)

        changes = data.changes()
        if "title" in changes:
            if changes["title"] is None:
                raise ValidationFailed("Task title cannot be cleared")
            task.title = changes["title"]
        if "priority" in changes:
            if changes["priority"] is None:
                raise ValidationFailed("Task priority cannot be cleared")
            task.priority = changes["priority"]
        if "description" in changes:
            task.description = changes["description"]
        if "due_date" in changes:
            task.due_date = changes["due_date"]
        if "estimated_hours" in changes:
            task.estimated_hours = changes["estimated_hours"]
        if "parent_task_id" in changes:
            parent_id = changes["parent_task_id"]
            if parent_id is None:
                task.parent_task_id = None
            else:
                parent = await self._resolve_parent(
                    session, task.project_id, int(parent_id), task.id
                )
                task.parent_task_id = parent.id

        task.version += 1
        task.updated_at = utcnow()
        await self.task_crud.update(session, task)
        await self.activity.record(
            session,
            ActivityEventType.TASK_UPDATED,
            actor_id,
            project_id=task.project_id,
            task_id=task.id,
            data={"key": task.key, "fields": sorted(changes)},
        )
        return TaskRead.model_validate(task)

    async def delete_task(
        self, session: AsyncSession, actor_id: int, task_id: int, version: int
    ) -> None:
        """Soft-delete a task.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            task_id: task to delete.
            version: version sent in the If-Match header.

        Raises:
            TaskNotFound: when the task is missing or the caller is not a
                member of its project.
            AccessDenied: when a member deletes a foreign task.
            ArchivedCollection: when the project is archived.
            StaleVersion: when the task changed since the version was read.
        """
        task, role = await self._load_task(session, task_id, actor_id)
        self._ensure_writable(task)
        self._ensure_version(task, version)

        is_manager = role.level >= ProjectRole.ADMIN.level
        if not is_manager and task.creator_id != actor_id:
            raise AccessDenied()

        task.deleted_at = utcnow()
        task.version += 1
        task.updated_at = utcnow()
        await self.task_crud.update(session, task)
        await self.activity.record(
            session,
            ActivityEventType.TASK_DELETED,
            actor_id,
            project_id=task.project_id,
            task_id=task.id,
            data={"key": task.key},
        )

    async def transition(
        self,
        session: AsyncSession,
        actor_id: int,
        task_id: int,
        data: TaskTransition,
    ) -> TaskTransitionRead:
        """Move a task to an adjacent board column.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            task_id: task to move.
            data: command payload naming the target status.

        Returns:
            TaskTransitionRead: the task with its new status.

        Raises:
            TaskNotFound: when the task is missing or the caller is not a
                member of its project.
            AccessDenied: when the caller cannot change task status.
            ArchivedCollection: when the project is archived.
            PayloadError: when the status belongs to another project.
            InvalidTransition: when the target column is not adjacent.
        """
        task, role = await self._load_task(session, task_id, actor_id)
        resolve_role(role, ProjectRole.MEMBER)
        self._ensure_writable(task)

        target = await self._get_target_status(session, task, data.status_id)
        self._ensure_adjacent(task, target)

        previous_key = task.status.key
        task.status_id = target.id
        task.status = target
        task.rank = await self.task_crud.next_rank(session, task.project_id, target.id)
        task.version += 1
        task.updated_at = utcnow()
        await self.task_crud.update(session, task)
        await self.activity.record(
            session,
            ActivityEventType.TASK_STATUS_CHANGED,
            actor_id,
            project_id=task.project_id,
            task_id=task.id,
            data={"key": task.key, "from": previous_key, "to": target.key},
        )

        return TaskTransitionRead(
            id=task.id,
            key=task.key,
            status=TaskStatusBrief.model_validate(target),
            updated_at=task.updated_at,
        )

    async def assign(
        self,
        session: AsyncSession,
        actor_id: int,
        task_id: int,
        data: TaskAssign,
    ) -> TaskAssignRead:
        """Assign a task to a project member.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            task_id: task to modify.
            data: command payload naming the assignee.

        Returns:
            TaskAssignRead: the task with its new assignee.

        Raises:
            TaskNotFound: when the task is missing or the caller is not a
                member of its project.
            AccessDenied: when the caller cannot assign tasks.
            ArchivedCollection: when the project is archived.
            PayloadError: when the assignee is not a project member.
            UserNotFound: when the assignee account does not exist.
        """
        task, role = await self._load_task(session, task_id, actor_id)
        resolve_role(role, ProjectRole.MEMBER)
        self._ensure_writable(task)

        assignee = await self._resolve_assignee(session, task.project_id, data.user_id)
        await self._get_user(session, data.user_id)

        task.assignee_id = data.user_id
        task.assignee = assignee
        task.version += 1
        task.updated_at = utcnow()
        await self.task_crud.update(session, task)
        await self.activity.record(
            session,
            ActivityEventType.TASK_ASSIGNED,
            actor_id,
            project_id=task.project_id,
            task_id=task.id,
            data={"key": task.key, "user_id": data.user_id},
        )

        return self._assign_read(task)

    async def unassign(
        self, session: AsyncSession, actor_id: int, task_id: int
    ) -> TaskAssignRead:
        """Remove the current assignee of a task.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            task_id: task to modify.

        Returns:
            TaskAssignRead: the task without an assignee.

        Raises:
            TaskNotFound: when the task is missing or the caller is not a
                member of its project.
            AccessDenied: when the caller cannot assign tasks.
            ArchivedCollection: when the project is archived.
        """
        task, role = await self._load_task(session, task_id, actor_id)
        resolve_role(role, ProjectRole.MEMBER)
        self._ensure_writable(task)

        previous_assignee_id = task.assignee_id
        task.assignee_id = None
        task.assignee = None
        task.version += 1
        task.updated_at = utcnow()
        await self.task_crud.update(session, task)
        await self.activity.record(
            session,
            ActivityEventType.TASK_UNASSIGNED,
            actor_id,
            project_id=task.project_id,
            task_id=task.id,
            data={"key": task.key, "user_id": previous_assignee_id},
        )

        return self._assign_read(task)

    async def reorder(
        self,
        session: AsyncSession,
        actor_id: int,
        task_id: int,
        data: TaskReorder,
    ) -> TaskPositionRead:
        """Place a card inside a board column and recalculate ranks.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            task_id: card to move.
            data: command payload with the target column and neighbors.

        Returns:
            TaskPositionRead: the final position of the card.

        Raises:
            TaskNotFound: when the task is missing or the caller is not a
                member of its project.
            AccessDenied: when the caller cannot edit tasks.
            ArchivedCollection: when the project is archived.
            PayloadError: when the status or a neighbor is semantically
                invalid.
            InvalidTransition: when the card also changes columns and the
                target column is not adjacent.
        """
        task, role = await self._load_task(session, task_id, actor_id)
        resolve_role(role, ProjectRole.MEMBER)
        self._ensure_writable(task)

        target = await self._get_target_status(session, task, data.status_id)
        if target.id != task.status_id:
            self._ensure_adjacent(task, target)

        before = await self._resolve_neighbor(
            session, task, target, data.before_task_id
        )
        after = await self._resolve_neighbor(session, task, target, data.after_task_id)

        column = [
            item
            for item in await self.task_crud.list_in_status(
                session, task.project_id, target.id, None
            )
            if item.id != task.id
        ]
        insert_at = self._insert_index(column, before, after)

        previous_status_id = task.status_id
        new_order = column[:insert_at] + [task] + column[insert_at:]
        for position, item in enumerate(new_order, start=1):
            item.rank = position

        task.status_id = target.id
        task.status = target
        task.version += 1
        task.updated_at = utcnow()
        await self.task_crud.update(session, task)
        if previous_status_id != target.id:
            await self.task_crud.renumber_column(
                session, task.project_id, previous_status_id
            )

        await self.activity.record(
            session,
            ActivityEventType.TASK_MOVED,
            actor_id,
            project_id=task.project_id,
            task_id=task.id,
            data={
                "key": task.key,
                "status_id": target.id,
                "rank": task.rank,
                "from_status_id": previous_status_id,
            },
        )

        return TaskPositionRead(
            id=task.id,
            key=task.key,
            status=TaskStatusBrief.model_validate(target),
            rank=task.rank,
            version=task.version,
            updated_at=task.updated_at,
        )

    async def get_board(
        self,
        session: AsyncSession,
        actor_id: int,
        project_id: int,
        limit_per_column: int = BOARD_LIMIT_DEFAULT,
    ) -> BoardRead:
        """Return tasks grouped by board column.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            project_id: project to render.
            limit_per_column: maximum number of cards per column.

        Returns:
            BoardRead: board columns with cards and has_more flags.

        Raises:
            ProjectNotFound: when the project is missing or the caller is not
                a member.
        """
        await load_role(self.member_crud, session, project_id, actor_id)
        statuses = await self.status_crud.list_by_project(session, project_id)

        columns = []
        for status in statuses:
            tasks = await self.task_crud.list_in_status(
                session, project_id, status.id, limit_per_column
            )
            total = await self.task_crud.count_in_status(session, project_id, status.id)
            columns.append(
                BoardColumn(
                    status=TaskStatusRead.model_validate(status),
                    tasks=[BoardCard.model_validate(item) for item in tasks],
                    has_more=total > len(tasks),
                )
            )
        return BoardRead(columns=columns)

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

    def _ensure_writable(self, task: Task) -> None:
        """Reject task mutations on archived projects.

        Args:
            task: task being modified.

        Raises:
            ArchivedCollection: when the project is archived.
        """
        if task.project.is_archived:
            raise ArchivedCollection()

    @staticmethod
    def _ensure_version(task: Task, version: int) -> None:
        """Enforce optimistic concurrency on task mutations.

        Args:
            task: task being modified.
            version: version sent in the If-Match header.

        Raises:
            StaleVersion: when the task changed since the version was read.
        """
        if task.version != version:
            raise StaleVersion()

    @staticmethod
    def _ensure_adjacent(task: Task, target: TaskStatus) -> None:
        """Validate a status change against the transition matrix.

        A task may move exactly one board position left or right.

        Args:
            task: task being moved.
            target: requested status.

        Raises:
            InvalidTransition: when the target column is not adjacent.
        """
        if abs(target.position - task.status.position) != 1:
            raise InvalidTransition()

    async def _get_writable_project(
        self, session: AsyncSession, project_id: int
    ) -> Project:
        """Load a project that accepts task writes.

        Args:
            session: active database session.
            project_id: project to load.

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

    async def _resolve_status(
        self, session: AsyncSession, project_id: int, status_id: int | None
    ) -> TaskStatus:
        """Resolve the status a new task starts in.

        Args:
            session: active database session.
            project_id: project owning the task.
            status_id: requested status id, None takes the first column.

        Returns:
            TaskStatus: the target status.

        Raises:
            PayloadError: when the status belongs to another project.
            ValidationFailed: when the project has no board columns.
        """
        if status_id is not None:
            status = await self.status_crud.get_by_id(session, project_id, status_id)
            if status is None:
                raise PayloadError("Status does not belong to the project")
            return status

        statuses = await self.status_crud.list_by_project(session, project_id)
        if not statuses:
            raise ValidationFailed("Project has no task statuses")
        return statuses[0]

    async def _resolve_assignee(
        self, session: AsyncSession, project_id: int, assignee_id: int | None
    ) -> User | None:
        """Resolve the user assigned to a task.

        Args:
            session: active database session.
            project_id: project owning the task.
            assignee_id: user id to assign, None keeps the task unassigned.

        Returns:
            User | None: the assignee account or None.

        Raises:
            PayloadError: when the user is not a member of the project.
        """
        if assignee_id is None:
            return None
        member = await self.member_crud.get_member(session, project_id, assignee_id)
        if member is None:
            raise PayloadError("Assignee must be a project member")
        return member.user

    async def _resolve_parent(
        self,
        session: AsyncSession,
        project_id: int,
        parent_task_id: int,
        task_id: int | None = None,
    ) -> Task:
        """Resolve a parent task and reject invalid hierarchies.

        Args:
            session: active database session.
            project_id: project owning the task.
            parent_task_id: id of the requested parent.
            task_id: id of the task being modified, None on creation.

        Returns:
            Task: the parent task.

        Raises:
            PayloadError: when the parent is missing, foreign, self or would
                close a cycle.
        """
        parent = await self.task_crud.get_by_id(session, parent_task_id)
        if parent is None or parent.project_id != project_id:
            raise PayloadError("Parent task must belong to the same project")
        if task_id is not None and parent.id == task_id:
            raise PayloadError("Task cannot be its own parent")

        seen = {parent.id}
        current: Task | None = parent
        while current is not None and current.parent_task_id is not None:
            if task_id is not None and current.parent_task_id == task_id:
                raise PayloadError("Task hierarchy cannot contain cycles")
            current = await self.task_crud.get_by_id(session, current.parent_task_id)
            if current is None or current.id in seen:
                raise PayloadError("Task hierarchy cannot contain cycles")
            seen.add(current.id)
        return parent

    async def _get_target_status(
        self, session: AsyncSession, task: Task, status_id: int
    ) -> TaskStatus:
        """Load the status a command wants to move a task to.

        Args:
            session: active database session.
            task: task being moved.
            status_id: requested status id.

        Returns:
            TaskStatus: the target status.

        Raises:
            PayloadError: when the status belongs to another project.
        """
        status = await self.status_crud.get_by_id(session, task.project_id, status_id)
        if status is None:
            raise PayloadError("Status does not belong to the project")
        return status

    async def _resolve_neighbor(
        self,
        session: AsyncSession,
        task: Task,
        target: TaskStatus,
        neighbor_id: int | None,
    ) -> Task | None:
        """Validate a reorder neighbor card.

        Args:
            session: active database session.
            task: card being moved.
            target: target board column.
            neighbor_id: id of the neighbor card, None when absent.

        Returns:
            Task | None: the neighbor card or None.

        Raises:
            PayloadError: when the neighbor is not a live card of the target
                column.
        """
        if neighbor_id is None:
            return None
        if neighbor_id == task.id:
            raise PayloadError("Task cannot be its own reorder neighbor")
        neighbor = await self.task_crud.get_by_id(session, neighbor_id)
        if (
            neighbor is None
            or neighbor.project_id != task.project_id
            or neighbor.status_id != target.id
        ):
            raise PayloadError("Reorder neighbor must live in the target column")
        return neighbor

    @staticmethod
    def _insert_index(
        column: list[Task], before: Task | None, after: Task | None
    ) -> int:
        """Compute the insertion index of a card inside a column.

        Without neighbors the card goes to the top of the column; with both
        neighbors the card goes between them and they must be adjacent.

        Args:
            column: ordered cards of the column without the moving card.
            before: neighbor the card is placed before.
            after: neighbor the card is placed after.

        Returns:
            int: zero-based insertion index.

        Raises:
            PayloadError: when both neighbors are given and are not adjacent.
        """
        if before is not None and after is not None:
            index = column.index(before)
            if index == 0 or column[index - 1] is not after:
                raise PayloadError("Reorder neighbors must be adjacent")
            return index
        if before is not None:
            return column.index(before)
        if after is not None:
            return column.index(after) + 1
        return 0

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
    def _assign_read(task: Task) -> TaskAssignRead:
        """Compose the assignment command response.

        Args:
            task: task after the assignment change.

        Returns:
            TaskAssignRead: response with the current assignee.
        """
        assignee = (
            UserBrief(id=task.assignee.id, username=task.assignee.username)
            if task.assignee is not None
            else None
        )
        return TaskAssignRead(
            id=task.id,
            key=task.key,
            assignee=assignee,
            updated_at=task.updated_at,
        )
