"""
Türk İmar Mevzuatı Kurallar Motoru
===================================
Planlı Alanlar İmar Yönetmeliği, Otopark Yönetmeliği, Binaların Yangından
Korunması Hakkında Yönetmelik, ve TSE standartlarını kodlar.

Tüm ölçüler metre (m) ve metrekare (m²) cinsindendir.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal


# ══════════════════════════════════════════════════════════════════════════════
# Enums & Constants
# ══════════════════════════════════════════════════════════════════════════════

class BuildingType(str, Enum):
    KONUT = "konut"
    OFIS = "ofis"
    TICARET = "ticaret"
    KARMA = "karma"
    SANAYI = "sanayi"
    EGITIM = "egitim"
    SAGLIK = "saglik"


class ViolationSeverity(str, Enum):
    ERROR = "error"       # Ruhsat engelleyen
    WARNING = "warning"   # Düzeltilmesi gereken
    INFO = "info"         # Bilgilendirme


# ── Minimum Oda Boyutları (TSE + Yönetmelik) ────────────────────────────────

MIN_ROOM_SPECS: dict[str, dict] = {
    "salon": {"min_area": 16.0, "min_width": 3.00, "label": "Salon/Oturma Odası"},
    "yatak_odasi": {"min_area": 9.0, "min_width": 2.60, "label": "Yatak Odası"},
    "mutfak": {"min_area": 5.0, "min_width": 1.80, "label": "Mutfak"},
    "banyo": {"min_area": 3.5, "min_width": 1.50, "label": "Banyo"},
    "wc": {"min_area": 1.2, "min_width": 0.90, "label": "WC"},
    "koridor": {"min_area": 0.0, "min_width": 1.10, "label": "Koridor"},
    "hol": {"min_area": 0.0, "min_width": 1.20, "label": "Giriş Holü"},
    "balkon": {"min_area": 0.0, "min_width": 0.90, "label": "Balkon"},
    "depo": {"min_area": 0.0, "min_width": 0.80, "label": "Depo/Kiler"},
}

# ── Otopark Normları (Otopark Yönetmeliği) ──────────────────────────────────

PARKING_NORMS: dict[str, float] = {
    "konut": 100.0,     # her 100m² için 1 araçlık
    "ofis": 30.0,       # her 30m² için 1
    "ticaret": 30.0,
    "karma": 50.0,
    "sanayi": 75.0,
    "egitim": 50.0,
    "saglik": 50.0,
}

# ── Kat Yükseklikleri ───────────────────────────────────────────────────────

DEFAULT_FLOOR_HEIGHT_GROSS = 2.80   # m (brüt)
DEFAULT_FLOOR_HEIGHT_NET = 2.40     # m (net, min)
DEFAULT_SLAB_THICKNESS = 0.15       # m
DEFAULT_FLOOR_FINISH = 0.05         # m

# ── Merdiven Kuralları ──────────────────────────────────────────────────────

MAX_RISER_HEIGHT = 0.175            # 17.5 cm
MIN_TREAD_DEPTH = 0.25             # 25 cm
MIN_STAIR_WIDTH_RESIDENTIAL = 1.20  # m
MIN_STAIR_WIDTH_OTHER = 1.50        # m
MIN_LANDING_LENGTH = 1.20           # m

# ── Kapı Genişlikleri ───────────────────────────────────────────────────────

MIN_INTERIOR_DOOR = 0.80           # m
MIN_ENTRANCE_DOOR = 0.90           # m
MIN_ACCESSIBLE_DOOR = 1.00         # m
MIN_FIRE_EXIT_DOOR = 0.90          # m

# ── Yangın Yönetmeliği ──────────────────────────────────────────────────────

MAX_ESCAPE_DISTANCE = 30.0         # m (sprinkler yoksa)
MAX_ESCAPE_WITH_SPRINKLER = 45.0   # m
FIRE_STAIR_MIN_WIDTH = 1.20        # m
FIRE_CABINET_AREA = 500.0          # her 500m² için 1 yangın dolabı
HIGH_RISE_THRESHOLD = 21.50        # m — yüksek bina eşiği


# ══════════════════════════════════════════════════════════════════════════════
# Data Classes
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ParcelInfo:
    """Parsel bilgileri — imar durumundan gelir."""
    width: float                          # m
    depth: float                          # m
    area: float = 0.0                     # m² (otomatik hesaplanır)
    taks_limit: float = 0.40              # max TAKS
    kaks_limit: float = 2.00              # max KAKS (emsal)
    max_floors: int = 5
    max_height: float = 15.50             # m
    front_setback: float = 5.0            # m
    side_setback: float = 3.0             # m
    rear_setback: float = 3.0             # m
    frost_depth: float = 0.80             # m
    city: str = "İstanbul"

    def __post_init__(self) -> None:
        if self.area <= 0:
            self.area = self.width * self.depth


@dataclass
class RoomSpec:
    """Oda spesifikasyonu."""
    name: str
    room_type: str                        # salon, yatak_odasi, mutfak, banyo, wc, koridor, hol
    area: float                           # m²
    width: float                          # m
    depth: float                          # m

    @property
    def min_dimension(self) -> float:
        return min(self.width, self.depth)


@dataclass
class UnitSpec:
    """Bağımsız bölüm (daire) spesifikasyonu."""
    unit_id: str                          # "A1", "B2" vb.
    rooms: list[RoomSpec] = field(default_factory=list)

    @property
    def gross_area(self) -> float:
        return sum(r.area for r in self.rooms)

    @property
    def net_area(self) -> float:
        """Net alan ≈ brüt × 0.80 (duvar payı düşmüş)."""
        return self.gross_area * 0.80


@dataclass
class FloorSpec:
    """Kat spesifikasyonu."""
    floor_number: int                     # -1=bodrum, 0=zemin, 1=1.kat ...
    floor_type: Literal["bodrum", "zemin", "normal", "cati"] = "normal"
    units: list[UnitSpec] = field(default_factory=list)
    height_gross: float = DEFAULT_FLOOR_HEIGHT_GROSS
    staircase_area: float = 12.0          # m²
    elevator_area: float = 4.0            # m²
    corridor_area: float = 0.0            # m²

    @property
    def label(self) -> str:
        if self.floor_type == "bodrum":
            return f"B{abs(self.floor_number)}. Bodrum Kat"
        if self.floor_type == "zemin":
            return "Zemin Kat"
        if self.floor_type == "cati":
            return "Çatı Katı"
        return f"{self.floor_number}. Normal Kat"

    @property
    def total_area(self) -> float:
        """Kattaki toplam alan (daireler + ortak alan)."""
        return sum(u.gross_area for u in self.units) + self.staircase_area + self.elevator_area + self.corridor_area

    @property
    def gross_area(self) -> float:
        """Brüt alan — total_area ile aynı, alan tablosu uyumluluğu."""
        return self.total_area


@dataclass
class BuildingSpec:
    """Bina spesifikasyonu."""
    building_type: BuildingType = BuildingType.KONUT
    floors: list[FloorSpec] = field(default_factory=list)
    footprint_width: float = 0.0          # m
    footprint_depth: float = 0.0          # m

    @property
    def footprint_area(self) -> float:
        return self.footprint_width * self.footprint_depth

    @property
    def total_construction_area(self) -> float:
        return sum(f.total_area for f in self.floors)

    @property
    def emsal_area(self) -> float:
        """Emsal alanı = toplam alan - emsal harici alanlar."""
        excluded = 0.0
        for f in self.floors:
            if f.floor_type == "bodrum":
                excluded += f.total_area  # Bodrum otopark emsal dışı
            excluded += f.staircase_area + f.elevator_area
        return self.total_construction_area - excluded

    @property
    def floor_count(self) -> int:
        return len(self.floors)

    @property
    def building_height(self) -> float:
        """Yer üstü bina yüksekliği."""
        return sum(
            f.height_gross for f in self.floors
            if f.floor_type != "bodrum"
        )

    @property
    def total_unit_count(self) -> int:
        return sum(len(f.units) for f in self.floors)

    @property
    def above_ground_floors(self) -> int:
        """Yer üstü kat sayısı (bodrum hariç)."""
        return sum(1 for f in self.floors if f.floor_type != "bodrum")


@dataclass
class StaircaseSpec:
    """Merdiven hesaplama sonucu."""
    riser_count: int
    riser_height: float                   # cm
    tread_depth: float                    # cm
    stair_width: float                    # m
    landing_count: int
    run_length: float                     # m (tek kolun yatay uzunluğu)
    total_area: float                     # m²
    formula: str                          # 2r + t açıklaması


@dataclass
class Violation:
    """Mevzuat ihlali."""
    code: str                             # "TAKS_001", "ROOM_002" vb.
    severity: ViolationSeverity
    category: str                         # "imar", "oda", "yangin", "otopark"
    message_tr: str
    current_value: str
    limit_value: str
    suggestion_tr: str = ""

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "category": self.category,
            "message": self.message_tr,
            "current": self.current_value,
            "limit": self.limit_value,
            "suggestion": self.suggestion_tr,
        }


@dataclass
class ComplianceReport:
    """Mevzuat uyumluluk raporu."""
    violations: list[Violation] = field(default_factory=list)
    taks_actual: float = 0.0
    taks_limit: float = 0.0
    kaks_actual: float = 0.0
    kaks_limit: float = 0.0
    parking_required: int = 0
    parking_provided: int = 0
    building_height: float = 0.0
    max_height: float = 0.0
    is_compliant: bool = True
    generated_at: str = ""
    summary_tr: str = ""

    def __post_init__(self) -> None:
        if not self.generated_at:
            self.generated_at = datetime.now().isoformat()

    @property
    def error_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == ViolationSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == ViolationSeverity.WARNING)

    def to_dict(self) -> dict:
        return {
            "is_compliant": self.is_compliant,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "taks": {"actual": round(self.taks_actual, 4), "limit": self.taks_limit},
            "kaks": {"actual": round(self.kaks_actual, 4), "limit": self.kaks_limit},
            "parking": {"required": self.parking_required, "provided": self.parking_provided},
            "height": {"actual": round(self.building_height, 2), "max": self.max_height},
            "violations": [v.to_dict() for v in self.violations],
            "summary_tr": self.summary_tr,
            "generated_at": self.generated_at,
        }


# ══════════════════════════════════════════════════════════════════════════════
# TurkishBuildingCode — Ana Hesaplama Sınıfı
# ══════════════════════════════════════════════════════════════════════════════

class TurkishBuildingCode:
    """Planlı Alanlar İmar Yönetmeliği hesaplayıcısı."""

    # ── TAKS / KAKS ──────────────────────────────────────────────────────

    @staticmethod
    def calculate_taks(footprint_area: float, parcel_area: float) -> float:
        """Taban Alanı Katsayısı = Bina oturumu / Parsel alanı."""
        if parcel_area <= 0:
            return 0.0
        return footprint_area / parcel_area

    @staticmethod
    def calculate_kaks(emsal_area: float, parcel_area: float) -> float:
        """Kat Alanı Katsayısı (Emsal) = Emsal alanı / Parsel alanı."""
        if parcel_area <= 0:
            return 0.0
        return emsal_area / parcel_area

    # ── Çekme Mesafeleri ─────────────────────────────────────────────────

    @staticmethod
    def calculate_min_side_setback(building_height: float) -> float:
        """Yan bahçe: max(3.00, h/2)."""
        return max(3.0, building_height / 2.0)

    @staticmethod
    def calculate_min_rear_setback(building_height: float) -> float:
        """Arka bahçe: max(3.00, h/2)."""
        return max(3.0, building_height / 2.0)

    @staticmethod
    def calculate_buildable_area(parcel: ParcelInfo, building_height: float) -> tuple[float, float]:
        """
        Çekme mesafelerinden kalan yapılaşılabilir alan.
        Returns: (buildable_width, buildable_depth)
        """
        side = max(parcel.side_setback, building_height / 2.0)
        rear = max(parcel.rear_setback, building_height / 2.0)

        buildable_w = parcel.width - 2 * side
        buildable_d = parcel.depth - parcel.front_setback - rear

        return (max(0, buildable_w), max(0, buildable_d))

    # ── Merdiven Hesabı ──────────────────────────────────────────────────

    @staticmethod
    def calculate_staircase(
        floor_height: float = DEFAULT_FLOOR_HEIGHT_GROSS,
        building_type: BuildingType = BuildingType.KONUT,
    ) -> StaircaseSpec:
        """
        Merdiven hesabı: 2r + t = 60-64cm kuralı.
        """
        stair_width = (
            MIN_STAIR_WIDTH_RESIDENTIAL
            if building_type == BuildingType.KONUT
            else MIN_STAIR_WIDTH_OTHER
        )

        height_cm = floor_height * 100
        riser_height_cm = MAX_RISER_HEIGHT * 100  # 17.5cm

        riser_count = math.ceil(height_cm / riser_height_cm)
        actual_riser = height_cm / riser_count
        tread_depth_cm = 63.0 - 2 * actual_riser  # 2r + t = 63 (ortalama)
        tread_depth_cm = max(tread_depth_cm, MIN_TREAD_DEPTH * 100)

        # İki kollu merdiven varsayımı
        risers_per_run = riser_count // 2
        run_length = risers_per_run * (tread_depth_cm / 100)
        landing_count = 1  # ara sahanlık

        # Merdiven alanı: genişlik × (2 × koşu uzunluğu + sahanlık)
        total_length = 2 * run_length + MIN_LANDING_LENGTH
        total_area = stair_width * total_length

        formula = f"2×{actual_riser:.1f} + {tread_depth_cm:.1f} = {2 * actual_riser + tread_depth_cm:.1f}cm"

        return StaircaseSpec(
            riser_count=riser_count,
            riser_height=round(actual_riser, 1),
            tread_depth=round(tread_depth_cm, 1),
            stair_width=stair_width,
            landing_count=landing_count,
            run_length=round(run_length, 2),
            total_area=round(total_area, 1),
            formula=formula,
        )

    # ── Otopark Hesabı ───────────────────────────────────────────────────

    @staticmethod
    def calculate_parking(
        total_area: float,
        building_type: BuildingType = BuildingType.KONUT,
    ) -> int:
        """Otopark Yönetmeliğine göre gerekli araç sayısı."""
        norm = PARKING_NORMS.get(building_type.value, 100.0)
        return max(1, math.ceil(total_area / norm))

    # ── Oda Boyutu Kontrolü ──────────────────────────────────────────────

    @staticmethod
    def validate_room(room: RoomSpec) -> list[Violation]:
        """Tek bir odanın minimum boyutlarını kontrol et."""
        violations: list[Violation] = []
        spec = MIN_ROOM_SPECS.get(room.room_type)

        if spec is None:
            return violations

        if spec["min_area"] > 0 and room.area < spec["min_area"]:
            violations.append(Violation(
                code=f"ROOM_{room.room_type.upper()}_AREA",
                severity=ViolationSeverity.ERROR,
                category="oda",
                message_tr=f'{spec["label"]} alanı yetersiz',
                current_value=f"{room.area:.1f} m²",
                limit_value=f"min {spec['min_area']:.1f} m²",
                suggestion_tr=f'{spec["label"]} alanını en az {spec["min_area"]:.1f} m² yapın',
            ))

        if spec["min_width"] > 0 and room.min_dimension < spec["min_width"]:
            violations.append(Violation(
                code=f"ROOM_{room.room_type.upper()}_WIDTH",
                severity=ViolationSeverity.ERROR,
                category="oda",
                message_tr=f'{spec["label"]} dar kenarı yetersiz',
                current_value=f"{room.min_dimension:.2f} m",
                limit_value=f"min {spec['min_width']:.2f} m",
                suggestion_tr=f'{spec["label"]} en dar kenarını en az {spec["min_width"]:.2f} m yapın',
            ))

        return violations

    # ── Tam Doğrulama ────────────────────────────────────────────────────

    @classmethod
    def validate_project(
        cls,
        parcel: ParcelInfo,
        building: BuildingSpec,
        parking_provided: int = 0,
    ) -> ComplianceReport:
        """
        Tüm mevzuat kurallarını uygulayarak uyumluluk raporu üret.
        """
        violations: list[Violation] = []

        # ── 1. TAKS / KAKS ──────────────────────────────────────────────

        taks = cls.calculate_taks(building.footprint_area, parcel.area)
        kaks = cls.calculate_kaks(building.emsal_area, parcel.area)

        if taks > parcel.taks_limit:
            violations.append(Violation(
                code="TAKS_001",
                severity=ViolationSeverity.ERROR,
                category="imar",
                message_tr="TAKS (Taban Alanı Katsayısı) sınırı aşılıyor",
                current_value=f"{taks:.4f}",
                limit_value=f"max {parcel.taks_limit:.4f}",
                suggestion_tr=f"Bina oturumunu {parcel.taks_limit * parcel.area:.1f} m²'ye düşürün",
            ))

        if kaks > parcel.kaks_limit:
            violations.append(Violation(
                code="KAKS_001",
                severity=ViolationSeverity.ERROR,
                category="imar",
                message_tr="KAKS (Emsal) sınırı aşılıyor",
                current_value=f"{kaks:.4f}",
                limit_value=f"max {parcel.kaks_limit:.4f}",
                suggestion_tr=f"Toplam emsal alanı {parcel.kaks_limit * parcel.area:.1f} m²'yi geçmemeli",
            ))

        # ── 2. Yükseklik ────────────────────────────────────────────────

        height = building.building_height
        if height > parcel.max_height:
            violations.append(Violation(
                code="HEIGHT_001",
                severity=ViolationSeverity.ERROR,
                category="imar",
                message_tr="Bina yüksekliği sınırı aşılıyor",
                current_value=f"{height:.2f} m",
                limit_value=f"max {parcel.max_height:.2f} m",
                suggestion_tr="Kat sayısını veya kat yüksekliğini azaltın",
            ))

        # ── 3. Kat sayısı ───────────────────────────────────────────────

        above_ground = sum(1 for f in building.floors if f.floor_type != "bodrum")
        if above_ground > parcel.max_floors:
            violations.append(Violation(
                code="FLOOR_001",
                severity=ViolationSeverity.ERROR,
                category="imar",
                message_tr="Kat sayısı sınırı aşılıyor",
                current_value=f"{above_ground} kat",
                limit_value=f"max {parcel.max_floors} kat",
                suggestion_tr="Kat sayısını imar planına uygun hale getirin",
            ))

        # ── 4. Çekme mesafeleri ──────────────────────────────────────────

        buildable_w, buildable_d = cls.calculate_buildable_area(parcel, height)

        if building.footprint_width > buildable_w + 0.01:
            violations.append(Violation(
                code="SETBACK_SIDE",
                severity=ViolationSeverity.ERROR,
                category="imar",
                message_tr="Yan bahçe çekme mesafesi ihlali",
                current_value=f"Bina genişliği: {building.footprint_width:.2f} m",
                limit_value=f"Max yapılaşılabilir: {buildable_w:.2f} m",
                suggestion_tr="Bina genişliğini çekme mesafeleri dahilinde daraltın",
            ))

        if building.footprint_depth > buildable_d + 0.01:
            violations.append(Violation(
                code="SETBACK_FRONT_REAR",
                severity=ViolationSeverity.ERROR,
                category="imar",
                message_tr="Ön/arka bahçe çekme mesafesi ihlali",
                current_value=f"Bina derinliği: {building.footprint_depth:.2f} m",
                limit_value=f"Max yapılaşılabilir: {buildable_d:.2f} m",
                suggestion_tr="Bina derinliğini ön ve arka çekme mesafelerine göre ayarlayın",
            ))

        # ── 5. Oda boyutları ─────────────────────────────────────────────

        for floor in building.floors:
            for unit in floor.units:
                for room in unit.rooms:
                    violations.extend(cls.validate_room(room))

        # ── 6. Otopark ──────────────────────────────────────────────────

        parking_required = cls.calculate_parking(
            building.total_construction_area,
            building.building_type,
        )
        if parking_provided < parking_required:
            violations.append(Violation(
                code="PARK_001",
                severity=ViolationSeverity.ERROR,
                category="otopark",
                message_tr="Otopark sayısı yetersiz",
                current_value=f"{parking_provided} araçlık",
                limit_value=f"min {parking_required} araçlık",
                suggestion_tr=f"En az {parking_required} araçlık otopark sağlayın (bodrum veya açık)",
            ))

        # ── 7. Yangın güvenliği ──────────────────────────────────────────

        if height > HIGH_RISE_THRESHOLD:
            violations.append(Violation(
                code="FIRE_HIGH_RISE",
                severity=ViolationSeverity.WARNING,
                category="yangin",
                message_tr="Yüksek bina — yangın merdiveni zorunlu",
                current_value=f"{height:.2f} m",
                limit_value=f"Eşik: {HIGH_RISE_THRESHOLD} m",
                suggestion_tr="Korunaklı yangın merdiveni, sprinkler sistemi ve duman tahliye planı gerekli",
            ))

        fire_cabinets_needed = max(1, math.ceil(building.total_construction_area / FIRE_CABINET_AREA))
        violations.append(Violation(
            code="FIRE_CABINET",
            severity=ViolationSeverity.INFO,
            category="yangin",
            message_tr=f"Yangın dolabı gereksinimi: {fire_cabinets_needed} adet",
            current_value=f"{building.total_construction_area:.0f} m²",
            limit_value=f"Her {FIRE_CABINET_AREA:.0f} m² için 1 adet",
        ))

        # ── 8. Kat yüksekliği kontrol ────────────────────────────────────

        for floor in building.floors:
            if floor.height_gross < DEFAULT_FLOOR_HEIGHT_GROSS and floor.floor_type != "bodrum":
                violations.append(Violation(
                    code="HEIGHT_FLOOR",
                    severity=ViolationSeverity.ERROR,
                    category="imar",
                    message_tr=f"{floor.label}: Kat yüksekliği yetersiz",
                    current_value=f"{floor.height_gross:.2f} m (brüt)",
                    limit_value=f"min {DEFAULT_FLOOR_HEIGHT_GROSS:.2f} m (brüt)",
                    suggestion_tr="Brüt kat yüksekliğini en az 2.80m yapın",
                ))

        # ── Rapor oluştur ────────────────────────────────────────────────

        is_compliant = all(v.severity != ViolationSeverity.ERROR for v in violations)

        report = ComplianceReport(
            violations=violations,
            taks_actual=taks,
            taks_limit=parcel.taks_limit,
            kaks_actual=kaks,
            kaks_limit=parcel.kaks_limit,
            parking_required=parking_required,
            parking_provided=parking_provided,
            building_height=height,
            max_height=parcel.max_height,
            is_compliant=is_compliant,
        )

        # Türkçe özet
        if is_compliant:
            report.summary_tr = (
                f"✓ Proje mevzuata uygun. "
                f"TAKS: {taks:.3f}/{parcel.taks_limit}, "
                f"KAKS: {kaks:.3f}/{parcel.kaks_limit}, "
                f"Yükseklik: {height:.1f}m/{parcel.max_height:.1f}m, "
                f"{report.warning_count} uyarı."
            )
        else:
            report.summary_tr = (
                f"✗ {report.error_count} mevzuat ihlali tespit edildi. "
                f"TAKS: {taks:.3f}/{parcel.taks_limit}, "
                f"KAKS: {kaks:.3f}/{parcel.kaks_limit}. "
                f"Detaylar için ihlal listesini inceleyin."
            )

        return report

    # ── Yardımcı Hesaplamalar ────────────────────────────────────────────

    @staticmethod
    def estimate_cost(total_area: float, building_type: BuildingType) -> dict:
        """
        Yaklaşık maliyet tahmini (2024 Türkiye m² birim fiyatları).
        Kaynak: Çevre, Şehircilik ve İklim Değişikliği Bakanlığı yapı yaklaşık birim fiyatları.
        """
        unit_costs = {
            "konut": {"low": 12_000, "mid": 18_000, "high": 28_000},
            "ofis": {"low": 15_000, "mid": 22_000, "high": 35_000},
            "ticaret": {"low": 14_000, "mid": 20_000, "high": 30_000},
            "karma": {"low": 14_000, "mid": 20_000, "high": 30_000},
            "sanayi": {"low": 8_000, "mid": 12_000, "high": 18_000},
            "egitim": {"low": 15_000, "mid": 22_000, "high": 32_000},
            "saglik": {"low": 20_000, "mid": 30_000, "high": 45_000},
        }

        costs = unit_costs.get(building_type.value, unit_costs["konut"])

        return {
            "total_area_m2": round(total_area, 1),
            "unit_costs_tl": costs,
            "estimates_tl": {
                "low": int(total_area * costs["low"]),
                "mid": int(total_area * costs["mid"]),
                "high": int(total_area * costs["high"]),
            },
            "currency": "TRY",
            "note": "2024 Bakanlık yapı yaklaşık birim fiyatları baz alınmıştır",
        }

    @staticmethod
    def format_area_table(parcel: ParcelInfo, building: BuildingSpec) -> dict:
        """Belediye sunumu için alan hesap tablosu."""
        floor_areas = []
        for f in building.floors:
            floor_areas.append({
                "label": f.label,
                "floor_type": f.floor_type,
                "area": round(f.total_area, 2),
                "unit_count": len(f.units),
                "units": [
                    {"id": u.unit_id, "gross": round(u.gross_area, 2), "net": round(u.net_area, 2)}
                    for u in f.units
                ],
            })

        return {
            "parcel_area": round(parcel.area, 2),
            "footprint_area": round(building.footprint_area, 2),
            "total_construction_area": round(building.total_construction_area, 2),
            "emsal_area": round(building.emsal_area, 2),
            "taks": round(building.footprint_area / parcel.area, 4) if parcel.area > 0 else 0,
            "kaks": round(building.emsal_area / parcel.area, 4) if parcel.area > 0 else 0,
            "building_height": round(building.building_height, 2),
            "floor_count": building.floor_count,
            "total_units": building.total_unit_count,
            "floors": floor_areas,
        }
