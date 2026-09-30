from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth_router,
    members_router,
    projects_router,
    statuses_router,
    tasks_router,
    users_router,
)

router = APIRouter()
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(projects_router)
router.include_router(members_router)
router.include_router(statuses_router)
router.include_router(tasks_router)
