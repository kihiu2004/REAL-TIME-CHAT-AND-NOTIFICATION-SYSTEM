from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.jwt import TokenError, decode_access_token, token_subject
from app.models.user import User, UserStatus


async def authenticate_websocket(websocket: WebSocket, db: AsyncSession) -> User:
    """Authenticate a WebSocket using ?token=... or the Authorization header."""
    token = websocket.query_params.get("token")

    if not token:
        header = websocket.headers.get("authorization", "")
        if header.lower().startswith("bearer "):
            token = header[7:].strip()

    if not token:
        raise UnauthorizedError("Missing access token")

    try:
        payload = decode_access_token(token)
        user_id = token_subject(payload)
    except TokenError as exc:
        raise UnauthorizedError(str(exc)) from exc

    user = await db.get(User, user_id)
    if user is None:
        raise UnauthorizedError("User no longer exists")
    if user.account_status != UserStatus.ACTIVE:
        raise ForbiddenError("Account is not active")

    return user
