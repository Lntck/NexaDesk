from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import load_role, resolve_role
from app.enums import ActivityEventType, ProjectRole
from app.exceptions import (
    AccessDenied,
    AlreadyExists,
    ArchivedCollection,
    ProjectNotFound,
    UserNotFound,
    ValidationFailed,
)
from app.models import Project, ProjectMember, TaskStatus
from app.models.task_status import DEFAULT_TASK_STATUSES
from app.protocols import (
    ActivityLogProtocol,
    ProjectCRUDProtocol,
    ProjectMemberCRUDProtocol,
    TaskStatusCRUDProtocol,
    UserCRUDProtocol,
)
from app.schemas import (
    MemberAdd,
    MemberList,
    MemberRead,
    MemberRolePatch,
    OwnershipTransfer,
    PageParams,
    Paginated,
    ProjectCreate,
    ProjectCreated,
    ProjectListItem,
    ProjectPatch,
    ProjectRead,
    check_sort,
)
from app.services.user_service import is_unique_violation
from app.utils import utcnow

PROJECT_SORT_FIELDS = {"created_at", "name", "key"}
PROJECT_SORT_DEFAULT = "created_at"


class ProjectService:
    """Project, membership and ownership management."""

    def __init__(
        self,
        project_crud: ProjectCRUDProtocol,
        member_crud: ProjectMemberCRUDProtocol,
        status_crud: TaskStatusCRUDProtocol,
        user_crud: UserCRUDProtocol,
        activity: ActivityLogProtocol,
    ):
        """Attach storage implementations.

        Args:
            project_crud: project row storage.
            member_crud: membership row storage.
            status_crud: board status storage used for default columns.
            user_crud: user storage used to validate new members.
            activity: activity history recorder.
        """
        self.project_crud = project_crud
        self.member_crud = member_crud
        self.status_crud = status_crud
        self.user_crud = user_crud
        self.activity = activity

    async def create_project(
        self, session: AsyncSession, actor_id: int, data: ProjectCreate
    ) -> ProjectCreated:
        """Create a project with the caller as owner and default statuses.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            data: validated project creation payload.

        Returns:
            ProjectCreated: the created project.

        Raises:
            AlreadyExists: when the project key is taken.
            IntegrityError: on other database integrity failures.
        """
        if await self.project_crud.get_by_key(session, data.key):
            raise AlreadyExists("Project key already exists")

        owner = await self.user_crud.get_by_id(session, actor_id)
        if owner is None:
            raise UserNotFound()

        now = utcnow()
        project = Project(
            key=data.key,
            name=data.name,
            description=data.description,
            owner_id=actor_id,
            task_counter=0,
            is_archived=False,
            created_at=now,
            updated_at=now,
        )
        project.owner = owner
        try:
            await self.project_crud.create_project(session, project)
        except IntegrityError as exc:
            if is_unique_violation(exc):
                raise AlreadyExists("Project key already exists") from exc
            raise

        await self.member_crud.create_member(
            session,
            ProjectMember(
                project_id=project.id, user_id=actor_id, role=ProjectRole.OWNER
            ),
        )
        for name, key, color, position in DEFAULT_TASK_STATUSES:
            await self.status_crud.create_status(
                session,
                TaskStatus(
                    project_id=project.id,
                    name=name,
                    key=key,
                    color=color,
                    position=position,
                ),
            )
        await self.activity.record(
            session,
            ActivityEventType.PROJECT_CREATED,
            actor_id,
            project_id=project.id,
            data={"key": project.key, "name": project.name},
        )
        return ProjectCreated.model_validate(project)

    async def list_projects(
        self,
        session: AsyncSession,
        actor_id: int,
        page: PageParams,
        search: str | None = None,
        archived: bool | None = None,
        sort: str | None = None,
    ) -> Paginated[ProjectListItem]:
        """List projects the caller belongs to.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            page: pagination parameters.
            search: optional substring filter on key and name.
            archived: archive filter, None excludes archived projects.
            sort: sort key from the collection whitelist.

        Returns:
            Paginated[ProjectListItem]: one page of projects with caller roles.

        Raises:
            ValidationFailed: when sort is outside the collection whitelist.
        """
        sort_value = check_sort(sort, PROJECT_SORT_FIELDS, PROJECT_SORT_DEFAULT)
        rows = await self.project_crud.list_for_user(
            session,
            actor_id,
            search,
            archived,
            sort_value,
            page.page_size,
            page.offset,
        )
        total = await self.project_crud.count_for_user(
            session, actor_id, search, archived
        )
        items = [
            ProjectListItem(
                id=project.id,
                key=project.key,
                name=project.name,
                role=role,
                is_archived=project.is_archived,
                created_at=project.created_at,
            )
            for project, role in rows
        ]
        return Paginated(
            items=items, page=page.page, page_size=page.page_size, total=total
        )

    async def get_project(
        self, session: AsyncSession, actor_id: int, project_id: int
    ) -> ProjectRead:
        """Return full project details.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            project_id: project to read.

        Returns:
            ProjectRead: project details with counters.

        Raises:
            ProjectNotFound: when the project is missing or the caller is not
                a member.
        """
        await load_role(self.member_crud, session, project_id, actor_id)
        project = await self._get_project(session, project_id)
        return await self._read(session, project)

    async def update_project(
        self,
        session: AsyncSession,
        actor_id: int,
        project_id: int,
        data: ProjectPatch,
    ) -> ProjectRead:
        """Update project metadata.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            project_id: project to update.
            data: merge patch payload with editable fields.

        Returns:
            ProjectRead: the updated project details.

        Raises:
            ProjectNotFound: when the project is missing or the caller is not
                a member.
            AccessDenied: when the caller cannot edit the project.
            ValidationFailed: when a non-nullable field is cleared.
        """
        resolve_role(
            await load_role(self.member_crud, session, project_id, actor_id),
            ProjectRole.ADMIN,
        )
        project = await self._get_project(session, project_id)

        changes = data.changes()
        if "name" in changes:
            if changes["name"] is None:
                raise ValidationFailed("Project name cannot be cleared")
            project.name = changes["name"]
        if "description" in changes:
            project.description = changes["description"]

        if changes:
            await self.activity.record(
                session,
                ActivityEventType.PROJECT_UPDATED,
                actor_id,
                project_id=project.id,
                data={"fields": sorted(changes)},
            )

        project.updated_at = utcnow()
        await self.project_crud.update(session, project)
        return await self._read(session, project)

    async def archive_project(
        self, session: AsyncSession, actor_id: int, project_id: int
    ) -> ProjectRead:
        """Archive a project, freezing all domain writes.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            project_id: project to archive.

        Returns:
            ProjectRead: the archived project details.

        Raises:
            ProjectNotFound: when the project is missing or the caller is not
                a member.
            AccessDenied: when the caller cannot archive the project.
        """
        resolve_role(
            await load_role(self.member_crud, session, project_id, actor_id),
            ProjectRole.ADMIN,
        )
        project = await self._get_project(session, project_id)
        if not project.is_archived:
            project.is_archived = True
            project.updated_at = utcnow()
            await self.project_crud.update(session, project)
            await self.activity.record(
                session,
                ActivityEventType.PROJECT_ARCHIVED,
                actor_id,
                project_id=project.id,
            )
        return await self._read(session, project)

    async def restore_project(
        self, session: AsyncSession, actor_id: int, project_id: int
    ) -> ProjectRead:
        """Restore an archived project.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            project_id: project to restore.

        Returns:
            ProjectRead: the restored project details.

        Raises:
            ProjectNotFound: when the project is missing or the caller is not
                a member.
            AccessDenied: when the caller cannot restore the project.
        """
        resolve_role(
            await load_role(self.member_crud, session, project_id, actor_id),
            ProjectRole.ADMIN,
        )
        project = await self._get_project(session, project_id)
        if project.is_archived:
            project.is_archived = False
            project.updated_at = utcnow()
            await self.project_crud.update(session, project)
            await self.activity.record(
                session,
                ActivityEventType.PROJECT_RESTORED,
                actor_id,
                project_id=project.id,
            )
        return await self._read(session, project)

    async def transfer_ownership(
        self,
        session: AsyncSession,
        actor_id: int,
        project_id: int,
        data: OwnershipTransfer,
    ) -> ProjectRead:
        """Transfer project ownership to another member.

        Both membership rows change in one transaction so a project never has
        two owners.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            project_id: project whose ownership is transferred.
            data: command payload naming the new owner.

        Returns:
            ProjectRead: the project details with the new owner.

        Raises:
            ProjectNotFound: when the project is missing or the caller is not
                a member.
            AccessDenied: when the caller is not the current owner.
            UserNotFound: when the target user is not a project member.
            AlreadyExists: when the target user already owns the project.
        """
        role = await load_role(self.member_crud, session, project_id, actor_id)
        resolve_role(role, ProjectRole.OWNER)
        project = await self._get_project(session, project_id)

        if data.user_id == project.owner_id:
            raise AlreadyExists("Target user is already the project owner")

        target = await self.member_crud.get_member(session, project_id, data.user_id)
        if target is None:
            raise UserNotFound("User is not a project member")

        previous = await self.member_crud.get_member(session, project_id, actor_id)
        previous_target_role = target.role
        if previous is not None:
            await self.member_crud.update_role(session, previous, ProjectRole.ADMIN)
        await self.member_crud.update_role(session, target, ProjectRole.OWNER)

        project.owner_id = data.user_id
        project.owner = target.user
        project.updated_at = utcnow()
        await self.project_crud.update(session, project)
        await self.activity.record(
            session,
            ActivityEventType.MEMBER_ROLE_CHANGED,
            actor_id,
            project_id=project.id,
            data={"user_id": actor_id, "from": "owner", "to": "admin"},
        )
        await self.activity.record(
            session,
            ActivityEventType.MEMBER_ROLE_CHANGED,
            actor_id,
            project_id=project.id,
            data={
                "user_id": data.user_id,
                "from": previous_target_role.value,
                "to": "owner",
            },
        )
        return await self._read(session, project)

    async def list_members(
        self, session: AsyncSession, actor_id: int, project_id: int
    ) -> MemberList:
        """List all project members with their roles.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            project_id: project to inspect.

        Returns:
            MemberList: membership rows ordered by user id.

        Raises:
            ProjectNotFound: when the project is missing or the caller is not
                a member.
        """
        await load_role(self.member_crud, session, project_id, actor_id)
        members = await self.member_crud.list_members(session, project_id)
        return MemberList(items=[MemberRead.model_validate(m) for m in members])

    async def add_member(
        self, session: AsyncSession, actor_id: int, project_id: int, data: MemberAdd
    ) -> MemberRead:
        """Add an existing user to a project.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            project_id: project to extend.
            data: command payload with the user and his role.

        Returns:
            MemberRead: the created membership.

        Raises:
            ProjectNotFound: when the project is missing or the caller is not
                a member.
            AccessDenied: when the caller cannot manage members.
            ArchivedCollection: when the project is archived.
            UserNotFound: when the user does not exist.
            AlreadyExists: when the user is already a member.
        """
        resolve_role(
            await load_role(self.member_crud, session, project_id, actor_id),
            ProjectRole.ADMIN,
        )
        await self._ensure_writable(session, project_id)

        user = await self.user_crud.get_by_id(session, data.user_id)
        if user is None:
            raise UserNotFound()
        if await self.member_crud.get_member(session, project_id, data.user_id):
            raise AlreadyExists("User is already a project member")

        member = await self.member_crud.create_member(
            session,
            ProjectMember(
                project_id=project_id,
                user_id=data.user_id,
                role=data.role,
                joined_at=utcnow(),
            ),
        )
        member.user = user
        await self.activity.record(
            session,
            ActivityEventType.MEMBER_ADDED,
            actor_id,
            project_id=project_id,
            data={"user_id": data.user_id, "role": data.role.value},
        )
        return MemberRead.model_validate(member)

    async def change_member_role(
        self,
        session: AsyncSession,
        actor_id: int,
        project_id: int,
        user_id: int,
        data: MemberRolePatch,
    ) -> MemberRead:
        """Change the project role of a member.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            project_id: project to manage.
            user_id: member whose role changes.
            data: command payload with the new role.

        Returns:
            MemberRead: the updated membership.

        Raises:
            ProjectNotFound: when the project is missing or the caller is not
                a member.
            AccessDenied: when the caller cannot manage the target member.
            ArchivedCollection: when the project is archived.
            UserNotFound: when the user is not a project member.
        """
        caller_role = await load_role(self.member_crud, session, project_id, actor_id)
        resolve_role(caller_role, ProjectRole.ADMIN)
        await self._ensure_writable(session, project_id)

        member = await self._get_member(session, project_id, user_id)
        self._ensure_manageable(caller_role, actor_id, member)

        previous_role = member.role
        await self.member_crud.update_role(session, member, data.role)
        await self.activity.record(
            session,
            ActivityEventType.MEMBER_ROLE_CHANGED,
            actor_id,
            project_id=project_id,
            data={
                "user_id": user_id,
                "from": previous_role.value,
                "to": data.role.value,
            },
        )
        return MemberRead.model_validate(member)

    async def remove_member(
        self, session: AsyncSession, actor_id: int, project_id: int, user_id: int
    ) -> None:
        """Remove a project member.

        Args:
            session: active database session.
            actor_id: id of the authenticated user.
            project_id: project to manage.
            user_id: member to remove.

        Raises:
            ProjectNotFound: when the project is missing or the caller is not
                a member.
            AccessDenied: when the caller cannot remove the target member.
            ArchivedCollection: when the project is archived.
            UserNotFound: when the user is not a project member.
        """
        caller_role = await load_role(self.member_crud, session, project_id, actor_id)
        resolve_role(caller_role, ProjectRole.ADMIN)
        await self._ensure_writable(session, project_id)

        member = await self._get_member(session, project_id, user_id)
        self._ensure_manageable(caller_role, actor_id, member)

        await self.member_crud.remove_member(session, member)
        await self.activity.record(
            session,
            ActivityEventType.MEMBER_REMOVED,
            actor_id,
            project_id=project_id,
            data={"user_id": user_id, "role": member.role.value},
        )

    async def _get_project(self, session: AsyncSession, project_id: int) -> Project:
        """Load a project row.

        Args:
            session: active database session.
            project_id: project to load.

        Returns:
            Project: the project row with the owner loaded.

        Raises:
            ProjectNotFound: when no project has the given id.
        """
        project = await self.project_crud.get_by_id(session, project_id)
        if project is None:
            raise ProjectNotFound()
        return project

    async def _read(self, session: AsyncSession, project: Project) -> ProjectRead:
        """Compose the project details response with live counters.

        Args:
            session: active database session.
            project: project to render.

        Returns:
            ProjectRead: project details with counters.
        """
        members_count = await self.project_crud.count_members(session, project.id)
        tasks_count = await self.project_crud.count_tasks(session, project.id)
        return ProjectRead.from_project(project, members_count, tasks_count)

    async def _ensure_writable(self, session: AsyncSession, project_id: int) -> None:
        """Reject member management on archived projects.

        Args:
            session: active database session.
            project_id: project to check.

        Raises:
            ArchivedCollection: when the project is archived.
        """
        project = await self._get_project(session, project_id)
        if project.is_archived:
            raise ArchivedCollection()

    async def _get_member(
        self, session: AsyncSession, project_id: int, user_id: int
    ) -> ProjectMember:
        """Load one membership row.

        Args:
            session: active database session.
            project_id: project to inspect.
            user_id: member to load.

        Returns:
            ProjectMember: the membership row.

        Raises:
            UserNotFound: when the user is not a member of the project.
        """
        member = await self.member_crud.get_member(session, project_id, user_id)
        if member is None:
            raise UserNotFound("User is not a project member")
        return member

    @staticmethod
    def _ensure_manageable(
        caller_role: ProjectRole, caller_id: int, member: ProjectMember
    ) -> None:
        """Check that the caller may modify the given membership.

        The owner role moves only through ownership transfer and admins can
        manage members and viewers only.

        Args:
            caller_role: project role of the caller.
            caller_id: id of the caller.
            member: membership being modified.

        Raises:
            AccessDenied: when the membership is out of the caller reach.
        """
        if member.role == ProjectRole.OWNER:
            raise AccessDenied(
                "Project owner is managed only through ownership transfer"
            )
        if (
            caller_role == ProjectRole.ADMIN
            and member.role == ProjectRole.ADMIN
            and member.user_id != caller_id
        ):
            raise AccessDenied("Only the owner can modify another admin")
