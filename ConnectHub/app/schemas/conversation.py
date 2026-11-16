import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.conversation import ConversationType
from app.models.conversation_member import MemberRole
from app.schemas.user import UserPublic


# CONVERSATION CREATION
class ConversationCreate(BaseModel):
    type: ConversationType = ConversationType.DIRECT
    name: str | None = Field(default=None, max_length=120)
    member_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_shape(self) -> "ConversationCreate":
        if self.type == ConversationType.GROUP:
            if not self.name or not self.name.strip():
                raise ValueError("Group conversations need a name")
            self.name = self.name.strip()
        elif self.name is not None:
            raise ValueError("Direct conversations cannot have a name")

        if len(set(self.member_ids)) != len(self.member_ids):
            raise ValueError("member_ids must not contain duplicates")

        if self.type == ConversationType.DIRECT and len(self.member_ids) != 1:
            raise ValueError("Direct conversations need exactly one other member")
        return self


class ConversationUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


# MEMBERSHIP
class MemberPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user: UserPublic
    role: MemberRole
    joined_at: datetime
    last_read_at: datetime | None = None


class MemberAdd(BaseModel):
    user_id: uuid.UUID


class MemberRoleUpdate(BaseModel):
    role: MemberRole


# CONVERSATION RESPONSE
class ConversationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: ConversationType
    name: str | None = None
    created_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    members: list[MemberPublic] = Field(default_factory=list)


# MESSAGE PREVIEW (must be declared before ConversationListItem)
class MessagePreview(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content: str | None = None
    sender_id: uuid.UUID | None = None
    created_at: datetime


# CONVERSATION LIST ITEM (adds the last message preview)
class ConversationListItem(ConversationPublic):
    last_message: MessagePreview | None = None
    unread_count: int = 0
