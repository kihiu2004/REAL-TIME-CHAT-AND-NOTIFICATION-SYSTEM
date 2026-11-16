import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.permissions import MANAGER_ROLES, get_membership, member_ids, require_member
from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember
from app.models.message import Message, MessageType
from app.models.message_read import MessageRead
from app.models.user import User
from app.schemas.message import MessageCreate, MessagePage, MessagePublic, MessageUpdate
from app.utils.datetime_utils import utcnow

MAX_PAGE_SIZE = 100


async def _load_message(db: AsyncSession, message_id: uuid.UUID) -> Message:
    stmt = (
        select(Message)
        .where(Message.id == message_id)
        .options(selectinload(Message.sender))
    )
    message = (await db.execute(stmt)).scalar_one_or_none()
    if message is None:
        raise NotFoundError("Message not found")
    return message


async def create_message(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    sender: User,
    payload: MessageCreate,
) -> tuple[Message, list[uuid.UUID]]:
    await require_member(db, conversation_id, sender.id)

    conversation = await db.get(Conversation, conversation_id)
    if conversation is None:
        raise NotFoundError("Conversation not found")

    if payload.reply_to_id is not None:
        reply = await db.get(Message, payload.reply_to_id)
        if reply is None or reply.conversation_id != conversation_id:
            raise BadRequestError("reply_to_id does not belong to this conversation")

    message = Message(
        conversation_id=conversation_id,
        sender=sender,
        content=payload.content,
        message_type=payload.message_type,
        reply_to_id=payload.reply_to_id,
    )
    db.add(message)
    conversation.updated_at = utcnow()
    await db.commit()

    # server defaults need one round-trip to be populated
    await db.refresh(message, attribute_names=["created_at", "updated_at"])

    return message, await member_ids(db, conversation_id)


async def list_messages(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user: User,
    *,
    limit: int = 50,
    before: datetime | None = None,
) -> MessagePage:
    await require_member(db, conversation_id, user.id)

    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .options(selectinload(Message.sender))
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(min(limit, MAX_PAGE_SIZE) + 1)
    )
    if before is not None:
        stmt = stmt.where(Message.created_at < before)

    rows = list((await db.execute(stmt)).scalars().all())
    has_more = len(rows) > limit
    items = rows[:limit]

    return MessagePage(
        items=[MessagePublic.model_validate(message) for message in items],
        has_more=has_more,
        next_before=items[-1].created_at if has_more and items else None,
    )


async def update_message(
    db: AsyncSession,
    message_id: uuid.UUID,
    user: User,
    payload: MessageUpdate,
) -> Message:
    message = await _load_message(db, message_id)
    await require_member(db, message.conversation_id, user.id)

    if message.sender_id != user.id:
        raise ForbiddenError("You can only edit your own messages")
    if message.message_type != MessageType.TEXT:
        raise BadRequestError("Only text messages can be edited")

    message.content = payload.content
    message.is_edited = True
    message.edited_at = utcnow()
    await db.commit()
    await db.refresh(message, attribute_names=["updated_at"])
    return message


async def delete_message(
    db: AsyncSession,
    message_id: uuid.UUID,
    user: User,
) -> uuid.UUID:
    message = await _load_message(db, message_id)
    membership = await require_member(db, message.conversation_id, user.id)

    is_sender = message.sender_id == user.id
    is_manager = membership.role in MANAGER_ROLES
    if not (is_sender or is_manager):
        raise ForbiddenError("You cannot delete this message")

    conversation_id = message.conversation_id
    await db.delete(message)
    await db.commit()
    return conversation_id


async def mark_read(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user: User,
    message_id: uuid.UUID | None = None,
) -> datetime:
    membership = await require_member(db, conversation_id, user.id)

    if message_id is not None:
        message = await db.get(Message, message_id)
        if message is None or message.conversation_id != conversation_id:
            raise NotFoundError("Message not found in this conversation")

        exists = (
            await db.execute(
                select(MessageRead.id).where(
                    MessageRead.message_id == message_id,
                    MessageRead.user_id == user.id,
                )
            )
        ).scalar_one_or_none()
        if exists is None:
            db.add(MessageRead(message_id=message_id, user_id=user.id))

    now = utcnow()
    membership.last_read_at = now
    await db.commit()
    return now


async def unread_count(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user: User,
) -> int:
    membership = await require_member(db, conversation_id, user.id)
    stmt = select(func.count(Message.id)).where(
        Message.conversation_id == conversation_id,
        Message.sender_id != user.id,
    )
    if membership.last_read_at is not None:
        stmt = stmt.where(Message.created_at > membership.last_read_at)
    return int((await db.execute(stmt)).scalar_one())


async def membership_for(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> ConversationMember | None:
    return await get_membership(db, conversation_id, user_id)
