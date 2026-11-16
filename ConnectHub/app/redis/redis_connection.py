import logging

from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger(__name__)

_redis: Redis | None = None


async def init_redis() -> Redis | None:
    """Connect to Redis. If it is down the app still starts in degraded mode."""
    global _redis
    if _redis is not None:
        return _redis

    try:
        client = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        await client.ping()
        _redis = client
        logger.info("Connected to Redis at %s", settings.REDIS_URL)
    except Exception as exc:  # pragma: no cover - depends on the environment
        logger.warning(
            "Redis is unavailable (%s). Presence and pub/sub stay in-process.",
            exc,
        )
        _redis = None

    return _redis


def get_redis() -> Redis | None:
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
