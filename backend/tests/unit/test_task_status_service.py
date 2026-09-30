import pytest

from app.exceptions import (
    AccessDenied,
    AlreadyExists,
    ArchivedCollection,
    StatusInUse,
    TaskStatusNotFound,
    ValidationFailed,
)
from app.schemas import (
    ProjectCreate,
    TaskCreate,
    TaskStatusCreate,
    TaskStatusPatch,
)
from tests.fakes.world import build_world


@pytest.mark.asyncio
async def test_create_status_inserts_at_position():
    world = await build_world()

    created = await world.status_service.create_status(
        None,
        1,
        1,
        TaskStatusCreate(name="Blocked", key="BLOCKED", color="#FF0000", position=2),
    )

    assert created.position == 2
    statuses = await world.status_service.list_statuses(None, 3, 1)
    assert [status.position for status in statuses] == [1, 2, 3, 4, 5]
    assert [status.key for status in statuses] == [
        "TODO",
        "BLOCKED",
        "IN_PROGRESS",
        "REVIEW",
        "DONE",
    ]


@pytest.mark.asyncio
async def test_create_status_appends_by_default():
    world = await build_world()

    created = await world.status_service.create_status(
        None, 1, 1, TaskStatusCreate(name="Blocked", key="BLOCKED", color="#FF0000")
    )

    assert created.position == 5


@pytest.mark.asyncio
async def test_create_status_duplicate_key():
    world = await build_world()

    with pytest.raises(AlreadyExists):
        await world.status_service.create_status(
            None, 1, 1, TaskStatusCreate(name="Copy", key="TODO", color="#FF0000")
        )


@pytest.mark.asyncio
async def test_member_cannot_manage_statuses():
    world = await build_world()

    with pytest.raises(AccessDenied):
        await world.status_service.create_status(
            None, 3, 1, TaskStatusCreate(name="Blocked", key="BLOCKED", color="#FF0000")
        )


@pytest.mark.asyncio
async def test_update_status_moves_column():
    world = await build_world()

    updated = await world.status_service.update_status(
        None, 2, 1, 4, TaskStatusPatch(position=2)
    )

    assert updated.position == 2
    statuses = await world.status_service.list_statuses(None, 3, 1)
    assert [status.key for status in statuses] == [
        "TODO",
        "DONE",
        "IN_PROGRESS",
        "REVIEW",
    ]


@pytest.mark.asyncio
async def test_update_status_clear_name_rejected():
    world = await build_world()

    with pytest.raises(ValidationFailed):
        await world.status_service.update_status(
            None, 1, 1, 1, TaskStatusPatch(name=None)
        )


@pytest.mark.asyncio
async def test_update_status_missing_status():
    world = await build_world()

    with pytest.raises(TaskStatusNotFound):
        await world.status_service.update_status(
            None, 1, 1, 99, TaskStatusPatch(name="Renamed")
        )


@pytest.mark.asyncio
async def test_update_status_of_other_project():
    world = await build_world()
    created = await world.project_service.create_project(
        None, 2, ProjectCreate(key="SHOP", name="Shop")
    )

    foreign_id = (await world.status_service.list_statuses(None, 2, created.id))[0].id
    with pytest.raises(TaskStatusNotFound):
        await world.status_service.update_status(
            None, 1, 1, foreign_id, TaskStatusPatch(name="Renamed")
        )


@pytest.mark.asyncio
async def test_delete_status_in_use():
    world = await build_world()
    await world.task_service.create_task(
        None, 3, 1, TaskCreate(title="First card", status_id=1)
    )

    with pytest.raises(StatusInUse):
        await world.status_service.delete_status(None, 1, 1, 1)


@pytest.mark.asyncio
async def test_delete_status_renumbers_board():
    world = await build_world()

    await world.status_service.delete_status(None, 1, 1, 2)

    statuses = await world.status_service.list_statuses(None, 3, 1)
    assert [status.key for status in statuses] == ["TODO", "REVIEW", "DONE"]
    assert [status.position for status in statuses] == [1, 2, 3]


@pytest.mark.asyncio
async def test_delete_status_free_after_task_deletion():
    world = await build_world()
    created = await world.task_service.create_task(
        None, 3, 1, TaskCreate(title="First card", status_id=1)
    )
    await world.task_service.delete_task(None, 3, created.id, created.version)

    await world.status_service.delete_status(None, 1, 1, 1)


@pytest.mark.asyncio
async def test_archived_project_rejects_status_management():
    world = await build_world()
    await world.project_service.archive_project(None, 1, 1)

    with pytest.raises(ArchivedCollection):
        await world.status_service.create_status(
            None, 1, 1, TaskStatusCreate(name="Blocked", key="BLOCKED", color="#FF0000")
        )
