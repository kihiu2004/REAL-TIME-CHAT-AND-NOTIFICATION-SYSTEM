import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.exceptions import AppError, ForbiddenError, UnauthorizedError
from app.database.session import asyncSessionLocal
from app.services import presence_service
from app.websocket.connection_manager import manager
from app.websocket.event_handler import handle_event
from app.websocket.websocket_auth import authenticate_websocket

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

CLOSE_UNAUTHORIZED = 4401
CLOSE_FORBIDDEN = 4403


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Authenticated realtime channel: /ws?token=<access token>."""
    await websocket.accept()

    async with asyncSessionLocal() as db:
        try:
            user = await authenticate_websocket(websocket, db)
        except AppError as exc:
            code = CLOSE_FORBIDDEN if isinstance(exc, ForbiddenError) else CLOSE_UNAUTHORIZED
            await websocket.close(code=code, reason=exc.detail[:120])
            return
        except Exception:
            logger.exception("WebSocket authentication failed")
            await websocket.close(code=CLOSE_UNAUTHORIZED, reason="Authentication failed")
            return

        user_id = str(user.id)
        await manager.connect(user_id, websocket)
        try:
            await presence_service.mark_online(db, user)
            await websocket.send_json(
                {"type": "connection.ready", "data": {"user_id": user_id}}
            )
            while True:
                raw = await websocket.receive_text()
                await handle_event(websocket, user, db, raw)
        except WebSocketDisconnect:
            pass
        except Exception:
            logger.exception("WebSocket connection error")
        finally:
            manager.disconnect(user_id, websocket)
            try:
                await db.rollback()
                await presence_service.mark_offline(db, user.id)
            except Exception:
                logger.exception("Failed to update presence on disconnect")
