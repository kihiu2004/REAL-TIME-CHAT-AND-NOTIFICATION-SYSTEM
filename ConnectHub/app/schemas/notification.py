import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.notification import NotificationType


# NOTIFICATION RESPONSE
class NotificationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: NotificationType
    title: str
    body: str | None = None
    data: dict[str, Any] | None = None
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime


# NOTIFICATION LIST
class NotificationPage(BaseModel):
    items: list[NotificationPublic]
    unread_count: int = 0


class UnreadCount(BaseModel):
    unread_count: int


# REUSABLE PAYLOAD USED BY THE SERVICES
class NotificationCreate(BaseModel):
    user_id: uuid.UUID
    type: NotificationType = NotificationType.SYSTEM
    title: str
    body: str | None = None
    data: dict[str, Any] | None = None
