from app.models import (
    ActivityEvent,
    Comment,
    Label,
    Notification,
    Project,
    ProjectMember,
    Task,
    TaskLabel,
    TaskStatus,
    TaskWatcher,
)


class DomainStore:
    """Shared in-memory tables for the project domain fakes."""

    def __init__(self):
        """Create empty tables with id sequences."""
        self.projects: dict[int, Project] = {}
        self.members: dict[tuple[int, int], ProjectMember] = {}
        self.statuses: dict[int, TaskStatus] = {}
        self.tasks: dict[int, Task] = {}
        self.comments: dict[int, Comment] = {}
        self.labels: dict[int, Label] = {}
        self.task_labels: dict[tuple[int, int], TaskLabel] = {}
        self.task_watchers: dict[tuple[int, int], TaskWatcher] = {}
        self.events: dict[str, ActivityEvent] = {}
        self.notifications: dict[int, Notification] = {}
        self.project_seq = 1
        self.status_seq = 1
        self.task_seq = 1
        self.comment_seq = 1
        self.label_seq = 1
        self.notification_seq = 1
