import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember, MemberRole

# ROLES THAT ARE ALLOWED TO MANAGE A CONVERSATION
MANAGER_ROLES = {MemberRole.OWNER, MemberRole.ADMIN}


async def get_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
) -> Conversation:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None:
        raise NotFoundError("Conversation not found")
    return conversation


async def get_membership(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> ConversationMember | None:
    stmt = select(ConversationMember).where(
        ConversationMember.conversation_id == conversation_id,
        ConversationMember.user_id == user_id,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def require_member(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> ConversationMember:
    membership = await get_membership(db, conversation_id, user_id)
    if membership is None:
        raise ForbiddenError("You are not a member of this conversation")
    return membership


async def require_manager(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> ConversationMember:
    membership = await require_member(db, conversation_id, user_id)
    if membership.role not in MANAGER_ROLES:
        raise ForbiddenError("Only conversation admins can do that")
    return membership


async def member_ids(db: AsyncSession, conversation_id: uuid.UUID) -> list[uuid.UUID]:
    stmt = select(ConversationMember.user_id).where(
        ConversationMember.conversation_id == conversation_id
    )
    return list((await db.execute(stmt)).scalars().all())
