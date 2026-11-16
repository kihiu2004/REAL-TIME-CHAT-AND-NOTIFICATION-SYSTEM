import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.redis import presence_manager
from app.utils.datetime_utils import utcnow


async def mark_online(db: AsyncSession, user: User) -> None:
    user.is_online = True
    user.last_seen_at = utcnow()
    await db.commit()
    await presence_manager.mark_online(str(user.id))


async def mark_offline(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Works even after a rollback: it uses a Core UPDATE, not an ORM object."""
    await presence_manager.mark_offline(str(user_id))
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(is_online=False, last_seen_at=utcnow())
    )
    await db.commit()


async def refresh(db: AsyncSession, user: User) -> None:
    await presence_manager.refresh(str(user.id))


async def presence_for(
    db: AsyncSession,
    user_ids: list[uuid.UUID],
) -> dict[str, bool]:
    """Redis is the source of truth; fall back to the users table."""
    ids = [str(user_id) for user_id in user_ids]
    live = await presence_manager.is_online_many(ids)

    missing = [user_id for user_id in ids if user_id not in live]
    if not missing:
        return live

    stmt = select(User.id, User.is_online).where(
        User.id.in_([uuid.UUID(user_id) for user_id in missing])
    )
    for user_id, is_online in (await db.execute(stmt)).all():
        live[str(user_id)] = bool(is_online)
    return live
