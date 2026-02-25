"""
Validate & Generate Router
===========================
/validate      — Projeyi mevzuata karşı doğrula
/generate-full — Tam proje dosyası üret (tüm paftalar + ZIP)
/regulations   — Şehre göre imar parametreleri
/estimate-cost — Yaklaşık maliyet hesapla
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ai.nlp_parser import NLPParser, ProjectRequest
from core.dxf_generator import ArchitecturalDXFGenerator
from core.project_builder import ProjectBuilder
from core.regulations import BuildingType, TurkishBuildingCode


router = APIRouter(tags=["project"])

# ── Module-level singletons (injected from main.py) ─────────────────────────
_nlp: NLPParser | None = None
_builder: ProjectBuilder | None = None
_dxf_gen = ArchitecturalDXFGenerator()


def set_dependencies(nlp: NLPParser, builder: ProjectBuilder) -> None:
    """main.py'den çağrılır — dependency injection."""
    global _nlp, _builder  # noqa: PLW0603
    _nlp = nlp
    _builder = builder


# ═════════════════════════════════════════════════════════════════════════════
# POST /project/generate-full — Tam proje üret (DXF dosyaları + ZIP)
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/project/generate-full", response_model=None)
async def generate_full_project(body: dict):
    """
    Doğal dil komutuyla tam proje üret.
    Body: {"prompt": "İstanbul, 600m² arsa, 5 katlı 3+1 konut", "output_dir": "/optional/path"}
    """
    if not _nlp or not _builder:
        return JSONResponse({"error": "Servis henüz hazır değil"}, status_code=503)

    prompt = body.get("prompt", "")
    if not prompt:
        return JSONResponse({"error": "prompt gerekli"}, status_code=400)

    output_dir = body.get("output_dir", str(Path.home() / "Desktop" / "autoCA_proje"))

    try:
        # 1. NLP → ProjectRequest
        project_request = await _nlp.parse_project(prompt)

        # 2. ProjectRequest → BuildingSpec + Regulation Check
        result = _builder.build(project_request)

        # 3. DXF Üretimi
        dxf_output = _dxf_gen.generate_project(
            result,
            output_dir=output_dir,
            project_name=project_request.project_name,
            city=project_request.parcel.city,
        )

        # 4. Response
        report = result["report"]

        return {
            "status": "success",
            "project_name": project_request.project_name,
            "building_type": project_request.building_type,
            "compliance": report.to_dict(),
            "cost_estimate": result["cost"],
            "area_table": result["area_table"],
            "dxf_files": dxf_output.to_dict(),
            "staircase": {
                "riser_count": result["staircase"].riser_count,
                "riser_height_cm": result["staircase"].riser_height,
                "tread_depth_cm": result["staircase"].tread_depth,
                "stair_width_m": result["staircase"].stair_width,
                "formula": result["staircase"].formula,
                "total_area_m2": result["staircase"].total_area,
            },
            "message_tr": (
                f"✓ Proje başarıyla oluşturuldu: {project_request.project_name} "
                f"({dxf_output.to_dict()['file_count']} pafta + ZIP)"
                if report.is_compliant
                else f"✗ Proje oluşturuldu ancak {report.error_count} mevzuat ihlali var "
                     f"({dxf_output.to_dict()['file_count']} pafta üretildi)"
            ),
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"error": str(e), "message_tr": "Proje oluşturulurken hata oluştu"},
            status_code=500,
        )



# ═════════════════════════════════════════════════════════════════════════════
# POST /project/validate — Mevcut projeyi doğrula
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/project/validate", response_model=None)
async def validate_project(body: dict):
    """
    Verilen proje parametrelerini mevzuata karşı doğrula.
    Body: ProjectRequest JSON
    """
    if not _builder:
        return JSONResponse({"error": "Servis henüz hazır değil"}, status_code=503)

    try:
        project_request = ProjectRequest(**body)
        result = _builder.build(project_request)
        report = result["report"]

        return {
            "status": "valid" if report.is_compliant else "invalid",
            "compliance": report.to_dict(),
            "area_table": result["area_table"],
        }

    except Exception as e:
        return JSONResponse(
            {"error": str(e), "message_tr": "Doğrulama sırasında hata oluştu"},
            status_code=500,
        )


# ═════════════════════════════════════════════════════════════════════════════
# GET /regulations/{city} — Şehir bazlı varsayılan imar parametreleri
# ═════════════════════════════════════════════════════════════════════════════

# Şehir bazlı varsayılanlar (genişletilebilir)
CITY_DEFAULTS: dict[str, dict] = {
    "istanbul": {
        "taks_limit": 0.40, "kaks_limit": 2.07,
        "max_floors": 5, "max_height": 15.50,
        "front_setback": 5.0, "side_setback": 3.0, "rear_setback": 3.0,
        "frost_depth": 0.80,
    },
    "ankara": {
        "taks_limit": 0.35, "kaks_limit": 1.75,
        "max_floors": 5, "max_height": 15.50,
        "front_setback": 5.0, "side_setback": 3.0, "rear_setback": 3.0,
        "frost_depth": 1.20,
    },
    "izmir": {
        "taks_limit": 0.40, "kaks_limit": 2.00,
        "max_floors": 5, "max_height": 15.50,
        "front_setback": 5.0, "side_setback": 3.0, "rear_setback": 3.0,
        "frost_depth": 0.60,
    },
    "antalya": {
        "taks_limit": 0.40, "kaks_limit": 1.80,
        "max_floors": 4, "max_height": 12.50,
        "front_setback": 5.0, "side_setback": 3.0, "rear_setback": 3.0,
        "frost_depth": 0.40,
    },
    "bursa": {
        "taks_limit": 0.35, "kaks_limit": 1.75,
        "max_floors": 5, "max_height": 15.50,
        "front_setback": 5.0, "side_setback": 3.0, "rear_setback": 3.0,
        "frost_depth": 0.90,
    },
}


@router.get("/regulations/{city}")
async def get_regulations(city: str):
    """Şehir bazlı imar parametreleri."""
    key = city.lower().strip()
    if key in CITY_DEFAULTS:
        return {
            "city": city,
            "regulations": CITY_DEFAULTS[key],
            "source": "Planlı Alanlar İmar Yönetmeliği (varsayılan değerler)",
        }
    return {
        "city": city,
        "regulations": CITY_DEFAULTS["istanbul"],  # Varsayılan
        "note": f"'{city}' için özel parametreler bulunamadı, İstanbul varsayılanları kullanılıyor",
        "source": "Planlı Alanlar İmar Yönetmeliği (varsayılan değerler)",
    }


# ═════════════════════════════════════════════════════════════════════════════
# POST /estimate-cost — Maliyet tahmini
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/estimate-cost", response_model=None)
async def estimate_cost(body: dict):
    """
    Yaklaşık maliyet tahmini.
    Body: {"total_area_m2": 1500, "building_type": "konut"}
    """
    total_area = body.get("total_area_m2", 0)
    building_type_str = body.get("building_type", "konut")

    if total_area <= 0:
        return JSONResponse({"error": "total_area_m2 > 0 olmalı"}, status_code=400)

    try:
        bt = BuildingType(building_type_str)
    except ValueError:
        bt = BuildingType.KONUT

    cost = TurkishBuildingCode.estimate_cost(total_area, bt)
    return {"status": "success", **cost}
