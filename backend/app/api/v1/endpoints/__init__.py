from .activity import router as activity_router
from .auth import router as auth_router
from .comments import router as comments_router
from .labels import router as labels_router
from .members import router as members_router
from .projects import router as projects_router
from .statuses import router as statuses_router
from .tasks import router as tasks_router
from .users import router as users_router
from .watchers import router as watchers_router

__all__ = (
    "activity_router",
    "auth_router",
    "comments_router",
    "labels_router",
    "members_router",
    "projects_router",
    "statuses_router",
    "tasks_router",
    "users_router",
    "watchers_router",
)
