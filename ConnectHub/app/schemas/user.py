import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserStatus


# PUBLIC USER (safe to return from the API)
class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: EmailStr
    full_name: str
    profile_picture_url: str | None = None
    account_status: UserStatus
    is_online: bool = False
    last_seen_at: datetime | None = None
    created_at: datetime


# PROFILE UPDATE
class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    email: EmailStr | None = None
    profile_picture_url: str | None = Field(default=None, max_length=500)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("full_name cannot be empty")
        return value

    @field_validator("profile_picture_url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.startswith(("http://", "https://")):
            raise ValueError("profile_picture_url must start with http:// or https://")
        return value
