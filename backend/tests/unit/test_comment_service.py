import pytest

from app.enums import ActivityEventType, ProjectRole, Role
from app.exceptions import (
    AccessDenied,
    ArchivedCollection,
    CommentNotFound,
    TaskNotFound,
    ValidationFailed,
)
from app.schemas import (
    CommentCreate,
    CommentPatch,
    MemberAdd,
    PageParams,
    TaskCreate,
)
from tests.fakes.world import build_world, make_user


async def _task(world, title: str = "First card"):
    """Create one task and return its response model.

    Args:
        world: assembled project domain.
        title: task title.

    Returns:
        TaskRead: the created task.
    """
    return await world.task_service.create_task(None, 3, 1, TaskCreate(title=title))


async def _add_member(world, user_id: int, role: ProjectRole) -> None:
    """Grant a project role to one seeded user.

    Args:
        world: assembled project domain.
        user_id: user to grant the role to.
        role: project role to grant.
    """
    await world.project_service.add_member(
        None, 1, 1, MemberAdd(user_id=user_id, role=role)
    )


@pytest.mark.asyncio
async def test_create_comment_shows_author_and_count():
    world = await build_world()
    task = await _task(world)

    created = await world.comment_service.create_comment(
        None, 3, task.id, CommentCreate(body="Ready for review")
    )

    assert created.author.id == 3
    assert created.task_id == task.id
    read = await world.task_service.get_task(None, 3, task.id)
    assert read.comments_count == 1


@pytest.mark.asyncio
async def test_empty_comment_rejected():
    world = await build_world()
    task = await _task(world)

    with pytest.raises(ValidationFailed):
        await world.comment_service.create_comment(
            None, 3, task.id, CommentCreate(body="   ")
        )


@pytest.mark.asyncio
async def test_viewer_cannot_comment():
    world = await build_world()
    task = await _task(world)
    await _add_member(world, 4, ProjectRole.VIEWER)

    with pytest.raises(AccessDenied):
        await world.comment_service.create_comment(
            None, 4, task.id, CommentCreate(body="Hello")
        )


@pytest.mark.asyncio
async def test_non_member_sees_no_task():
    world = await build_world()
    task = await _task(world)

    with pytest.raises(TaskNotFound):
        await world.comment_service.create_comment(
            None, 4, task.id, CommentCreate(body="Hello")
        )
    with pytest.raises(TaskNotFound):
        await world.comment_service.list_comments(None, 4, task.id, PageParams())


@pytest.mark.asyncio
async def test_update_comment_by_author():
    world = await build_world()
    task = await _task(world)
    created = await world.comment_service.create_comment(
        None, 3, task.id, CommentCreate(body="First draft")
    )

    updated = await world.comment_service.update_comment(
        None, 3, created.id, CommentPatch(body="Second draft")
    )

    assert updated.body == "Second draft"
    assert updated.updated_at >= created.created_at


@pytest.mark.asyncio
async def test_update_comment_of_another_member_denied():
    world = await build_world()
    task = await _task(world)
    await _add_member(world, 4, ProjectRole.MEMBER)
    created = await world.comment_service.create_comment(
        None, 3, task.id, CommentCreate(body="First draft")
    )

    with pytest.raises(AccessDenied):
        await world.comment_service.update_comment(
            None, 4, created.id, CommentPatch(body="Hacked")
        )


@pytest.mark.asyncio
async def test_project_admin_and_global_admin_may_edit():
    world = await build_world()
    task = await _task(world)
    created = await world.comment_service.create_comment(
        None, 3, task.id, CommentCreate(body="First draft")
    )

    moderated = await world.comment_service.update_comment(
        None, 2, created.id, CommentPatch(body="Moderated")
    )
    assert moderated.body == "Moderated"

    root = make_user(5, "root")
    root.role = Role.ADMIN
    world.user_crud.users[5] = root
    await _add_member(world, 5, ProjectRole.VIEWER)

    updated = await world.comment_service.update_comment(
        None, 5, created.id, CommentPatch(body="Moderated twice")
    )
    assert updated.body == "Moderated twice"


