import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Index,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UTCDateTime
from app.utils.datetime_utils import utcnow

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.message_read import MessageRead
    from app.models.user import User


# MESSAGE CONTENT KIND
class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"


# MESSAGE DATABASE MODEL
class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )

    # PRIMARY KEY
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # RELATIONS
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Kept if the sending account is deleted
    sender_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reply_to_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
    )

    # CONTENT
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_type: Mapped[MessageType] = mapped_column(
        SQLAlchemyEnum(
            MessageType,
            name="message_type",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=MessageType.TEXT,
        nullable=False,
    )
    is_edited: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    edited_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime,
        nullable=True,
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
    conversation: Mapped["Conversation"] = relationship(
        back_populates="messages",
    )
    sender: Mapped["User | None"] = relationship(
        back_populates="messages",
    )
    reply_to: Mapped["Message | None"] = relationship(
        remote_side="Message.id",
    )
    read_receipts: Mapped[list["MessageRead"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, conversation_id={self.conversation_id})>"
