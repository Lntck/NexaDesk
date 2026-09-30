from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator

from app.enums import Role


# Base schema for user data
class UserBase(BaseModel):
    username: str = Field(..., min_length=4, max_length=24)
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        """Lowercase the username before validation of other rules.

        Args:
            value: raw username from the request.

        Returns:
            str: normalized lowercase username.
        """
        return value.lower()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """Lowercase the email so uniqueness checks are case insensitive.

        Args:
            value: raw email from the request.

        Returns:
            str: normalized lowercase email.
        """
        return value.lower()


# Schema for user registration data | Input
class UserRegister(UserBase):
    password: SecretStr = Field(..., min_length=8, max_length=24)


# Compact user reference embedded into domain responses
class UserBrief(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)


# Schema for reading user data | Output
class UserRead(UserBase):
    id: int
    is_active: bool
    role: Role
    created_at: datetime
    updated_at: datetime


# Schema for token response | Output
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
