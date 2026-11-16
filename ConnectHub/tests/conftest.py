"""Shared pytest fixtures for the ConnectHub API.

The suite runs the real FastAPI application and the real SQLAlchemy models,
but against a throwaway SQLite database (``aiosqlite``) so it needs neither
MySQL nor Redis. The database file lives inside ``tests/``, is created once
per session, and every table is emptied after each test.

The production configuration is untouched: ``DATABASE_URL`` is overridden in
the environment *before* ``app.config`` is imported.
"""

from __future__ import annotations

import os
import sys
import uuid
from itertools import count
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_DB_PATH = ROOT / "tests" / ".pytest_connecthub.db"

# Settings read the environment at import time, so override everything that
# would otherwise point at a real service.
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["REDIS_URL"] = "redis://127.0.0.1:1/0"
os.environ["DEBUG"] = "false"
os.environ["ENVIRONMENT"] = "test"
# bcrypt is deliberately expensive; a low cost keeps the suite fast while
# still exercising the real hashing/verification path.
os.environ["BCRYPT_ROUNDS"] = "4"
os.environ.setdefault("JWT_SECRET_KEY", "pytest-secret-key-not-for-production")

from tests.helpers import API, PASSWORD  # noqa: E402

import app.models  # noqa: E402,F401  (registers every mapper)
from app.database.base import Base  # noqa: E402

SYNC_DB_URL = f"sqlite:///{TEST_DB_PATH.as_posix()}"


def _remove_database_files() -> None:
    for suffix in ("", "-wal", "-shm"):
        path = TEST_DB_PATH.with_name(TEST_DB_PATH.name + suffix)
        path.unlink(missing_ok=True)


@pytest.fixture(scope="session", autouse=True)
def _database_schema():
    _remove_database_files()
    engine = create_engine(SYNC_DB_URL)
    Base.metadata.create_all(engine)
    engine.dispose()
    try:
        yield
    finally:
        _remove_database_files()


@pytest.fixture(autouse=True)
def _clean_tables(_database_schema):
    """Empty every table between tests so cases stay independent."""
    yield

    engine = create_engine(SYNC_DB_URL)
    try:
        with engine.begin() as connection:
            connection.execute(text("PRAGMA foreign_keys=OFF"))
            for table in reversed(Base.metadata.sorted_tables):
                connection.execute(table.delete())
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def client(_database_schema):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_user(client):
    """Register a fresh account and return its token, profile and headers."""
    sequence = count(1)

    def _make_user(prefix: str = "user", password: str = PASSWORD) -> dict:
        number = next(sequence)
        username = f"{prefix}{number}{uuid.uuid4().hex[:8]}"[:50]
        email = f"{username}@example.com"
        payload = {
            "username": username,
            "email": email,
            "full_name": f"{prefix.title()} Tester {number}",
            "password": password,
        }
        response = client.post(f"{API}/auth/register", json=payload)
        assert response.status_code == 201, response.text
        body = response.json()
        return {
            "token": body["access_token"],
            "user": body["user"],
            "headers": {"Authorization": f"Bearer {body['access_token']}"},
            "username": username,
            "email": email,
            "password": password,
        }

    return _make_user


@pytest.fixture
def alice(make_user) -> dict:
    return make_user("alice")


@pytest.fixture
def bob(make_user) -> dict:
    return make_user("bob")


@pytest.fixture
def carol(make_user) -> dict:
    return make_user("carol")


@pytest.fixture
def direct_conversation(client):
    """Create a direct conversation between two users via the real API."""

    def _create(first: dict, second: dict) -> dict:
        response = client.post(
            f"{API}/conversations",
            headers=first["headers"],
            json={"type": "direct", "member_ids": [second["user"]["id"]]},
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _create


@pytest.fixture
def group_conversation(client):
    """Create a named group owned by ``owner`` with the given members."""

    def _create(owner: dict, members: list[dict], name: str = "Test group") -> dict:
        response = client.post(
            f"{API}/conversations",
            headers=owner["headers"],
            json={
                "type": "group",
                "name": name,
                "member_ids": [member["user"]["id"] for member in members],
            },
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _create


@pytest.fixture
def send_message(client):
    """Send a message and return the API response body."""

    def _send(sender: dict, conversation_id: str, content: str, **extra) -> dict:
        response = client.post(
            f"{API}/conversations/{conversation_id}/messages",
            headers=sender["headers"],
            json={"content": content, **extra},
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _send
