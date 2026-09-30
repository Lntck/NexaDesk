from fastapi import APIRouter

from app.api.v1.endpoints import (
    activity_router,
    auth_router,
    comments_router,
    events_router,
    labels_router,
    members_router,
    notifications_router,
    projects_router,
    statuses_router,
    tasks_router,
    users_router,
    watchers_router,
)

router = APIRouter()
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(projects_router)
router.include_router(members_router)
router.include_router(statuses_router)
router.include_router(tasks_router)
router.include_router(activity_router)
router.include_router(events_router)
router.include_router(comments_router)
router.include_router(labels_router)
router.include_router(watchers_router)
router.include_router(notifications_router)
