from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.enums import Priority
from app.schemas.common import PatchSchema
from app.schemas.label import LabelRead
from app.schemas.task_status import TaskStatusRead
from app.schemas.user import UserBrief


# Task creation | Input
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    assignee_id: int | None = None
    status_id: int | None = None
    priority: Priority = Priority.MEDIUM
    due_date: date | None = None
    estimated_hours: Decimal | None = Field(default=None, ge=0)
    parent_task_id: int | None = None


# Editable task fields update | Input
class TaskPatch(PatchSchema):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    priority: Priority | None = None
    due_date: date | None = None
    estimated_hours: Decimal | None = Field(default=None, ge=0)
    parent_task_id: int | None = None


# Status change command | Input
class TaskTransition(BaseModel):
    status_id: int


# Assignment command | Input
class TaskAssign(BaseModel):
    user_id: int


# Board reorder command | Input
class TaskReorder(BaseModel):
    status_id: int
    before_task_id: int | None = None
    after_task_id: int | None = None


# Compact status reference | Output
class TaskStatusBrief(BaseModel):
    id: int
    key: str
    name: str

    model_config = ConfigDict(from_attributes=True)


# One row of a task collection | Output
class TaskListItem(BaseModel):
    id: int
    key: str
    title: str
    status: TaskStatusBrief
    priority: Priority
    assignee: UserBrief | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Full task details | Output
class TaskRead(BaseModel):
    id: int
    key: str
    project_id: int
    title: str
    description: str | None = None
    status: TaskStatusBrief
    priority: Priority
    creator: UserBrief
    assignee: UserBrief | None = None
    labels: list[LabelRead] = Field(default_factory=list)
    comments_count: int = 0
    watchers_count: int = 0
    parent_task_id: int | None = None
    due_date: date | None = None
    estimated_hours: Decimal | None = None
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Status change result | Output
class TaskTransitionRead(BaseModel):
    id: int
    key: str
    status: TaskStatusBrief
    updated_at: datetime


# Assignment result | Output
class TaskAssignRead(BaseModel):
    id: int
    key: str
    assignee: UserBrief | None = None
    updated_at: datetime


# Final card position after a reorder | Output
class TaskPositionRead(BaseModel):
    id: int
    key: str
    status: TaskStatusBrief
    rank: int
    version: int
    updated_at: datetime


# Card of a board column | Output
class BoardCard(BaseModel):
    id: int
    key: str
    title: str
    priority: Priority
    assignee: UserBrief | None = None
    rank: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Single board column | Output
class BoardColumn(BaseModel):
    status: TaskStatusRead
    tasks: list[BoardCard]
    has_more: bool


# Kanban board | Output
class BoardRead(BaseModel):
    columns: list[BoardColumn]
