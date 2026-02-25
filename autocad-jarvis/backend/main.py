"""AutoCAD JARVIS AI Copilot — FAZ 3 Backend Entry Point."""

from __future__ import annotations

import asyncio
import os
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ai.openai_client import OpenAIClient
from ai.nlp_parser import NLPParser
from config import settings
from core.connection_manager import ConnectionManager
from core.dxf_parser import DXFParser
from core.watcher import DXFFileHandler, WatcherService
from models.project import AnalysisResult, ProjectModel
from models.websocket_message import MessageType, WebSocketMessage
from routers.websocket import router as ws_router, set_dependencies
from routers.validate import router as validate_router, set_dependencies as set_validate_deps
from routers.download import router as download_router, set_download_deps
from routers.generate_nlp import router as nlp_router, set_nlp_deps
from ai.ai_architect import AIArchitect
from core.project_builder import ProjectBuilder
from core.project_store import ProjectStore


# ── Helpers ─────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── Shared singletons ──────────────────────────────────────────────────────

manager = ConnectionManager()
parser = DXFParser()
# Use OpenRouter (Gemini) if key available, else fallback to OpenAI
_or_key = settings.openrouter_api_key
_oai_key = settings.openai_api_key

if _or_key:
    openai_client = OpenAIClient(
        api_key=_or_key,
        model=settings.ai_model,
        mini_model=settings.ai_fast_model,
        base_url=settings.ai_base_url,
    )
else:
    openai_client = OpenAIClient(
        api_key=_oai_key,
        model=settings.openai_model,
        mini_model=settings.openai_mini_model,
    )

# FAZ 3A singletons
nlp_parser = NLPParser(openai_client)
project_builder = ProjectBuilder()
project_store = ProjectStore()

# Sprint 6: AI Architect
ai_architect = AIArchitect()


class AppState:
    """In-memory application state (no database for FAZ 1-2)."""

    def __init__(self) -> None:
        self.last_project: ProjectModel | None = None
        self.last_analysis: AnalysisResult | None = None
        self.watcher_active: bool = False
        self.watched_paths: list[str] = []
        self.openai_healthy: bool = False


app_state = AppState()
watcher_service: WatcherService | None = None


# ── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global watcher_service  # noqa: PLW0603

    print(f"[{_ts()}] [MAIN] ═══ AutoCAD JARVIS v2.0 başlatılıyor ═══")

    # OpenAI health check
    try:
        app_state.openai_healthy = await openai_client.health_check()
        status = "✓ OK" if app_state.openai_healthy else "⚠ ULAŞILAMADI"
        print(f"[{_ts()}] [MAIN] OpenAI durumu: {status}")
    except Exception as exc:
        print(f"[{_ts()}] [MAIN] WARNING: OpenAI health check hatası: {exc}")
        app_state.openai_healthy = False

    # File Watcher
    loop = asyncio.get_event_loop()
    handler = DXFFileHandler(
        parser=parser,
        ai_client=openai_client,
        manager=manager,
        loop=loop,
        app_state=app_state,
    )
    watcher_service = WatcherService(handler=handler)

    for path_str in settings.watch_paths_list:
        expanded = str(Path(path_str).expanduser())
        if os.path.isdir(expanded):
            watcher_service.watch_directory(expanded)
            app_state.watched_paths.append(expanded)
        else:
            print(f"[{_ts()}] [WATCHER] WARNING: Klasör bulunamadı, atlandı: {expanded}")

    watcher_service.start()
    app_state.watcher_active = True

    print(f"[{_ts()}] [MAIN] Backend hazır → http://localhost:{settings.backend_port}")
    print(f"[{_ts()}] [MAIN] Swagger UI → http://localhost:{settings.backend_port}/docs")
    print(f"[{_ts()}] [MAIN] WebSocket  → ws://localhost:{settings.backend_port}/ws")

    yield

    print(f"[{_ts()}] [MAIN] ═══ Kapatılıyor ═══")
    if watcher_service:
        watcher_service.stop()
    print(f"[{_ts()}] [MAIN] Güle güle!")


# ── FastAPI App ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="AutoCAD JARVIS API",
    description="AI-powered AutoCAD Copilot Backend — FAZ 3 (Mevzuat Motoru)",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        # Production: Vercel domains (set via CORS_ORIGINS env var or wildcard)
        *[o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()],
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",  # All Vercel preview deploys
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inject dependencies into WS router
set_dependencies(manager=manager, app_state=app_state)
app.include_router(ws_router)

# FAZ 3A — Validate router
set_validate_deps(nlp=nlp_parser, builder=project_builder)
app.include_router(validate_router)

# Sprint 4 — Download + Form router
set_download_deps(builder=project_builder, store=project_store)
app.include_router(download_router)

# Sprint 6 — NLP Generate router (GPT-powered)
set_nlp_deps(architect=ai_architect, builder=project_builder, store=project_store)
app.include_router(nlp_router)


