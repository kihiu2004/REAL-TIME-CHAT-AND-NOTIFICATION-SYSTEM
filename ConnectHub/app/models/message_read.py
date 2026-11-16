import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UTCDateTime
from app.utils.datetime_utils import utcnow

if TYPE_CHECKING:
    from app.models.message import Message
    from app.models.user import User


# READ RECEIPT FOR A SINGLE MESSAGE
class MessageRead(Base):
    __tablename__ = "message_reads"
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", name="uq_message_reads_message_user"),
    )

    # PRIMARY KEY
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # RELATIONS
    message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # TIMESTAMP
    read_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=utcnow,
        nullable=False,
    )

    # RELATIONSHIPS
    message: Mapped["Message"] = relationship(
        back_populates="read_receipts",
    )
    user: Mapped["User"] = relationship(
        back_populates="message_reads",
    )

    def __repr__(self) -> str:
        return f"<MessageRead(message_id={self.message_id}, user_id={self.user_id})>"
