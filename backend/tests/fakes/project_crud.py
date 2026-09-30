from app.models import Project
from app.utils import utcnow

from .domain import DomainStore


class FakeProjectCRUD:
    """In-memory stand-in for ProjectCRUD used in unit tests."""

    def __init__(self, store: DomainStore):
        """Attach the shared in-memory tables.

        Args:
            store: shared domain tables.
        """
        self.store = store

    async def create_project(self, session, project: Project) -> Project:
        """Store a project and assign an id.

        Args:
            session: unused session placeholder.
            project: project to store.

        Returns:
            Project: the stored project with assigned id.
        """
        project.id = self.store.project_seq
        self.store.project_seq += 1
        project.task_counter = project.task_counter or 0
        project.is_archived = bool(project.is_archived)
        project.created_at = project.created_at or utcnow()
        project.updated_at = project.updated_at or utcnow()
        self.store.projects[project.id] = project
        return project

    async def get_by_id(self, session, project_id: int) -> Project | None:
        """Return the project with the given id.

        Args:
            session: unused session placeholder.
            project_id: id of the requested project.

        Returns:
            Project | None: the stored project or None.
        """
        return self.store.projects.get(project_id)

    async def get_by_key(self, session, key: str) -> Project | None:
        """Return the project with the given key.

        Args:
            session: unused session placeholder.
            key: project key to look up.

        Returns:
            Project | None: the stored project or None.
        """
        for project in self.store.projects.values():
            if project.key == key:
                return project
        return None

    async def list_for_user(
        self,
        session,
        user_id: int,
        search,
        archived,
        sort: str,
        limit: int,
        offset: int,
    ) -> list[tuple[Project, object]]:
        """Return one page of projects the user belongs to.

        Args:
            session: unused session placeholder.
            user_id: member whose projects are listed.
            search: optional substring filter on key and name.
            archived: archive filter, None excludes archived projects.
            sort: validated sort key with optional "-" prefix.
            limit: page size.
            offset: rows to skip.

        Returns:
            list[tuple[Project, object]]: project with the caller role.
        """
        rows = self._rows_for_user(user_id, search, archived)
        rows.sort(key=lambda row: row[0].id)
        rows.sort(
            key=lambda row: self._sort_value(row[0], sort), reverse=sort.startswith("-")
        )
        return rows[offset : offset + limit]

    async def count_for_user(self, session, user_id: int, search, archived) -> int:
        """Count projects matching a user project listing filter.

        Args:
            session: unused session placeholder.
            user_id: member whose projects are counted.
            search: optional substring filter on key and name.
            archived: archive filter, None excludes archived projects.

        Returns:
            int: total number of matching projects.
        """
        return len(self._rows_for_user(user_id, search, archived))

    async def count_members(self, session, project_id: int) -> int:
        """Count memberships of a project.

        Args:
            session: unused session placeholder.
            project_id: project to inspect.

        Returns:
            int: number of project members.
        """
        return len(
            [
                member
                for (member_project_id, _), member in self.store.members.items()
                if member_project_id == project_id
            ]
        )

    async def count_tasks(self, session, project_id: int) -> int:
        """Count live tasks of a project.

        Args:
            session: unused session placeholder.
            project_id: project to inspect.

        Returns:
            int: number of live tasks.
        """
        return len(
            [
                task
                for task in self.store.tasks.values()
                if task.project_id == project_id and task.deleted_at is None
            ]
        )

    async def lock_by_id(self, session, project_id: int) -> Project | None:
        """Return the project row, no locking in memory.

        Args:
            session: unused session placeholder.
            project_id: project id to lock.

        Returns:
            Project | None: the stored project or None.
        """
        return self.store.projects.get(project_id)

    async def update(self, session, project: Project) -> Project:
        """Flush pending changes of a project row.

        Args:
            session: unused session placeholder.
            project: project to flush.

        Returns:
            Project: the same project instance.
        """
        return project

    def _rows_for_user(
        self, user_id: int, search, archived
    ) -> list[tuple[Project, object]]:
        """Collect project rows joined with the caller role.

        Args:
            user_id: member whose projects are collected.
            search: optional substring filter on key and name.
            archived: archive filter, None excludes archived projects.

        Returns:
            list[tuple[Project, object]]: project with the caller role.
        """
        rows = []
        for (project_id, member_user_id), member in self.store.members.items():
            if member_user_id != user_id:
                continue
            project = self.store.projects[project_id]
            if project.is_archived != bool(archived):
                continue
            haystack = f"{project.key} {project.name}".lower()
            if search and search.lower() not in haystack:
                continue
            rows.append((project, member.role))
        return rows

    @staticmethod
    def _sort_value(project: Project, sort: str):
        """Return the sortable value of a project row.

        Args:
            project: project to sort.
            sort: sort key with optional "-" prefix.

        Returns:
            object: comparable field value.
        """
        field = sort[1:] if sort.startswith("-") else sort
        return {
            "created_at": project.created_at,
            "name": project.name.lower(),
            "key": project.key.lower(),
        }[field]
