"""Notification creation, listing and read state."""

from __future__ import annotations

import uuid

from tests.helpers import API


def test_sending_a_message_notifies_the_other_member(
    client, alice, bob, direct_conversation, send_message
):
    conversation = direct_conversation(alice, bob)
    message = send_message(alice, conversation["id"], "Ping!")

    inbox = client.get(f"{API}/notifications", headers=bob["headers"])
    assert inbox.status_code == 200
    page = inbox.json()
    assert page["unread_count"] == 1
    assert len(page["items"]) == 1

    notification = page["items"][0]
    assert notification["type"] == "message"
    assert notification["title"] == f"New message from {alice['username']}"
    assert notification["body"] == "Ping!"
    assert notification["is_read"] is False
    assert notification["read_at"] is None
    assert notification["data"]["conversation_id"] == conversation["id"]
    assert notification["data"]["message_id"] == message["id"]
    assert notification["data"]["sender_id"] == alice["user"]["id"]


def test_sender_does_not_receive_a_notification(
    client, alice, bob, direct_conversation, send_message
):
    conversation = direct_conversation(alice, bob)
    send_message(alice, conversation["id"], "No self notification")

    inbox = client.get(f"{API}/notifications", headers=alice["headers"]).json()
    assert inbox["items"] == []
    assert inbox["unread_count"] == 0


def test_unread_count_endpoint(
    client, alice, bob, direct_conversation, send_message
):
    conversation = direct_conversation(alice, bob)
    send_message(alice, conversation["id"], "One")
    send_message(alice, conversation["id"], "Two")

    response = client.get(
        f"{API}/notifications/unread-count",
        headers=bob["headers"],
    )

    assert response.status_code == 200
    assert response.json() == {"unread_count": 2}


def test_mark_one_notification_read(
    client, alice, bob, direct_conversation, send_message
):
    conversation = direct_conversation(alice, bob)
    send_message(alice, conversation["id"], "Read me")

    notification = client.get(
        f"{API}/notifications", headers=bob["headers"]
    ).json()["items"][0]

    response = client.post(
        f"{API}/notifications/{notification['id']}/read",
        headers=bob["headers"],
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["is_read"] is True
    assert body["read_at"] is not None

    count = client.get(
        f"{API}/notifications/unread-count", headers=bob["headers"]
    ).json()
    assert count["unread_count"] == 0

    # Marking it again is idempotent.
    again = client.post(
        f"{API}/notifications/{notification['id']}/read",
        headers=bob["headers"],
    )
    assert again.status_code == 200
    assert again.json()["is_read"] is True


def test_mark_all_notifications_read(
    client, alice, bob, direct_conversation, send_message
):
    conversation = direct_conversation(alice, bob)
    for index in range(3):
        send_message(alice, conversation["id"], f"Message {index}")

    response = client.post(f"{API}/notifications/read-all", headers=bob["headers"])

    assert response.status_code == 200, response.text
    assert response.json()["unread_count"] == 0

    inbox = client.get(f"{API}/notifications", headers=bob["headers"]).json()
    assert inbox["unread_count"] == 0
    assert all(item["is_read"] for item in inbox["items"])
    assert all(item["read_at"] is not None for item in inbox["items"])


def test_unread_only_filter_and_pagination(
    client, alice, bob, direct_conversation, send_message
):
    conversation = direct_conversation(alice, bob)
    ids = [send_message(alice, conversation["id"], f"Msg {i}")["id"] for i in range(3)]

    notifications = client.get(
        f"{API}/notifications", headers=bob["headers"]
    ).json()["items"]
    assert len(notifications) == 3

    client.post(
        f"{API}/notifications/{notifications[0]['id']}/read",
        headers=bob["headers"],
    )

    unread = client.get(
        f"{API}/notifications",
        headers=bob["headers"],
        params={"unread_only": True},
    ).json()
    assert unread["unread_count"] == 2
    assert len(unread["items"]) == 2
    assert all(not item["is_read"] for item in unread["items"])

    page = client.get(
        f"{API}/notifications",
        headers=bob["headers"],
        params={"limit": 2, "offset": 0},
    ).json()
    assert len(page["items"]) == 2
    assert page["unread_count"] == 2

    assert {
        item["data"]["message_id"] for item in notifications
    } == set(ids)


def test_cannot_mark_someone_elses_notification(
    client, alice, bob, direct_conversation, send_message
):
    conversation = direct_conversation(alice, bob)
    send_message(alice, conversation["id"], "Private notification")

    notification = client.get(
        f"{API}/notifications", headers=bob["headers"]
    ).json()["items"][0]

    response = client.post(
        f"{API}/notifications/{notification['id']}/read",
        headers=alice["headers"],
    )

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_unknown_notification_returns_404(client, alice):
    response = client.post(
        f"{API}/notifications/{uuid.uuid4()}/read",
        headers=alice["headers"],
    )

    assert response.status_code == 404
