from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PatchSchema
from app.schemas.task_status import COLOR_PATTERN

LABEL_NAME_PATTERN = r"^[\w][\w \-]{0,49}$"


# Label creation | Input
class LabelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, pattern=LABEL_NAME_PATTERN)
    color: str = Field(..., pattern=COLOR_PATTERN)


# Editable label fields update | Input
class LabelPatch(PatchSchema):
    name: str | None = Field(
        default=None, min_length=1, max_length=50, pattern=LABEL_NAME_PATTERN
    )
    color: str | None = Field(default=None, pattern=COLOR_PATTERN)


# One project label | Output
class LabelRead(BaseModel):
    id: int
    name: str
    color: str

    model_config = ConfigDict(from_attributes=True)
