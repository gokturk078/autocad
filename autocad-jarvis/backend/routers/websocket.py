"""WebSocket endpoint router with dependency injection."""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# Injected by main.py at startup
_manager = None
_app_state = None


def set_dependencies(manager, app_state) -> None:  # noqa: ANN001
    """Called from main.py to inject shared singletons."""
    global _manager, _app_state  # noqa: PLW0603
    _manager = manager
    _app_state = app_state


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Main WebSocket endpoint — accepts connections, replays state, handles ping/pong."""
    await _manager.connect(websocket)

    # Replay last project state on connect
    if _app_state and _app_state.last_project is not None:
        try:
            await websocket.send_text(json.dumps({
                "type": "project_update",
                "timestamp": datetime.now().isoformat(),
                "payload": _app_state.last_project.model_dump(mode="json"),
            }, default=str))
        except Exception:
            pass

    # Replay last analysis on connect
    if _app_state and _app_state.last_analysis is not None:
        try:
            await websocket.send_text(json.dumps({
                "type": "ai_analysis",
                "timestamp": datetime.now().isoformat(),
                "payload": _app_state.last_analysis.model_dump(mode="json"),
            }, default=str))
        except Exception:
            pass

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if msg.get("type") == "ping":
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat(),
                    "payload": {"connections": _manager.connection_count},
                }))

    except WebSocketDisconnect:
        _manager.disconnect(websocket)
    except Exception as exc:
        _manager.disconnect(websocket)
        print(f"[{_ts()}] [WS] ERROR: {exc}")
