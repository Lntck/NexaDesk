from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.user import UserBrief


# One task watcher subscription | Output
class WatcherRead(BaseModel):
    user: UserBrief
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
