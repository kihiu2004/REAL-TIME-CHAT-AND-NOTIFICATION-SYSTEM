# CREATES AN ASYNCHRONOUS DATABASE ENGINE SO FastAPI CAN TALK TO MYSQL
# WITHOUT BLOCKING THE EVENT LOOP
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings

# MySQL DATETIME has no timezone, so every session is pinned to UTC. That keeps
# server-side defaults (func.now()) and Python's datetime.now(timezone.utc) in
# the same clock, which matters for unread counts and message ordering.
_connect_args: dict[str, str] = {}
if settings.DATABASE_URL.startswith("mysql"):
    _connect_args["init_command"] = "SET time_zone = '+00:00'"

# DATABASE ENGINE
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    connect_args=_connect_args,
)


# CLOSE DATABASE CONNECTION
async def close_database_connection() -> None:
    await engine.dispose()
