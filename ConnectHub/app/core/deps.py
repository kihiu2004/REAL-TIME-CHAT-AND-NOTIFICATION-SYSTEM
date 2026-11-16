from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.jwt import TokenError, decode_access_token, token_subject
from app.database.session import get_db
from app.models.user import User, UserStatus

# auto_error=False so we can return our own consistent 401 payload
bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
) -> User:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Not authenticated")

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = token_subject(payload)
    except TokenError as exc:
        raise UnauthorizedError(str(exc)) from exc

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise UnauthorizedError("User no longer exists")

    if user.account_status != UserStatus.ACTIVE:
        raise ForbiddenError("Account is not active")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
