import pytest

from app.enums import ActivityEventType, ProjectRole
from app.events import ActivityLog, drain_events
from app.exceptions import ProjectNotFound, TaskNotFound
from app.schemas import (
    MemberAdd,
    MemberRolePatch,
    PageParams,
    TaskAssign,
    TaskCreate,
    TaskPatch,
    TaskTransition,
)
from tests.fakes.world import build_world


def types(world) -> list[str]:
    """Return recorded event type keys in creation order.

    Args:
        world: domain world with recorded activity.

    Returns:
        list[str]: event type keys in insertion order.
    """
    return [event.type.value for event in world.store.events.values()]


@pytest.mark.asyncio
async def test_project_lifecycle_is_recorded():
    world = await build_world()

    assert types(world)[0] == ActivityEventType.PROJECT_CREATED.value

    await world.project_service.archive_project(None, 1, 1)
    await world.project_service.restore_project(None, 1, 1)

    assert ActivityEventType.PROJECT_ARCHIVED.value in types(world)
    assert ActivityEventType.PROJECT_RESTORED.value in types(world)


@pytest.mark.asyncio
async def test_member_changes_are_recorded():
    world = await build_world()

    await world.project_service.add_member(
        None, 1, 1, MemberAdd(user_id=4, role=ProjectRole.VIEWER)
    )
    await world.project_service.change_member_role(
        None, 1, 1, 4, MemberRolePatch(role=ProjectRole.MEMBER)
    )
    await world.project_service.remove_member(None, 1, 1, 4)

    assert ActivityEventType.MEMBER_ADDED.value in types(world)
    assert ActivityEventType.MEMBER_ROLE_CHANGED.value in types(world)
    assert ActivityEventType.MEMBER_REMOVED.value in types(world)


@pytest.mark.asyncio
async def test_task_lifecycle_is_recorded():
    world = await build_world()

    created = await world.task_service.create_task(
        None, 3, 1, TaskCreate(title="Implement activity log")
    )
    await world.task_service.update_task(
        None,
        3,
        created.id,
        TaskPatch(title="Implement activity log v2"),
        created.version,
    )
    await world.task_service.assign(None, 3, created.id, TaskAssign(user_id=3))
    await world.task_service.unassign(None, 3, created.id)

    event_types = types(world)
    assert ActivityEventType.TASK_CREATED.value in event_types
    assert ActivityEventType.TASK_UPDATED.value in event_types
    assert ActivityEventType.TASK_ASSIGNED.value in event_types
    assert ActivityEventType.TASK_UNASSIGNED.value in event_types


@pytest.mark.asyncio
async def test_status_change_records_from_and_to():
    world = await build_world()

    created = await world.task_service.create_task(
        None, 3, 1, TaskCreate(title="Move me")
    )
    await world.task_service.transition(
        None, 3, created.id, TaskTransition(status_id=world.column("IN_PROGRESS").id)
    )

    status_events = [
        event
        for event in world.store.events.values()
        if event.type == ActivityEventType.TASK_STATUS_CHANGED
    ]
    assert len(status_events) == 1
    assert status_events[0].data["from"] == "TODO"
    assert status_events[0].data["to"] == "IN_PROGRESS"


@pytest.mark.asyncio
async def test_task_deletion_is_recorded():
    world = await build_world()

    created = await world.task_service.create_task(
        None, 3, 1, TaskCreate(title="Delete me")
    )
    await world.task_service.delete_task(None, 3, created.id, created.version)

    assert ActivityEventType.TASK_DELETED.value in types(world)


@pytest.mark.asyncio
async def test_list_project_activity_is_paginated_and_scoped():
    world = await build_world()
    await world.task_service.create_task(None, 3, 1, TaskCreate(title="One"))

    page = await world.activity_service.list_project_activity(
        None, 3, 1, PageParams(page=1, page_size=2)
    )

    assert page.total == 4
    assert len(page.items) == 2
    assert page.items[0].created_at >= page.items[1].created_at


@pytest.mark.asyncio
async def test_list_project_activity_rejects_outsider():
    world = await build_world()

    with pytest.raises(ProjectNotFound):
        await world.activity_service.list_project_activity(
            None, 4, 1, PageParams(page=1, page_size=20)
        )


@pytest.mark.asyncio
async def test_list_task_activity_returns_task_events():
    world = await build_world()
    created = await world.task_service.create_task(
        None, 3, 1, TaskCreate(title="Watched")
    )

    page = await world.activity_service.list_task_activity(
        None, 3, created.id, PageParams(page=1, page_size=20)
    )

    assert page.total == 1
    assert page.items[0].type == ActivityEventType.TASK_CREATED
    assert page.items[0].task_id == created.id


@pytest.mark.asyncio
async def test_list_task_activity_unknown_task():
    world = await build_world()

    with pytest.raises(TaskNotFound):
        await world.activity_service.list_task_activity(
            None, 3, 999, PageParams(page=1, page_size=20)
        )


@pytest.mark.asyncio
async def test_activity_log_queues_domain_event():
    world = await build_world()

    class SessionStub:
        """Minimal session carrying only the event queue."""

        def __init__(self):
            self.info: dict = {}

    session = SessionStub()
    log = ActivityLog(world.activity_crud)
    await log.record(
        session,
        ActivityEventType.TASK_CREATED,
        1,
        project_id=1,
        task_id=7,
        data={"key": "NEXA-7"},
    )

    events = drain_events(session)
    assert len(events) == 1
    assert events[0].type == ActivityEventType.TASK_CREATED.value
    assert events[0].task_id == 7
    assert events[0].id is not None
    assert drain_events(session) == []
