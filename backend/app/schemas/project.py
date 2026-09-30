from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums import ProjectRole
from app.models import Project
from app.schemas.common import PatchSchema
from app.schemas.user import UserBrief

PROJECT_KEY_PATTERN = r"^[A-Z][A-Z0-9]{1,9}$"


# Schema for project creation | Input
class ProjectCreate(BaseModel):
    key: str = Field(..., pattern=PROJECT_KEY_PATTERN)
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)


# Schema for project metadata update | Input
class ProjectPatch(PatchSchema):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)


# One row of the project collection | Output
class ProjectListItem(BaseModel):
    id: int
    key: str
    name: str
    role: ProjectRole
    is_archived: bool
    created_at: datetime


# Full project details | Output
class ProjectRead(BaseModel):
    id: int
    key: str
    name: str
    description: str | None = None
    owner: UserBrief
    members_count: int
    tasks_count: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_project(
        cls, project: Project, members_count: int, tasks_count: int
    ) -> ProjectRead:
        """Compose the response from a project row and its counters.

        Args:
            project: project row with the owner relationship loaded.
            members_count: number of project memberships.
            tasks_count: number of live tasks in the project.

        Returns:
            ProjectRead: response model for project details.
        """
        return cls(
            id=project.id,
            key=project.key,
            name=project.name,
            description=project.description,
            owner=UserBrief(id=project.owner.id, username=project.owner.username),
            members_count=members_count,
            tasks_count=tasks_count,
            is_archived=project.is_archived,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )


# Project creation result | Output
class ProjectCreated(BaseModel):
    id: int
    key: str
    name: str
    description: str | None = None
    owner_id: int
    is_archived: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Ownership transfer command | Input
class OwnershipTransfer(BaseModel):
    user_id: int
