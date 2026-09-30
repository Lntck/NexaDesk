from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.enums import ActivityEventType
from app.schemas.user import UserBrief


# One immutable history entry | Output
class ActivityEventRead(BaseModel):
    id: str
    type: ActivityEventType
    actor: UserBrief | None = None
    task_id: int | None = None
    data: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
