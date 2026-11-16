"""Authentication: registration, login and token enforcement."""

from __future__ import annotations

import uuid

from tests.helpers import API, PASSWORD


def test_register_returns_token_and_safe_profile(client):
    payload = {
        "username": "ada",
        "email": "ada@example.com",
        "full_name": "Ada Lovelace",
        "password": PASSWORD,
    }

    response = client.post(f"{API}/auth/register", json=payload)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["username"] == "ada"
    assert body["user"]["email"] == "ada@example.com"
    assert body["user"]["account_status"] == "active"
    assert "hashed_password" not in body["user"]
    assert "password" not in body["user"]


def test_register_normalises_username_and_email(client):
    response = client.post(
        f"{API}/auth/register",
        json={
            "username": "  MiXeD.Case  ",
            "email": "MiXeD@Example.COM",
            "full_name": "  Mixed Case  ",
            "password": PASSWORD,
        },
    )

    assert response.status_code == 201, response.text
    user = response.json()["user"]
    assert user["username"] == "mixed.case"
    assert user["email"] == "mixed@example.com"
    assert user["full_name"] == "Mixed Case"


def test_register_rejects_duplicate_username(client):
    first = {
        "username": "duplicate",
        "email": "first@example.com",
        "full_name": "First",
        "password": PASSWORD,
    }
    assert client.post(f"{API}/auth/register", json=first).status_code == 201

    second = {**first, "email": "second@example.com"}
    response = client.post(f"{API}/auth/register", json=second)

    assert response.status_code == 409
    assert "already registered" in response.json()["detail"]


def test_register_rejects_duplicate_email(client):
    first = {
        "username": "emailone",
        "email": "shared@example.com",
        "full_name": "One",
        "password": PASSWORD,
    }
    assert client.post(f"{API}/auth/register", json=first).status_code == 201

    second = {**first, "username": "emailtwo"}
    response = client.post(f"{API}/auth/register", json=second)

    assert response.status_code == 409


def test_register_validates_fields(client):
    invalid_password = {
        "username": "shortpass",
        "email": "shortpass@example.com",
        "full_name": "Short Pass",
        "password": "1234567",
    }
    assert client.post(f"{API}/auth/register", json=invalid_password).status_code == 422

    invalid_username = {
        "username": "not allowed!",
        "email": "badname@example.com",
        "full_name": "Bad Name",
        "password": PASSWORD,
    }
    assert client.post(f"{API}/auth/register", json=invalid_username).status_code == 422

    invalid_email = {
        "username": "badmail",
        "email": "not-an-email",
        "full_name": "Bad Mail",
        "password": PASSWORD,
    }
    assert client.post(f"{API}/auth/register", json=invalid_email).status_code == 422


def test_login_accepts_username_or_email(client, alice):
    for identifier in (alice["username"], alice["email"]):
        response = client.post(
            f"{API}/auth/login",
            json={"identifier": identifier, "password": alice["password"]},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["user"]["id"] == alice["user"]["id"]
        assert body["access_token"]


def test_login_rejects_wrong_password(client, alice):
    response = client.post(
        f"{API}/auth/login",
        json={"identifier": alice["username"], "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_login_rejects_unknown_account(client):
    response = client.post(
        f"{API}/auth/login",
        json={"identifier": "nobody-here", "password": PASSWORD},
    )

    assert response.status_code == 401


def test_protected_routes_require_a_token(client):
    for path in (
        f"{API}/users/me",
        f"{API}/users",
        f"{API}/conversations",
        f"{API}/notifications",
    ):
        assert client.get(path).status_code == 401


def test_invalid_token_is_rejected(client):
    response = client.get(
        f"{API}/users/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401


def test_valid_token_identifies_the_user(client, alice):
    response = client.get(f"{API}/users/me", headers=alice["headers"])

    assert response.status_code == 200
    assert response.json()["id"] == alice["user"]["id"]


def test_unknown_bearer_subject_is_rejected(client):
    from app.core.jwt import create_access_token

    token = create_access_token(uuid.uuid4())
    response = client.get(
        f"{API}/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_health_is_public(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["database"] == "up"
