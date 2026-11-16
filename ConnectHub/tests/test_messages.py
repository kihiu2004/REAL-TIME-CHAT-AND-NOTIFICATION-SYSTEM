"""Messages: sending, pagination, replies, edits, deletes and read state."""

from __future__ import annotations

import uuid

from tests.helpers import API


def test_send_and_fetch_message(client, alice, bob, direct_conversation):
    conversation = direct_conversation(alice, bob)

    sent = client.post(
        f"{API}/conversations/{conversation['id']}/messages",
        headers=alice["headers"],
        json={"content": "  Hello Bob!  "},
    )

    assert sent.status_code == 201, sent.text
    message = sent.json()
    assert message["content"] == "Hello Bob!"
    assert message["conversation_id"] == conversation["id"]
    assert message["sender"]["id"] == alice["user"]["id"]
    assert message["message_type"] == "text"
    assert message["is_edited"] is False

    history = client.get(
        f"{API}/conversations/{conversation['id']}/messages",
        headers=bob["headers"],
    )
    assert history.status_code == 200
    body = history.json()
    assert [item["id"] for item in body["items"]] == [message["id"]]
    assert body["has_more"] is False
    assert body["next_before"] is None


def test_message_validation(client, alice, bob, direct_conversation):
    conversation = direct_conversation(alice, bob)
    path = f"{API}/conversations/{conversation['id']}/messages"

    for payload in (
        {"content": ""},
        {"content": "   "},
        {"content": "x" * 4001},
        {},
    ):
        response = client.post(path, headers=alice["headers"], json=payload)
        assert response.status_code == 422, (payload, response.text)


def test_non_members_cannot_read_or_send(client, alice, bob, carol, direct_conversation):
    conversation = direct_conversation(alice, bob)
    path = f"{API}/conversations/{conversation['id']}/messages"

    assert client.get(path, headers=carol["headers"]).status_code == 403
    assert (
        client.post(
            path,
            headers=carol["headers"],
            json={"content": "Intruder"},
        ).status_code
        == 403
    )


def test_messages_are_paginated_newest_first(client, alice, bob, direct_conversation):
    conversation = direct_conversation(alice, bob)
    path = f"{API}/conversations/{conversation['id']}/messages"

    created = []
    for index in range(5):
        response = client.post(
            path,
            headers=alice["headers"],
            json={"content": f"Message {index}"},
        )
        assert response.status_code == 201, response.text
        created.append(response.json())

    first_page = client.get(path, headers=bob["headers"], params={"limit": 2})
    assert first_page.status_code == 200
    page = first_page.json()
    assert len(page["items"]) == 2
    assert page["has_more"] is True
    assert page["next_before"]

    received = list(page["items"])
    cursor = page["next_before"]
    for _ in range(3):
        response = client.get(
            path,
            headers=bob["headers"],
            params={"limit": 2, "before": cursor},
        )
        assert response.status_code == 200, response.text
        page = response.json()
        received.extend(page["items"])
        if not page["has_more"]:
            break
        cursor = page["next_before"]

    assert {item["id"] for item in received} == {item["id"] for item in created}
    created_at = [item["created_at"] for item in received]
    assert created_at == sorted(created_at, reverse=True)


def test_reply_to_message(client, alice, bob, direct_conversation, send_message):
    conversation = direct_conversation(alice, bob)
    original = send_message(alice, conversation["id"], "Original")

    reply = client.post(
        f"{API}/conversations/{conversation['id']}/messages",
        headers=bob["headers"],
        json={"content": "Replying", "reply_to_id": original["id"]},
    )

    assert reply.status_code == 201, reply.text
    assert reply.json()["reply_to_id"] == original["id"]


