from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.core.security import hash_password, verify_password
from app.models.user import User, UserStatus
from app.schemas.auth import RegisterRequest


async def get_user_by_identifier(db: AsyncSession, identifier: str) -> User | None:
    stmt = select(User).where(
        or_(User.username == identifier, User.email == identifier)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def register_user(db: AsyncSession, payload: RegisterRequest) -> User:
    stmt = select(User).where(
        or_(
            User.username == payload.username,
            User.email == str(payload.email).lower(),
        )
    )
    if (await db.execute(stmt)).scalars().first() is not None:
        raise ConflictError("That username or email is already registered")

    user = User(
        username=payload.username,
        email=str(payload.email).lower(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("That username or email is already registered") from exc

    await db.refresh(user)
    return user


async def authenticate(db: AsyncSession, identifier: str, password: str) -> User:
    user = await get_user_by_identifier(db, identifier.strip().lower())

    # Same error for "no such user" and "wrong password" on purpose
    if user is None or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Invalid username/email or password")

    if user.account_status != UserStatus.ACTIVE:
        raise ForbiddenError("This account is not active")

    return user
