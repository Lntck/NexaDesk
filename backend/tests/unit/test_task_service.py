from datetime import date

import pytest

from app.enums import Priority
from app.exceptions import (
    AccessDenied,
    ArchivedCollection,
    InvalidTransition,
    PayloadError,
    ProjectNotFound,
    StaleVersion,
    TaskNotFound,
    ValidationFailed,
)
from app.schemas import (
    PageParams,
    TaskAssign,
    TaskCreate,
    TaskPatch,
    TaskReorder,
    TaskTransition,
)
from tests.fakes.world import build_world


async def _card(world, title: str, status_id: int = 1, **kwargs):
    """Create one task and return its response model.

    Args:
        world: assembled project domain.
        title: task title.
        status_id: id of the starting column.
        **kwargs: extra TaskCreate fields.

    Returns:
        TaskRead: the created task.
    """
    return await world.task_service.create_task(
        None, 3, 1, TaskCreate(title=title, status_id=status_id, **kwargs)
    )


@pytest.mark.asyncio
async def test_create_task_allocates_number_and_key():
    world = await build_world()

    first = await _card(world, "First card")
    second = await _card(world, "Second card")

    assert first.key == "NEXA-1"
    assert second.key == "NEXA-2"
    assert first.id != second.id
    assert first.status.key == "TODO"
    assert first.version == 1
    assert first.creator.id == 3


@pytest.mark.asyncio
async def test_create_task_foreign_status_rejected():
    world = await build_world()

    with pytest.raises(PayloadError):
        await _card(world, "Bad card", status_id=99)


@pytest.mark.asyncio
async def test_create_task_assignee_must_be_member():
    world = await build_world()

    with pytest.raises(PayloadError):
        await _card(world, "Bad card", assignee_id=4)


@pytest.mark.asyncio
async def test_create_task_forbidden_for_non_member():
    world = await build_world()

    with pytest.raises(ProjectNotFound):
        await world.task_service.create_task(
            None, 4, 1, TaskCreate(title="Foreign card")
        )


@pytest.mark.asyncio
async def test_get_task_hidden_from_non_member():
    world = await build_world()
    created = await _card(world, "First card")

    with pytest.raises(TaskNotFound):
        await world.task_service.get_task(None, 4, created.id)


@pytest.mark.asyncio
async def test_update_task_rejects_stale_version():
    world = await build_world()
    created = await _card(world, "First card")

    with pytest.raises(StaleVersion):
        await world.task_service.update_task(
            None, 3, created.id, TaskPatch(title="Renamed"), version=99
        )


@pytest.mark.asyncio
async def test_update_task_clear_title_rejected():
    world = await build_world()
    created = await _card(world, "First card")

    with pytest.raises(ValidationFailed):
        await world.task_service.update_task(
            None, 3, created.id, TaskPatch(title=None), version=created.version
        )


@pytest.mark.asyncio
async def test_update_task_bumps_version():
    world = await build_world()
    created = await _card(world, "First card")

    updated = await world.task_service.update_task(
        None,
        3,
        created.id,
        TaskPatch(
            title="Renamed", priority=Priority.CRITICAL, due_date=date(2026, 1, 1)
        ),
        version=created.version,
    )

    assert updated.title == "Renamed"
    assert updated.priority == Priority.CRITICAL
    assert updated.version == created.version + 1


@pytest.mark.asyncio
async def test_update_task_parent_cycle_rejected():
    world = await build_world()
    parent = await _card(world, "Parent")
    child = await _card(world, "Child", parent_task_id=parent.id)

    with pytest.raises(PayloadError):
        await world.task_service.update_task(
            None,
            3,
            parent.id,
            TaskPatch(parent_task_id=child.id),
            version=parent.version,
        )


@pytest.mark.asyncio
async def test_update_task_parent_self_rejected():
    world = await build_world()
    created = await _card(world, "First card")

    with pytest.raises(PayloadError):
        await world.task_service.update_task(
            None,
            3,
            created.id,
            TaskPatch(parent_task_id=created.id),
            version=created.version,
        )


