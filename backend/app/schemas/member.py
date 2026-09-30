from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.enums import ProjectRole
from app.schemas.common import PatchSchema
from app.schemas.user import UserBrief


# Member addition command | Input
class MemberAdd(BaseModel):
    user_id: int
    role: ProjectRole = ProjectRole.MEMBER

    @field_validator("role")
    @classmethod
    def reject_owner_role(cls, value: ProjectRole) -> ProjectRole:
        """Keep the owner role exclusive to the ownership transfer command.

        Args:
            value: project role sent by the client.

        Returns:
            ProjectRole: the accepted role.

        Raises:
            ValueError: when the client tries to assign the owner role.
        """
        if value == ProjectRole.OWNER:
            raise ValueError("owner role is assigned only by ownership transfer")
        return value


# Member role change command | Input
class MemberRolePatch(PatchSchema):
    role: ProjectRole

    @field_validator("role")
    @classmethod
    def reject_owner_role(cls, value: ProjectRole) -> ProjectRole:
        """Keep the owner role exclusive to the ownership transfer command.

        Args:
            value: project role sent by the client.

        Returns:
            ProjectRole: the accepted role.

        Raises:
            ValueError: when the client tries to assign the owner role.
        """
        if value == ProjectRole.OWNER:
            raise ValueError("owner role is assigned only by ownership transfer")
        return value


# One membership row | Output
class MemberRead(BaseModel):
    user: UserBrief
    role: ProjectRole
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Membership collection | Output
class MemberList(BaseModel):
    items: list[MemberRead]
