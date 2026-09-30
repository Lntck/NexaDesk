from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.enums import NotificationType
from app.schemas.user import UserBrief


# Project a notification refers to | Output
class NotificationProject(BaseModel):
    id: int
    key: str


# Task a notification refers to | Output
class NotificationTask(BaseModel):
    id: int
    key: str
    title: str


# One user notification | Output
class NotificationRead(BaseModel):
    id: int
    type: NotificationType
    project: NotificationProject | None = None
    task: NotificationTask | None = None
    actor: UserBrief | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    is_read: bool
    created_at: datetime
