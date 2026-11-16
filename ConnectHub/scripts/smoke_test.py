"""End-to-end smoke test for the running API contract.

It creates a throwaway MySQL database, builds the schema from the SQLAlchemy
metadata, exercises the public REST + WebSocket surface, and then deletes the
database again.

    python scripts/smoke_test.py

Requires a running MySQL (XAMPP) and the DATABASE_URL credentials in .env.
The database name defaults to ``connecthub_test`` and can be overridden with
``SMOKE_TEST_DB``. Your real ``connecthub`` database is never touched.
"""

import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# The settings module reads DATABASE_URL at import time, so point it at a
# scratch database before anything from ``app`` is imported.
TEST_DB = os.getenv("SMOKE_TEST_DB", "connecthub_test")
BASE_URL = os.getenv(
    "SMOKE_TEST_DATABASE_URL",
    f"mysql+aiomysql://root:@localhost:3306/{TEST_DB}?charset=utf8mb4",
)
os.environ["DATABASE_URL"] = BASE_URL
os.environ.setdefault("DEBUG", "false")

from sqlalchemy import create_engine, text  # noqa: E402

import app.models  # noqa: E402,F401  (registers the models)
from app.database.base import Base  # noqa: E402
from app.database.connection import engine  # noqa: E402


def admin_url() -> str:
    parts = urlsplit(BASE_URL)
    return urlunsplit(parts._replace(path="/", query="")).replace(
        "+aiomysql", "+pymysql"
    )


