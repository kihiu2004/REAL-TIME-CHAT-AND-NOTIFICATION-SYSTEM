import asyncio
import json
import logging
from typing import Any

from app.redis.redis_connection import get_redis

logger = logging.getLogger(__name__)

CHANNEL_PREFIX = "connecthub:user:"

_listener_task: asyncio.Task[None] | None = None


def channel_for(user_id: str) -> str:
    return f"{CHANNEL_PREFIX}{user_id}"


async def publish_user_event(user_id: str, event: dict[str, Any]) -> None:
    """Deliver an event to one user, through Redis when possible."""
    payload = json.dumps(event, default=str)

    redis = get_redis()
    if redis is not None:
        try:
            await redis.publish(channel_for(user_id), payload)
            return
        except Exception:  # pragma: no cover - depends on the environment
            logger.warning("Redis publish failed; delivering in-process")

    await deliver_local(user_id, event)


async def publish_to_users(user_ids: list[str], event: dict[str, Any]) -> None:
    for user_id in dict.fromkeys(user_ids):
        await publish_user_event(user_id, event)


async def deliver_local(user_id: str, event: dict[str, Any]) -> None:
    # Imported lazily to avoid a circular import at module load time
    from app.websocket.connection_manager import manager

    await manager.deliver(user_id, event)


async def _listen() -> None:
    redis = get_redis()
    if redis is None:
        return

    pubsub = redis.pubsub()
    await pubsub.psubscribe(f"{CHANNEL_PREFIX}*")
    logger.info("Listening for realtime events on %s*", CHANNEL_PREFIX)

    try:
        async for message in pubsub.listen():
            if message.get("type") != "pmessage":
                continue
            user_id = str(message["channel"]).rsplit(":", 1)[-1]
            try:
                event = json.loads(message["data"])
            except (TypeError, ValueError):
                logger.warning("Ignoring malformed realtime event")
                continue
            await deliver_local(user_id, event)
    except asyncio.CancelledError:
        raise
    except Exception:  # pragma: no cover - depends on the environment
        logger.exception("Realtime listener stopped unexpectedly")
    finally:
        await pubsub.aclose()


async def start_listener() -> None:
    global _listener_task
    if get_redis() is None or _listener_task is not None:
        return
    _listener_task = asyncio.create_task(_listen(), name="realtime-listener")


async def stop_listener() -> None:
    global _listener_task
    task, _listener_task = _listener_task, None
    if task is None:
        return
    task.cancel()
    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass
