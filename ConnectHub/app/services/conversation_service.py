import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import MANAGER_ROLES, require_manager, require_member
from app.models.conversation import Conversation, ConversationType
from app.models.conversation_member import ConversationMember, MemberRole
from app.models.message import Message
from app.models.user import User
from app.schemas.conversation import (
    ConversationCreate,
    ConversationListItem,
    ConversationPublic,
    ConversationUpdate,
    MessagePreview,
)
from app.utils.datetime_utils import utcnow

# Eager-load members (and each member's user) so responses never trigger a
# lazy load outside the async context.
_MEMBERS_LOAD = selectinload(Conversation.members).selectinload(ConversationMember.user)


async def load_conversation(db: AsyncSession, conversation_id: uuid.UUID) -> Conversation:
    stmt = (
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(_MEMBERS_LOAD)
    )
    conversation = (await db.execute(stmt)).scalar_one_or_none()
    if conversation is None:
        raise NotFoundError("Conversation not found")
    return conversation


async def _find_direct(
    db: AsyncSession,
    user_ids: set[uuid.UUID],
) -> Conversation | None:
    """Return the existing 1-to-1 conversation between these users, if any."""
    stmt = (
        select(Conversation)
        .where(Conversation.type == ConversationType.DIRECT)
        .where(
            Conversation.id.in_(
                select(ConversationMember.conversation_id).where(
                    ConversationMember.user_id.in_(user_ids)
                )
            )
        )
        .options(_MEMBERS_LOAD)
    )
    for conversation in (await db.execute(stmt)).scalars().all():
        if {member.user_id for member in conversation.members} == user_ids:
            return conversation
    return None


async def create_conversation(
    db: AsyncSession,
    creator: User,
    payload: ConversationCreate,
) -> Conversation:
    member_ids = {creator.id, *payload.member_ids}

    found = (
        await db.execute(select(User.id).where(User.id.in_(member_ids)))
    ).scalars().all()
    if len(found) != len(member_ids):
        raise BadRequestError("One or more users do not exist")

    if payload.type == ConversationType.DIRECT:
        existing = await _find_direct(db, member_ids)
        if existing is not None:
            return existing

    conversation = Conversation(
        type=payload.type,
        name=payload.name,
        created_by=creator.id,
    )
    db.add(conversation)
    await db.flush()

    for user_id in member_ids:
        db.add(
            ConversationMember(
                conversation_id=conversation.id,
                user_id=user_id,
                role=MemberRole.OWNER if user_id == creator.id else MemberRole.MEMBER,
                last_read_at=utcnow(),
            )
        )

    await db.commit()
    return await load_conversation(db, conversation.id)


async def list_conversations(
    db: AsyncSession,
    user: User,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[ConversationListItem]:
    stmt = (
        select(Conversation)
        .join(ConversationMember)
        .where(ConversationMember.user_id == user.id)
        .options(_MEMBERS_LOAD)
        .order_by(Conversation.updated_at.desc())
        .limit(min(limit, 100))
        .offset(max(offset, 0))
    )
    conversations = list((await db.execute(stmt)).scalars().all())
    if not conversations:
        return []

    ids = [conversation.id for conversation in conversations]

    # Latest message per conversation (single query, ties resolved in Python)
    latest_at = (
        select(
            Message.conversation_id.label("conversation_id"),
            func.max(Message.created_at).label("last_at"),
        )
        .where(Message.conversation_id.in_(ids))
        .group_by(Message.conversation_id)
        .subquery()
    )
    last_messages_stmt = (
        select(Message)
        .join(
            latest_at,
            and_(
                Message.conversation_id == latest_at.c.conversation_id,
                Message.created_at == latest_at.c.last_at,
            ),
        )
        .order_by(Message.created_at.desc())
    )
    last_messages: dict[uuid.UUID, Message] = {}
    for message in (await db.execute(last_messages_stmt)).scalars().all():
        last_messages.setdefault(message.conversation_id, message)

    # Unread counts per conversation (single query)
    unread_stmt = (
        select(ConversationMember.conversation_id, func.count(Message.id))
        .join(Message, Message.conversation_id == ConversationMember.conversation_id)
        .where(
            ConversationMember.user_id == user.id,
            ConversationMember.conversation_id.in_(ids),
            Message.sender_id != user.id,
            or_(
                ConversationMember.last_read_at.is_(None),
                Message.created_at > ConversationMember.last_read_at,
            ),
        )
        .group_by(ConversationMember.conversation_id)
    )
    unread = {
        conversation_id: count
        for conversation_id, count in (await db.execute(unread_stmt)).all()
    }

    return [
        build_list_item(
            conversation,
            last_messages.get(conversation.id),
            unread.get(conversation.id, 0),
        )
        for conversation in conversations
    ]


def build_list_item(
    conversation: Conversation,
    last_message: Message | None,
    unread_count: int,
) -> ConversationListItem:
    base = ConversationPublic.model_validate(conversation)
    return ConversationListItem(
        **base.model_dump(),
        last_message=MessagePreview.model_validate(last_message) if last_message else None,
        unread_count=unread_count,
    )


async def update_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user: User,
    payload: ConversationUpdate,
) -> Conversation:
    conversation = await load_conversation(db, conversation_id)
    await require_manager(db, conversation_id, user.id)

    if conversation.type != ConversationType.GROUP:
        raise BadRequestError("Only group conversations can be renamed")

    conversation.name = payload.name.strip()
    conversation.updated_at = utcnow()
    await db.commit()
    return await load_conversation(db, conversation_id)


async def add_member(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    actor: User,
    new_user_id: uuid.UUID,
) -> Conversation:
    conversation = await load_conversation(db, conversation_id)
    await require_manager(db, conversation_id, actor.id)

    if conversation.type != ConversationType.GROUP:
        raise BadRequestError("Direct conversations cannot have extra members")

    if await db.get(User, new_user_id) is None:
        raise NotFoundError("User not found")

    if any(member.user_id == new_user_id for member in conversation.members):
        raise ConflictError("That user is already a member")

    db.add(
        ConversationMember(
            conversation_id=conversation_id,
            user_id=new_user_id,
            role=MemberRole.MEMBER,
        )
    )
    conversation.updated_at = utcnow()
    await db.commit()

    # The session keeps the old members collection cached (expire_on_commit is
    # off), so drop it before reloading to include the new member.
    db.expire(conversation, ["members"])
    return await load_conversation(db, conversation_id)


async def remove_member(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    actor: User,
    target_user_id: uuid.UUID,
) -> None:
    conversation = await load_conversation(db, conversation_id)
    actor_membership = await require_member(db, conversation_id, actor.id)

    target = next(
        (member for member in conversation.members if member.user_id == target_user_id),
        None,
    )
    if target is None:
        raise NotFoundError("That user is not a member of this conversation")

    if target.user_id != actor.id:
        if actor_membership.role not in MANAGER_ROLES:
            raise ForbiddenError("Only conversation admins can remove other members")
        if target.role == MemberRole.OWNER:
            raise ForbiddenError("The conversation owner cannot be removed")

    await db.delete(target)
    conversation.updated_at = utcnow()
    await db.commit()
