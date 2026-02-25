"""
NLP-based Project Generation Router
=====================================
POST /project/generate-nlp — Doğal dil prompt → GPT → DXF proje seti

Pipeline:
  1. Frontend prompt gönderir
  2. AIArchitect (GPT-4.1) prompt'u parse eder → ProjectRequest
  3. ProjectBuilder → BuildingSpec + ComplianceReport
  4. DXFGenerator → 13+ pafta DXF + ZIP
  5. ProjectStore'a kaydet → Frontend'e döndür
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ai.ai_architect import AIArchitect
from core.dxf_generator import ArchitecturalDXFGenerator
from core.project_builder import ProjectBuilder
from core.project_store import ProjectStore


router = APIRouter(tags=["project"])


# ── Module-level singletons ─────────────────────────────────────────────────
_architect: AIArchitect | None = None
_builder: ProjectBuilder | None = None
_store: ProjectStore | None = None
_dxf_gen = ArchitecturalDXFGenerator()


def set_nlp_deps(architect: AIArchitect, builder: ProjectBuilder, store: ProjectStore) -> None:
    """main.py'den çağrılır — dependency injection."""
    global _architect, _builder, _store  # noqa: PLW0603
    _architect = architect
    _builder = builder
    _store = store


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── Request model ────────────────────────────────────────────────────────────

class NLPGenerateRequest(BaseModel):
    prompt: str


# ═════════════════════════════════════════════════════════════════════════════
# POST /project/generate-nlp — Doğal dil → tam proje
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/project/generate-nlp")
async def generate_from_nlp(body: NLPGenerateRequest):
    """
    Doğal dil prompt → GPT-powered mimari proje üretimi.

    Body: { "prompt": "İstanbul, 25x20m arsa, 4 katlı 3+1 konut, asansörlü" }
    """
    if not _architect or not _builder or not _store:
        return JSONResponse({"error": "Servis hazır değil"}, status_code=503)

    if not _architect.is_ready:
        return JSONResponse(
            {"error": "OpenAI API key yapılandırılmamış", "message_tr": "API key eksik"},
            status_code=503,
        )

    try:
        # ─── 1. GPT ile prompt'u profesyonel ProjectRequest'e dönüştür ───
        print(f"[{_ts()}] [NLP-GEN] ═══ Prompt alındı: '{body.prompt[:80]}...'")
        project_request = await _architect.design_project(body.prompt)

        # ─── 2. ProjectRequest → BuildingSpec + Compliance ───
        print(f"[{_ts()}] [NLP-GEN] Proje hesaplanıyor...")
        result = _builder.build(project_request)

        # ─── 3. DXF üretimi ───
        safe_name = project_request.project_name.replace(" ", "_").replace("/", "_")
        output_dir = os.path.join(
            tempfile.gettempdir(),
            f"autoCA_{safe_name}_{datetime.now().strftime('%H%M%S')}",
        )

        print(f"[{_ts()}] [NLP-GEN] DXF üretimi başlıyor...")
        dxf_output = _dxf_gen.generate_project(
            result,
            output_dir=output_dir,
            project_name=project_request.project_name,
            city=project_request.parcel.city,
        )

        # ─── 4. Staircase data ───
        staircase_data = {}
        if "staircase" in result:
            sc = result["staircase"]
            staircase_data = {
                "riser_count": sc.riser_count,
                "riser_height_cm": sc.riser_height,
                "tread_depth_cm": sc.tread_depth,
                "stair_width_m": sc.stair_width,
                "formula": sc.formula,
                "total_area_m2": sc.total_area,
            }

        # ─── 5. Store'a kaydet ───
        report = result["report"]
        stored = _store.add(
            project_name=project_request.project_name,
            building_type=project_request.building_type,
            output_dir=output_dir,
            zip_path=dxf_output.zip_path,
            files=dxf_output.files,
            compliance=report.to_dict(),
            cost=result.get("cost", {}),
            area_table=result.get("area_table", {}),
            staircase=staircase_data,
        )

        _store.cleanup_old(max_count=20)

        print(f"[{_ts()}] [NLP-GEN] ✓ Proje tamamlandı: {stored.project_id} "
              f"({stored.file_count} dosya)")

        return {
            "status": "success",
            "project_id": stored.project_id,
            "project": stored.to_full(),
            "ai_model": _architect.model,
            "message_tr": (
                f"✓ Proje başarıyla oluşturuldu: {project_request.project_name} "
                f"({stored.file_count} pafta + ZIP)"
                if report.is_compliant
                else f"✗ Proje oluşturuldu ancak {report.error_count} mevzuat ihlali var"
            ),
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {
                "error": str(e),
                "message_tr": f"Proje oluşturulurken hata: {str(e)[:200]}",
            },
            status_code=500,
        )


# ═════════════════════════════════════════════════════════════════════════════
# GET /ai/health — AI model durumu
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/ai/health")
async def ai_health():
    """AI model bağlantı kontrolü."""
    if not _architect:
        return {"status": "not_initialized"}
    return await _architect.health_check()
