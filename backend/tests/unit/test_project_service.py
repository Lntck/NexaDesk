import pytest

from app.enums import ProjectRole
from app.exceptions import (
    AccessDenied,
    AlreadyExists,
    ArchivedCollection,
    ProjectNotFound,
    UserNotFound,
    ValidationFailed,
)
from app.schemas import (
    MemberAdd,
    MemberRolePatch,
    OwnershipTransfer,
    PageParams,
    ProjectCreate,
    ProjectPatch,
)
from tests.fakes.world import build_world


@pytest.mark.asyncio
async def test_create_project_seeds_owner_and_default_statuses():
    world = await build_world()

    created = await world.project_service.create_project(
        None, 4, ProjectCreate(key="SHOP", name="Shop")
    )

    assert created.key == "SHOP"
    assert created.owner_id == 4
    statuses = await world.status_service.list_statuses(None, 4, created.id)
    assert [status.key for status in statuses] == [
        "TODO",
        "IN_PROGRESS",
        "REVIEW",
        "DONE",
    ]
    role = await world.member_crud.get_project_role(None, created.id, 4)
    assert role == ProjectRole.OWNER


@pytest.mark.asyncio
async def test_create_project_duplicate_key():
    world = await build_world()

    with pytest.raises(AlreadyExists):
        await world.project_service.create_project(
            None, 2, ProjectCreate(key="NEXA", name="Duplicate")
        )


@pytest.mark.asyncio
async def test_list_projects_search_and_archive_filter():
    world = await build_world()
    await world.project_service.create_project(
        None, 1, ProjectCreate(key="SHOP", name="Shop")
    )
    await world.project_service.archive_project(None, 1, 1)

    default = await world.project_service.list_projects(None, 1, PageParams())
    assert [item.key for item in default.items] == ["SHOP"]

    search = await world.project_service.list_projects(
        None, 1, PageParams(), search="shop"
    )
    assert [item.key for item in search.items] == ["SHOP"]

    hidden = await world.project_service.list_projects(
        None, 1, PageParams(), search="nexa"
    )
    assert hidden.items == []

    archived = await world.project_service.list_projects(
        None, 1, PageParams(), archived=True
    )
    assert [item.key for item in archived.items] == ["NEXA"]


@pytest.mark.asyncio
async def test_list_projects_sorted_by_name_desc():
    world = await build_world()
    await world.project_service.create_project(
        None, 1, ProjectCreate(key="AAA", name="Alpha")
    )

    listing = await world.project_service.list_projects(
        None, 1, PageParams(), sort="-name"
    )
    assert [item.name for item in listing.items] == ["NexaDesk", "Alpha"]


@pytest.mark.asyncio
async def test_get_project_non_member_sees_404():
    world = await build_world()

    with pytest.raises(ProjectNotFound):
        await world.project_service.get_project(None, 4, 1)


@pytest.mark.asyncio
async def test_update_project_member_denied():
    world = await build_world()

    with pytest.raises(AccessDenied):
        await world.project_service.update_project(
            None, 3, 1, ProjectPatch(name="Renamed")
        )


@pytest.mark.asyncio
async def test_update_project_clear_name_rejected():
    world = await build_world()

    with pytest.raises(ValidationFailed):
        await world.project_service.update_project(None, 1, 1, ProjectPatch(name=None))


@pytest.mark.asyncio
async def test_update_project_by_admin():
    world = await build_world()

    updated = await world.project_service.update_project(
        None, 2, 1, ProjectPatch(name="Renamed", description="new")
    )

    assert updated.name == "Renamed"
    assert updated.description == "new"
    assert updated.members_count == 3
    assert updated.tasks_count == 0
    assert updated.owner.id == 1


@pytest.mark.asyncio
async def test_add_member_and_manage_roles():
    world = await build_world()

    member = await world.project_service.add_member(
        None, 2, 1, MemberAdd(user_id=4, role=ProjectRole.VIEWER)
    )
    assert member.user.id == 4
    assert member.role == ProjectRole.VIEWER

    with pytest.raises(AlreadyExists):
        await world.project_service.add_member(
            None, 2, 1, MemberAdd(user_id=4, role=ProjectRole.MEMBER)
        )

    with pytest.raises(UserNotFound):
        await world.project_service.add_member(
            None, 2, 1, MemberAdd(user_id=99, role=ProjectRole.MEMBER)
        )


@pytest.mark.asyncio
async def test_member_cannot_manage_members():
    world = await build_world()

    with pytest.raises(AccessDenied):
        await world.project_service.add_member(
            None, 3, 1, MemberAdd(user_id=4, role=ProjectRole.MEMBER)
        )


@pytest.mark.asyncio
async def test_owner_role_changes_only_via_transfer():
    world = await build_world()

    with pytest.raises(ValueError):
        MemberAdd(user_id=4, role=ProjectRole.OWNER)

    with pytest.raises(AccessDenied):
        await world.project_service.change_member_role(
            None, 2, 1, 1, MemberRolePatch(role=ProjectRole.VIEWER)
        )


@pytest.mark.asyncio
async def test_admin_cannot_modify_another_admin():
    world = await build_world()
    await world.project_service.add_member(
        None, 1, 1, MemberAdd(user_id=4, role=ProjectRole.ADMIN)
    )

    with pytest.raises(AccessDenied):
        await world.project_service.change_member_role(
            None, 2, 1, 4, MemberRolePatch(role=ProjectRole.VIEWER)
        )


@pytest.mark.asyncio
async def test_remove_member_owner_denied():
    world = await build_world()

    with pytest.raises(AccessDenied):
        await world.project_service.remove_member(None, 2, 1, 1)


@pytest.mark.asyncio
async def test_remove_member_by_owner():
    world = await build_world()

    await world.project_service.remove_member(None, 1, 1, 2)

    role = await world.member_crud.get_project_role(None, 1, 2)
    assert role is None


@pytest.mark.asyncio
async def test_archived_project_rejects_member_management():
    world = await build_world()
    await world.project_service.archive_project(None, 1, 1)

    with pytest.raises(ArchivedCollection):
        await world.project_service.add_member(
            None, 1, 1, MemberAdd(user_id=4, role=ProjectRole.MEMBER)
        )


@pytest.mark.asyncio
async def test_transfer_ownership_swaps_roles():
    world = await build_world()

    updated = await world.project_service.transfer_ownership(
        None, 1, 1, OwnershipTransfer(user_id=3)
    )

    assert updated.owner.id == 3
    assert await world.member_crud.get_project_role(None, 1, 3) == ProjectRole.OWNER
    assert await world.member_crud.get_project_role(None, 1, 1) == ProjectRole.ADMIN


@pytest.mark.asyncio
async def test_transfer_ownership_requires_owner():
    world = await build_world()

    with pytest.raises(AccessDenied):
        await world.project_service.transfer_ownership(
            None, 2, 1, OwnershipTransfer(user_id=3)
        )


@pytest.mark.asyncio
async def test_transfer_ownership_to_non_member():
    world = await build_world()

    with pytest.raises(UserNotFound):
        await world.project_service.transfer_ownership(
            None, 1, 1, OwnershipTransfer(user_id=4)
        )


@pytest.mark.asyncio
async def test_transfer_ownership_to_current_owner():
    world = await build_world()

    with pytest.raises(AlreadyExists):
        await world.project_service.transfer_ownership(
            None, 1, 1, OwnershipTransfer(user_id=1)
        )
