import pytest

from app.enums import ActivityEventType, ProjectRole
from app.exceptions import AccessDenied, TaskNotFound
from app.schemas import MemberAdd, TaskCreate
from tests.fakes.world import build_world


async def _task(world, title: str = "First card"):
    """Create one task and return its response model.

    Args:
        world: assembled project domain.
        title: task title.

    Returns:
        TaskRead: the created task.
    """
    return await world.task_service.create_task(None, 3, 1, TaskCreate(title=title))


@pytest.mark.asyncio
async def test_watch_is_idempotent():
    world = await build_world()
    task = await _task(world)

    first = await world.watcher_service.watch(None, 3, task.id)
    second = await world.watcher_service.watch(None, 3, task.id)

    assert first.user.id == 3
    assert second.user.id == 3
    watchers = await world.watcher_service.list_watchers(None, 3, task.id)
    assert [watcher.user.id for watcher in watchers] == [3]
    assert (
        len(
            [
                event
                for event in world.store.events.values()
                if event.type == ActivityEventType.WATCHER_ADDED
            ]
        )
        == 1
    )


@pytest.mark.asyncio
async def test_unwatch_is_idempotent():
    world = await build_world()
    task = await _task(world)

    await world.watcher_service.watch(None, 3, task.id)
    await world.watcher_service.unwatch(None, 3, task.id)
    await world.watcher_service.unwatch(None, 3, task.id)

    assert await world.watcher_service.list_watchers(None, 3, task.id) == []
    assert (
        len(
            [
                event
                for event in world.store.events.values()
                if event.type == ActivityEventType.WATCHER_REMOVED
            ]
        )
        == 1
    )


@pytest.mark.asyncio
async def test_viewer_can_watch():
    world = await build_world()
    task = await _task(world)
    await world.project_service.add_member(
        None, 1, 1, MemberAdd(user_id=4, role=ProjectRole.VIEWER)
    )

    await world.watcher_service.watch(None, 4, task.id)

    watchers = await world.watcher_service.list_watchers(None, 4, task.id)
    assert [watcher.user.id for watcher in watchers] == [4]


@pytest.mark.asyncio
async def test_non_member_cannot_watch():
    world = await build_world()
    task = await _task(world)

    with pytest.raises(TaskNotFound):
        await world.watcher_service.watch(None, 4, task.id)
    with pytest.raises(TaskNotFound):
        await world.watcher_service.list_watchers(None, 4, task.id)


@pytest.mark.asyncio
async def test_admin_can_remove_another_watcher():
    world = await build_world()
    task = await _task(world)
    await world.watcher_service.watch(None, 3, task.id)

    await world.watcher_service.remove_watcher(None, 2, task.id, 3)

    assert await world.watcher_service.list_watchers(None, 3, task.id) == []
    assert [
        event.data["username"]
        for event in world.store.events.values()
        if event.type == ActivityEventType.WATCHER_REMOVED
    ] == ["member"]


@pytest.mark.asyncio
async def test_member_cannot_remove_another_watcher():
    world = await build_world()
    task = await _task(world)
    await world.watcher_service.watch(None, 1, task.id)

    with pytest.raises(AccessDenied):
        await world.watcher_service.remove_watcher(None, 3, task.id, 1)


@pytest.mark.asyncio
async def test_watcher_can_remove_himself():
    world = await build_world()
    task = await _task(world)
    await world.watcher_service.watch(None, 3, task.id)

    await world.watcher_service.remove_watcher(None, 3, task.id, 3)

    assert await world.watcher_service.list_watchers(None, 3, task.id) == []


@pytest.mark.asyncio
async def test_task_read_counts_watchers():
    world = await build_world()
    task = await _task(world)
    await world.watcher_service.watch(None, 1, task.id)
    await world.watcher_service.watch(None, 3, task.id)

    read = await world.task_service.get_task(None, 3, task.id)

    assert read.watchers_count == 2
