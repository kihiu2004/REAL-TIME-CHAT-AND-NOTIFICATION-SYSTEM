"""Realtime channel: authentication, events and fan-out over /ws."""

from __future__ import annotations

import pytest
from starlette.websockets import WebSocketDisconnect

from tests.helpers import API


def _ready(socket) -> dict:
    event = socket.receive_json()
    assert event["type"] == "connection.ready", event
    return event


def test_websocket_without_a_token_is_rejected(client):
    with pytest.raises(WebSocketDisconnect) as closed:
        with client.websocket_connect("/ws") as socket:
            socket.receive_json()

    assert closed.value.code == 4401


def test_websocket_with_an_invalid_token_is_rejected(client):
    with pytest.raises(WebSocketDisconnect) as closed:
        with client.websocket_connect("/ws?token=not-a-real-token") as socket:
            socket.receive_json()

    assert closed.value.code == 4401


def test_connection_ready_identifies_the_user(client, alice):
    with client.websocket_connect(f"/ws?token={alice['token']}") as socket:
        event = _ready(socket)

    assert event["data"]["user_id"] == alice["user"]["id"]


def test_ping_gets_a_pong(client, alice):
    with client.websocket_connect(f"/ws?token={alice['token']}") as socket:
        _ready(socket)

        socket.send_json({"type": "ping"})

        assert socket.receive_json()["type"] == "pong"


def test_malformed_frames_return_errors(client, alice):
    with client.websocket_connect(f"/ws?token={alice['token']}") as socket:
        _ready(socket)

        socket.send_text("this is not json")
        invalid_json = socket.receive_json()
        assert invalid_json["type"] == "error"
        assert invalid_json["data"]["code"] == "invalid_json"

        socket.send_json([1, 2, 3])
        invalid_payload = socket.receive_json()
        assert invalid_payload["type"] == "error"
        assert invalid_payload["data"]["code"] == "invalid_payload"

        socket.send_json({"type": "does.not.exist"})
        unknown = socket.receive_json()
        assert unknown["type"] == "error"
        assert unknown["data"]["code"] == "unknown_event"


def test_message_send_is_delivered_and_notified(
    client, alice, bob, direct_conversation
):
    conversation = direct_conversation(alice, bob)

    with client.websocket_connect(
        f"/ws?token={alice['token']}"
    ) as alice_socket, client.websocket_connect(
        f"/ws?token={bob['token']}"
    ) as bob_socket:
        _ready(alice_socket)
        _ready(bob_socket)

        alice_socket.send_json(
            {
                "type": "message.send",
                "data": {
                    "conversation_id": conversation["id"],
                    "content": "  sent over the socket  ",
                },
            }
        )

        sender_event = alice_socket.receive_json()
        assert sender_event["type"] == "message.new"
        assert sender_event["data"]["content"] == "sent over the socket"
        assert sender_event["data"]["sender"]["id"] == alice["user"]["id"]

        recipient_event = bob_socket.receive_json()
        assert recipient_event["type"] == "message.new"
        assert recipient_event["data"]["id"] == sender_event["data"]["id"]

        notification = bob_socket.receive_json()
        assert notification["type"] == "notification.new"
        assert notification["data"]["data"]["conversation_id"] == conversation["id"]

    history = client.get(
        f"{API}/conversations/{conversation['id']}/messages",
        headers=bob["headers"],
    ).json()
    assert [item["content"] for item in history["items"]] == ["sent over the socket"]


def test_message_send_validates_the_payload(client, alice, bob, direct_conversation):
    conversation = direct_conversation(alice, bob)

    with client.websocket_connect(f"/ws?token={alice['token']}") as socket:
        _ready(socket)

        socket.send_json(
            {
                "type": "message.send",
                "data": {"conversation_id": conversation["id"], "content": "   "},
            }
        )
        event = socket.receive_json()

        assert event["type"] == "error"
        assert event["data"]["code"] == "validation_error"

        socket.send_json(
            {
                "type": "message.send",
                "data": {"conversation_id": "not-a-uuid", "content": "hello"},
            }
        )
        bad_id = socket.receive_json()

        assert bad_id["type"] == "error"
        assert bad_id["data"]["code"] == "bad_request"


def test_typing_is_relayed_to_the_other_member(
    client, alice, bob, direct_conversation
):
    conversation = direct_conversation(alice, bob)

    with client.websocket_connect(
        f"/ws?token={alice['token']}"
    ) as alice_socket, client.websocket_connect(
        f"/ws?token={bob['token']}"
    ) as bob_socket:
        _ready(alice_socket)
        _ready(bob_socket)

        alice_socket.send_json(
            {"type": "typing.start", "data": {"conversation_id": conversation["id"]}}
        )
        started = bob_socket.receive_json()
        assert started["type"] == "typing"
        assert started["data"]["user_id"] == alice["user"]["id"]
        assert started["data"]["username"] == alice["username"]
        assert started["data"]["is_typing"] is True

        alice_socket.send_json(
            {"type": "typing.stop", "data": {"conversation_id": conversation["id"]}}
        )
        stopped = bob_socket.receive_json()
        assert stopped["type"] == "typing"
        assert stopped["data"]["is_typing"] is False


def test_outsiders_get_a_forbidden_error(client, alice, bob, carol, direct_conversation):
    conversation = direct_conversation(alice, bob)

    with client.websocket_connect(f"/ws?token={carol['token']}") as socket:
        _ready(socket)

        socket.send_json(
            {"type": "typing.start", "data": {"conversation_id": conversation["id"]}}
        )
        event = socket.receive_json()

    assert event["type"] == "error"
    assert event["data"]["code"] == "forbidden"


def test_read_receipts_are_relayed(client, alice, bob, direct_conversation, send_message):
    conversation = direct_conversation(alice, bob)
    message = send_message(alice, conversation["id"], "Read me")

    with client.websocket_connect(
        f"/ws?token={alice['token']}"
    ) as alice_socket, client.websocket_connect(
        f"/ws?token={bob['token']}"
    ) as bob_socket:
        _ready(alice_socket)
        _ready(bob_socket)

        bob_socket.send_json(
            {
                "type": "message.read",
                "data": {
                    "conversation_id": conversation["id"],
                    "message_id": message["id"],
                },
            }
        )

        receipt = alice_socket.receive_json()
        assert receipt["type"] == "message.read"
        assert receipt["data"]["conversation_id"] == conversation["id"]
        assert receipt["data"]["user_id"] == bob["user"]["id"]
        assert receipt["data"]["last_read_at"]

    listed = client.get(f"{API}/conversations", headers=bob["headers"]).json()
    assert listed[0]["unread_count"] == 0
