import uuid
from datetime import datetime

from app.models.message import Message
from app.models.user import User
from app.redis.pubsub_manager import publish_to_users
from app.schemas.message import MessagePublic


async def broadcast_new_message(
    message: Message,
    recipient_ids: list[uuid.UUID],
) -> None:
    await publish_to_users(
        [str(user_id) for user_id in recipient_ids],
        {
            "type": "message.new",
            "data": MessagePublic.model_validate(message).model_dump(mode="json"),
        },
    )


async def broadcast_message_updated(
    message: Message,
    recipient_ids: list[uuid.UUID],
) -> None:
    await publish_to_users(
        [str(user_id) for user_id in recipient_ids],
        {
            "type": "message.updated",
            "data": MessagePublic.model_validate(message).model_dump(mode="json"),
        },
    )


async def broadcast_message_deleted(
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    recipient_ids: list[uuid.UUID],
) -> None:
    await publish_to_users(
        [str(user_id) for user_id in recipient_ids],
        {
            "type": "message.deleted",
            "data": {
                "conversation_id": str(conversation_id),
                "message_id": str(message_id),
            },
        },
    )


async def broadcast_typing(
    conversation_id: uuid.UUID,
    user: User,
    is_typing: bool,
    recipient_ids: list[uuid.UUID],
) -> None:
    await publish_to_users(
        [str(user_id) for user_id in recipient_ids],
        {
            "type": "typing",
            "data": {
                "conversation_id": str(conversation_id),
                "user_id": str(user.id),
                "username": user.username,
                "is_typing": is_typing,
            },
        },
    )


async def broadcast_read(
    conversation_id: uuid.UUID,
    user: User,
    last_read_at: datetime,
    recipient_ids: list[uuid.UUID],
) -> None:
    await publish_to_users(
        [str(user_id) for user_id in recipient_ids],
        {
            "type": "message.read",
            "data": {
                "conversation_id": str(conversation_id),
                "user_id": str(user.id),
                "last_read_at": last_read_at.isoformat(),
            },
        },
    )