# ── REST Endpoints ──────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "ws_connections": manager.connection_count,
        "watcher_active": app_state.watcher_active,
        "watched_paths": app_state.watched_paths,
        "openai_healthy": app_state.openai_healthy,
        "last_project": app_state.last_project.filename if app_state.last_project else None,
    }


@app.post("/watch", response_model=None)
async def watch_path(body: dict):
    path_str = body.get("path", "")
    if not path_str:
        return JSONResponse({"error": "path gerekli"}, status_code=400)
    path = Path(path_str).expanduser().resolve()
    if not path.exists():
        return JSONResponse({"error": f"Klasör bulunamadı: {path}"}, status_code=404)
    if not path.is_dir():
        return JSONResponse({"error": "Klasör değil"}, status_code=400)
    if str(path) in app_state.watched_paths:
        return {"watched": True, "path": str(path), "message": "Zaten izleniyor"}

    if watcher_service:
        watcher_service.watch_directory(str(path))
    app_state.watched_paths.append(str(path))

    await manager.broadcast(
        WebSocketMessage(
            type=MessageType.WATCHER_STATUS,
            payload={
                "message": f"Yeni klasör izlemeye alındı: {path}",
                "watched_paths": app_state.watched_paths,
            },
        ).to_dict()
    )
    return {"watched": True, "path": str(path)}


@app.get("/project/current", response_model=None)
async def get_current_project():
    if not app_state.last_project:
        return JSONResponse({"error": "Henüz hiçbir proje parse edilmedi"}, status_code=404)
    return app_state.last_project.model_dump(mode="json")


@app.post("/project/test")
async def create_test_project() -> dict:
    """Generate a test DXF, parse it, and broadcast via WebSocket."""
    from core.dxf_generator import create_test_dxf

    tmp_path = os.path.join(tempfile.gettempdir(), "jarvis_test.dxf")
    create_test_dxf(tmp_path)

    project = parser.parse(tmp_path)
    app_state.last_project = project

    await manager.broadcast(
        WebSocketMessage(
            type=MessageType.PROJECT_UPDATE,
            payload=project.model_dump(mode="json"),
        ).to_dict()
    )

    try:
        analysis = await openai_client.analyze_project(project)
        app_state.last_analysis = analysis
        await manager.broadcast(
            WebSocketMessage(
                type=MessageType.AI_ANALYSIS,
                payload=analysis.model_dump(mode="json"),
            ).to_dict()
        )
    except Exception as exc:
        print(f"[{_ts()}] [API] WARNING: OpenAI analizi başarısız: {exc}")

    return {"success": True, "path": tmp_path, "project": project.model_dump(mode="json")}


@app.post("/generate", response_model=None)
async def generate_dxf(body: dict):
    """
    FAZ 2: Generate DXF from natural language.
    Body: {"prompt": "120m² 3+1 konut planı", "output_dir": "/abs/path"}
    """
    from ai.nlp_parser import NLPParser
    from core.dxf_generator import DXFGenerator

    prompt_text = body.get("prompt", "")
    output_dir = body.get("output_dir", str(Path.home() / "Desktop"))

    if not prompt_text:
        return JSONResponse({"error": "prompt gerekli"}, status_code=400)

    # Step 1: NLP parse
    nlp = NLPParser(openai_client)
    try:
        request_model = await nlp.parse(prompt_text)
    except Exception as exc:
        return JSONResponse({"error": f"Komut ayrıştırılamadı: {exc}"}, status_code=422)

    # Step 2: Generate DXF
    generator = DXFGenerator()
    output_path = os.path.join(
        output_dir,
        f"jarvis_{request_model.type}_{request_model.area_m2}m2.dxf",
    )

    try:
        generated_path = generator.generate(request_model, output_path)
    except Exception as exc:
        return JSONResponse({"error": f"DXF üretilemedi: {exc}"}, status_code=500)

    # Step 3: Parse generated DXF and broadcast
    project = parser.parse(generated_path)
    app_state.last_project = project

    await manager.broadcast(
        WebSocketMessage(
            type=MessageType.PROJECT_UPDATE,
            payload={
                **project.model_dump(mode="json"),
                "generated": True,
                "source_prompt": prompt_text,
            },
        ).to_dict()
    )

    try:
        analysis = await openai_client.analyze_project(project)
        app_state.last_analysis = analysis
        await manager.broadcast(
            WebSocketMessage(
                type=MessageType.AI_ANALYSIS,
                payload=analysis.model_dump(mode="json"),
            ).to_dict()
        )
    except Exception as exc:
        print(f"[{_ts()}] [API] WARNING: Üretim sonrası analiz başarısız: {exc}")

    return {
        "success": True,
        "output_path": generated_path,
        "request": request_model.model_dump(),
        "project": project.model_dump(mode="json"),
    }


# ── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Railway provides PORT env var; fallback to settings
    port = int(os.environ.get("PORT", settings.backend_port))
    is_dev = os.environ.get("RAILWAY_ENVIRONMENT") is None
    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=port,
        reload=is_dev,
        log_level=settings.log_level.lower(),
    )