@pytest.mark.asyncio
async def test_update_comment_clear_body_rejected():
    world = await build_world()
    task = await _task(world)
    created = await world.comment_service.create_comment(
        None, 3, task.id, CommentCreate(body="First draft")
    )

    with pytest.raises(ValidationFailed):
        await world.comment_service.update_comment(
            None, 3, created.id, CommentPatch(body=None)
        )


@pytest.mark.asyncio
async def test_delete_comment_hides_it_from_the_task():
    world = await build_world()
    task = await _task(world)
    created = await world.comment_service.create_comment(
        None, 3, task.id, CommentCreate(body="First draft")
    )

    await world.comment_service.delete_comment(None, 3, created.id)

    page = await world.comment_service.list_comments(None, 3, task.id, PageParams())
    assert page.items == []
    assert page.total == 0
    read = await world.task_service.get_task(None, 3, task.id)
    assert read.comments_count == 0

    with pytest.raises(CommentNotFound):
        await world.comment_service.update_comment(
            None, 3, created.id, CommentPatch(body="Ghost")
        )


@pytest.mark.asyncio
async def test_archived_project_rejects_new_comments():
    world = await build_world()
    task = await _task(world)
    created = await world.comment_service.create_comment(
        None, 3, task.id, CommentCreate(body="Before the archive")
    )
    await world.project_service.archive_project(None, 1, 1)

    with pytest.raises(ArchivedCollection):
        await world.comment_service.create_comment(
            None, 3, task.id, CommentCreate(body="After the archive")
        )
    with pytest.raises(ArchivedCollection):
        await world.comment_service.update_comment(
            None, 3, created.id, CommentPatch(body="Edited after the archive")
        )


@pytest.mark.asyncio
async def test_global_admin_moderates_archived_project():
    world = await build_world()
    task = await _task(world)
    created = await world.comment_service.create_comment(
        None, 3, task.id, CommentCreate(body="Abuse")
    )

    root = make_user(5, "root")
    root.role = Role.ADMIN
    world.user_crud.users[5] = root
    await _add_member(world, 5, ProjectRole.VIEWER)
    await world.project_service.archive_project(None, 1, 1)

    await world.comment_service.delete_comment(None, 5, created.id)

    page = await world.comment_service.list_comments(None, 5, task.id, PageParams())
    assert page.items == []


@pytest.mark.asyncio
async def test_mentions_record_events():
    world = await build_world()
    task = await _task(world)

    await world.comment_service.create_comment(
        None, 3, task.id, CommentCreate(body="cc @owner and @admin, again @owner")
    )

    mentioned = [
        event.data["username"]
        for event in world.store.events.values()
        if event.type == ActivityEventType.COMMENT_MENTIONED
    ]
    assert mentioned == ["owner", "admin"]


@pytest.mark.asyncio
async def test_self_mention_is_skipped():
    world = await build_world()
    task = await _task(world)

    await world.comment_service.create_comment(
        None, 3, task.id, CommentCreate(body="note for @member")
    )

    mentioned = [
        event
        for event in world.store.events.values()
        if event.type == ActivityEventType.COMMENT_MENTIONED
    ]
    assert mentioned == []


@pytest.mark.asyncio
async def test_comment_events_are_recorded():
    world = await build_world()
    task = await _task(world)

    created = await world.comment_service.create_comment(
        None, 3, task.id, CommentCreate(body="First draft")
    )
    await world.comment_service.update_comment(
        None, 3, created.id, CommentPatch(body="Second draft")
    )
    await world.comment_service.delete_comment(None, 3, created.id)

    types = [
        event.type
        for event in world.store.events.values()
        if event.task_id == task.id
        and event.type
        in (
            ActivityEventType.COMMENT_CREATED,
            ActivityEventType.COMMENT_UPDATED,
            ActivityEventType.COMMENT_DELETED,
        )
    ]
    assert types == [
        ActivityEventType.COMMENT_CREATED,
        ActivityEventType.COMMENT_UPDATED,
        ActivityEventType.COMMENT_DELETED,
    ]