def test_reply_must_belong_to_the_same_conversation(
    client, alice, bob, carol, direct_conversation, send_message
):
    first = direct_conversation(alice, bob)
    second = direct_conversation(alice, carol)
    original = send_message(alice, first["id"], "Elsewhere")

    response = client.post(
        f"{API}/conversations/{second['id']}/messages",
        headers=alice["headers"],
        json={"content": "Wrong thread", "reply_to_id": original["id"]},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "bad_request"


def test_edit_own_message(client, alice, bob, direct_conversation, send_message):
    conversation = direct_conversation(alice, bob)
    message = send_message(alice, conversation["id"], "Typo")

    response = client.patch(
        f"{API}/messages/{message['id']}",
        headers=alice["headers"],
        json={"content": "Fixed"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["content"] == "Fixed"
    assert body["is_edited"] is True
    assert body["edited_at"] is not None


def test_cannot_edit_someone_elses_message(
    client, alice, bob, direct_conversation, send_message
):
    conversation = direct_conversation(alice, bob)
    message = send_message(alice, conversation["id"], "Mine")

    response = client.patch(
        f"{API}/messages/{message['id']}",
        headers=bob["headers"],
        json={"content": "Hijacked"},
    )

    assert response.status_code == 403


def test_edit_requires_membership(
    client, alice, bob, carol, direct_conversation, send_message
):
    conversation = direct_conversation(alice, bob)
    message = send_message(alice, conversation["id"], "Private")

    response = client.patch(
        f"{API}/messages/{message['id']}",
        headers=carol["headers"],
        json={"content": "Peeking"},
    )

    assert response.status_code == 403


def test_delete_own_message(client, alice, bob, direct_conversation, send_message):
    conversation = direct_conversation(alice, bob)
    message = send_message(alice, conversation["id"], "Delete me")

    response = client.delete(
        f"{API}/messages/{message['id']}",
        headers=alice["headers"],
    )
    assert response.status_code == 204

    history = client.get(
        f"{API}/conversations/{conversation['id']}/messages",
        headers=bob["headers"],
    ).json()
    assert history["items"] == []


def test_group_owner_can_delete_any_message(
    client, alice, bob, group_conversation, send_message
):
    group = group_conversation(alice, [bob])
    message = send_message(bob, group["id"], "Bob wrote this")

    response = client.delete(
        f"{API}/messages/{message['id']}",
        headers=alice["headers"],
    )

    assert response.status_code == 204


def test_regular_member_cannot_delete_someone_elses_message(
    client, alice, bob, carol, group_conversation, send_message
):
    group = group_conversation(alice, [bob, carol])
    message = send_message(alice, group["id"], "Owner's message")

    response = client.delete(
        f"{API}/messages/{message['id']}",
        headers=carol["headers"],
    )

    assert response.status_code == 403


def test_missing_message_returns_404(client, alice):
    response = client.patch(
        f"{API}/messages/{uuid.uuid4()}",
        headers=alice["headers"],
        json={"content": "Nothing"},
    )

    assert response.status_code == 404


def test_unread_count_and_mark_read(
    client, alice, bob, direct_conversation, send_message
):
    conversation = direct_conversation(alice, bob)
    send_message(alice, conversation["id"], "First")
    send_message(alice, conversation["id"], "Second")

    bob_list = client.get(f"{API}/conversations", headers=bob["headers"]).json()
    assert bob_list[0]["unread_count"] == 2
    assert bob_list[0]["last_message"]["content"] == "Second"

    read = client.post(
        f"{API}/conversations/{conversation['id']}/read",
        headers=bob["headers"],
        json={"message_id": None},
    )
    assert read.status_code == 200, read.text
    assert read.json()["last_read_at"]

    bob_list = client.get(f"{API}/conversations", headers=bob["headers"]).json()
    assert bob_list[0]["unread_count"] == 0

    # Alice still sees no unread messages: her own messages never count.
    alice_list = client.get(f"{API}/conversations", headers=alice["headers"]).json()
    assert alice_list[0]["unread_count"] == 0


def test_mark_read_rejects_foreign_message(
    client, alice, bob, carol, direct_conversation, send_message
):
    conversation = direct_conversation(alice, bob)
    other = direct_conversation(alice, carol)
    message = send_message(alice, other["id"], "Not for Bob")

    response = client.post(
        f"{API}/conversations/{conversation['id']}/read",
        headers=bob["headers"],
        json={"message_id": message["id"]},
    )

    assert response.status_code == 404
