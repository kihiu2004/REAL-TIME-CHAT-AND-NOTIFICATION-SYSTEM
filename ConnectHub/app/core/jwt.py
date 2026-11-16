import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt as pyjwt

from app.config import settings

TOKEN_TYPE = "access"


class TokenError(Exception):
    """Raised when a token is missing, malformed, expired or of the wrong type."""


def create_access_token(
    subject: str | uuid.UUID,
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": TOKEN_TYPE,
        "iat": now,
        "exp": expire,
    }
    return pyjwt.encode(
        payload,
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = pyjwt.decode(
            token,
            settings.JWT_SECRET_KEY.get_secret_value(),
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except pyjwt.PyJWTError as exc:
        raise TokenError("Invalid or expired token") from exc

    if payload.get("type") != TOKEN_TYPE:
        raise TokenError("Invalid token type")

    return payload


def token_subject(payload: dict[str, Any]) -> uuid.UUID:
    """Return the user id stored in a decoded token."""
    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise TokenError("Invalid token subject") from exc
