# ConnectHub

Realtime chat and notification system: FastAPI + MySQL + Redis + WebSockets on
the backend, React + TypeScript + Vite on the frontend.

## Requirements

- Python 3.14+
- MySQL (XAMPP is fine) with a `connecthub` database
- Redis (optional in development; without it, presence and realtime events work
  in-process only)

## Setup

```powershell
cd ConnectHub
python -m pip install -r requirements.txt

# Start MySQL in the XAMPP control panel, then create the database:
#   CREATE DATABASE connecthub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

alembic upgrade head           # apply the included initial migration
# or, for a quick local schema without Alembic:
# python scripts/init_db.py

uvicorn app.main:app --reload
```

- API docs: http://127.0.0.1:8000/docs
- Health probe: http://127.0.0.1:8000/health

`/health` reports `status: degraded` while the database is unreachable; the
process still starts so you can inspect the API.

## Frontend

Two ways to run the React app:

**Development (hot reload)** — start the API on port 8000, then:

```powershell
cd frontend
npm install
npm run dev        # http://127.0.0.1:5173
```

Vite proxies `/api` and `/ws` to `http://127.0.0.1:8000`, so the browser uses
same-origin URLs and no CORS setup is needed.

**Production build (single server)** — build once and let FastAPI serve it:

```powershell
cd frontend
npm install
npm run build      # writes frontend/dist
cd ..
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

If `frontend/dist/index.html` exists, `app.main` mounts it at `/`, so the whole
app is available at http://127.0.0.1:8000. Without a build, `/` redirects to
the API docs.

## Demo people to chat with

The "New conversation" dialog only lists **other** registered accounts, so a
fresh install with one account looks empty. Seed three demo users:

```powershell
python scripts/seed_demo_users.py
```

| Username | Email | Full name |
|---|---|---|
| `alice` | alice@example.com | Alice Wanjiku |
| `brian` | brian@example.com | Brian Otieno |
| `grace` | grace@example.com | Grace Muthoni |

All three use the password `Password123!`. The script is idempotent, so it is
safe to run again.

To try a real conversation, log in as two different accounts in two browser
profiles (or one normal and one private window), then use **New conversation**
to pick the other person. Groups are private invitations: create one from the
**Group** tab of the same dialog and add members there.

## Tests

```powershell
python -m pytest
```

The suite uses a throwaway SQLite database (`aiosqlite`), so it needs neither
MySQL nor Redis. It covers auth, users, conversations, messages,
notifications, presence and the WebSocket protocol. Password hashing uses a
low bcrypt cost during tests (`BCRYPT_ROUNDS=4`); production keeps the default
12.

## Smoke test

```powershell
python scripts/smoke_test.py
```

It creates a throwaway `connecthub_test` database, exercises auth, users,
conversations, messages, notifications and the WebSocket protocol end to end,
then drops the database again. Your real `connecthub` database is untouched.

## Layout

```
app/
  config.py        # settings loaded from .env
  main.py          # FastAPI app, lifespan, CORS, /health
  core/            # security (bcrypt), JWT, dependencies, permissions, errors
  database/        # async engine, session factory, declarative base
  models/          # SQLAlchemy models (user, conversation, message, ...)
  schemas/         # Pydantic request/response models
  services/        # business logic (auth, users, conversations, messages, ...)
  routers/         # REST endpoints (/api/v1/...) and /ws
  redis/           # connection, presence, pub/sub fan-out
  websocket/       # connection manager, auth, event handling, broadcasts
frontend/          # React + TypeScript client (Vite)
migrations/        # Alembic environment
tests/             # pytest suite (SQLite, no external services)
scripts/           # init_db.py, seed_demo_users.py, smoke_test.py
```

## Authentication

1. `POST /api/v1/auth/register` with `{username, email, full_name, password}`
2. `POST /api/v1/auth/login` with `{identifier, password}` (`identifier` is the
   username **or** email)
3. Send `Authorization: Bearer <access_token>` on every REST request.

## REST endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/auth/register` | Create an account (returns a token) |
| POST | `/api/v1/auth/login` | Log in |
| GET | `/api/v1/auth/me` | Current account |
| GET/PATCH | `/api/v1/users/me` | Read / update my profile |
| GET | `/api/v1/users` | List/search users |
| GET | `/api/v1/users/{id}` | One user |
| POST | `/api/v1/conversations` | Create a direct or group conversation |
| GET | `/api/v1/conversations` | My conversations + last message + unread count |
| GET/PATCH | `/api/v1/conversations/{id}` | Read / rename a group |
| POST | `/api/v1/conversations/{id}/members` | Add a group member |
| DELETE | `/api/v1/conversations/{id}/members/{user_id}` | Remove / leave |
| POST | `/api/v1/conversations/{id}/read` | Mark as read |
| POST | `/api/v1/conversations/{id}/messages` | Send a message |
| GET | `/api/v1/conversations/{id}/messages` | History (newest first, `before` cursor) |
| PATCH/DELETE | `/api/v1/messages/{id}` | Edit / delete |
| GET | `/api/v1/notifications` | My notifications |
| GET | `/api/v1/notifications/unread-count` | Unread count |
| POST | `/api/v1/notifications/{id}/read` | Mark one read |
| POST | `/api/v1/notifications/read-all` | Mark all read |

Creating a direct conversation is idempotent: if the two users already have one,
it is returned instead of creating a duplicate.

## WebSocket

Connect to `ws://127.0.0.1:8000/ws?token=<access_token>`.

Server events:

- `connection.ready` — `{user_id}`
- `message.new`, `message.updated`, `message.deleted`
- `typing` — `{conversation_id, user_id, username, is_typing}`
- `message.read` — `{conversation_id, user_id, last_read_at}`
- `notification.new` — full notification object
- `pong`, `error`

Client events (JSON `{ "type": ..., "data": {...} }`):

```json
{"type": "message.send", "data": {"conversation_id": "...", "content": "hello"}}
{"type": "typing.start", "data": {"conversation_id": "..."}}
{"type": "typing.stop",  "data": {"conversation_id": "..."}}
{"type": "message.read", "data": {"conversation_id": "...", "message_id": "..."}}
{"type": "ping"}
```

`message_id` is optional for `message.read`; omit it to mark the whole
conversation as read.

## Notes

- Passwords are hashed with bcrypt; only the hash is stored. Tune the cost with
  `BCRYPT_ROUNDS` (default 12, minimum 4).
- JWT tokens are HS256 and expire after `ACCESS_TOKEN_EXPIRE_MINUTES`.
- Timestamps are generated by the application in UTC with microsecond
  precision (`DATETIME(6)` on MySQL), so unread counts and ordering are exact.
- Events are published through Redis when it is available, so multiple workers
  can deliver realtime updates to each other; otherwise delivery is local.
