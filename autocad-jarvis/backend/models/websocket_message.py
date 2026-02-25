"""WebSocket message schema — all messages sent to frontend conform to this shape."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Discriminator for WebSocket message routing."""

    PROJECT_UPDATE = "project_update"
    AI_ANALYSIS = "ai_analysis"
    WATCHER_STATUS = "watcher_status"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


class WebSocketMessage(BaseModel):
    """Envelope that wraps every WebSocket payload."""

    type: MessageType
    timestamp: datetime = Field(default_factory=datetime.now)
    payload: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict suitable for JSON encoding."""
        return {
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
        }
