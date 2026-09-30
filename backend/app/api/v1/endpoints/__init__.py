from .auth import router as auth_router
from .members import router as members_router
from .projects import router as projects_router
from .statuses import router as statuses_router
from .tasks import router as tasks_router
from .users import router as users_router

__all__ = (
    "auth_router",
    "members_router",
    "projects_router",
    "statuses_router",
    "tasks_router",
    "users_router",
)
