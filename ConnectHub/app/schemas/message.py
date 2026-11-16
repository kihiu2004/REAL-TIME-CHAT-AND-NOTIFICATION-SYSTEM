import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.message import MessageType
from app.schemas.user import UserPublic


# SEND A MESSAGE
class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    message_type: MessageType = MessageType.TEXT
    reply_to_id: uuid.UUID | None = None

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message content cannot be empty")
        return value


# EDIT A MESSAGE
class MessageUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        return value.strip()


# MESSAGE RESPONSE
class MessagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    sender: UserPublic | None = None
    content: str | None = None
    message_type: MessageType
    reply_to_id: uuid.UUID | None = None
    is_edited: bool = False
    edited_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


# PAGINATED MESSAGE LIST
class MessagePage(BaseModel):
    items: list[MessagePublic]
    has_more: bool = False
    next_before: datetime | None = None


# MARK A CONVERSATION AS READ
class ReadRequest(BaseModel):
    message_id: uuid.UUID | None = None


class ReadState(BaseModel):
    last_read_at: datetime
