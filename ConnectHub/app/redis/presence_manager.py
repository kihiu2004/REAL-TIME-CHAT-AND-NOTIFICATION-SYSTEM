import logging
import time

from app.redis.redis_connection import get_redis

logger = logging.getLogger(__name__)

PRESENCE_KEY = "connecthub:presence"
# A user counts as online while their last heartbeat is younger than this
PRESENCE_TTL_SECONDS = 60

# Used when Redis is not available
_memory: dict[str, float] = {}


def _is_fresh(score: float | None) -> bool:
    return score is not None and (time.time() - score) <= PRESENCE_TTL_SECONDS


async def mark_online(user_id: str) -> None:
    now = time.time()
    redis = get_redis()
    if redis is None:
        _memory[user_id] = now
        return
    try:
        await redis.zadd(PRESENCE_KEY, {user_id: now})
    except Exception:  # pragma: no cover - depends on the environment
        logger.warning("Redis presence write failed; using memory fallback")
        _memory[user_id] = now


async def refresh(user_id: str) -> None:
    await mark_online(user_id)


async def mark_offline(user_id: str) -> None:
    _memory.pop(user_id, None)
    redis = get_redis()
    if redis is None:
        return
    try:
        await redis.zrem(PRESENCE_KEY, user_id)
    except Exception:  # pragma: no cover - depends on the environment
        logger.warning("Redis presence delete failed")


async def is_online(user_id: str) -> bool:
    return (await is_online_many([user_id])).get(user_id, False)


async def is_online_many(user_ids: list[str]) -> dict[str, bool]:
    if not user_ids:
        return {}

    result = {user_id: False for user_id in user_ids}
    redis = get_redis()

    if redis is None:
        for user_id in user_ids:
            result[user_id] = _is_fresh(_memory.get(user_id))
        return result

    try:
        scores = await redis.zmscore(PRESENCE_KEY, user_ids)
        for user_id, score in zip(user_ids, scores):
            result[user_id] = _is_fresh(score)
    except Exception:  # pragma: no cover - depends on the environment
        for user_id in user_ids:
            result[user_id] = _is_fresh(_memory.get(user_id))

    return result
