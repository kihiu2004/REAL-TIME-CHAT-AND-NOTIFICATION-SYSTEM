import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, DbSession
from app.core.permissions import member_ids
from app.schemas.message import (
    MessageCreate,
    MessagePage,
    MessagePublic,
    MessageUpdate,
)
from app.services import message_service, notification_service
from app.websocket import realtime

logger = logging.getLogger(__name__)

router = APIRouter(tags=["messages"])


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessagePublic,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message",
)
async def send_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    db: DbSession,
    user: CurrentUser,
) -> MessagePublic:
    message, recipients = await message_service.create_message(
        db, conversation_id, user, payload
    )

    await realtime.broadcast_new_message(message, recipients)

    others = [recipient for recipient in recipients if recipient != user.id]
    if others:
        try:
            await notification_service.notify_new_message(
                db,
                others,
                sender=user,
                message_id=message.id,
                conversation_id=conversation_id,
                preview=message.content,
            )
        except Exception:  # notifications must never break message delivery
            logger.exception("Failed to create message notifications")

    return MessagePublic.model_validate(message)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=MessagePage,
    summary="Message history (newest first)",
)
async def list_messages(
    conversation_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=100),
    before: datetime | None = Query(
        default=None,
        description="Return messages created before this ISO-8601 timestamp",
    ),
) -> MessagePage:
    return await message_service.list_messages(
        db, conversation_id, user, limit=limit, before=before
    )


@router.patch(
    "/messages/{message_id}",
    response_model=MessagePublic,
    summary="Edit my message",
)
async def update_message(
    message_id: uuid.UUID,
    payload: MessageUpdate,
    db: DbSession,
    user: CurrentUser,
) -> MessagePublic:
    message = await message_service.update_message(db, message_id, user, payload)
    recipients = await member_ids(db, message.conversation_id)
    await realtime.broadcast_message_updated(message, recipients)
    return MessagePublic.model_validate(message)


@router.delete(
    "/messages/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a message",
)
async def delete_message(
    message_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> None:
    conversation_id = await message_service.delete_message(db, message_id, user)
    recipients = await member_ids(db, conversation_id)
    await realtime.broadcast_message_deleted(conversation_id, message_id, recipients)
