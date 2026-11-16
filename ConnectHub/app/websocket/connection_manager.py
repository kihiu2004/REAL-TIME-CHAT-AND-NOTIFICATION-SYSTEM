from collections import defaultdict

from fastapi import WebSocket

from app.schemas.message import MessagePublic


class ConnectionManager:
    """Keeps the WebSocket connections owned by this process."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        self._connections[user_id].add(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        connections = self._connections.get(user_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(user_id, None)

    async def deliver(self, user_id: str, event: dict) -> int:
        """Send an event to every connection of one user on this process."""
        sent = 0
        for websocket in list(self._connections.get(user_id, ())):
            try:
                await websocket.send_json(event)
                sent += 1
            except Exception:
                self.disconnect(user_id, websocket)
        return sent

    def online_users(self) -> set[str]:
        return set(self._connections)


manager = ConnectionManager()
