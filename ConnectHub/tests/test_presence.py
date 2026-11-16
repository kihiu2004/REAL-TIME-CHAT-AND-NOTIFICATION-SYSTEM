"""Presence: in-process fallback store and WebSocket-driven online state."""

from __future__ import annotations

import asyncio
import time

import pytest

from app.redis import presence_manager
from tests.helpers import API


@pytest.fixture(autouse=True)
def _clean_presence():
    """Each test starts from an empty in-memory presence store."""
    presence_manager._memory.clear()
    yield
    presence_manager._memory.clear()


def test_mark_online_and_offline():
    asyncio.run(presence_manager.mark_online("user-1"))
    assert asyncio.run(presence_manager.is_online("user-1")) is True

    asyncio.run(presence_manager.mark_offline("user-1"))
    assert asyncio.run(presence_manager.is_online("user-1")) is False


def test_heartbeat_refreshes_the_last_seen_timestamp():
    presence_manager._memory["user-1"] = time.time() - presence_manager.PRESENCE_TTL_SECONDS + 5
    assert asyncio.run(presence_manager.is_online("user-1")) is True

    asyncio.run(presence_manager.refresh("user-1"))

    remaining = (
        presence_manager.PRESENCE_TTL_SECONDS - (time.time() - presence_manager._memory["user-1"])
    )
    assert remaining > presence_manager.PRESENCE_TTL_SECONDS - 5


def test_stale_presence_expires():
    presence_manager._memory["user-1"] = (
        time.time() - presence_manager.PRESENCE_TTL_SECONDS - 1
    )
    assert asyncio.run(presence_manager.is_online("user-1")) is False


def test_is_online_many_returns_every_requested_user():
    asyncio.run(presence_manager.mark_online("user-1"))

    result = asyncio.run(
        presence_manager.is_online_many(["user-1", "user-2", "user-3"])
    )

    assert result == {"user-1": True, "user-2": False, "user-3": False}
    assert asyncio.run(presence_manager.is_online_many([])) == {}


def test_websocket_connections_update_the_user_record(client, alice):
    with client.websocket_connect(f"/ws?token={alice['token']}") as socket:
        socket.receive_json()  # connection.ready is sent after mark_online commits

        online = client.get(f"{API}/users/me", headers=alice["headers"])
        assert online.status_code == 200
        assert online.json()["is_online"] is True
        assert online.json()["last_seen_at"] is not None

    # The disconnect path is covered by the presence-manager unit tests above.
    # (TestClient tears the ASGI task down as soon as the context exits, so the
    # server's finally block is not guaranteed to finish here.)
