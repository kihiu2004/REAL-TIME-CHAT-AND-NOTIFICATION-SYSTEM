import json
import logging
import uuid

from fastapi import WebSocket
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, BadRequestError
from app.core.permissions import member_ids, require_member
from app.models.user import User
from app.redis import presence_manager
from app.schemas.message import MessageCreate
from app.services import message_service, notification_service
from app.websocket import realtime

logger = logging.getLogger(__name__)


def _uuid(value: object, field: str) -> uuid.UUID:
    if not isinstance(value, str):
        raise BadRequestError(f"{field} must be a UUID string")
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise BadRequestError(f"{field} must be a valid UUID") from exc


def _optional_uuid(value: object, field: str) -> uuid.UUID | None:
    if value in (None, ""):
        return None
    return _uuid(value, field)


async def _send_error(websocket: WebSocket, detail: str, code: str) -> None:
    await websocket.send_json({"type": "error", "data": {"detail": detail, "code": code}})


async def handle_event(
    websocket: WebSocket,
    user: User,
    db: AsyncSession,
    raw: str,
) -> None:
    """Handle one inbound WebSocket frame."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        await _send_error(websocket, "Payload must be valid JSON", "invalid_json")
        return

    if not isinstance(payload, dict):
        await _send_error(websocket, "Payload must be a JSON object", "invalid_payload")
        return

    event_type = payload.get("type")
    data = payload.get("data") or {}
    if not isinstance(data, dict):
        await _send_error(websocket, "data must be a JSON object", "invalid_payload")
        return

    try:
        if event_type == "ping":
            await presence_manager.refresh(str(user.id))
            await websocket.send_json({"type": "pong", "data": {}})
        elif event_type == "message.send":
            await _message_send(db, user, data)
        elif event_type in {"typing.start", "typing.stop"}:
            await _typing(db, user, data, is_typing=event_type == "typing.start")
        elif event_type == "message.read":
            await _message_read(db, user, data)
        else:
            await _send_error(
                websocket,
                f"Unknown event type: {event_type!r}",
                "unknown_event",
            )
    except AppError as exc:
        await _send_error(websocket, exc.detail, exc.code)
    except ValidationError as exc:
        details = "; ".join(error["msg"] for error in exc.errors())
        await _send_error(websocket, details, "validation_error")
    except Exception:
        logger.exception("WebSocket event failed")
        await db.rollback()
        await _send_error(websocket, "Internal error while handling the event", "internal_error")


async def _message_send(db: AsyncSession, user: User, data: dict) -> None:
    conversation_id = _uuid(data.get("conversation_id"), "conversation_id")
    payload = MessageCreate(
        content=data.get("content") or "",
        message_type=data.get("message_type") or "text",
        reply_to_id=_optional_uuid(data.get("reply_to_id"), "reply_to_id"),
    )

    message, recipients = await message_service.create_message(
        db, conversation_id, user, payload
    )
    await realtime.broadcast_new_message(message, recipients)

    others = [user_id for user_id in recipients if user_id != user.id]
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


async def _typing(db: AsyncSession, user: User, data: dict, *, is_typing: bool) -> None:
    conversation_id = _uuid(data.get("conversation_id"), "conversation_id")
    await require_member(db, conversation_id, user.id)

    recipients = [
        user_id
        for user_id in await member_ids(db, conversation_id)
        if user_id != user.id
    ]
    await realtime.broadcast_typing(conversation_id, user, is_typing, recipients)


async def _message_read(db: AsyncSession, user: User, data: dict) -> None:
    conversation_id = _uuid(data.get("conversation_id"), "conversation_id")
    message_id = _optional_uuid(data.get("message_id"), "message_id")

    last_read_at = await message_service.mark_read(
        db, conversation_id, user, message_id
    )
    recipients = [
        user_id
        for user_id in await member_ids(db, conversation_id)
        if user_id != user.id
    ]
    await realtime.broadcast_read(conversation_id, user, last_read_at, recipients)
