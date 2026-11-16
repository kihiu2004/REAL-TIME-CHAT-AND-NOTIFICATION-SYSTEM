import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Enum as SQLAlchemyEnum,
    ForeignKey,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UTCDateTime
from app.utils.datetime_utils import utcnow

if TYPE_CHECKING:
    from app.models.conversation_member import ConversationMember
    from app.models.message import Message
    from app.models.user import User


# CONVERSATION KIND
class ConversationType(str, Enum):
    DIRECT = "direct"
    GROUP = "group"


# CONVERSATION DATABASE MODEL
class Conversation(Base):
    __tablename__ = "conversations"

    # PRIMARY KEY
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # CONVERSATION INFORMATION
    type: Mapped[ConversationType] = mapped_column(
        SQLAlchemyEnum(
            ConversationType,
            name="conversation_type",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=ConversationType.DIRECT,
        nullable=False,
    )
    # Only used by group conversations
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # OWNER (kept if the account is deleted)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # TIMESTAMP
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    # RELATIONSHIPS
    creator: Mapped["User | None"] = relationship(
        back_populates="conversations_created",
    )
    members: Mapped[list["ConversationMember"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, type='{self.type}')>"