def recreate_database() -> None:
    engine_ = create_engine(admin_url(), isolation_level="AUTOCOMMIT")
    with engine_.connect() as connection:
        connection.execute(text(f"DROP DATABASE IF EXISTS `{TEST_DB}`"))
        connection.execute(
            text(
                f"CREATE DATABASE `{TEST_DB}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )
    engine_.dispose()


def drop_database() -> None:
    engine_ = create_engine(admin_url(), isolation_level="AUTOCOMMIT")
    with engine_.connect() as connection:
        connection.execute(text(f"DROP DATABASE IF EXISTS `{TEST_DB}`"))
    engine_.dispose()


async def create_schema() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()


FAILURES: list[str] = []


def check(label: str, ok: bool, extra: object = "") -> None:
    suffix = f"  [{extra}]" if extra != "" else ""
    print(f"{'PASS' if ok else 'FAIL'} | {label}{suffix}")
    if not ok:
        FAILURES.append(label)


def run_checks() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        health = client.get("/health").json()
        check("health: database up", health["database"] == "up", health["status"])

        alice_resp = client.post(
            "/api/v1/auth/register",
            json={
                "username": "alice",
                "email": "alice@example.com",
                "full_name": "Alice Anderson",
                "password": "correct-horse-1",
            },
        )
        check("register alice -> 201", alice_resp.status_code == 201, alice_resp.status_code)
        alice = alice_resp.json()
        check("password hash is never returned", "hashed_password" not in alice["user"])

        bob_resp = client.post(
            "/api/v1/auth/register",
            json={
                "username": "bob",
                "email": "bob@example.com",
                "full_name": "Bob Brown",
                "password": "correct-horse-2",
            },
        )
        check("register bob -> 201", bob_resp.status_code == 201, bob_resp.status_code)
        bob = bob_resp.json()

        alice_token = alice["access_token"]
        bob_token = bob["access_token"]
        alice_h = {"Authorization": f"Bearer {alice_token}"}
        bob_h = {"Authorization": f"Bearer {bob_token}"}
        bob_id = bob["user"]["id"]

        duplicate = client.post(
            "/api/v1/auth/register",
            json={
                "username": "alice",
                "email": "other@example.com",
                "full_name": "Duplicate",
                "password": "whatever-123",
            },
        )
        check("duplicate username -> 409", duplicate.status_code == 409, duplicate.status_code)

        bad_login = client.post(
            "/api/v1/auth/login",
            json={"identifier": "alice", "password": "wrong-password"},
        )
        check("wrong password -> 401", bad_login.status_code == 401, bad_login.status_code)

        login = client.post(
            "/api/v1/auth/login",
            json={"identifier": "ALICE@example.com", "password": "correct-horse-1"},
        )
        check(
            "login by email (case-insensitive)",
            login.status_code == 200
            and login.json()["user"]["id"] == alice["user"]["id"],
            login.status_code,
        )

        me = client.get("/api/v1/auth/me", headers=alice_h)
        check("auth/me", me.status_code == 200 and me.json()["username"] == "alice")

        anonymous = client.get("/api/v1/conversations")
        check("missing token -> 401", anonymous.status_code == 401, anonymous.status_code)

        search = client.get("/api/v1/users", params={"q": "bob"}, headers=alice_h)
        check(
            "user search",
            search.status_code == 200
            and any(item["username"] == "bob" for item in search.json()),
        )

        conversation = client.post(
            "/api/v1/conversations",
            json={"type": "direct", "member_ids": [bob_id]},
            headers=alice_h,
        )
        check("create direct conversation -> 201", conversation.status_code == 201)
        conversation_id = conversation.json()["id"]
        check("direct conversation has 2 members", len(conversation.json()["members"]) == 2)

        again = client.post(
            "/api/v1/conversations",
            json={"type": "direct", "member_ids": [bob_id]},
            headers=alice_h,
        )
        check("direct conversation is idempotent", again.json()["id"] == conversation_id)

        sent = client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={"content": "hello bob"},
            headers=alice_h,
        )
        check("send message -> 201", sent.status_code == 201)
        message = sent.json()
        message_id = message["id"]
        check(
            "message includes sender and timestamp",
            message["sender"]["username"] == "alice" and bool(message["created_at"]),
        )

        notifications = client.get("/api/v1/notifications", headers=bob_h).json()
        check(
            "recipient gets one unread notification",
            notifications["unread_count"] == 1 and len(notifications["items"]) == 1,
            notifications["unread_count"],
        )

        bob_list = client.get("/api/v1/conversations", headers=bob_h).json()
        check("recipient unread count is 1", bob_list[0]["unread_count"] == 1, bob_list[0]["unread_count"])
        check("last message preview", bob_list[0]["last_message"]["content"] == "hello bob")

        history = client.get(
            f"/api/v1/conversations/{conversation_id}/messages", headers=bob_h
        ).json()
        check(
            "message history",
            len(history["items"]) == 1 and history["items"][0]["id"] == message_id,
        )

        garbage = client.get(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers={"Authorization": "Bearer nope"},
        )
        check("garbage token -> 401", garbage.status_code == 401, garbage.status_code)

        read = client.post(
            f"/api/v1/conversations/{conversation_id}/read",
            json={"message_id": message_id},
            headers=bob_h,
        )
        check("mark conversation read -> 200", read.status_code == 200, read.status_code)

        bob_after = client.get("/api/v1/conversations", headers=bob_h).json()
        check("unread cleared after read", bob_after[0]["unread_count"] == 0, bob_after[0]["unread_count"])

        notification_id = notifications["items"][0]["id"]
        marked = client.post(
            f"/api/v1/notifications/{notification_id}/read", headers=bob_h
        )
        check(
            "notification marked read",
            marked.status_code == 200 and marked.json()["is_read"] is True,
        )

        group = client.post(
            "/api/v1/conversations",
            json={"type": "group", "name": "Team", "member_ids": [bob_id]},
            headers=alice_h,
        )
        check("create group -> 201", group.status_code == 201)
        group_id = group.json()["id"]

        denied = client.patch(
            f"/api/v1/conversations/{group_id}", json={"name": "Hacked"}, headers=bob_h
        )
        check("member cannot rename group -> 403", denied.status_code == 403, denied.status_code)

        renamed = client.patch(
            f"/api/v1/conversations/{group_id}", json={"name": "Team 2"}, headers=alice_h
        )
        check("owner renames group", renamed.status_code == 200 and renamed.json()["name"] == "Team 2")

        edited = client.patch(
            f"/api/v1/messages/{message_id}",
            json={"content": "hello bob!"},
            headers=alice_h,
        )
        check("edit message", edited.status_code == 200 and edited.json()["is_edited"] is True)

        with client.websocket_connect(f"/ws?token={bob_token}") as bob_ws, (
            client.websocket_connect(f"/ws?token={alice_token}")
        ) as alice_ws:
            check("websocket ready (bob)", bob_ws.receive_json()["type"] == "connection.ready")
            check("websocket ready (alice)", alice_ws.receive_json()["type"] == "connection.ready")

            client.post(
                f"/api/v1/conversations/{conversation_id}/messages",
                json={"content": "realtime!"},
                headers=alice_h,
            )
            new_event = bob_ws.receive_json()
            check(
                "websocket message.new delivered",
                new_event["type"] == "message.new"
                and new_event["data"]["content"] == "realtime!",
                new_event["type"],
            )
            # The sender is a recipient too, so drain her own copy first.
            check(
                "websocket message.new echoed to sender",
                alice_ws.receive_json()["type"] == "message.new",
            )
            notification_event = bob_ws.receive_json()
            check(
                "websocket notification.new delivered",
                notification_event["type"] == "notification.new",
                notification_event["type"],
            )

            alice_ws.send_json(
                {"type": "typing.start", "data": {"conversation_id": conversation_id}}
            )
            typing = bob_ws.receive_json()
            check(
                "websocket typing relayed",
                typing["type"] == "typing"
                and typing["data"]["username"] == "alice"
                and typing["data"]["is_typing"] is True,
                typing["type"],
            )

            alice_ws.send_json({"type": "ping"})
            check("websocket ping/pong", alice_ws.receive_json()["type"] == "pong")

        deleted = client.delete(f"/api/v1/messages/{message_id}", headers=alice_h)
        check("delete message -> 204", deleted.status_code == 204, deleted.status_code)


def main() -> int:
    recreate_database()
    try:
        asyncio.run(create_schema())
        run_checks()
    finally:
        drop_database()

    if FAILURES:
        print(f"\n{len(FAILURES)} CHECK(S) FAILED")
        for label in FAILURES:
            print(f"  - {label}")
        return 1

    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
