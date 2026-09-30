from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PatchSchema
from app.schemas.user import UserBrief


# Comment creation | Input
class CommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=10000)


# Editable comment fields update | Input
class CommentPatch(PatchSchema):
    body: str | None = Field(default=None, min_length=1, max_length=10000)


# One comment of a task | Output
class CommentRead(BaseModel):
    id: int
    task_id: int
    author: UserBrief
    body: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
