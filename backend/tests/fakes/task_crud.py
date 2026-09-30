from app.enums import Priority
from app.models import Task
from app.utils import utcnow

from .domain import DomainStore

_PRIORITY_ORDER = {
    Priority.LOW: 1,
    Priority.MEDIUM: 2,
    Priority.HIGH: 3,
    Priority.CRITICAL: 4,
}


class FakeTaskCRUD:
    """In-memory stand-in for TaskCRUD used in unit tests."""

    def __init__(self, store: DomainStore):
        """Attach the shared in-memory tables.

        Args:
            store: shared domain tables.
        """
        self.store = store

    async def create_task(self, session, task: Task) -> Task:
        """Store a task and assign an id.

        Args:
            session: unused session placeholder.
            task: task to store.

        Returns:
            Task: the stored task with assigned id.
        """
        task.id = self.store.task_seq
        self.store.task_seq += 1
        task.version = task.version or 1
        task.rank = task.rank or 0
        task.deleted_at = None
        task.created_at = task.created_at or utcnow()
        task.updated_at = task.updated_at or utcnow()
        self.store.tasks[task.id] = task
        return task

    async def get_by_id(self, session, task_id: int) -> Task | None:
        """Return one live task by primary key.

        Args:
            session: unused session placeholder.
            task_id: task id to look up.

        Returns:
            Task | None: the task or None when missing or soft-deleted.
        """
        task = self.store.tasks.get(task_id)
        if task is None or task.deleted_at is not None:
            return None
        return task

    async def list_for_project(
        self,
        session,
        project_id: int,
        filters: dict,
        sort: str,
        limit: int,
        offset: int,
    ) -> list[Task]:
        """Return one page of live project tasks matching the filters.

        Args:
            session: unused session placeholder.
            project_id: owning project.
            filters: request filters, see the protocol for keys.
            sort: validated sort key with optional "-" prefix.
            limit: page size.
            offset: rows to skip.

        Returns:
            list[Task]: matching tasks in sort order.
        """
        tasks = self._filtered(project_id, filters)
        tasks.sort(key=lambda task: task.id)
        tasks.sort(
            key=lambda task: self._sort_value(task, sort), reverse=sort.startswith("-")
        )
        return tasks[offset : offset + limit]

    async def count_for_project(self, session, project_id: int, filters: dict) -> int:
        """Count live project tasks matching the filters.

        Args:
            session: unused session placeholder.
            project_id: owning project.
            filters: request filters, see the protocol for keys.

        Returns:
            int: total number of matching tasks.
        """
        return len(self._filtered(project_id, filters))

    async def list_in_status(
        self, session, project_id: int, status_id: int, limit: int | None
    ) -> list[Task]:
        """Return cards of one board column ordered by rank.

        Args:
            session: unused session placeholder.
            project_id: owning project.
            status_id: board column to read.
            limit: maximum number of cards, None returns the full column.

        Returns:
            list[Task]: cards of the column.
        """
        tasks = [
            task
            for task in self.store.tasks.values()
            if task.project_id == project_id
            and task.status_id == status_id
            and task.deleted_at is None
        ]
        tasks.sort(key=lambda task: (task.rank, task.id))
        return tasks if limit is None else tasks[:limit]

    async def count_in_status(self, session, project_id: int, status_id: int) -> int:
        """Count live tasks in one board column.

        Args:
            session: unused session placeholder.
            project_id: owning project.
            status_id: board column to count.

        Returns:
            int: number of live tasks in the column.
        """
        return len(await self.list_in_status(session, project_id, status_id, None))

    async def next_rank(self, session, project_id: int, status_id: int) -> int:
        """Return the rank following the last card of a board column.

        Args:
            session: unused session placeholder.
            project_id: owning project.
            status_id: board column to inspect.

        Returns:
            int: free rank at the end of the column.
        """
        tasks = await self.list_in_status(session, project_id, status_id, None)
        return (max(task.rank for task in tasks) if tasks else 0) + 1

    async def renumber_column(self, session, project_id: int, status_id: int) -> None:
        """Reassign dense ranks 1..n inside one board column.

        Args:
            session: unused session placeholder.
            project_id: owning project.
            status_id: board column to normalize.
        """
        tasks = await self.list_in_status(session, project_id, status_id, None)
        for position, task in enumerate(tasks, start=1):
            task.rank = position

    async def update(self, session, task: Task) -> Task:
        """Flush pending changes of a task row.

        Args:
            session: unused session placeholder.
            task: task to flush.

        Returns:
            Task: the same task instance.
        """
        return task

    def _filtered(self, project_id: int, filters: dict) -> list[Task]:
        """Collect live project tasks matching the filters.

        Args:
            project_id: owning project.
            filters: request filters, see the protocol for keys.

        Returns:
            list[Task]: matching tasks in id order.
        """
        tasks = [
            task
            for task in self.store.tasks.values()
            if task.project_id == project_id and task.deleted_at is None
        ]

        search = filters.get("search")
        if search:
            pattern = search.lower()
            tasks = [
                task
                for task in tasks
                if pattern in task.title.lower()
                or pattern in (task.description or "").lower()
            ]
        status_key = filters.get("status")
        if status_key:
            tasks = [
                task
                for task in tasks
                if task.status is not None and task.status.key == status_key
            ]
        priority = filters.get("priority")
        if priority:
            tasks = [task for task in tasks if task.priority == priority]
        assignee_id = filters.get("assignee_id")
        if assignee_id is not None:
            tasks = [task for task in tasks if task.assignee_id == assignee_id]
        creator_id = filters.get("creator_id")
        if creator_id is not None:
            tasks = [task for task in tasks if task.creator_id == creator_id]
        due_before = filters.get("due_before")
        if due_before is not None:
            tasks = [
                task
                for task in tasks
                if task.due_date is not None and task.due_date <= due_before
            ]
        due_after = filters.get("due_after")
        if due_after is not None:
            tasks = [
                task
                for task in tasks
                if task.due_date is not None and task.due_date >= due_after
            ]
        return tasks

    @staticmethod
    def _sort_value(task: Task, sort: str):
        """Return the sortable value of a task row.

        Args:
            task: task to sort.
            sort: sort key with optional "-" prefix.

        Returns:
            object: comparable field value.
        """
        field = sort[1:] if sort.startswith("-") else sort
        return {
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "title": task.title.lower(),
            "priority": _PRIORITY_ORDER[task.priority],
            "due_date": task.due_date.isoformat() if task.due_date else "9999-12-31",
            "number": task.number,
            "rank": task.rank,
        }[field]
