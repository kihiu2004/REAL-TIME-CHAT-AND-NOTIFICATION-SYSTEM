from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database.connection import engine

# ASYNCHRONOUS DATABASE SESSION FACTORY
asyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# DATABASE DEPENDENCY THAT PROVIDES AN ASYNC SESSION TO FASTAPI ROUTES
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with asyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
