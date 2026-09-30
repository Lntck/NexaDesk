from app.models import ActivityEvent, Project, ProjectMember, Task, TaskStatus


class DomainStore:
    """Shared in-memory tables for the project domain fakes."""

    def __init__(self):
        """Create empty tables with id sequences."""
        self.projects: dict[int, Project] = {}
        self.members: dict[tuple[int, int], ProjectMember] = {}
        self.statuses: dict[int, TaskStatus] = {}
        self.tasks: dict[int, Task] = {}
        self.events: dict[str, ActivityEvent] = {}
        self.project_seq = 1
        self.status_seq = 1
        self.task_seq = 1
