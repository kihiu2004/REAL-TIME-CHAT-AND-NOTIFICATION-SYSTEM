"""Conversation creation, membership and group management."""

from __future__ import annotations

import uuid

from tests.helpers import API


def test_create_direct_conversation(client, alice, bob):
    response = client.post(
        f"{API}/conversations",
        headers=alice["headers"],
        json={"type": "direct", "member_ids": [bob["user"]["id"]]},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["type"] == "direct"
    assert body["name"] is None
    assert body["created_by"] == alice["user"]["id"]
    members = {member["user"]["id"]: member for member in body["members"]}
    assert set(members) == {alice["user"]["id"], bob["user"]["id"]}
    assert members[alice["user"]["id"]]["role"] == "owner"
    assert members[bob["user"]["id"]]["role"] == "member"
    assert members[alice["user"]["id"]]["last_read_at"] is not None


def test_direct_conversation_is_reused(client, alice, bob):
    first = client.post(
        f"{API}/conversations",
        headers=alice["headers"],
        json={"type": "direct", "member_ids": [bob["user"]["id"]]},
    ).json()

    second = client.post(
        f"{API}/conversations",
        headers=bob["headers"],
        json={"type": "direct", "member_ids": [alice["user"]["id"]]},
    ).json()

    assert first["id"] == second["id"]


def test_direct_conversation_requires_exactly_one_peer(client, alice, bob, carol):
    too_many = client.post(
        f"{API}/conversations",
        headers=alice["headers"],
        json={
            "type": "direct",
            "member_ids": [bob["user"]["id"], carol["user"]["id"]],
        },
    )
    assert too_many.status_code == 422

    empty = client.post(
        f"{API}/conversations",
        headers=alice["headers"],
        json={"type": "direct", "member_ids": []},
    )
    assert empty.status_code == 422


def test_direct_conversation_cannot_have_a_name(client, alice, bob):
    response = client.post(
        f"{API}/conversations",
        headers=alice["headers"],
        json={
            "type": "direct",
            "name": "Should fail",
            "member_ids": [bob["user"]["id"]],
        },
    )

    assert response.status_code == 422


def test_create_group_conversation(client, alice, bob, carol):
    response = client.post(
        f"{API}/conversations",
        headers=alice["headers"],
        json={
            "type": "group",
            "name": "  Project Team  ",
            "member_ids": [bob["user"]["id"], carol["user"]["id"]],
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["type"] == "group"
    assert body["name"] == "Project Team"
    roles = {member["user"]["id"]: member["role"] for member in body["members"]}
    assert roles[alice["user"]["id"]] == "owner"
    assert roles[bob["user"]["id"]] == "member"
    assert roles[carol["user"]["id"]] == "member"


def test_group_conversation_requires_a_name(client, alice, bob):
    for name in (None, "", "   "):
        response = client.post(
            f"{API}/conversations",
            headers=alice["headers"],
            json={
                "type": "group",
                "name": name,
                "member_ids": [bob["user"]["id"]],
            },
        )
        assert response.status_code == 422, response.text


def test_create_conversation_rejects_unknown_members(client, alice):
    response = client.post(
        f"{API}/conversations",
        headers=alice["headers"],
        json={"type": "direct", "member_ids": [str(uuid.uuid4())]},
    )

    assert response.status_code == 400
    assert "do not exist" in response.json()["detail"]


def test_list_conversations_only_returns_memberships(client, alice, bob, carol):
    direct = client.post(
        f"{API}/conversations",
        headers=alice["headers"],
        json={"type": "direct", "member_ids": [bob["user"]["id"]]},
    ).json()

    alice_list = client.get(f"{API}/conversations", headers=alice["headers"]).json()
    bob_list = client.get(f"{API}/conversations", headers=bob["headers"]).json()
    carol_list = client.get(f"{API}/conversations", headers=carol["headers"]).json()

    assert [item["id"] for item in alice_list] == [direct["id"]]
    assert [item["id"] for item in bob_list] == [direct["id"]]
    assert carol_list == []

    listed = alice_list[0]
    assert listed["last_message"] is None
    assert listed["unread_count"] == 0


def test_get_conversation_requires_membership(client, alice, bob, carol):
    conversation = client.post(
        f"{API}/conversations",
        headers=alice["headers"],
        json={"type": "direct", "member_ids": [bob["user"]["id"]]},
    ).json()

    member_view = client.get(
        f"{API}/conversations/{conversation['id']}",
        headers=bob["headers"],
    )
    assert member_view.status_code == 200

    outsider_view = client.get(
        f"{API}/conversations/{conversation['id']}",
        headers=carol["headers"],
    )
    assert outsider_view.status_code == 403

    missing = client.get(
        f"{API}/conversations/{uuid.uuid4()}",
        headers=alice["headers"],
    )
    assert missing.status_code == 404


def test_only_managers_can_rename_a_group(
    client, alice, bob, group_conversation
):
    group = group_conversation(alice, [bob], name="Old name")

    renamed = client.patch(
        f"{API}/conversations/{group['id']}",
        headers=alice["headers"],
        json={"name": "New name"},
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["name"] == "New name"

    forbidden = client.patch(
        f"{API}/conversations/{group['id']}",
        headers=bob["headers"],
        json={"name": "Hijacked"},
    )
    assert forbidden.status_code == 403

    outsider = client.patch(
        f"{API}/conversations/{group['id']}",
        headers=bob["headers"],
        json={"name": ""},
    )
    assert outsider.status_code == 422


def test_direct_conversations_cannot_be_renamed(
    client, alice, bob, direct_conversation
):
    direct = direct_conversation(alice, bob)

    response = client.patch(
        f"{API}/conversations/{direct['id']}",
        headers=alice["headers"],
        json={"name": "Not a group"},
    )

    assert response.status_code == 400


def test_add_member_to_group(client, alice, bob, carol, group_conversation):
    group = group_conversation(alice, [bob])

    response = client.post(
        f"{API}/conversations/{group['id']}/members",
        headers=alice["headers"],
        json={"user_id": carol["user"]["id"]},
    )

    assert response.status_code == 201, response.text
    member_ids = {member["user"]["id"] for member in response.json()["members"]}
    assert member_ids == {
        alice["user"]["id"],
        bob["user"]["id"],
        carol["user"]["id"],
    }

    # Carol can now see the group and its history.
    carol_view = client.get(
        f"{API}/conversations/{group['id']}",
        headers=carol["headers"],
    )
    assert carol_view.status_code == 200


def test_add_member_validation(client, alice, bob, carol, group_conversation):
    group = group_conversation(alice, [bob])
    path = f"{API}/conversations/{group['id']}/members"

    already_member = client.post(
        path,
        headers=alice["headers"],
        json={"user_id": bob["user"]["id"]},
    )
    assert already_member.status_code == 409

    missing_user = client.post(
        path,
        headers=alice["headers"],
        json={"user_id": str(uuid.uuid4())},
    )
    assert missing_user.status_code == 404

    non_manager = client.post(
        path,
        headers=bob["headers"],
        json={"user_id": carol["user"]["id"]},
    )
    assert non_manager.status_code == 403

    direct = client.post(
        f"{API}/conversations",
        headers=alice["headers"],
        json={"type": "direct", "member_ids": [bob["user"]["id"]]},
    ).json()
    direct_add = client.post(
        f"{API}/conversations/{direct['id']}/members",
        headers=alice["headers"],
        json={"user_id": carol["user"]["id"]},
    )
    assert direct_add.status_code == 400


def test_members_can_leave_and_managers_can_remove(
    client, alice, bob, carol, group_conversation
):
    group = group_conversation(alice, [bob, carol])

    leave = client.delete(
        f"{API}/conversations/{group['id']}/members/{carol['user']['id']}",
        headers=carol["headers"],
    )
    assert leave.status_code == 204
    assert client.get(
        f"{API}/conversations/{group['id']}", headers=carol["headers"]
    ).status_code == 403

    owner_removes = client.delete(
        f"{API}/conversations/{group['id']}/members/{bob['user']['id']}",
        headers=alice["headers"],
    )
    assert owner_removes.status_code == 204

    owner_cannot_be_removed = client.delete(
        f"{API}/conversations/{group['id']}/members/{alice['user']['id']}",
        headers=bob["headers"],
    )
    # Bob is no longer a member, so he is rejected before the owner rule.
    assert owner_cannot_be_removed.status_code == 403

    outsider = client.delete(
        f"{API}/conversations/{group['id']}/members/{alice['user']['id']}",
        headers=carol["headers"],
    )
    assert outsider.status_code == 403
