# ConnectHub Frontend

React 19 + TypeScript + Vite client for the ConnectHub realtime chat API.

## Requirements

- Node.js 20+
- The ConnectHub API running on `http://127.0.0.1:8000`

## Development

```powershell
npm install
npm run dev
```

Open http://127.0.0.1:5173. The dev server proxies `/api` and `/ws` to the
FastAPI process (see `vite.config.ts`), so no CORS or URL configuration is
required.

## Production build

```powershell
npm run build
```

This runs `tsc --noEmit` and writes a static bundle to `dist/`. The backend
serves that folder automatically when it exists:

```powershell
cd ..
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open http://127.0.0.1:8000.

## Configuration

Both variables are optional. Leave them unset for local development; set them
only when the API is hosted on another origin.

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_URL` | `/api/v1` | REST base URL |
| `VITE_WS_URL` | current host + `/ws` | WebSocket URL |

Copy `.env.example` to `.env.local` to override them.

## Features

- Register / log in with JWT (token persisted in `localStorage`)
- Direct and group conversations, with member management
- Live messages, typing indicators and read receipts over WebSocket
- Message replies, edits and deletes
- Notifications panel with unread counts
- Profile editing and online presence
- Responsive layout for desktop and mobile

## Project structure

```
src/
  api/          # typed fetch client + API types
  components/   # UI (sidebar, chat window, modals, notifications)
  context/      # auth, chat and toast state
  hooks/        # WebSocket connection with reconnect + heartbeat
  lib/          # formatting helpers
  App.tsx       # signed-out / signed-in routing
```
