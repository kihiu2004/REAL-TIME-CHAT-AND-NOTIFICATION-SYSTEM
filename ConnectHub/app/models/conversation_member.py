import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UTCDateTime
from app.utils.datetime_utils import utcnow

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.user import User


# ROLE OF A USER INSIDE A CONVERSATION
class MemberRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


# CONVERSATION <-> USER MAPPING
class ConversationMember(Base):
    __tablename__ = "conversation_members"

    # COMPOSITE PRIMARY KEY
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )

    # MEMBERSHIP INFORMATION
    role: Mapped[MemberRole] = mapped_column(
        SQLAlchemyEnum(
            MemberRole,
            name="member_role",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=MemberRole.MEMBER,
        nullable=False,
    )
    joined_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=utcnow,
        nullable=False,
    )
    last_read_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime,
        nullable=True,
    )

    # RELATIONSHIPS
    conversation: Mapped["Conversation"] = relationship(
        back_populates="members",
    )
    user: Mapped["User"] = relationship(
        back_populates="memberships",
    )

    def __repr__(self) -> str:
        return (
            f"<ConversationMember(conversation_id={self.conversation_id}, "
            f"user_id={self.user_id}, role='{self.role}')>"
        )