@pytest.mark.asyncio
async def test_delete_task_by_creator_and_denied_for_member():
    world = await build_world()
    mine = await _card(world, "My card")
    foreign = await world.task_service.create_task(
        None, 2, 1, TaskCreate(title="Foreign card")
    )

    await world.task_service.delete_task(None, 3, mine.id, mine.version)

    with pytest.raises(AccessDenied):
        await world.task_service.delete_task(
            None, 3, foreign.id, version=foreign.version
        )


@pytest.mark.asyncio
async def test_delete_task_by_admin():
    world = await build_world()
    created = await _card(world, "First card")

    await world.task_service.delete_task(None, 2, created.id, created.version)

    with pytest.raises(TaskNotFound):
        await world.task_service.get_task(None, 3, created.id)


@pytest.mark.asyncio
async def test_delete_task_requires_if_match_version():
    world = await build_world()
    created = await _card(world, "First card")

    with pytest.raises(StaleVersion):
        await world.task_service.delete_task(None, 3, created.id, 0)


@pytest.mark.asyncio
async def test_transition_moves_card_to_adjacent_column():
    world = await build_world()
    created = await _card(world, "First card")

    moved = await world.task_service.transition(
        None, 3, created.id, TaskTransition(status_id=2)
    )

    assert moved.status.key == "IN_PROGRESS"
    updated = await world.task_service.get_task(None, 3, created.id)
    assert updated.version == created.version + 1


@pytest.mark.asyncio
async def test_transition_rejects_distant_column():
    world = await build_world()
    created = await _card(world, "First card")

    with pytest.raises(InvalidTransition):
        await world.task_service.transition(
            None, 3, created.id, TaskTransition(status_id=3)
        )


@pytest.mark.asyncio
async def test_transition_foreign_status_rejected():
    world = await build_world()
    created = await _card(world, "First card")

    with pytest.raises(PayloadError):
        await world.task_service.transition(
            None, 3, created.id, TaskTransition(status_id=99)
        )


@pytest.mark.asyncio
async def test_assign_and_unassign():
    world = await build_world()
    created = await _card(world, "First card")

    assigned = await world.task_service.assign(
        None, 3, created.id, TaskAssign(user_id=2)
    )
    assert assigned.assignee.id == 2

    unassigned = await world.task_service.unassign(None, 3, created.id)
    assert unassigned.assignee is None


@pytest.mark.asyncio
async def test_assign_rejects_non_member():
    world = await build_world()
    created = await _card(world, "First card")

    with pytest.raises(PayloadError):
        await world.task_service.assign(None, 3, created.id, TaskAssign(user_id=4))


@pytest.mark.asyncio
async def test_reorder_without_neighbors_puts_card_on_top():
    world = await build_world()
    await _card(world, "First card")
    second = await _card(world, "Second card")

    moved = await world.task_service.reorder(
        None, 3, second.id, TaskReorder(status_id=1)
    )

    assert moved.rank == 1
    cards = await world.task_crud.list_in_status(None, 1, 1, None)
    assert [card.title for card in cards] == ["Second card", "First card"]


@pytest.mark.asyncio
async def test_reorder_after_neighbor():
    world = await build_world()
    first = await _card(world, "First card")
    await _card(world, "Second card")
    third = await _card(world, "Third card")

    moved = await world.task_service.reorder(
        None, 3, third.id, TaskReorder(status_id=1, after_task_id=first.id)
    )

    assert moved.rank == 2
    cards = await world.task_crud.list_in_status(None, 1, 1, None)
    assert [card.title for card in cards] == ["First card", "Third card", "Second card"]


@pytest.mark.asyncio
async def test_reorder_between_adjacent_neighbors():
    world = await build_world()
    first = await _card(world, "First card")
    second = await _card(world, "Second card")
    third = await _card(world, "Third card")

    moved = await world.task_service.reorder(
        None,
        3,
        third.id,
        TaskReorder(status_id=1, before_task_id=second.id, after_task_id=first.id),
    )

    assert moved.rank == 2
    cards = await world.task_crud.list_in_status(None, 1, 1, None)
    assert [card.title for card in cards] == ["First card", "Third card", "Second card"]


