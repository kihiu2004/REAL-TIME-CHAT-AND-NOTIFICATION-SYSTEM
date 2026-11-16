"""User profiles, search and profile validation."""

from __future__ import annotations

import uuid

from tests.helpers import API


def test_read_own_profile(client, alice):
    response = client.get(f"{API}/users/me", headers=alice["headers"])

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == alice["user"]["id"]
    assert body["username"] == alice["username"]
    assert body["email"] == alice["email"]
    assert body["profile_picture_url"] is None
    assert body["is_online"] is False
    assert "hashed_password" not in body


def test_update_profile(client, alice):
    response = client.patch(
        f"{API}/users/me",
        headers=alice["headers"],
        json={
            "full_name": "Ada Byron",
            "email": "ada.byron@example.com",
            "profile_picture_url": "https://example.com/ada.png",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["full_name"] == "Ada Byron"
    assert body["email"] == "ada.byron@example.com"
    assert body["profile_picture_url"] == "https://example.com/ada.png"

    refreshed = client.get(f"{API}/users/me", headers=alice["headers"]).json()
    assert refreshed["full_name"] == "Ada Byron"


def test_update_profile_can_clear_optional_fields(client, alice):
    client.patch(
        f"{API}/users/me",
        headers=alice["headers"],
        json={"profile_picture_url": "https://example.com/ada.png"},
    )

    response = client.patch(
        f"{API}/users/me",
        headers=alice["headers"],
        json={"profile_picture_url": None},
    )

    assert response.status_code == 200
    assert response.json()["profile_picture_url"] is None


def test_update_profile_rejects_taken_email(client, alice, bob):
    response = client.patch(
        f"{API}/users/me",
        headers=alice["headers"],
        json={"email": bob["email"]},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "conflict"


def test_update_profile_rejects_invalid_values(client, alice):
    blank_name = client.patch(
        f"{API}/users/me",
        headers=alice["headers"],
        json={"full_name": "   "},
    )
    assert blank_name.status_code == 422

    null_email = client.patch(
        f"{API}/users/me",
        headers=alice["headers"],
        json={"email": None},
    )
    assert null_email.status_code == 400

    bad_picture = client.patch(
        f"{API}/users/me",
        headers=alice["headers"],
        json={"profile_picture_url": "ftp://example.com/avatar.png"},
    )
    assert bad_picture.status_code == 422


def test_list_users_is_sorted_and_searchable(client, alice, bob, carol):
    response = client.get(f"{API}/users", headers=alice["headers"])

    assert response.status_code == 200
    usernames = [user["username"] for user in response.json()]
    assert usernames == sorted(usernames)
    assert {alice["username"], bob["username"], carol["username"]} <= set(usernames)

    found = client.get(
        f"{API}/users",
        headers=alice["headers"],
        params={"q": bob["username"]},
    ).json()
    assert [user["id"] for user in found] == [bob["user"]["id"]]

    by_name = client.get(
        f"{API}/users",
        headers=alice["headers"],
        params={"q": "Bob Tester"},
    ).json()
    assert bob["user"]["id"] in {user["id"] for user in by_name}


def test_list_users_supports_pagination(client, alice, bob, carol):
    response = client.get(
        f"{API}/users",
        headers=alice["headers"],
        params={"limit": 2, "offset": 0},
    )

    assert response.status_code == 200
    assert len(response.json()) <= 2

    invalid = client.get(
        f"{API}/users",
        headers=alice["headers"],
        params={"limit": 500},
    )
    assert invalid.status_code == 422


def test_read_user_by_id(client, alice, bob):
    response = client.get(
        f"{API}/users/{bob['user']['id']}",
        headers=alice["headers"],
    )

    assert response.status_code == 200
    assert response.json()["username"] == bob["username"]


def test_read_missing_user_returns_404(client, alice):
    response = client.get(
        f"{API}/users/{uuid.uuid4()}",
        headers=alice["headers"],
    )

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
