import pytest

from app.enums import ActivityEventType, NotificationType, ProjectRole
from app.exceptions import NotificationNotFound
from app.models import ActivityEvent
from app.schemas import (
    CommentCreate,
    CommentPatch,
    MemberAdd,
    PageParams,
    TaskAssign,
    TaskCreate,
    TaskPatch,
    TaskTransition,
)
from app.utils import utcnow
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


async def _notifications(world, user_id: int, notification_type=None):
    """Return the notifications of one user, optionally filtered by type.

    Args:
        world: assembled project domain.
        user_id: recipient to inspect.
        notification_type: notification type to filter by.

    Returns:
        list[NotificationRead]: matching notifications, newest first.
    """
    page = await world.notification_service.list_notifications(
        None, user_id, PageParams()
    )
    if notification_type is None:
        return page.items
    return [item for item in page.items if item.type == notification_type]


@pytest.mark.asyncio
async def test_assignment_notifies_only_assignee():
    world = await build_world()
    task = await _task(world)

    await world.task_service.assign(None, 3, task.id, TaskAssign(user_id=2))

    items = await _notifications(world, 2, NotificationType.TASK_ASSIGNED)
    assert len(items) == 1
    notice = items[0]
    assert notice.task.key == "NEXA-1"
    assert notice.task.title == "First card"
    assert notice.project.key == "NEXA"
    assert notice.actor.id == 3
    assert notice.is_read is False
    assert notice.data["task_key"] == "NEXA-1"
    assert await _notifications(world, 3, NotificationType.TASK_ASSIGNED) == []


@pytest.mark.asyncio
async def test_self_assignment_is_silent():
    world = await build_world()
    task = await _task(world)

    await world.task_service.assign(None, 3, task.id, TaskAssign(user_id=3))

    assert await _notifications(world, 3, NotificationType.TASK_ASSIGNED) == []


@pytest.mark.asyncio
async def test_status_change_notifies_watchers():
    world = await build_world()
    task = await _task(world)
    await world.watcher_service.watch(None, 2, task.id)

    await world.task_service.transition(
        None, 3, task.id, TaskTransition(status_id=world.column("IN_PROGRESS").id)
    )

    items = await _notifications(world, 2, NotificationType.TASK_STATUS_CHANGED)
    assert len(items) == 1
    assert items[0].data["from"] == "TODO"
    assert items[0].data["to"] == "IN_PROGRESS"
    assert await _notifications(world, 3, NotificationType.TASK_STATUS_CHANGED) == []


@pytest.mark.asyncio
async def test_task_update_notifies_watchers():
    world = await build_world()
    task = await _task(world)
    await world.watcher_service.watch(None, 2, task.id)

    await world.task_service.update_task(
        None, 3, task.id, TaskPatch(title="Renamed"), version=1
    )

    items = await _notifications(world, 2, NotificationType.TASK_UPDATED)
    assert len(items) == 1
    assert items[0].data["fields"] == ["title"]
    assert items[0].task.title == "Renamed"


@pytest.mark.asyncio
async def test_comment_splits_watchers_and_mentions():
    world = await build_world()
    task = await _task(world)
    await world.watcher_service.watch(None, 2, task.id)

    comment = await world.comment_service.create_comment(
        None, 1, task.id, CommentCreate(body="cc @admin @outsider")
    )

    # a mentioned watcher gets the mention notice, not the comment notice
    mentioned = await _notifications(world, 2, NotificationType.COMMENT_MENTIONED)
    assert len(mentioned) == 1
    assert mentioned[0].data["comment_id"] == comment.id
    assert mentioned[0].task.key == "NEXA-1"
    assert await _notifications(world, 2, NotificationType.COMMENT_CREATED) == []
    # a user outside the project is never notified
    assert await _notifications(world, 4, NotificationType.COMMENT_MENTIONED) == []

    # watchers not mentioned in the comment get the comment notice
    await world.comment_service.create_comment(
        None, 1, task.id, CommentCreate(body="plain note")
    )
    created = await _notifications(world, 2, NotificationType.COMMENT_CREATED)
    assert len(created) == 1
    assert created[0].task.key == "NEXA-1"


@pytest.mark.asyncio
async def test_remention_on_edit_notifies_once():
    world = await build_world()
    task = await _task(world)
    comment = await world.comment_service.create_comment(
        None, 1, task.id, CommentCreate(body="hi @admin")
    )

    await world.comment_service.update_comment(
        None, 1, comment.id, CommentPatch(body="hi again @admin")
    )

    items = await _notifications(world, 2, NotificationType.COMMENT_MENTIONED)
    assert len(items) == 1


