from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.enums import ProjectRole
from app.models import Project, User
from app.schemas import (
    MemberAdd,
    MemberRolePatch,
    ProjectCreate,
    ProjectRead,
    TaskStatusCreate,
)


def test_project_create_validates_key_pattern():
    """Project key must match the UPPER_SNAKE project pattern."""
    ProjectCreate(key="NEXA", name="NexaDesk")

    for bad in ("nexa", "1NEXA", "TOO_LONG_PROJECT_KEY", "N-EXA"):
        with pytest.raises(ValidationError):
            ProjectCreate(key=bad, name="NexaDesk")


def test_member_commands_reject_owner_role():
    """Owner role is assigned only by the ownership transfer command."""
    with pytest.raises(ValidationError):
        MemberAdd(user_id=1, role=ProjectRole.OWNER)

    with pytest.raises(ValidationError):
        MemberRolePatch(role=ProjectRole.OWNER)

    assert MemberAdd(user_id=1).role == ProjectRole.MEMBER


def test_task_status_create_validates_patterns():
    """Status key and color follow the documented patterns."""
    TaskStatusCreate(name="Blocked", key="BLOCKED_1", color="#12abEF")

    with pytest.raises(ValidationError):
        TaskStatusCreate(name="Blocked", key="blocked", color="#FFFFFF")

    with pytest.raises(ValidationError):
        TaskStatusCreate(name="Blocked", key="BLOCKED", color="#FFFFF")

    with pytest.raises(ValidationError):
        TaskStatusCreate(name="Blocked", key="BLOCKED", color="#FFFFFF", position=0)


def test_project_read_from_project_maps_owner_and_counts():
    """ProjectRead carries the owner brief and the live counters."""
    owner = User(
        id=1,
        username="owner",
        email="owner@example.com",
        password_hash="x",
    )
    project = Project(
        id=1,
        key="NEXA",
        name="NexaDesk",
        description="tasks",
        owner_id=1,
        is_archived=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    project.owner = owner

    read = ProjectRead.from_project(project, members_count=3, tasks_count=7)

    assert read.owner.id == 1
    assert read.owner.username == "owner"
    assert read.members_count == 3
    assert read.tasks_count == 7
    assert read.key == "NEXA"
