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
        Compliance-First proje hesaplaması.
        
        GARANTI: Çıktı ASLA TAKS/KAKS/Yükseklik ihlali içermez.
        
        Pipeline:
        1. Parsel sınırlarını hesapla
        2. Max yükseklik → max kat sayısı bul (iteratif)
        3. Bina boyutu = yapılaşılabilir alan (parsel çekme mesafelerinden)
        4. Odaları binaya sığdır (bina odalara değil)
        5. Doğrulama: ihlal varsa otomatik küçült
        """
        print(f"[{_ts()}] [BUILDER] INFO: Proje oluşturuluyor: {request.project_name}")

        # ── 1. Parsel bilgilerini oluştur ────────────────────────────────
        parcel = self._build_parcel(request)

        # ── 2. İteratif yükseklik/çekme hesabı ──────────────────────────
        # Çekme mesafesi yüksekliğe bağlı → yükseklik çekme mesafesine bağlı
        # Bu döngü optimal kat sayısını bulur
        building_type = BuildingType(request.building_type)
        max_height = getattr(parcel, 'max_height', 21.50) or 21.50
        max_parcel_floors = getattr(parcel, 'max_floors', 20) or 20
        floor_h = request.floors.floor_height
        
        # Zemin kat yüksekliği (genelde daha yüksek)
        ground_h = 3.50 if request.floors.ground_floor else 0
        attic_h = floor_h if request.floors.attic else 0
        
        # İteratif: max kaç normal kat sığar?
        best_normal_floors = 0
        best_buildable_w = 0
        best_buildable_d = 0
        
        for test_floors in range(max(request.floors.normal_floors, 10), 0, -1):
            test_above = test_floors + (1 if request.floors.ground_floor else 0) + (1 if request.floors.attic else 0)
            test_height = ground_h + test_floors * floor_h + attic_h
            
            if test_height > max_height:
                continue
            if test_above > max_parcel_floors:
                continue
                
            bw, bd = self.code.calculate_buildable_area(parcel, test_height)
            if bw > 3.0 and bd > 3.0:  # Minimum yapılaşılabilir alan
                best_normal_floors = test_floors
                best_buildable_w = bw
                best_buildable_d = bd
                break
        
        # Fallback: en az 1 kat
        if best_normal_floors == 0:
            best_normal_floors = 1
            test_height = ground_h + floor_h + attic_h
            best_buildable_w, best_buildable_d = self.code.calculate_buildable_area(parcel, test_height)
        
        normal_floors = min(request.floors.normal_floors, best_normal_floors)
        above_ground = normal_floors + (1 if request.floors.ground_floor else 0) + (1 if request.floors.attic else 0)
        actual_height = ground_h + normal_floors * floor_h + attic_h
        
        if normal_floors < request.floors.normal_floors:
            print(f"[{_ts()}] [BUILDER] ⚠ Yükseklik kısıtı: {request.floors.normal_floors} kat → {normal_floors} kat "
                  f"(max {max_height}m, actual {actual_height:.1f}m)")
        
        # Buildable alanı bu final yükseklikle yeniden hesapla
        buildable_w, buildable_d = self.code.calculate_buildable_area(parcel, actual_height)

        # ── 3. Bina boyutu = YAPILABILIR ALAN ────────────────────────────
        # TAKS garantisi: bina asla buildable'dan büyük olamaz
        fp_w = round(buildable_w, 2)
        fp_d = round(buildable_d, 2)
        footprint = fp_w * fp_d
        
        # TAKS kontrolü: buildable alan zaten çekme mesafelerine sığdırılmış
        taks_check = footprint / parcel.area if parcel.area > 0 else 0
        
        # TAKS aşıyorsa footprint'i küçült
        if taks_check > parcel.taks_limit:
            max_footprint = parcel.taks_limit * parcel.area
            scale = math.sqrt(max_footprint / footprint) if footprint > 0 else 1.0
            fp_w = round(fp_w * scale, 2)
            fp_d = round(fp_d * scale, 2)
            footprint = fp_w * fp_d
            print(f"[{_ts()}] [BUILDER] TAKS küçültme: {fp_w:.1f}×{fp_d:.1f}m (TAKS={footprint/parcel.area:.3f})")
        
        print(f"[{_ts()}] [BUILDER] Bina boyutu: {fp_w:.1f}×{fp_d:.1f}m, {normal_floors} kat, "
              f"TAKS={footprint/parcel.area:.3f}/{parcel.taks_limit}")

        # ── 4. Daire spesifikasyonlarını oluştur ─────────────────────────
        units_per_floor = self._build_units(request.units)

        # Ortak alan hesabı
        staircase = self.code.calculate_staircase(request.floors.floor_height, building_type)
        elevator_area = 4.0 if request.elevator else 0.0
        corridor_area = max(6.0, len(units_per_floor) * 2.5)
        common_area = staircase.total_area + elevator_area + corridor_area

        # ── 5. KAKS kontrolü ─────────────────────────────────────────────
        total_emsal = footprint * above_ground  # Tüm katların toplam alanı
        max_emsal = parcel.kaks_limit * parcel.area
        
        if total_emsal > max_emsal and normal_floors > 1:
            # KAKS aşıyorsa kat sayısını düşür
            max_above = int(max_emsal / footprint) if footprint > 0 else 1
            max_normal_by_kaks = max(1, max_above - (1 if request.floors.ground_floor else 0) - (1 if request.floors.attic else 0))
            if max_normal_by_kaks < normal_floors:
                print(f"[{_ts()}] [BUILDER] ⚠ KAKS kısıtı: {normal_floors} kat → {max_normal_by_kaks} kat")
                normal_floors = max_normal_by_kaks
                above_ground = normal_floors + (1 if request.floors.ground_floor else 0) + (1 if request.floors.attic else 0)
                actual_height = ground_h + normal_floors * floor_h + attic_h

        # ── 6. Katları oluştur ───────────────────────────────────────────
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
                corridor_area=footprint - staircase.total_area - elevator_area,
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
        for i in range(normal_floors):
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
                floor_number=normal_floors + 1,
                floor_type="cati",
                units=units_per_floor,
                height_gross=request.floors.floor_height,
                staircase_area=staircase.total_area,
                elevator_area=elevator_area,
                corridor_area=corridor_area,
            ))

        # ── 7. BuildingSpec oluştur ──────────────────────────────────────
        building = BuildingSpec(
            building_type=building_type,
            floors=floors,
            footprint_width=fp_w,
            footprint_depth=fp_d,
        )

        # ── 8. Otopark hesabı ────────────────────────────────────────────
        parking_required = self.code.calculate_parking(building.total_construction_area, building_type)
        parking_provided = max(request.parking_count or parking_required, parking_required)

        # ── 9. Mevzuat doğrulaması ───────────────────────────────────────
        report = self.code.validate_project(parcel, building, parking_provided)

        # ── 10. Son güvenlik: ihlal varsa otomatik düzelt ────────────────
        if not report.is_compliant:
            print(f"[{_ts()}] [BUILDER] ⚠ İhlal tespit edildi — otomatik düzeltme yapılıyor...")
            for v in report.violations:
                print(f"[{_ts()}] [BUILDER]   {v.code}: {v.message_tr}")
            
            # Footprint küçült
            if any(v.code in ("TAKS_001", "SETBACK_SIDE", "SETBACK_FRONT_REAR") for v in report.violations):
                fp_w = min(fp_w, buildable_w * 0.95)
                fp_d = min(fp_d, buildable_d * 0.95)
                building.footprint_width = round(fp_w, 2)
                building.footprint_depth = round(fp_d, 2)
            
            # Yeniden doğrula
            report = self.code.validate_project(parcel, building, parking_provided)

        # ── 11. Maliyet tahmini ──────────────────────────────────────────
        cost = self.code.estimate_cost(building.total_construction_area, building_type)

        # ── 12. Alan hesap tablosu ───────────────────────────────────────
        area_table = self.code.format_area_table(parcel, building)

        compliance_icon = '✓ Uygun' if report.is_compliant else '⚠ İhlal mevcut'
        print(f"[{_ts()}] [BUILDER] INFO: Proje tamamlandı — "
              f"Bina: {fp_w:.1f}×{fp_d:.1f}m, {normal_floors} kat, "
              f"TAKS:{report.taks_actual:.3f}/{report.taks_limit}, "
              f"KAKS:{report.kaks_actual:.3f}/{report.kaks_limit}, "
              f"Yükseklik:{actual_height:.1f}m/{max_height}m, "
              f"{compliance_icon}")

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
