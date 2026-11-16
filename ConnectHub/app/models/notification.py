import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    JSON,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UTCDateTime
from app.utils.datetime_utils import utcnow

if TYPE_CHECKING:
    from app.models.user import User


# NOTIFICATION CATEGORY
class NotificationType(str, Enum):
    MESSAGE = "message"
    MENTION = "mention"
    CONVERSATION_INVITE = "conversation_invite"
    SYSTEM = "system"


# NOTIFICATION DATABASE MODEL
class Notification(Base):
    __tablename__ = "notifications"

    # PRIMARY KEY
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # RECIPIENT
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # CONTENT
    type: Mapped[NotificationType] = mapped_column(
        SQLAlchemyEnum(
            NotificationType,
            name="notification_type",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=NotificationType.SYSTEM,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # READ STATE
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    read_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime,
        nullable=True,
    )

    # TIMESTAMP
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=utcnow,
        nullable=False,
    )

    # RELATIONSHIPS
    user: Mapped["User"] = relationship(
        back_populates="notifications",
    )

    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, type='{self.type}', user_id={self.user_id})>"
