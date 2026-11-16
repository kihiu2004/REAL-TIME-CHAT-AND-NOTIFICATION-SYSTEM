"""Create every table directly from the SQLAlchemy metadata.

Useful for a quick local setup when you do not want to run Alembic:

    python scripts/init_db.py

The versioned path (preferred) is:

    alembic upgrade head
"""

import asyncio
import sys
from pathlib import Path

# Allow "python scripts/init_db.py" from the ConnectHub folder
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: E402,F401  (registers the models)
from app.database.base import Base  # noqa: E402
from app.database.connection import engine  # noqa: E402


async def create_tables() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print(f"Created {len(Base.metadata.tables)} tables: "
          + ", ".join(sorted(Base.metadata.tables)))


if __name__ == "__main__":
    asyncio.run(create_tables())
