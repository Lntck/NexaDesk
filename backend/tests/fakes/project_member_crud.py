from app.models import ProjectMember
from app.utils import utcnow

from .domain import DomainStore


class FakeProjectMemberCRUD:
    """In-memory stand-in for ProjectMemberCRUD used in unit tests."""

    def __init__(self, store: DomainStore):
        """Attach the shared in-memory tables.

        Args:
            store: shared domain tables.
        """
        self.store = store

    async def get_project_role(self, session, project_id: int, user_id: int):
        """Return the role of the user in the project.

        Args:
            session: unused session placeholder.
            project_id: project to inspect.
            user_id: user whose role is looked up.

        Returns:
            ProjectRole | None: member role or None.
        """
        member = self.store.members.get((project_id, user_id))
        return member.role if member else None

    async def create_member(self, session, member: ProjectMember) -> ProjectMember:
        """Store a new membership row.

        Args:
            session: unused session placeholder.
            member: membership to store.

        Returns:
            ProjectMember: the stored membership.
        """
        member.joined_at = member.joined_at or utcnow()
        self.store.members[(member.project_id, member.user_id)] = member
        return member

    async def get_member(
        self, session, project_id: int, user_id: int
    ) -> ProjectMember | None:
        """Return one membership row.

        Args:
            session: unused session placeholder.
            project_id: project to inspect.
            user_id: member to look up.

        Returns:
            ProjectMember | None: the membership or None.
        """
        return self.store.members.get((project_id, user_id))

    async def list_members(self, session, project_id: int) -> list[ProjectMember]:
        """Return all memberships of a project ordered by user id.

        Args:
            session: unused session placeholder.
            project_id: project to inspect.

        Returns:
            list[ProjectMember]: stored memberships.
        """
        members = [
            member
            for (member_project_id, _), member in self.store.members.items()
            if member_project_id == project_id
        ]
        members.sort(key=lambda member: member.user_id)
        return members

    async def count_members(self, session, project_id: int) -> int:
        """Count memberships of a project.

        Args:
            session: unused session placeholder.
            project_id: project to inspect.

        Returns:
            int: number of project members.
        """
        return len(await self.list_members(session, project_id))

    async def update_role(self, session, member: ProjectMember, role) -> ProjectMember:
        """Change the role stored in a membership row.

        Args:
            session: unused session placeholder.
            member: membership to update.
            role: new project role.

        Returns:
            ProjectMember: the updated membership.
        """
        member.role = role
        return member

    async def remove_member(self, session, member: ProjectMember) -> None:
        """Delete a membership row.

        Args:
            session: unused session placeholder.
            member: membership to delete.
        """
        self.store.members.pop((member.project_id, member.user_id), None)
