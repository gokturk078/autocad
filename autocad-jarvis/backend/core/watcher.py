"""File watcher — monitors directories for DXF changes using watchdog."""

from __future__ import annotations

import asyncio
import os
import threading
from datetime import datetime
from typing import TYPE_CHECKING

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from models.websocket_message import MessageType, WebSocketMessage

if TYPE_CHECKING:
    from ai.openai_client import OpenAIClient
    from core.connection_manager import ConnectionManager
    from core.dxf_parser import DXFParser


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class DXFFileHandler(FileSystemEventHandler):
    """Handles file-system events, debounces rapid saves, and triggers DXF analysis."""

    def __init__(
        self,
        parser: DXFParser,
        ai_client: OpenAIClient,
        manager: ConnectionManager,
        loop: asyncio.AbstractEventLoop,
        app_state=None,  # noqa: ANN001
    ) -> None:
        super().__init__()
        self.parser = parser
        self.ai_client = ai_client
        self.manager = manager
        self.loop = loop
        self.app_state = app_state
        self._debounce_timer: threading.Timer | None = None
        self._debounce_delay: float = 0.8
        self._processing: bool = False

    def on_modified(self, event) -> None:  # noqa: ANN001
        if event.is_directory:
            return
        src = event.src_path
        if not src.endswith(".dxf"):
            return
        basename = os.path.basename(src)
        if basename.startswith("~$") or basename.startswith(".~"):
            return
        if self._processing:
            return

        print(f"[{_ts()}] [WATCHER] INFO: DXF modified: {basename}")

        if self._debounce_timer is not None:
            self._debounce_timer.cancel()

        self._debounce_timer = threading.Timer(
            self._debounce_delay,
            self._schedule_analysis,
            args=[src],
        )
        self._debounce_timer.start()

    def _schedule_analysis(self, filepath: str) -> None:
        future = asyncio.run_coroutine_threadsafe(
            self._analyze(filepath),
            self.loop,
        )
        try:
            future.result(timeout=30)
        except Exception as exc:
            print(f"[{_ts()}] [WATCHER] ERROR: {exc}")

    async def _analyze(self, filepath: str) -> None:
        self._processing = True
        try:
            # 1. Parse DXF
            project = self.parser.parse(filepath)

            # Update app state
            if self.app_state is not None:
                self.app_state.last_project = project

            # 2. Broadcast project update immediately
            await self.manager.broadcast(
                WebSocketMessage(
                    type=MessageType.PROJECT_UPDATE,
                    payload=project.model_dump(mode="json"),
                ).to_dict()
            )

            # 3. AI analysis
            analysis = await self.ai_client.analyze_project(project)

            if self.app_state is not None:
                self.app_state.last_analysis = analysis

            # 4. Broadcast AI analysis
            await self.manager.broadcast(
                WebSocketMessage(
                    type=MessageType.AI_ANALYSIS,
                    payload=analysis.model_dump(mode="json"),
                ).to_dict()
            )

        except Exception as exc:
            print(f"[{_ts()}] [WATCHER] ERROR: Pipeline error: {exc}")
            await self.manager.broadcast(
                WebSocketMessage(
                    type=MessageType.ERROR,
                    payload={"message": str(exc), "filepath": filepath},
                ).to_dict()
            )
        finally:
            self._processing = False


class WatcherService:
    """Manages the watchdog Observer lifecycle."""

    def __init__(self, handler: DXFFileHandler) -> None:
        self.handler = handler
        self.observer = Observer()
        self._watched_paths: set[str] = set()

    def watch_directory(self, directory: str) -> bool:
        directory = os.path.expanduser(directory)
        if directory in self._watched_paths:
            return False
        if not os.path.isdir(directory):
            print(f"[{_ts()}] [WATCHER] WARNING: Klasör bulunamadı: {directory}")
            return False

        self.observer.schedule(self.handler, directory, recursive=True)
        self._watched_paths.add(directory)
        print(f"[{_ts()}] [WATCHER] INFO: İzleniyor: {directory}")
        return True

    def watch_file(self, filepath: str) -> bool:
        filepath = os.path.expanduser(filepath)
        parent = os.path.dirname(filepath)
        return self.watch_directory(parent)

    def start(self) -> None:
        self.observer.start()
        print(f"[{_ts()}] [WATCHER] INFO: Başlatıldı. {len(self._watched_paths)} klasör izleniyor.")

    def stop(self) -> None:
        self.observer.stop()
        self.observer.join(timeout=5)
        print(f"[{_ts()}] [WATCHER] INFO: Durduruldu.")

    @property
    def watched_paths(self) -> list[str]:
        return list(self._watched_paths)

    @property
    def is_active(self) -> bool:
        return self.observer.is_alive()
