from app.enums import ProjectRole
from app.events import ActivityLog
from app.models import User
from app.schemas import MemberAdd, ProjectCreate
from app.services import (
    ActivityService,
    CommentService,
    LabelService,
    ProjectService,
    TaskService,
    TaskStatusService,
    WatcherService,
)

from .activity_crud import FakeActivityCRUD
from .comment_crud import FakeCommentCRUD
from .domain import DomainStore
from .label_crud import FakeLabelCRUD
from .project_crud import FakeProjectCRUD
from .project_member_crud import FakeProjectMemberCRUD
from .task_crud import FakeTaskCRUD
from .task_label_crud import FakeTaskLabelCRUD
from .task_status_crud import FakeTaskStatusCRUD
from .task_watcher_crud import FakeTaskWatcherCRUD
from .user_crud import StaticUserCRUD


def make_user(user_id: int, username: str) -> User:
    """Build a plain active user account.

    Args:
        user_id: id of the account.
        username: unique username.

    Returns:
        User: account with a placeholder password hash.
    """
    return User(
        id=user_id,
        username=username,
        email=f"{username}@example.com",
        password_hash="x",
        is_active=True,
    )


class DomainWorld:
    """In-memory project domain with users, one project and its services."""

    def __init__(self):
        """Assemble fakes and services around one shared store."""
        self.store = DomainStore()
        self.user_crud = StaticUserCRUD(
            [
                make_user(1, "owner"),
                make_user(2, "admin"),
                make_user(3, "member"),
                make_user(4, "outsider"),
            ]
        )
        self.project_crud = FakeProjectCRUD(self.store)
        self.member_crud = FakeProjectMemberCRUD(self.store)
        self.status_crud = FakeTaskStatusCRUD(self.store)
        self.task_crud = FakeTaskCRUD(self.store)
        self.comment_crud = FakeCommentCRUD(self.store)
        self.label_crud = FakeLabelCRUD(self.store)
        self.task_label_crud = FakeTaskLabelCRUD(self.store)
        self.task_watcher_crud = FakeTaskWatcherCRUD(self.store, self.user_crud)
        self.activity_crud = FakeActivityCRUD(self.store)
        self.activity = ActivityLog(self.activity_crud)
        self.project_service = ProjectService(
            self.project_crud,
            self.member_crud,
            self.status_crud,
            self.user_crud,
            self.activity,
        )
        self.status_service = TaskStatusService(
            self.status_crud, self.task_crud, self.project_crud, self.member_crud
        )
        self.task_service = TaskService(
            self.task_crud,
            self.project_crud,
            self.member_crud,
            self.status_crud,
            self.user_crud,
            self.comment_crud,
            self.task_label_crud,
            self.task_watcher_crud,
            self.activity,
        )
        self.comment_service = CommentService(
            self.comment_crud,
            self.task_crud,
            self.member_crud,
            self.user_crud,
            self.activity,
        )
        self.label_service = LabelService(
            self.label_crud,
            self.task_label_crud,
            self.task_crud,
            self.project_crud,
            self.member_crud,
            self.activity,
        )
        self.watcher_service = WatcherService(
            self.task_watcher_crud,
            self.task_crud,
            self.member_crud,
            self.user_crud,
            self.activity,
        )
        self.activity_service = ActivityService(
            self.activity_crud, self.member_crud, self.task_crud
        )

    @property
    def project(self):
        """Return the seeded project.

        Returns:
            Project: project created by build_world.
        """
        return self.store.projects[1]

    @property
    def statuses(self):
        """Return the seeded board columns in board order.

        Returns:
            list[TaskStatus]: default columns of the project.
        """
        return self.store.statuses

    def column(self, key: str):
        """Return one seeded board column by its key.

        Args:
            key: status key, e.g. TODO.

        Returns:
            TaskStatus: the matching column.
        """
        for status in self.store.statuses.values():
            if status.key == key:
                return status
        raise KeyError(key)


async def build_world() -> DomainWorld:
    """Seed a project owned by user 1 with an admin and a member.

    Returns:
        DomainWorld: world with the project, default statuses and memberships.
    """
    world = DomainWorld()
    await world.project_service.create_project(
        None, 1, ProjectCreate(key="NEXA", name="NexaDesk")
    )
    await world.project_service.add_member(
        None, 1, 1, MemberAdd(user_id=2, role=ProjectRole.ADMIN)
    )
    await world.project_service.add_member(
        None, 1, 1, MemberAdd(user_id=3, role=ProjectRole.MEMBER)
    )
    return world
