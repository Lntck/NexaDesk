from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PatchSchema

STATUS_KEY_PATTERN = r"^[A-Z][A-Z0-9_]{1,29}$"
COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}$"


# Board status creation | Input
class TaskStatusCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    key: str = Field(..., pattern=STATUS_KEY_PATTERN)
    color: str = Field(..., pattern=COLOR_PATTERN)
    position: int | None = Field(default=None, ge=1)


# Board status metadata update | Input
class TaskStatusPatch(PatchSchema):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    color: str | None = Field(default=None, pattern=COLOR_PATTERN)
    position: int | None = Field(default=None, ge=1)


# Board status | Output
class TaskStatusRead(BaseModel):
    id: int
    name: str
    key: str
    color: str
    position: int

    model_config = ConfigDict(from_attributes=True)