@pytest.mark.asyncio
async def test_member_added_notifies_new_member():
    world = await build_world()

    await world.project_service.add_member(
        None, 1, 1, MemberAdd(user_id=4, role=ProjectRole.MEMBER)
    )

    items = await _notifications(world, 4, NotificationType.MEMBER_ADDED)
    assert len(items) == 1
    assert items[0].project.key == "NEXA"
    assert items[0].actor.id == 1
    assert items[0].data["role"] == ProjectRole.MEMBER.value


@pytest.mark.asyncio
async def test_events_without_rules_do_not_notify():
    world = await build_world()
    task = await _task(world)

    await world.watcher_service.watch(None, 2, task.id)

    # task.created and watcher.added have no notification rules
    items = await _notifications(world, 2)
    assert [item.type for item in items] == [NotificationType.MEMBER_ADDED]


@pytest.mark.asyncio
async def test_deliveries_are_addressed_to_one_recipient():
    world = await build_world()
    task = await _task(world)
    event = ActivityEvent(
        id="0199c0d0e0f04a00000000000000000a",
        type=ActivityEventType.TASK_ASSIGNED,
        project_id=1,
        task_id=task.id,
        actor_id=3,
        data={"key": "NEXA-1", "user_id": 2},
        created_at=utcnow(),
    )

    deliveries = await world.notification_service.react(None, event)

    assert len(deliveries) == 1
    assert deliveries[0].user_id == 2
    assert deliveries[0].payload["type"] == "task.assigned"
    assert deliveries[0].payload["is_read"] is False
    assert deliveries[0].payload["task"]["key"] == "NEXA-1"


@pytest.mark.asyncio
async def test_mark_read_flow_is_idempotent():
    world = await build_world()
    task = await _task(world)
    await world.task_service.assign(None, 3, task.id, TaskAssign(user_id=2))

    unread = await world.notification_service.list_notifications(
        None, 2, PageParams(), read=False
    )
    notice = [
        item for item in unread.items if item.type == NotificationType.TASK_ASSIGNED
    ][0]

    marked = await world.notification_service.mark_read(None, 2, notice.id)
    assert marked.is_read is True

    again = await world.notification_service.mark_read(None, 2, notice.id)
    assert again.is_read is True
    assert again.id == marked.id

    still_unread = await world.notification_service.list_notifications(
        None, 2, PageParams(), read=False
    )
    assert notice.id not in [item.id for item in still_unread.items]
    read_page = await world.notification_service.list_notifications(
        None, 2, PageParams(), read=True
    )
    assert [item.id for item in read_page.items] == [notice.id]


@pytest.mark.asyncio
async def test_foreign_notification_is_not_found():
    world = await build_world()
    task = await _task(world)
    await world.task_service.assign(None, 3, task.id, TaskAssign(user_id=2))
    notice = (await _notifications(world, 2, NotificationType.TASK_ASSIGNED))[0]

    with pytest.raises(NotificationNotFound):
        await world.notification_service.mark_read(None, 3, notice.id)


@pytest.mark.asyncio
async def test_mark_all_read_counts_updates():
    world = await build_world()
    task = await _task(world)
    await world.task_service.assign(None, 3, task.id, TaskAssign(user_id=2))

    updated = await world.notification_service.mark_all_read(None, 2)

    assert updated == 2
    all_page = await world.notification_service.list_notifications(
        None, 2, PageParams()
    )
    assert all_page.total == 2
    assert all(item.is_read for item in all_page.items)
    assert (
        await world.notification_service.list_notifications(
            None, 2, PageParams(), read=False
        )
    ).total == 0


@pytest.mark.asyncio
async def test_notification_list_is_paginated_newest_first():
    world = await build_world()
    task = await _task(world)
    await world.task_service.assign(None, 3, task.id, TaskAssign(user_id=2))

    first = await world.notification_service.list_notifications(
        None, 2, PageParams(page=1, page_size=1)
    )
    second = await world.notification_service.list_notifications(
        None, 2, PageParams(page=2, page_size=1)
    )

    assert first.total == second.total == 2
    assert first.items[0].id != second.items[0].id
    assert first.items[0].type == NotificationType.TASK_ASSIGNED
    assert second.items[0].type == NotificationType.MEMBER_ADDED
