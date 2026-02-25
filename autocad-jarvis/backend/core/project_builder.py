"""
Proje Oluşturucu (Project Builder)
==================================
NLP çıktısını (ProjectRequest) → Regulations doğrulaması →
BuildingSpec + ComplianceReport'a dönüştürür.
"""

from __future__ import annotations

import math
from datetime import datetime

from ai.nlp_parser import ProjectRequest, UnitRequest
from core.regulations import (
    BuildingSpec,
    BuildingType,
    ComplianceReport,
    FloorSpec,
    ParcelInfo,
    RoomSpec,
    TurkishBuildingCode,
    UnitSpec,
)


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── Varsayılan Oda Listeleri ─────────────────────────────────────────────────

DEFAULT_ROOMS: dict[str, list[dict]] = {
    "1+0": [
        {"name": "Oda + Salon", "room_type": "salon", "min_area_m2": 22},
        {"name": "Mutfak (açık)", "room_type": "mutfak", "min_area_m2": 5},
        {"name": "Banyo", "room_type": "banyo", "min_area_m2": 4},
        {"name": "Hol", "room_type": "hol", "min_area_m2": 3},
    ],
    "1+1": [
        {"name": "Salon", "room_type": "salon", "min_area_m2": 18},
        {"name": "Yatak Odası", "room_type": "yatak_odasi", "min_area_m2": 12},
        {"name": "Mutfak", "room_type": "mutfak", "min_area_m2": 7},
        {"name": "Banyo", "room_type": "banyo", "min_area_m2": 4},
        {"name": "Hol", "room_type": "hol", "min_area_m2": 3},
        {"name": "Koridor", "room_type": "koridor", "min_area_m2": 2},
    ],
    "2+1": [
        {"name": "Salon", "room_type": "salon", "min_area_m2": 22},
        {"name": "Yatak Odası 1", "room_type": "yatak_odasi", "min_area_m2": 12},
        {"name": "Yatak Odası 2", "room_type": "yatak_odasi", "min_area_m2": 10},
        {"name": "Mutfak", "room_type": "mutfak", "min_area_m2": 8},
        {"name": "Banyo", "room_type": "banyo", "min_area_m2": 5},
        {"name": "WC", "room_type": "wc", "min_area_m2": 2},
        {"name": "Hol", "room_type": "hol", "min_area_m2": 4},
        {"name": "Koridor", "room_type": "koridor", "min_area_m2": 3},
        {"name": "Balkon", "room_type": "balkon", "min_area_m2": 3},
    ],
    "3+1": [
        {"name": "Salon", "room_type": "salon", "min_area_m2": 25},
        {"name": "Yatak Odası 1 (Ebeveyn)", "room_type": "yatak_odasi", "min_area_m2": 15},
        {"name": "Yatak Odası 2", "room_type": "yatak_odasi", "min_area_m2": 12},
        {"name": "Yatak Odası 3", "room_type": "yatak_odasi", "min_area_m2": 10},
        {"name": "Mutfak", "room_type": "mutfak", "min_area_m2": 10},
        {"name": "Banyo 1", "room_type": "banyo", "min_area_m2": 5},
        {"name": "Banyo 2 (Ebeveyn)", "room_type": "banyo", "min_area_m2": 4},
        {"name": "WC", "room_type": "wc", "min_area_m2": 2},
        {"name": "Hol", "room_type": "hol", "min_area_m2": 5},
        {"name": "Koridor", "room_type": "koridor", "min_area_m2": 5},
        {"name": "Balkon", "room_type": "balkon", "min_area_m2": 4},
    ],
    "4+1": [
        {"name": "Salon", "room_type": "salon", "min_area_m2": 30},
        {"name": "Yatak Odası 1 (Ebeveyn)", "room_type": "yatak_odasi", "min_area_m2": 16},
        {"name": "Yatak Odası 2", "room_type": "yatak_odasi", "min_area_m2": 14},
        {"name": "Yatak Odası 3", "room_type": "yatak_odasi", "min_area_m2": 12},
        {"name": "Yatak Odası 4", "room_type": "yatak_odasi", "min_area_m2": 10},
        {"name": "Mutfak", "room_type": "mutfak", "min_area_m2": 12},
        {"name": "Banyo 1", "room_type": "banyo", "min_area_m2": 6},
        {"name": "Banyo 2 (Ebeveyn)", "room_type": "banyo", "min_area_m2": 5},
        {"name": "WC", "room_type": "wc", "min_area_m2": 2},
        {"name": "Hol", "room_type": "hol", "min_area_m2": 6},
        {"name": "Koridor", "room_type": "koridor", "min_area_m2": 6},
        {"name": "Balkon 1", "room_type": "balkon", "min_area_m2": 4},
        {"name": "Balkon 2", "room_type": "balkon", "min_area_m2": 3},
    ],
}


