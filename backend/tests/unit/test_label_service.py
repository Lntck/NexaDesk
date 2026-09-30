import pytest

from app.enums import ActivityEventType, ProjectRole
from app.exceptions import (
    AccessDenied,
    AlreadyExists,
    ArchivedCollection,
    LabelNotFound,
    ProjectNotFound,
    ValidationFailed,
)
from app.schemas import (
    LabelCreate,
    LabelPatch,
    MemberAdd,
    ProjectCreate,
    TaskCreate,
)
from tests.fakes.world import build_world


async def _task(world):
    """Create one task and return its response model.

    Args:
        world: assembled project domain.

    Returns:
        TaskRead: the created task.
    """
    return await world.task_service.create_task(
        None, 3, 1, TaskCreate(title="First card")
    )


async def _label(world, name: str = "backend", color: str = "#0C66E4"):
    """Create one project label.

    Args:
        world: assembled project domain.
        name: label name.
        color: label color.

    Returns:
        LabelRead: the created label.
    """
    return await world.label_service.create_label(
        None, 1, 1, LabelCreate(name=name, color=color)
    )


@pytest.mark.asyncio
async def test_create_label_requires_admin():
    world = await build_world()

    with pytest.raises(AccessDenied):
        await world.label_service.create_label(
            None, 3, 1, LabelCreate(name="member-made", color="#0C66E4")
        )

    created = await _label(world, name="backend")
    assert created.name == "backend"

    listed = await world.label_service.list_labels(None, 3, 1)
    assert [label.name for label in listed] == ["backend"]


@pytest.mark.asyncio
async def test_label_name_unique_case_insensitively():
    world = await build_world()
    await _label(world, name="backend")

    with pytest.raises(AlreadyExists):
        await _label(world, name="Backend")


@pytest.mark.asyncio
async def test_rename_label_to_taken_name():
    world = await build_world()
    first = await _label(world, name="backend")
    await _label(world, name="frontend")

    with pytest.raises(AlreadyExists):
        await world.label_service.update_label(
            None, 1, 1, first.id, LabelPatch(name="Frontend")
        )


@pytest.mark.asyncio
async def test_update_label_rejects_cleared_fields():
    world = await build_world()
    label = await _label(world, name="backend")

    with pytest.raises(ValidationFailed):
        await world.label_service.update_label(
            None, 1, 1, label.id, LabelPatch(name=None)
        )
    with pytest.raises(ValidationFailed):
        await world.label_service.update_label(
            None, 1, 1, label.id, LabelPatch(color=None)
        )


@pytest.mark.asyncio
async def test_update_missing_label():
    world = await build_world()

    with pytest.raises(LabelNotFound):
        await world.label_service.update_label(
            None, 1, 1, 99, LabelPatch(name="Renamed")
        )


@pytest.mark.asyncio
async def test_label_list_hidden_from_non_member():
    world = await build_world()
    await _label(world, name="backend")

    with pytest.raises(ProjectNotFound):
        await world.label_service.list_labels(None, 4, 1)


@pytest.mark.asyncio
async def test_attach_label_to_task():
    world = await build_world()
    task = await _task(world)
    label = await _label(world, name="backend")

    attached = await world.label_service.attach_label(None, 3, task.id, label.id)

    assert attached.name == "backend"
    read = await world.task_service.get_task(None, 3, task.id)
    assert [item.name for item in read.labels] == ["backend"]
    assert [
        event.type
        for event in world.store.events.values()
        if event.type == ActivityEventType.LABEL_ADDED
    ] == [ActivityEventType.LABEL_ADDED]


@pytest.mark.asyncio
async def test_attach_label_is_rejected_when_already_attached():
    world = await build_world()
    task = await _task(world)
    label = await _label(world, name="backend")
    await world.label_service.attach_label(None, 3, task.id, label.id)

    with pytest.raises(AlreadyExists):
        await world.label_service.attach_label(None, 3, task.id, label.id)


@pytest.mark.asyncio
async def test_attach_foreign_label_rejected():
    world = await build_world()
    task = await _task(world)
    created = await world.project_service.create_project(
        None, 2, ProjectCreate(key="SHOP", name="Shop")
    )
    foreign = await world.label_service.create_label(
        None, 2, created.id, LabelCreate(name="backend", color="#0C66E4")
    )

    with pytest.raises(LabelNotFound):
        await world.label_service.attach_label(None, 3, task.id, foreign.id)


@pytest.mark.asyncio
async def test_viewer_cannot_attach_label():
    world = await build_world()
    task = await _task(world)
    label = await _label(world, name="backend")
    await world.project_service.add_member(
        None, 1, 1, MemberAdd(user_id=4, role=ProjectRole.VIEWER)
    )

    with pytest.raises(AccessDenied):
        await world.label_service.attach_label(None, 4, task.id, label.id)


@pytest.mark.asyncio
async def test_detach_label_removes_relation():
    world = await build_world()
    task = await _task(world)
    label = await _label(world, name="backend")
    await world.label_service.attach_label(None, 3, task.id, label.id)

    await world.label_service.detach_label(None, 3, task.id, label.id)

    read = await world.task_service.get_task(None, 3, task.id)
    assert read.labels == []


@pytest.mark.asyncio
async def test_delete_label_detaches_it_from_tasks():
    world = await build_world()
    task = await _task(world)
    label = await _label(world, name="backend")
    await world.label_service.attach_label(None, 3, task.id, label.id)

    await world.label_service.delete_label(None, 2, 1, label.id)

    read = await world.task_service.get_task(None, 3, task.id)
    assert read.labels == []
    with pytest.raises(LabelNotFound):
        await world.label_service.attach_label(None, 3, task.id, label.id)


@pytest.mark.asyncio
async def test_archived_project_rejects_label_changes():
    world = await build_world()
    task = await _task(world)
    label = await _label(world, name="backend")
    await world.project_service.archive_project(None, 1, 1)

    with pytest.raises(ArchivedCollection):
        await world.label_service.create_label(
            None, 1, 1, LabelCreate(name="frontend", color="#0C66E4")
        )
    with pytest.raises(ArchivedCollection):
        await world.label_service.attach_label(None, 3, task.id, label.id)
    with pytest.raises(ArchivedCollection):
        await world.label_service.delete_label(None, 1, 1, label.id)
