import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Enum as SQLAlchemyEnum,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UTCDateTime
from app.utils.datetime_utils import utcnow

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.conversation_member import ConversationMember
    from app.models.message import Message
    from app.models.message_read import MessageRead
    from app.models.notification import Notification


# USER ACCOUNT STATUS
class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


# USER DATABASE MODEL
class User(Base):
    __tablename__ = "users"

    # PRIMARY KEY
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # USER INFORMATION
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)

    # CREDENTIALS (never exposed through the API)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # PROFILE INFORMATION
    profile_picture_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # ACCOUNT STATUS
    account_status: Mapped[UserStatus] = mapped_column(
        SQLAlchemyEnum(
            UserStatus,
            name="user_status",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=UserStatus.ACTIVE,
        nullable=False,
    )

    # ONLINE PRESENCE
    is_online: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
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
    conversations_created: Mapped[list["Conversation"]] = relationship(
        back_populates="creator",
    )
    memberships: Mapped[list["ConversationMember"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    messages: Mapped[list["Message"]] = relationship(
        back_populates="sender",
    )
    message_reads: Mapped[list["MessageRead"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # STRING REPRESENTATION
    def __repr__(self) -> str:
        return (
            f"<User(id={self.id}, "
            f"username='{self.username}', "
            f"email='{self.email}')>"
        )
