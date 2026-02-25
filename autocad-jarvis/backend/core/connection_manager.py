"""WebSocket connection manager — hub for broadcasting to multiple browser tabs."""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import WebSocket


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class ConnectionManager:
    """Manages all active WebSocket connections and provides broadcast helpers."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket client."""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[{_ts()}] [WS] INFO: Yeni bağlantı. Aktif: {self.connection_count}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket client from the active list."""
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            pass
        print(f"[{_ts()}] [WS] INFO: Bağlantı kesildi. Aktif: {self.connection_count}")

    async def broadcast(self, message: dict) -> None:
        """Send a dict message to every connected client. Stale connections are cleaned up."""
        disconnected: list[WebSocket] = []
        message_text = json.dumps(message, default=str)

        for connection in self.active_connections:
            try:
                await connection.send_text(message_text)
            except Exception as exc:
                print(f"[{_ts()}] [WS] WARNING: Broadcast hatası, bağlantı temizleniyor: {exc}")
                disconnected.append(connection)

        for conn in disconnected:
            try:
                self.active_connections.remove(conn)
            except ValueError:
                pass

        if self.active_connections:
            print(f"[{_ts()}] [WS] INFO: Broadcast gönderildi → {self.connection_count} istemci")

    @property
    def connection_count(self) -> int:
        """Return the number of currently active connections."""
        return len(self.active_connections)