@pytest.mark.asyncio
async def test_reorder_rejects_distant_neighbors():
    world = await build_world()
    first = await _card(world, "First card")
    await _card(world, "Second card")
    third = await _card(world, "Third card")
    fourth = await _card(world, "Fourth card")

    with pytest.raises(PayloadError):
        await world.task_service.reorder(
            None,
            3,
            fourth.id,
            TaskReorder(status_id=1, before_task_id=third.id, after_task_id=first.id),
        )


@pytest.mark.asyncio
async def test_reorder_rejects_foreign_column_neighbor():
    world = await build_world()
    first = await _card(world, "First card")
    other = await _card(world, "Other card", status_id=2)

    with pytest.raises(PayloadError):
        await world.task_service.reorder(
            None, 3, first.id, TaskReorder(status_id=1, before_task_id=other.id)
        )


@pytest.mark.asyncio
async def test_reorder_across_adjacent_columns():
    world = await build_world()
    await _card(world, "First card")
    second = await _card(world, "Second card")

    moved = await world.task_service.reorder(
        None, 3, second.id, TaskReorder(status_id=2)
    )

    assert moved.status.key == "IN_PROGRESS"
    assert moved.rank == 1
    assert [
        card.title for card in await world.task_crud.list_in_status(None, 1, 1, None)
    ] == ["First card"]
    assert await world.task_crud.count_in_status(None, 1, 2) == 1


@pytest.mark.asyncio
async def test_reorder_across_distant_columns_rejected():
    world = await build_world()
    created = await _card(world, "First card")

    with pytest.raises(InvalidTransition):
        await world.task_service.reorder(None, 3, created.id, TaskReorder(status_id=4))


@pytest.mark.asyncio
async def test_list_tasks_filters_and_pagination():
    world = await build_world()
    await _card(world, "Fix login", priority=Priority.HIGH)
    await _card(world, "Write docs", priority=Priority.LOW, status_id=2)

    all_tasks = await world.task_service.list_tasks(
        None, 3, 1, PageParams(), sort="title"
    )
    assert all_tasks.total == 2
    assert [item.title for item in all_tasks.items] == ["Fix login", "Write docs"]

    filtered = await world.task_service.list_tasks(
        None, 3, 1, PageParams(), search="login"
    )
    assert [item.title for item in filtered.items] == ["Fix login"]

    by_status = await world.task_service.list_tasks(
        None, 3, 1, PageParams(), status="IN_PROGRESS"
    )
    assert [item.title for item in by_status.items] == ["Write docs"]

    by_priority = await world.task_service.list_tasks(
        None, 3, 1, PageParams(), priority=Priority.HIGH, sort="priority"
    )
    assert [item.title for item in by_priority.items] == ["Fix login"]


@pytest.mark.asyncio
async def test_get_board_groups_cards_and_flags_overflow():
    world = await build_world()
    await _card(world, "First card")
    await _card(world, "Second card")

    board = await world.task_service.get_board(None, 3, 1, limit_per_column=1)

    assert [column.status.key for column in board.columns] == [
        "TODO",
        "IN_PROGRESS",
        "REVIEW",
        "DONE",
    ]
    assert [len(column.tasks) for column in board.columns] == [1, 0, 0, 0]
    assert [column.has_more for column in board.columns] == [True, False, False, False]
    assert board.columns[0].tasks[0].key == "NEXA-1"


@pytest.mark.asyncio
async def test_archived_project_rejects_task_writes():
    world = await build_world()
    created = await _card(world, "First card")
    await world.project_service.archive_project(None, 1, 1)

    with pytest.raises(ArchivedCollection):
        await world.task_service.update_task(
            None, 3, created.id, TaskPatch(title="Renamed"), version=created.version
        )
