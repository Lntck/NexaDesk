from typing import Any, Sequence

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import Priority
from app.models import Task, TaskStatus

SORT_FIELDS = {
    "created_at",
    "updated_at",
    "title",
    "priority",
    "due_date",
    "number",
    "rank",
}

_PRIORITY_ORDER = case(
    (Task.priority == Priority.LOW, 1),
    (Task.priority == Priority.MEDIUM, 2),
    (Task.priority == Priority.HIGH, 3),
    (Task.priority == Priority.CRITICAL, 4),
    else_=0,
)


class TaskCRUD:
    """Task row data access including board column ordering."""

    async def create_task(self, session: AsyncSession, task: Task) -> Task:
        """Persist a new task.

        Args:
            session: active database session.
            task: task to persist.

        Returns:
            Task: the persisted task.
        """
        session.add(task)
        await session.flush()
        return task

    async def get_by_id(self, session: AsyncSession, task_id: int) -> Task | None:
        """Return one live task by primary key.

        Args:
            session: active database session.
            task_id: task id to look up.

        Returns:
            Task | None: the task or None when missing or soft-deleted.
        """
        stmt = select(Task).where(Task.id == task_id, Task.deleted_at.is_(None))
        result = await session.scalar(stmt)
        return result

    async def list_for_project(
        self,
        session: AsyncSession,
        project_id: int,
        filters: dict[str, Any],
        sort: str,
        limit: int,
        offset: int,
    ) -> Sequence[Task]:
        """Return one page of live project tasks matching the filters.

        Args:
            session: active database session.
            project_id: owning project.
            filters: supported keys: search, status, priority, assignee_id,
                creator_id, due_before, due_after.
            sort: validated sort key with optional "-" prefix.
            limit: page size.
            offset: rows to skip.

        Returns:
            Sequence[Task]: matching tasks in sort order.
        """
        stmt = select(Task).where(
            Task.project_id == project_id, Task.deleted_at.is_(None)
        )
        stmt = self._apply_filters(stmt, filters)
        stmt = stmt.order_by(*self._order_by(sort)).limit(limit).offset(offset)
        return (await session.scalars(stmt)).all()

    async def count_for_project(
        self, session: AsyncSession, project_id: int, filters: dict[str, Any]
    ) -> int:
        """Count live project tasks matching the filters.

        Args:
            session: active database session.
            project_id: owning project.
            filters: same keys as in list_for_project.

        Returns:
            int: total number of matching tasks.
        """
        stmt = (
            select(func.count())
            .select_from(Task)
            .where(Task.project_id == project_id, Task.deleted_at.is_(None))
        )
        stmt = self._apply_filters(stmt, filters)
        return int(await session.scalar(stmt) or 0)

    async def list_in_status(
        self,
        session: AsyncSession,
        project_id: int,
        status_id: int,
        limit: int | None,
    ) -> Sequence[Task]:
        """Return the first cards of one board column ordered by rank.

        Args:
            session: active database session.
            project_id: owning project.
            status_id: board column to read.
            limit: maximum number of cards, None returns the full column.

        Returns:
            Sequence[Task]: cards of the column.
        """
        stmt = (
            select(Task)
            .where(
                Task.project_id == project_id,
                Task.status_id == status_id,
                Task.deleted_at.is_(None),
            )
            .order_by(Task.rank, Task.id)
            .limit(limit)
        )
        return (await session.scalars(stmt)).all()

    async def count_in_status(
        self, session: AsyncSession, project_id: int, status_id: int
    ) -> int:
        """Count live tasks in one board column.

        Args:
            session: active database session.
            project_id: owning project.
            status_id: board column to count.

        Returns:
            int: number of live tasks in the column.
        """
        stmt = (
            select(func.count())
            .select_from(Task)
            .where(
                Task.project_id == project_id,
                Task.status_id == status_id,
                Task.deleted_at.is_(None),
            )
        )
        return int(await session.scalar(stmt) or 0)

    async def next_rank(
        self, session: AsyncSession, project_id: int, status_id: int
    ) -> int:
        """Return the rank following the last card of a board column.

        Args:
            session: active database session.
            project_id: owning project.
            status_id: board column to inspect.

        Returns:
            int: free rank at the end of the column.
        """
        stmt = select(func.coalesce(func.max(Task.rank), 0)).where(
            Task.project_id == project_id,
            Task.status_id == status_id,
            Task.deleted_at.is_(None),
        )
        return int(await session.scalar(stmt) or 0) + 1

    async def renumber_column(
        self, session: AsyncSession, project_id: int, status_id: int
    ) -> None:
        """Reassign dense ranks 1..n inside one board column.

        Args:
            session: active database session.
            project_id: owning project.
            status_id: board column to normalize.
        """
        stmt = (
            select(Task)
            .where(
                Task.project_id == project_id,
                Task.status_id == status_id,
                Task.deleted_at.is_(None),
            )
            .order_by(Task.rank, Task.id)
        )
        tasks = (await session.scalars(stmt)).all()
        for position, task in enumerate(tasks, start=1):
            task.rank = position
        await session.flush()

    async def update(self, session: AsyncSession, task: Task) -> Task:
        """Flush pending changes of a task row.

        Args:
            session: active database session.
            task: task to flush.

        Returns:
            Task: the same task instance.
        """
        await session.flush()
        return task

    @staticmethod
    def _apply_filters(stmt, filters: dict[str, Any]):
        """Restrict a task listing statement by the request filters.

        Args:
            stmt: select statement to filter.
            filters: supported keys: search, status, priority, assignee_id,
                creator_id, due_before, due_after.

        Returns:
            the filtered select statement.
        """
        search = filters.get("search")
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(Task.title.ilike(pattern), Task.description.ilike(pattern))
            )
        status = filters.get("status")
        if status:
            stmt = stmt.where(Task.status.has(TaskStatus.key == status))
        priority = filters.get("priority")
        if priority:
            stmt = stmt.where(Task.priority == priority)
        assignee_id = filters.get("assignee_id")
        if assignee_id is not None:
            stmt = stmt.where(Task.assignee_id == assignee_id)
        creator_id = filters.get("creator_id")
        if creator_id is not None:
            stmt = stmt.where(Task.creator_id == creator_id)
        due_before = filters.get("due_before")
        if due_before is not None:
            stmt = stmt.where(Task.due_date <= due_before)
        due_after = filters.get("due_after")
        if due_after is not None:
            stmt = stmt.where(Task.due_date >= due_after)
        return stmt

    @staticmethod
    def _order_by(sort: str):
        """Build order-by expressions for a validated sort key.

        Args:
            sort: sort key with optional "-" prefix.

        Returns:
            tuple: order-by expressions.
        """
        descending = sort.startswith("-")
        field = sort[1:] if descending else sort
        column = _PRIORITY_ORDER if field == "priority" else getattr(Task, field)
        return (column.desc(), Task.id) if descending else (column.asc(), Task.id)
