import uuid

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, DbSession
from app.core.permissions import member_ids, require_member
from app.schemas.conversation import (
    ConversationCreate,
    ConversationListItem,
    ConversationPublic,
    ConversationUpdate,
    MemberAdd,
)
from app.schemas.message import ReadRequest, ReadState
from app.services import conversation_service, message_service
from app.websocket import realtime

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post(
    "",
    response_model=ConversationPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create a conversation",
)
async def create_conversation(
    payload: ConversationCreate,
    db: DbSession,
    user: CurrentUser,
) -> ConversationPublic:
    conversation = await conversation_service.create_conversation(db, user, payload)
    return ConversationPublic.model_validate(conversation)


@router.get("", response_model=list[ConversationListItem], summary="My conversations")
async def list_conversations(
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[ConversationListItem]:
    return await conversation_service.list_conversations(
        db, user, limit=limit, offset=offset
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationPublic,
    summary="One conversation",
)
async def get_conversation(
    conversation_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> ConversationPublic:
    # Load first so a missing conversation is a 404, not a 403.
    conversation = await conversation_service.load_conversation(db, conversation_id)
    await require_member(db, conversation_id, user.id)
    return ConversationPublic.model_validate(conversation)


@router.patch(
    "/{conversation_id}",
    response_model=ConversationPublic,
    summary="Rename a group",
)
async def update_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationUpdate,
    db: DbSession,
    user: CurrentUser,
) -> ConversationPublic:
    conversation = await conversation_service.update_conversation(
        db, conversation_id, user, payload
    )
    return ConversationPublic.model_validate(conversation)


@router.post(
    "/{conversation_id}/members",
    response_model=ConversationPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Add a member to a group",
)
async def add_member(
    conversation_id: uuid.UUID,
    payload: MemberAdd,
    db: DbSession,
    user: CurrentUser,
) -> ConversationPublic:
    conversation = await conversation_service.add_member(
        db, conversation_id, user, payload.user_id
    )
    return ConversationPublic.model_validate(conversation)


@router.delete(
    "/{conversation_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member (or leave)",
)
async def remove_member(
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> None:
    await conversation_service.remove_member(db, conversation_id, user, user_id)


@router.post(
    "/{conversation_id}/read",
    response_model=ReadState,
    summary="Mark a conversation as read",
)
async def mark_read(
    conversation_id: uuid.UUID,
    payload: ReadRequest,
    db: DbSession,
    user: CurrentUser,
) -> ReadState:
    last_read_at = await message_service.mark_read(
        db, conversation_id, user, payload.message_id
    )

    recipients = [
        member
        for member in await member_ids(db, conversation_id)
        if member != user.id
    ]
    await realtime.broadcast_read(conversation_id, user, last_read_at, recipients)

    return ReadState(last_read_at=last_read_at)
