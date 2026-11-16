"""Create demo accounts so you can try conversations locally.

    python scripts/seed_demo_users.py

Safe to re-run: usernames that already exist are skipped. Every demo account
uses the same password, printed at the end.

The app's "New conversation" dialog lists other registered users, so it stays
empty until at least one more account exists.
"""

import asyncio
import sys
from pathlib import Path

# Allow "python scripts/seed_demo_users.py" from the ConnectHub folder
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import or_, select  # noqa: E402

from app.database.connection import engine  # noqa: E402
from app.database.session import asyncSessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.schemas.auth import RegisterRequest  # noqa: E402
from app.services.auth_service import register_user  # noqa: E402

DEMO_PASSWORD = "Password123!"

DEMO_USERS = [
    ("alice", "alice@example.com", "Alice Wanjiku"),
    ("brian", "brian@example.com", "Brian Otieno"),
    ("grace", "grace@example.com", "Grace Muthoni"),
]


async def seed() -> None:
    created: list[str] = []
    skipped: list[str] = []

    async with asyncSessionLocal() as db:
        for username, email, full_name in DEMO_USERS:
            existing = (
                await db.execute(
                    select(User).where(
                        or_(User.username == username, User.email == email)
                    )
                )
            ).scalars().first()

            if existing is not None:
                skipped.append(username)
                print(f"skip   {username} (already exists)")
                continue

            await register_user(
                db,
                RegisterRequest(
                    username=username,
                    email=email,
                    full_name=full_name,
                    password=DEMO_PASSWORD,
                ),
            )
            created.append(username)
            print(f"added  {username}  ({full_name} <{email}>)")

    await engine.dispose()

    print()
    print(f"{len(created)} account(s) created, {len(skipped)} already present.")
    if created:
        print("Log in as any of them with:")
        print(f"  password: {DEMO_PASSWORD}")
        for username in created:
            print(f"  username: {username}")


if __name__ == "__main__":
    asyncio.run(seed())