# ══════════════════════════════════════════════════════════════════════════════
# ProjectBuilder
# ══════════════════════════════════════════════════════════════════════════════

class ProjectBuilder:
    """
    ProjectRequest → (BuildingSpec, ParcelInfo, ComplianceReport) dönüşümü.
    """

    def __init__(self) -> None:
        self.code = TurkishBuildingCode()

    def build(self, request: ProjectRequest) -> dict:
        """
        Tam proje hesaplaması yap ve sonuç döndür.

        Returns:
            {
                "parcel": ParcelInfo,
                "building": BuildingSpec,
                "report": ComplianceReport,
                "staircase": StaircaseSpec,
                "cost": dict,
                "area_table": dict,
            }
        """
        print(f"[{_ts()}] [BUILDER] INFO: Proje oluşturuluyor: {request.project_name}")

        # ── 1. Parsel bilgilerini oluştur ────────────────────────────────
        parcel = self._build_parcel(request)

        # ── 2. Bina çekme mesafelerine göre oturum hesapla ───────────────
        building_type = BuildingType(request.building_type)

        # Tahmini yükseklik (iteratif olarak düzeltilecek)
        above_ground = request.floors.normal_floors + (1 if request.floors.ground_floor else 0) + (1 if request.floors.attic else 0)
        est_height = above_ground * request.floors.floor_height

        buildable_w, buildable_d = self.code.calculate_buildable_area(parcel, est_height)

        # ── 3. Daire spesifikasyonlarını oluştur ─────────────────────────
        units_per_floor = self._build_units(request.units)

        # Katta toplam daire alanı
        floor_unit_area = sum(u.gross_area for u in units_per_floor)

        # Ortak alan hesabı
        staircase = self.code.calculate_staircase(request.floors.floor_height, building_type)
        elevator_area = 4.0 if request.elevator else 0.0
        corridor_area = max(6.0, len(units_per_floor) * 2.5)  # daire başı ~2.5m² koridor
        common_area = staircase.total_area + elevator_area + corridor_area

        # Kat toplam alanı
        floor_total = floor_unit_area + common_area

        # Bina oturumu — constraint: buildable alana sığmalı
        footprint_area = floor_total
        fp_w = min(buildable_w, math.sqrt(footprint_area * (buildable_w / max(buildable_d, 1))))
        fp_d = footprint_area / fp_w if fp_w > 0 else 0

        # Oturumu çekme alanına sığdır
        if fp_d > buildable_d:
            fp_d = buildable_d
            fp_w = footprint_area / fp_d if fp_d > 0 else 0
            if fp_w > buildable_w:
                fp_w = buildable_w
                fp_d = buildable_d

        # ── 4. Katları oluştur ───────────────────────────────────────────
        floors: list[FloorSpec] = []

        # Bodrum katlar
        for i in range(request.floors.basement_count):
            floors.append(FloorSpec(
                floor_number=-(i + 1),
                floor_type="bodrum",
                units=[],
                height_gross=2.80,
                staircase_area=staircase.total_area,
                elevator_area=elevator_area,
                corridor_area=fp_w * fp_d - staircase.total_area - elevator_area,  # Otopark alanı
            ))

        # Zemin kat
        if request.floors.ground_floor:
            floors.append(FloorSpec(
                floor_number=0,
                floor_type="zemin",
                units=units_per_floor,
                height_gross=request.floors.floor_height,
                staircase_area=staircase.total_area,
                elevator_area=elevator_area,
                corridor_area=corridor_area,
            ))

        # Normal katlar
        for i in range(request.floors.normal_floors):
            floor_num = i + 1
            floors.append(FloorSpec(
                floor_number=floor_num,
                floor_type="normal",
                units=units_per_floor,
                height_gross=request.floors.floor_height,
                staircase_area=staircase.total_area,
                elevator_area=elevator_area,
                corridor_area=corridor_area,
            ))

        # Çatı katı
        if request.floors.attic:
            floors.append(FloorSpec(
                floor_number=request.floors.normal_floors + 1,
                floor_type="cati",
                units=units_per_floor,
                height_gross=request.floors.floor_height,
                staircase_area=staircase.total_area,
                elevator_area=elevator_area,
                corridor_area=corridor_area,
            ))

        # ── 5. BuildingSpec oluştur ──────────────────────────────────────
        building = BuildingSpec(
            building_type=building_type,
            floors=floors,
            footprint_width=round(fp_w, 2),
            footprint_depth=round(fp_d, 2),
        )

        # ── 6. Otopark hesabı ────────────────────────────────────────────
        parking_required = self.code.calculate_parking(building.total_construction_area, building_type)
        parking_provided = request.parking_count or parking_required  # Sağlanmadıysa gerekli kadar varsay

        # ── 7. Mevzuat doğrulaması ───────────────────────────────────────
        report = self.code.validate_project(parcel, building, parking_provided)

        # ── 8. Maliyet tahmini ───────────────────────────────────────────
        cost = self.code.estimate_cost(building.total_construction_area, building_type)

        # ── 9. Alan hesap tablosu ────────────────────────────────────────
        area_table = self.code.format_area_table(parcel, building)

        print(f"[{_ts()}] [BUILDER] INFO: Proje tamamlandı — "
              f"TAKS:{report.taks_actual:.3f}/{report.taks_limit}, "
              f"KAKS:{report.kaks_actual:.3f}/{report.kaks_limit}, "
              f"{'✓ Uygun' if report.is_compliant else '✗ İhlal var'}")

        return {
            "parcel": parcel,
            "building": building,
            "report": report,
            "staircase": staircase,
            "cost": cost,
            "area_table": area_table,
        }

    # ── Yardımcı Fonksiyonlar ────────────────────────────────────────────

    def _build_parcel(self, request: ProjectRequest) -> ParcelInfo:
        """NLP çıktısından ParcelInfo oluştur."""
        p = request.parcel
        width = p.width
        depth = p.depth
        area = p.area_m2

        # Alan verilmiş ama boyutlar verilmemişse → kare parsel varsay
        if area > 0 and (width <= 0 or depth <= 0):
            side = math.sqrt(area)
            width = round(side, 1)
            depth = round(side, 1)

        # Hiçbiri verilmemişse → toplam alandan geriye hesapla
        if width <= 0 and depth <= 0 and area <= 0:
            total_area = request.total_area_m2 or 500
            floors = request.floors.normal_floors + (1 if request.floors.ground_floor else 0)
            footprint_need = total_area / max(floors, 1)
            parcel_need = footprint_need / p.taks_limit
            side = math.sqrt(parcel_need) * 1.2  # %20 fazlalık (çekme mesafeleri)
            width = round(side, 1)
            depth = round(side, 1)

        return ParcelInfo(
            width=width,
            depth=depth,
            taks_limit=p.taks_limit,
            kaks_limit=p.kaks_limit,
            max_floors=p.max_floors,
            max_height=p.max_height,
            front_setback=p.front_setback,
            side_setback=p.side_setback,
            rear_setback=p.rear_setback,
            city=p.city,
        )

    def _build_units(self, unit_requests: list[UnitRequest]) -> list[UnitSpec]:
        """NLP çıktısından daire listesi oluştur."""
        units: list[UnitSpec] = []

        for idx, ur in enumerate(unit_requests):
            for i in range(ur.count):
                unit_id = f"{chr(65 + idx)}{i + 1}"  # A1, A2, B1, B2...

                rooms: list[RoomSpec] = []

                # NLP'den gelen odalar
                if ur.rooms:
                    for r in ur.rooms:
                        for _ in range(r.count):
                            area = max(r.min_area_m2, 4.0)
                            w = math.sqrt(area * 0.8)
                            d = area / w
                            rooms.append(RoomSpec(
                                name=r.name,
                                room_type=r.room_type,
                                area=round(area, 1),
                                width=round(w, 2),
                                depth=round(d, 2),
                            ))
                else:
                    # Varsayılan oda listesi
                    defaults = DEFAULT_ROOMS.get(ur.unit_type, DEFAULT_ROOMS["2+1"])
                    target = ur.target_area_m2 or 0
                    default_total = sum(r["min_area_m2"] for r in defaults)
                    scale = target / default_total if target > 0 and default_total > 0 else 1.0

                    for r in defaults:
                        area = round(r["min_area_m2"] * scale, 1)
                        area = max(area, r["min_area_m2"])
                        w = math.sqrt(area * 0.8)
                        d = area / w
                        rooms.append(RoomSpec(
                            name=r["name"],
                            room_type=r["room_type"],
                            area=area,
                            width=round(w, 2),
                            depth=round(d, 2),
                        ))

                units.append(UnitSpec(unit_id=unit_id, rooms=rooms))

        # Hiç daire yoksa, varsayılan 2+1 ekle
        if not units:
            defaults = DEFAULT_ROOMS["2+1"]
            rooms = []
            for r in defaults:
                area = r["min_area_m2"]
                w = math.sqrt(area * 0.8)
                d = area / w
                rooms.append(RoomSpec(
                    name=r["name"],
                    room_type=r["room_type"],
                    area=area,
                    width=round(w, 2),
                    depth=round(d, 2),
                ))
            units.append(UnitSpec(unit_id="A1", rooms=rooms))

        return units
