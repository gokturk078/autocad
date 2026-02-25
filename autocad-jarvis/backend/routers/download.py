"""
Download & Form-Generate Router
=================================
Sprint 4 endpoint'leri:
  GET  /project/download/{project_id}/{filename}  — Tek DXF indirme
  GET  /project/download-zip/{project_id}         — ZIP paketi indirme
  POST /project/generate-form                     — Form tabanlı üretim (NLP bypass)
  GET  /project/list                              — Proje listesi
  GET  /project/{project_id}                      — Proje detayı
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

from ai.nlp_parser import ProjectRequest
from core.dxf_generator import ArchitecturalDXFGenerator
from core.project_builder import ProjectBuilder
from core.project_store import ProjectStore


router = APIRouter(tags=["project"])

# ── Module-level singletons (injected from main.py) ─────────────────────────
_builder: ProjectBuilder | None = None
_store: ProjectStore | None = None
_dxf_gen = ArchitecturalDXFGenerator()


def set_download_deps(builder: ProjectBuilder, store: ProjectStore) -> None:
    """main.py'den çağrılır — dependency injection."""
    global _builder, _store  # noqa: PLW0603
    _builder = builder
    _store = store


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ═════════════════════════════════════════════════════════════════════════════
# GET /project/list — Üretilen projelerin listesi
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/project/list")
async def list_projects():
    """Tüm üretilen projelerin özet listesi."""
    if not _store:
        return JSONResponse({"error": "Servis hazır değil"}, status_code=503)

    return {
        "status": "success",
        "count": _store.count,
        "projects": _store.list_all(),
    }


# ═════════════════════════════════════════════════════════════════════════════
# GET /project/{project_id} — Proje detayı
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/project/{project_id}")
async def get_project_detail(project_id: str):
    """Tek projenin tam detayı."""
    if not _store:
        return JSONResponse({"error": "Servis hazır değil"}, status_code=503)

    project = _store.get(project_id)
    if not project:
        return JSONResponse(
            {"error": f"Proje bulunamadı: {project_id}"},
            status_code=404,
        )

    return {"status": "success", "project": project.to_full()}


# ═════════════════════════════════════════════════════════════════════════════
# GET /project/download/{project_id}/{filename} — Tek DXF indirme
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/project/download/{project_id}/{filename}")
async def download_dxf(project_id: str, filename: str):
    """Tek DXF dosyası indir."""
    if not _store:
        return JSONResponse({"error": "Servis hazır değil"}, status_code=503)

    project = _store.get(project_id)
    if not project:
        return JSONResponse(
            {"error": f"Proje bulunamadı: {project_id}"},
            status_code=404,
        )

    # Dosyayı bul
    file_path = None
    for label, fpath in project.files.items():
        if os.path.basename(fpath) == filename:
            file_path = fpath
            break

    if not file_path or not os.path.exists(file_path):
        return JSONResponse(
            {"error": f"Dosya bulunamadı: {filename}"},
            status_code=404,
        )

    return FileResponse(
        file_path,
        media_type="application/dxf",
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


# ═════════════════════════════════════════════════════════════════════════════
# GET /project/download-zip/{project_id} — ZIP paketi indirme
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/project/download-zip/{project_id}")
async def download_zip(project_id: str):
    """Tam proje ZIP paketi indir."""
    if not _store:
        return JSONResponse({"error": "Servis hazır değil"}, status_code=503)

    project = _store.get(project_id)
    if not project:
        return JSONResponse(
            {"error": f"Proje bulunamadı: {project_id}"},
            status_code=404,
        )

    if not project.zip_path or not os.path.exists(project.zip_path):
        return JSONResponse(
            {"error": "ZIP dosyası bulunamadı"},
            status_code=404,
        )

    zip_filename = os.path.basename(project.zip_path)
    return FileResponse(
        project.zip_path,
        media_type="application/zip",
        filename=zip_filename,
        headers={
            "Content-Disposition": f'attachment; filename="{zip_filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


# ═════════════════════════════════════════════════════════════════════════════
# POST /project/generate-form — Form tabanlı üretim (NLP bypass)
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/project/generate-form")
async def generate_from_form(body: dict):
    """
    Form tabanlı proje üretimi — NLP atlanır, doğrudan yapısal girdi.

    Body: ProjectRequest JSON
    Örnek:
    {
        "project_name": "Deniz Evleri",
        "building_type": "konut",
        "parcel": {"width": 25, "depth": 20, "taks_limit": 0.40, "kaks_limit": 2.0},
        "floors": {"normal_floors": 3, "ground_floor": true, "floor_height": 2.80},
        "units": [{"unit_type": "3+1", "count": 2, "target_area_m2": 120}],
        "elevator": true
    }
    """
    if not _builder or not _store:
        return JSONResponse({"error": "Servis hazır değil"}, status_code=503)

    try:
        # 1. Body → ProjectRequest (doğrudan yapısal parse)
        project_request = ProjectRequest(**body)
        print(f"[{_ts()}] [FORM-GEN] Proje: {project_request.project_name}")

        # 2. ProjectRequest → BuildingSpec + Regulation Check
        result = _builder.build(project_request)

        # 3. Output dizini
        safe_name = project_request.project_name.replace(" ", "_").replace("/", "_")
        output_dir = os.path.join(
            tempfile.gettempdir(),
            f"autoCA_{safe_name}_{datetime.now().strftime('%H%M%S')}",
        )

        # 4. DXF Üretimi
        dxf_output = _dxf_gen.generate_project(
            result,
            output_dir=output_dir,
            project_name=project_request.project_name,
            city=project_request.parcel.city,
        )

        # 5. Staircase data
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

        # 6. Store'a kaydet
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

        # 7. Cleanup (max 20 proje tut)
        _store.cleanup_old(max_count=20)

        print(f"[{_ts()}] [FORM-GEN] ✓ {stored.project_id}: "
              f"{stored.file_count} dosya üretildi")

        return {
            "status": "success",
            "project_id": stored.project_id,
            "project": stored.to_full(),
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
            {"error": str(e), "message_tr": "Proje oluşturulurken hata oluştu"},
            status_code=500,
        )
