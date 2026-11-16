import uuid
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.redis.pubsub_manager import publish_user_event
from app.schemas.notification import NotificationPage, NotificationPublic
from app.utils.datetime_utils import utcnow


async def create_notifications(
    db: AsyncSession,
    user_ids: list[uuid.UUID],
    *,
    notification_type: NotificationType,
    title: str,
    body: str | None = None,
    data: dict[str, Any] | None = None,
) -> list[Notification]:
    recipients = list(dict.fromkeys(user_ids))
    if not recipients:
        return []

    now = utcnow()
    notifications = [
        Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            body=body,
            data=data,
            created_at=now,
        )
        for user_id in recipients
    ]
    db.add_all(notifications)
    await db.commit()

    # Push each notification to the recipient if they are connected
    for notification in notifications:
        await publish_user_event(
            str(notification.user_id),
            {
                "type": "notification.new",
                "data": NotificationPublic.model_validate(notification).model_dump(mode="json"),
            },
        )

    return notifications


async def notify_new_message(
    db: AsyncSession,
    recipients: list[uuid.UUID],
    *,
    sender: User,
    message_id: uuid.UUID,
    conversation_id: uuid.UUID,
    preview: str | None,
) -> None:
    await create_notifications(
        db,
        recipients,
        notification_type=NotificationType.MESSAGE,
        title=f"New message from {sender.username}",
        body=(preview or "Sent an attachment")[:200],
        data={
            "conversation_id": str(conversation_id),
            "message_id": str(message_id),
            "sender_id": str(sender.id),
        },
    )


async def list_notifications(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> NotificationPage:
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(min(limit, 100))
        .offset(max(offset, 0))
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))

    items = list((await db.execute(stmt)).scalars().all())
    return NotificationPage(
        items=[NotificationPublic.model_validate(item) for item in items],
        unread_count=await unread_count(db, user_id),
    )


async def unread_count(db: AsyncSession, user_id: uuid.UUID) -> int:
    stmt = select(func.count(Notification.id)).where(
        Notification.user_id == user_id,
        Notification.is_read.is_(False),
    )
    return int((await db.execute(stmt)).scalar_one())


async def mark_read(
    db: AsyncSession,
    user_id: uuid.UUID,
    notification_id: uuid.UUID,
) -> Notification:
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    )
    notification = (await db.execute(stmt)).scalar_one_or_none()
    if notification is None:
        raise NotFoundError("Notification not found")

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = utcnow()
        await db.commit()
        await db.refresh(notification)

    return notification


async def mark_all_read(db: AsyncSession, user_id: uuid.UUID) -> int:
    result = await db.execute(
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True, read_at=utcnow())
    )
    await db.commit()
    return int(result.rowcount or 0)
