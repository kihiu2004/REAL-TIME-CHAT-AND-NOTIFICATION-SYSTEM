import uuid

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.user import User
from app.schemas.user import UserUpdate


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    return user


async def list_users(
    db: AsyncSession,
    *,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[User]:
    stmt = select(User).order_by(User.username)
    if search:
        term = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                User.username.ilike(term),
                User.full_name.ilike(term),
                User.email.ilike(term),
            )
        )
    stmt = stmt.limit(min(limit, 100)).offset(max(offset, 0))
    return list((await db.execute(stmt)).scalars().all())


async def update_profile(
    db: AsyncSession,
    user: User,
    payload: UserUpdate,
) -> User:
    changes = payload.model_dump(exclude_unset=True)

    # These columns are NOT NULL. Explicit JSON null must be rejected rather
    # than written to the database as an empty string.
    for field in ("full_name", "email"):
        if field in changes and changes[field] is None:
            raise BadRequestError(f"{field} cannot be null")

    new_email = changes.get("email")
    if new_email is not None and str(new_email).lower() != user.email:
        normalized_email = str(new_email).lower()
        existing = (
            await db.execute(select(User).where(User.email == normalized_email))
        ).scalar_one_or_none()
        if existing is not None:
            raise ConflictError("That email is already in use")
        changes["email"] = normalized_email

    for field, value in changes.items():
        setattr(user, field, value)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("That email is already in use") from exc

    await db.refresh(user)
    return user
