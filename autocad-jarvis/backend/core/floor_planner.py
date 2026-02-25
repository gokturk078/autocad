"""
Profesyonel Kat Planı Algoritması v4.0 (Floor Planner)
======================================================
Çift çizgili duvar, hedef alan ± %5 fitting, çakışmasız oda
yerleşimi, kapı/pencere açıklıkları, aks grid sistemi.

Algoritma:
1. Bina dış sınır → duvar kalınlığı ile iç net alan hesapla
2. Çekirdek (merdiven + asansör) koridor ucuna yerleştir
3. Koridor omurgası — çekirdeğe hizalı
4. Kalan alanı Kuzey / Güney zonlara böl
5. Her zon → dairelere böl (duvar kalınlıkları dahil)
6. Her daire → oda yerleşimi (target area ± %5)
7. Kapı/pencere açıklıkları → duvar polyline gap
8. Aks grid veri yapısı
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from core.regulations import (
    BuildingSpec,
    FloorSpec,
    RoomSpec,
    UnitSpec,
)

# ══════════════════════════════════════════════════════════════════════════════
# Sabitler
# ══════════════════════════════════════════════════════════════════════════════

EXT_WALL = 0.25       # m — dış duvar kalınlığı
INT_WALL = 0.10       # m — iç duvar kalınlığı
PARTITION = 0.07      # m — bölme duvar

CORRIDOR_WIDTH = 1.40  # m — koridor net genişlik
MIN_ROOM_DIM = 2.40    # m — oda minimum kenar uzunluğu

# ── Oda Boyut Tablosu (min_w, max_w, min_d, max_d, min_area) ────────────
ROOM_DEFAULTS: dict[str, dict] = {
    "salon":       {"min_w": 4.5, "max_w": 6.5, "min_d": 5.0, "max_d": 7.0, "min_area": 22},
    "yatak_odasi": {"min_w": 3.0, "max_w": 4.5, "min_d": 3.5, "max_d": 5.0, "min_area": 12},
    "mutfak":      {"min_w": 2.5, "max_w": 4.0, "min_d": 3.0, "max_d": 4.5, "min_area": 8},
    "banyo":       {"min_w": 1.8, "max_w": 2.8, "min_d": 2.2, "max_d": 3.0, "min_area": 4},
    "wc":          {"min_w": 0.9, "max_w": 1.5, "min_d": 1.5, "max_d": 2.0, "min_area": 1.5},
    "hol":         {"min_w": 1.5, "max_w": 3.0, "min_d": 2.0, "max_d": 3.5, "min_area": 4},
    "koridor":     {"min_w": 1.2, "max_w": 2.0, "min_d": 3.0, "max_d": 10.0, "min_area": 4},
    "balkon":      {"min_w": 1.5, "max_w": 3.0, "min_d": 1.2, "max_d": 2.5, "min_area": 3},
    "giyinme":     {"min_w": 1.5, "max_w": 2.5, "min_d": 2.0, "max_d": 3.0, "min_area": 4},
    "depo":        {"min_w": 1.0, "max_w": 2.0, "min_d": 1.5, "max_d": 2.5, "min_area": 2},
}

# ── Pencere Boyutu → Oda Tipine Göre ─────────────────────────────────────
WINDOW_BY_ROOM: dict[str, str] = {
    "salon":       "WINDOW_200x150",
    "yatak_odasi": "WINDOW_150x150",
    "mutfak":      "WINDOW_100x120",
    "banyo":       "WINDOW_60x60",
    "wc":          "WINDOW_60x60",
    "balkon":      "WINDOW_240x220",
}

STAIR_W = 2.50         # m — U-tipi merdiven genişliği
STAIR_D = 5.60         # m — U-tipi merdiven derinliği
ELEV_W = 1.60          # m — asansör kabini genişlik
ELEV_D = 1.80          # m — asansör kabini derinlik
ELEV_GAP = 0.30        # m — asansör-merdiven arası boşluk


# ══════════════════════════════════════════════════════════════════════════════
# Veri Yapıları
# ══════════════════════════════════════════════════════════════════════════════

class WallType(str, Enum):
    EXTERIOR = "exterior"
    INTERIOR = "interior"
    PARTITION = "partition"


@dataclass
class WallOpening:
    """Duvar üzerindeki kapı veya pencere açıklığı."""
    offset: float           # duvarın başlangıcından mesafe (m)
    width: float            # açıklık genişliği (m)
    opening_type: str       # "door" | "window"
    block_name: str = ""    # DXF block adı
    height: float = 0.0     # pencere yüksekliği (m)


@dataclass
class Wall:
    """
    Çift çizgili duvar segmenti.
    start/end merkez çizgi noktaları.
    Kalınlık ± t/2 offset ile iç/dış yüzey oluşturur.
    """
    start: tuple[float, float]
    end: tuple[float, float]
    thickness: float
    wall_type: WallType
    layer: str = "A-WALL"
    openings: list[WallOpening] = field(default_factory=list)

    @property
    def length(self) -> float:
        dx = self.end[0] - self.start[0]
        dy = self.end[1] - self.start[1]
        return math.sqrt(dx * dx + dy * dy)

    @property
    def is_horizontal(self) -> bool:
        return abs(self.end[1] - self.start[1]) < 0.001

    @property
    def is_vertical(self) -> bool:
        return abs(self.end[0] - self.start[0]) < 0.001

    @property
    def inner_lines(self) -> list[tuple[tuple[float, float], tuple[float, float]]]:
        """Açıklıkları dikkate alarak iç yüz çizgi segmentleri döndür."""
        return self._offset_with_openings(-self.thickness / 2)

    @property
    def outer_lines(self) -> list[tuple[tuple[float, float], tuple[float, float]]]:
        """Açıklıkları dikkate alarak dış yüz çizgi segmentleri döndür."""
        return self._offset_with_openings(+self.thickness / 2)

    def _offset_with_openings(
        self, offset: float,
    ) -> list[tuple[tuple[float, float], tuple[float, float]]]:
        """
        Merkez çizgiyi offset kadar kaydır, açıklık yerlerinde boşluk bırak.
        """
        sx, sy = self.start
        ex, ey = self.end

        # Yön vektörü
        dx = ex - sx
        dy = ey - sy
        length = math.sqrt(dx * dx + dy * dy)
        if length < 0.001:
            return []

        ux, uy = dx / length, dy / length        # birim yön
        nx, ny = -uy * offset, ux * offset        # normal offset

        # Offset edilmiş başlangıç/bitiş
        osx, osy = sx + nx, sy + ny
        oex, oey = ex + nx, ey + ny

        if not self.openings:
            return [((osx, osy), (oex, oey))]

        # Açıklıkları sırala
        sorted_opens = sorted(self.openings, key=lambda o: o.offset)
        segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
        cursor = 0.0

        for op in sorted_opens:
            gap_start = op.offset
            gap_end = op.offset + op.width

            if gap_start > cursor + 0.001:
                # Açıklık öncesi segment
                p1 = (osx + ux * cursor, osy + uy * cursor)
                p2 = (osx + ux * gap_start, osy + uy * gap_start)
                segments.append((p1, p2))

            cursor = gap_end

        # Son segment
        if cursor < length - 0.001:
            p1 = (osx + ux * cursor, osy + uy * cursor)
            p2 = (oex, oey)
            segments.append((p1, p2))

        return segments

    @property
    def hatch_polygons(self) -> list[list[tuple[float, float]]]:
        """
        Duvar kesit hatch'i için kapalı polygon verileri.
        Her solid duvar parçası (açıklıklar arası) ayrı polygon.
        """
        sx, sy = self.start
        ex, ey = self.end
        t = self.thickness
        dx = ex - sx
        dy = ey - sy
        length = math.sqrt(dx * dx + dy * dy)
        if length < 0.001:
            return []

        ux, uy = dx / length, dy / length
        nx, ny = -uy, ux  # birim normal

        # İç/dış offset
        half = t / 2
        inx, iny = nx * (-half), ny * (-half)
        outx, outy = nx * half, ny * half

        # Açıklık olmayan bölgeleri hesapla
        sorted_opens = sorted(self.openings, key=lambda o: o.offset)
        solid_ranges: list[tuple[float, float]] = []
        cursor = 0.0

        for op in sorted_opens:
            if op.offset > cursor + 0.001:
                solid_ranges.append((cursor, op.offset))
            cursor = op.offset + op.width

        if cursor < length - 0.001:
            solid_ranges.append((cursor, length))

        if not solid_ranges and not sorted_opens:
            solid_ranges = [(0.0, length)]

        polys = []
        for a, b in solid_ranges:
            # 4 köşe: iç-başlangıç, iç-bitiş, dış-bitiş, dış-başlangıç
            p1 = (sx + ux * a + inx, sy + uy * a + iny)
            p2 = (sx + ux * b + inx, sy + uy * b + iny)
            p3 = (sx + ux * b + outx, sy + uy * b + outy)
            p4 = (sx + ux * a + outx, sy + uy * a + outy)
            polys.append([p1, p2, p3, p4])

        return polys


@dataclass
class PlacedRoom:
    """Yerleştirilmiş oda — iç net alan."""
    name: str
    room_type: str
    x: float                # sol alt x (iç net)
    y: float                # sol alt y (iç net)
    width: float            # iç net genişlik
    depth: float            # iç net derinlik
    unit_id: str = ""
    hatch_pattern: str = "" # boş = hatch yok, "ANSI37" = banyo vb.

    @property
    def area(self) -> float:
        return self.width * self.depth

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.depth / 2)

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        return (self.x, self.y, self.x + self.width, self.y + self.depth)


@dataclass
class PlacedDoor:
    """Yerleştirilmiş kapı."""
    x: float
    y: float
    width: float
    rotation: float = 0.0
    block_name: str = "DOOR_90"
    is_exterior: bool = False
    mirror: bool = False


@dataclass
class PlacedWindow:
    """Yerleştirilmiş pencere."""
    x: float
    y: float
    width: float
    height: float = 1.50
    rotation: float = 0.0
    block_name: str = "WINDOW_150x150"
    wall_side: Literal["north", "south", "east", "west"] = "south"


@dataclass
class Column:
    """Yapısal kolon."""
    x: float
    y: float
    size: float = 0.40
    block_name: str = "COLUMN_40x40"


@dataclass
class AxisLine:
    """Aks çizgisi."""
    label: str              # "A", "B", "1", "2"
    direction: str          # "horizontal" | "vertical"
    position: float         # x veya y koordinatı
    start: float            # çizgi başlangıçı
    end: float              # çizgi bitişi


@dataclass
class FloorPlanResult:
    """Kat planı üretim sonucu."""
    floor_number: int
    floor_type: str
    building_width: float
    building_depth: float

    walls: list[Wall] = field(default_factory=list)
    rooms: list[PlacedRoom] = field(default_factory=list)
    doors: list[PlacedDoor] = field(default_factory=list)
    windows: list[PlacedWindow] = field(default_factory=list)
    columns: list[Column] = field(default_factory=list)
    axes: list[AxisLine] = field(default_factory=list)

    stair_x: float = 0.0
    stair_y: float = 0.0
    stair_block: str = "STAIR_U"

    elevator_x: float = 0.0
    elevator_y: float = 0.0
    has_elevator: bool = False

    @property
    def net_width(self) -> float:
        """İç net genişlik (dış duvar hariç)."""
        return self.building_width - 2 * EXT_WALL

    @property
    def net_depth(self) -> float:
        """İç net derinlik (dış duvar hariç)."""
        return self.building_depth - 2 * EXT_WALL


# ══════════════════════════════════════════════════════════════════════════════
# FloorPlanner v4.0
# ══════════════════════════════════════════════════════════════════════════════

class FloorPlanner:
    """
    Profesyonel kat planı üretici.

    Çift çizgili duvar, hedef alan fitting, çakışmasız yerleşim.
    """

    def __init__(self) -> None:
        self.ext_wall = EXT_WALL
        self.int_wall = INT_WALL

    # ── Ana entry point ──────────────────────────────────────────────────

    def plan_floor(
        self,
        floor: FloorSpec,
        building_w: float,
        building_d: float,
        has_elevator: bool = False,
    ) -> FloorPlanResult:
        """Tek bir kat planı üret."""
        result = FloorPlanResult(
            floor_number=floor.floor_number,
            floor_type=floor.floor_type,
            building_width=building_w,
            building_depth=building_d,
            has_elevator=has_elevator,
        )

        # 1. Dış duvarlar (çift çizgi)
        self._create_exterior_walls(result)

        # 2. Yapısal kolonlar + aks grid
        self._create_columns_and_axes(result)

        # 3. Çekirdek: merdiven + asansör (koridor ucunda)
        core_end_x = self._create_core(result, has_elevator)

        # 4. Koridor omurgası
        corridor_y_bottom, corridor_y_top = self._create_corridor(result, core_end_x)

        # 5. Daireleri yerleştir (kuzey + güney zonlar)
        self._place_units(result, floor.units, corridor_y_bottom, corridor_y_top, core_end_x)

        # 6. Pencereler — dış duvara temas eden odalara
        self._place_windows(result)

        # 7. Kapılar — her odaya
        self._place_doors(result, corridor_y_bottom, corridor_y_top)

        # 8. Bina giriş kapısı
        self._place_entrance(result)

        return result

    # ══════════════════════════════════════════════════════════════════════
    # 1. Dış Duvarlar
    # ══════════════════════════════════════════════════════════════════════

    def _create_exterior_walls(self, r: FloorPlanResult) -> None:
        """4 dış duvar — çift çizgi, EXT_WALL kalınlık."""
        w, d = r.building_width, r.building_depth
        t = self.ext_wall
        half = t / 2

        # Merkez çizgi dış duvar kenarından t/2 içeride
        # Güney duvar (alt)
        r.walls.append(Wall(
            start=(0, half), end=(w, half),
            thickness=t, wall_type=WallType.EXTERIOR, layer="A-WALL",
        ))
        # Kuzey duvar (üst)
        r.walls.append(Wall(
            start=(0, d - half), end=(w, d - half),
            thickness=t, wall_type=WallType.EXTERIOR, layer="A-WALL",
        ))
        # Batı duvar (sol)
        r.walls.append(Wall(
            start=(half, 0), end=(half, d),
            thickness=t, wall_type=WallType.EXTERIOR, layer="A-WALL",
        ))
        # Doğu duvar (sağ)
        r.walls.append(Wall(
            start=(w - half, 0), end=(w - half, d),
            thickness=t, wall_type=WallType.EXTERIOR, layer="A-WALL",
        ))

    # ══════════════════════════════════════════════════════════════════════
    # 2. Kolonlar + Aks Grid
    # ══════════════════════════════════════════════════════════════════════

    def _create_columns_and_axes(self, r: FloorPlanResult) -> None:
        """Kolon aksları A-B-C / 1-2-3 ve kolonlar."""
        w, d = r.building_width, r.building_depth
        ew = self.ext_wall

        # X aksları (soldan sağa) — ~5-7m arası
        grid_x = _compute_grid_positions(ew, w - ew, max_spacing=6.5)
        # Y aksları (alttan yukarıya)
        grid_y = _compute_grid_positions(ew, d - ew, max_spacing=6.5)

        # Aks çizgileri
        for i, gx in enumerate(grid_x):
            label = chr(65 + i)  # A, B, C, ...
            r.axes.append(AxisLine(
                label=label, direction="vertical",
                position=gx, start=-1.5, end=d + 1.5,
            ))

        for i, gy in enumerate(grid_y):
            label = str(i + 1)  # 1, 2, 3, ...
            r.axes.append(AxisLine(
                label=label, direction="horizontal",
                position=gy, start=-1.5, end=w + 1.5,
            ))

        # Kolonlar — aks kesişim noktaları
        for gx in grid_x:
            for gy in grid_y:
                r.columns.append(Column(x=gx, y=gy))

    # ══════════════════════════════════════════════════════════════════════
    # 3. Çekirdek (Merdiven + Asansör)
    # ══════════════════════════════════════════════════════════════════════

    def _create_core(self, r: FloorPlanResult, has_elevator: bool) -> float:
        """
        Merdiven ve asansörü bina sol tarafına yerleştir (koridor ucunda).
        Returns: çekirdek bölgesinin bina içindeki sağ sınırı (x).
        """
        ew = self.ext_wall
        half_d = r.building_depth / 2

        # Merdiven — sol duvar iç yüzeyinden 0.3m gap
        stair_x = ew + 0.30
        stair_y = half_d - STAIR_D / 2

        r.stair_x = stair_x
        r.stair_y = stair_y
        r.stair_block = "STAIR_U"

        core_right = stair_x + STAIR_W

        if has_elevator:
            elev_x = core_right + ELEV_GAP
            elev_y = half_d - ELEV_D / 2
            r.elevator_x = elev_x
            r.elevator_y = elev_y
            r.has_elevator = True
            core_right = elev_x + ELEV_W

        # Çekirdek etrafına duvarlar
        core_left = ew
        core_top = stair_y + STAIR_D
        core_bottom = stair_y
        core_right_wall = core_right + 0.20  # 20cm gap + duvar

        # Çekirdek sağ duvar
        r.walls.append(Wall(
            start=(core_right_wall, core_bottom),
            end=(core_right_wall, core_top),
            thickness=self.int_wall, wall_type=WallType.INTERIOR,
            layer="A-WALL-INT",
        ))

        # Merdiven holü oda olarak
        r.rooms.append(PlacedRoom(
            name="Merdiven Holü",
            room_type="hol",
            x=stair_x, y=core_bottom,
            width=core_right_wall - stair_x - self.int_wall / 2,
            depth=STAIR_D,
            unit_id="COMMON",
        ))

        return core_right_wall + self.int_wall / 2

    # ══════════════════════════════════════════════════════════════════════
    # 4. Koridor
    # ══════════════════════════════════════════════════════════════════════

    def _create_corridor(
        self, r: FloorPlanResult, core_end_x: float,
    ) -> tuple[float, float]:
        """
        Ana koridor — bina ortasında, çekirdeğe hizalı.
        Returns: (corridor_y_bottom, corridor_y_top) iç net sınırlar.
        """
        half_d = r.building_depth / 2
        half_c = CORRIDOR_WIDTH / 2
        ew = self.ext_wall

        corridor_y_center = half_d
        corridor_bottom = corridor_y_center - half_c
        corridor_top = corridor_y_center + half_c

        # Koridor alt duvar (merkez çizgi = corridor_bottom)
        r.walls.append(Wall(
            start=(core_end_x, corridor_bottom),
            end=(r.building_width - ew, corridor_bottom),
            thickness=self.int_wall, wall_type=WallType.INTERIOR,
            layer="A-WALL-INT",
        ))
        # Koridor üst duvar
        r.walls.append(Wall(
            start=(core_end_x, corridor_top),
            end=(r.building_width - ew, corridor_top),
            thickness=self.int_wall, wall_type=WallType.INTERIOR,
            layer="A-WALL-INT",
        ))

        # Koridor oda
        r.rooms.append(PlacedRoom(
            name="Koridor",
            room_type="koridor",
            x=core_end_x,
            y=corridor_bottom + self.int_wall / 2,
            width=(r.building_width - ew) - core_end_x,
            depth=CORRIDOR_WIDTH - self.int_wall,
            unit_id="COMMON",
        ))

        return corridor_bottom, corridor_top

    # ══════════════════════════════════════════════════════════════════════
    # 5. Daire Yerleşimi
    # ══════════════════════════════════════════════════════════════════════

    def _place_units(
        self,
        r: FloorPlanResult,
        units: list[UnitSpec],
        corridor_bottom: float,
        corridor_top: float,
        core_end_x: float,
    ) -> None:
        """
        Daireleri kuzey ve güney zonlara dağıt.
        """
        ew = self.ext_wall
        iw = self.int_wall

        # Kullanılabilir genişlik: çekirdek sonu → dış duvar iç yüz
        avail_x_start = core_end_x
        avail_x_end = r.building_width - ew

        # Güney zon: dış duvar iç yüz → koridor alt duvar iç yüz
        south_y_start = ew
        south_y_end = corridor_bottom - iw / 2
        south_depth = south_y_end - south_y_start

        # Kuzey zon: koridor üst duvar iç yüz → dış duvar iç yüz
        north_y_start = corridor_top + iw / 2
        north_y_end = r.building_depth - ew
        north_depth = north_y_end - north_y_start

        unit_count = len(units)
        if unit_count == 0:
            return

        # Daireleri ikiye böl
        south_count = unit_count // 2
        north_count = unit_count - south_count

        if south_count == 0:
            south_count = 1
            north_count = unit_count - 1
            if north_count <= 0:
                north_count = 0

        south_units = units[:south_count]
        north_units = units[south_count:]

        avail_w = avail_x_end - avail_x_start

        # Güney zona yerleştir
        if south_units:
            self._layout_zone(
                r, south_units,
                zone_x=avail_x_start, zone_y=south_y_start,
                zone_w=avail_w, zone_h=south_depth,
                facade="south",
            )

        # Kuzey zona yerleştir
        if north_units:
            self._layout_zone(
                r, north_units,
                zone_x=avail_x_start, zone_y=north_y_start,
                zone_w=avail_w, zone_h=north_depth,
                facade="north",
            )

    def _layout_zone(
        self,
        r: FloorPlanResult,
        units: list[UnitSpec],
        zone_x: float, zone_y: float,
        zone_w: float, zone_h: float,
        facade: str,
    ) -> None:
        """Bir zon içinde daireleri yan yana yerleştir."""
        n = len(units)
        if n == 0:
            return

        iw = self.int_wall
        total_wall_space = (n - 1) * iw
        unit_w = (zone_w - total_wall_space) / n

        for i, unit in enumerate(units):
            ux = zone_x + i * (unit_w + iw)

            # Daire ayırıcı duvar
            if i > 0:
                sep_x = ux - iw / 2
                r.walls.append(Wall(
                    start=(sep_x, zone_y),
                    end=(sep_x, zone_y + zone_h),
                    thickness=iw, wall_type=WallType.INTERIOR,
                    layer="A-WALL-INT",
                ))

            # Odaları yerleştir
            self._layout_rooms(r, unit, ux, zone_y, unit_w, zone_h, facade)

    def _layout_rooms(
        self,
        r: FloorPlanResult,
        unit: UnitSpec,
        ux: float, uy: float,
        unit_w: float, unit_h: float,
        facade: str,
    ) -> None:
        """
        Tek daire içinde odaları constraint-based grid pack ile yerleştir.

        Strateji:
        - CEPHE SIRASI: Salon + Yatak odaları → dış duvar (büyük pencereler)
        - İÇ SIRA: Hol + Mutfak + Banyo + WC → koridor tarafı (tesisat şaftı)
        - Her oda ROOM_DEFAULTS tablosundan gerçekçi boyut alır
        - Aspect ratio 1:1 ile 1:2 arasında zorlanır
        """
        rooms = unit.rooms
        if not rooms:
            return

        iw = self.int_wall

        # ── Odaları kategorize ────────────────────────────────────────
        facade_rooms = [rm for rm in rooms if rm.room_type in ("salon", "yatak_odasi")]
        inner_rooms = [rm for rm in rooms if rm.room_type in ("mutfak", "banyo", "wc")]
        other_rooms = [rm for rm in rooms if rm.room_type in ("hol", "koridor", "balkon", "depo", "giyinme")]

        # Hol'ü iç sıranın başına ekle
        hol_rooms = [rm for rm in other_rooms if rm.room_type == "hol"]
        inner_with_hol = hol_rooms + inner_rooms

        # ── Derinlik hesaplaması ──────────────────────────────────────
        # Cephe sırası: odaların ortalama derinliğine göre
        available_h = unit_h - iw  # araya duvar girer

        # Cephe odaları daha derin (salon, yatak), iç odalar daha sığ (banyo, wc)
        facade_default_depth = 0
        if facade_rooms:
            facade_depths = []
            for rm in facade_rooms:
                rd = ROOM_DEFAULTS.get(rm.room_type, {})
                target_d = (rd.get("min_d", 3.5) + rd.get("max_d", 5.0)) / 2
                facade_depths.append(target_d)
            facade_default_depth = sum(facade_depths) / len(facade_depths)

        inner_default_depth = 0
        if inner_with_hol:
            inner_depths = []
            for rm in inner_with_hol:
                rd = ROOM_DEFAULTS.get(rm.room_type, {})
                target_d = (rd.get("min_d", 2.0) + rd.get("max_d", 3.0)) / 2
                inner_depths.append(target_d)
            inner_default_depth = sum(inner_depths) / len(inner_depths)

        # Derinlik dağılımı: zone toplam derinliğe sığdır
        total_default = facade_default_depth + inner_default_depth
        if total_default > 0:
            facade_ratio = facade_default_depth / total_default
        else:
            facade_ratio = 0.60

        facade_ratio = max(0.50, min(0.70, facade_ratio))
        facade_depth = round(available_h * facade_ratio, 2)
        inner_depth = round(available_h - facade_depth, 2)

        # ── Y pozisyonu cepheye bağlı ────────────────────────────────
        if facade == "south":
            facade_y = uy
            inner_y = uy + facade_depth + iw
        else:
            inner_y = uy
            facade_y = uy + inner_depth + iw

        # ── Yatay ayırıcı duvar ──────────────────────────────────────
        sep_wall_y = inner_y if facade == "south" else inner_y + inner_depth
        r.walls.append(Wall(
            start=(ux, sep_wall_y),
            end=(ux + unit_w, sep_wall_y),
            thickness=iw, wall_type=WallType.INTERIOR,
            layer="A-WALL-INT",
        ))

        # ── Cephe sırasına yerleştir ─────────────────────────────────
        self._pack_rooms_in_row(r, facade_rooms, ux, facade_y, unit_w, facade_depth, unit.unit_id, "facade")

        # ── İç sıraya yerleştir ──────────────────────────────────────
        self._pack_rooms_in_row(r, inner_with_hol, ux, inner_y, unit_w, inner_depth, unit.unit_id, "wet")

    def _pack_rooms_in_row(
        self,
        r: FloorPlanResult,
        rooms: list[RoomSpec],
        x_start: float, y_start: float,
        row_w: float, row_h: float,
        unit_id: str,
        row_type: str,
    ) -> None:
        """
        Constraint-based oda yerleştirme — her oda kendi boyutunu alır.

        1. Her oda için ROOM_DEFAULTS'tan hedef genişlik hesapla
        2. target_area / row_h → gerçekçi genişlik
        3. Kalan alanı orantılı dağıt (boşluk bırakma)
        4. Aspect ratio 1:1 ile 1:2 arası zorla
        """
        if not rooms:
            return

        iw = self.int_wall
        n = len(rooms)
        total_wall = (n - 1) * iw
        available_w = row_w - total_wall

        # ── Adım 1: Her oda için hedef genişlik hesapla ──────────────
        target_widths = []
        for rm in rooms:
            rd = ROOM_DEFAULTS.get(rm.room_type, {"min_w": 2.5, "max_w": 4.0, "min_area": 6})
            target_area = max(rm.area, rd.get("min_area", 4.0))

            # Genişlik = alan / zone derinliği
            ideal_w = target_area / row_h if row_h > 0 else rd.get("min_w", 2.5)

            # Min/max clamp
            min_w = rd.get("min_w", 1.5)
            max_w = rd.get("max_w", 6.0)
            ideal_w = max(min_w, min(max_w, ideal_w))

            # Aspect ratio check: width/depth 1:2 max
            if row_h > ideal_w * 2.5:
                ideal_w = row_h / 2.0  # en az yarı derinlik kadar genişlik

            target_widths.append(ideal_w)

        # ── Adım 2: Toplam genişliği mevcut alana sığdır ─────────────
        total_target_w = sum(target_widths)

        if total_target_w > 0:
            scale = available_w / total_target_w
        else:
            scale = 1.0

        # Ölçeklenmiş genişlikler
        final_widths = []
        for i, rm in enumerate(rooms):
            rd = ROOM_DEFAULTS.get(rm.room_type, {"min_w": 1.5})
            w = target_widths[i] * scale
            w = max(w, rd.get("min_w", 1.5))  # minimum genişlikten küçülmesin
            final_widths.append(w)

        # Son düzeltme: toplam = available_w olsun
        total_final = sum(final_widths)
        if total_final > 0 and abs(total_final - available_w) > 0.01:
            adjust = available_w / total_final
            final_widths = [w * adjust for w in final_widths]

        # ── Adım 3: Yerleştir ────────────────────────────────────────
        cursor_x = x_start

        for i, rm in enumerate(rooms):
            room_w = round(final_widths[i], 3)

            # Hatch pattern
            hatch = ""
            if rm.room_type in ("banyo", "wc"):
                hatch = "ANSI37"
            elif rm.room_type == "mutfak":
                hatch = "DOTS"

            r.rooms.append(PlacedRoom(
                name=rm.name,
                room_type=rm.room_type,
                x=round(cursor_x, 3),
                y=round(y_start, 3),
                width=room_w,
                depth=round(row_h, 3),
                unit_id=unit_id,
                hatch_pattern=hatch,
            ))

            # Oda ayırıcı duvar
            if i > 0:
                r.walls.append(Wall(
                    start=(cursor_x, y_start),
                    end=(cursor_x, y_start + row_h),
                    thickness=iw, wall_type=WallType.PARTITION,
                    layer="A-WALL-INT",
                ))

            cursor_x += room_w + iw

    # ══════════════════════════════════════════════════════════════════════
    # 6. Pencereler
    # ══════════════════════════════════════════════════════════════════════

    def _place_windows(self, r: FloorPlanResult) -> None:
        """Dış duvara temas eden odalara pencere yerleştir."""
        w, d = r.building_width, r.building_depth
        ew = self.ext_wall

        for room in r.rooms:
            if room.room_type in ("koridor", "hol", "depo", "wc"):
                continue

            rx1, ry1, rx2, ry2 = room.bounds

            # ── Güney duvar ──
            if abs(ry1 - ew) < 0.5:
                self._add_window_on_wall(r, room, "south", rx1, rx2, 0)

            # ── Kuzey duvar ──
            if abs(ry2 - (d - ew)) < 0.5:
                self._add_window_on_wall(r, room, "north", rx1, rx2, d)

            # ── Batı duvar ──
            if abs(rx1 - ew) < 0.5:
                self._add_window_on_wall_v(r, room, "west", ry1, ry2, 0)

            # ── Doğu duvar ──
            if abs(rx2 - (w - ew)) < 0.5:
                self._add_window_on_wall_v(r, room, "east", ry1, ry2, w)

    def _add_window_on_wall(
        self, r: FloorPlanResult,
        room: PlacedRoom, side: str,
        rx1: float, rx2: float, wall_y: float,
    ) -> None:
        """Yatay duvara pencere ekle — oda tipine göre boyut."""
        # Oda tipine göre pencere boyutu
        preferred_block = WINDOW_BY_ROOM.get(room.room_type, "WINDOW_150x150")
        from core.blocks import WINDOW_SPECS
        spec = WINDOW_SPECS.get(preferred_block, {"width": 1.50})
        win_w = min(spec["width"], room.width * 0.70)
        win_w = max(win_w, 0.60)
        win_x = rx1 + (room.width - win_w) / 2

        r.windows.append(PlacedWindow(
            x=round(win_x, 3),
            y=round(wall_y, 3),
            width=round(win_w, 3),
            height=spec.get("height", 1.50),
            rotation=0,
            block_name=_pick_window_block(win_w),
            wall_side=side,
        ))

        # Duvar'a opening ekle
        self._add_opening_to_wall(r, wall_y, "horizontal", win_x, win_w, "window")

    def _add_window_on_wall_v(
        self, r: FloorPlanResult,
        room: PlacedRoom, side: str,
        ry1: float, ry2: float, wall_x: float,
    ) -> None:
        """Dikey duvara pencere ekle."""
        win_w = min(1.50, room.depth * 0.50)
        win_w = max(win_w, 0.80)
        win_y = ry1 + (room.depth - win_w) / 2

        r.windows.append(PlacedWindow(
            x=round(wall_x, 3),
            y=round(win_y, 3),
            width=round(win_w, 3),
            height=1.50,
            rotation=90,
            block_name=_pick_window_block(win_w),
            wall_side=side,
        ))

        self._add_opening_to_wall(r, wall_x, "vertical", win_y, win_w, "window")

    # ══════════════════════════════════════════════════════════════════════
    # 7. Kapılar
    # ══════════════════════════════════════════════════════════════════════

    def _place_doors(
        self, r: FloorPlanResult,
        corridor_bottom: float, corridor_top: float,
    ) -> None:
        """Her odaya giriş kapısı — koridor tarafı duvarında."""
        iw = self.int_wall

        for room in r.rooms:
            if room.room_type in ("koridor", "balkon"):
                continue

            rx1, ry1, rx2, ry2 = room.bounds
            door_w = _pick_door_width(room.room_type)
            block = _pick_door_block(room.room_type)

            # Koridorun alt kenarına temas?
            if abs(ry2 - (corridor_bottom - iw / 2)) < 0.8:
                door_x = rx1 + min(0.30, room.width * 0.1)
                r.doors.append(PlacedDoor(
                    x=round(door_x, 3), y=round(ry2, 3),
                    width=door_w, rotation=0,
                    block_name=block,
                ))
                self._add_opening_to_wall(
                    r, corridor_bottom, "horizontal",
                    door_x, door_w, "door",
                )
                continue

            # Koridorun üst kenarına temas?
            if abs(ry1 - (corridor_top + iw / 2)) < 0.8:
                door_x = rx1 + min(0.30, room.width * 0.1)
                r.doors.append(PlacedDoor(
                    x=round(door_x, 3), y=round(ry1, 3),
                    width=door_w, rotation=180,
                    block_name=block,
                ))
                self._add_opening_to_wall(
                    r, corridor_top, "horizontal",
                    door_x, door_w, "door",
                )
                continue

            # Koridora temas ETMİYOR → iç duvardan kapı
            if room.unit_id and room.unit_id != "COMMON":
                door_x = rx1
                door_y = ry1 + room.depth * 0.25
                r.doors.append(PlacedDoor(
                    x=round(door_x, 3), y=round(door_y, 3),
                    width=door_w, rotation=90,
                    block_name=block,
                ))

    def _place_entrance(self, r: FloorPlanResult) -> None:
        """Bina giriş kapısı — güney cephe, çekirdek hizası."""
        entrance_x = r.stair_x + STAIR_W / 2 - 0.60
        r.doors.append(PlacedDoor(
            x=round(entrance_x, 3), y=0,
            width=1.20, rotation=0,
            block_name="DOOR_120",
            is_exterior=True,
        ))
        # Güney dış duvara opening ekle
        self._add_opening_to_wall(r, self.ext_wall / 2, "horizontal", entrance_x, 1.20, "door")

    # ══════════════════════════════════════════════════════════════════════
    # Yardımcı: Duvara Opening Ekle
    # ══════════════════════════════════════════════════════════════════════

    def _add_opening_to_wall(
        self,
        r: FloorPlanResult,
        wall_pos: float,
        wall_dir: str,
        opening_pos: float,
        opening_width: float,
        opening_type: str,
    ) -> None:
        """
        Belirtilen konumdaki duvara opening ekle.
        wall_pos: duvar merkez çizgisinin y (horizontal) veya x (vertical) değeri.
        """
        for wall in r.walls:
            if wall_dir == "horizontal" and wall.is_horizontal:
                wy = wall.start[1]
                if abs(wy - wall_pos) < 0.3:
                    # Opening offset = duvar başlangıcından mesafe
                    wall_start_x = min(wall.start[0], wall.end[0])
                    offset = opening_pos - wall_start_x
                    if offset >= -0.1:
                        wall.openings.append(WallOpening(
                            offset=max(0, offset),
                            width=opening_width,
                            opening_type=opening_type,
                        ))
                        return

            elif wall_dir == "vertical" and wall.is_vertical:
                wx = wall.start[0]
                if abs(wx - wall_pos) < 0.3:
                    wall_start_y = min(wall.start[1], wall.end[1])
                    offset = opening_pos - wall_start_y
                    if offset >= -0.1:
                        wall.openings.append(WallOpening(
                            offset=max(0, offset),
                            width=opening_width,
                            opening_type=opening_type,
                        ))
                        return


# ══════════════════════════════════════════════════════════════════════════════
# Yardımcı Fonksiyonlar
# ══════════════════════════════════════════════════════════════════════════════

def _compute_grid_positions(start: float, end: float, max_spacing: float = 6.5) -> list[float]:
    """Eşit aralıklı grid pozisyonları hesapla."""
    span = end - start
    if span <= 0:
        return [start]

    n_spaces = max(1, math.ceil(span / max_spacing))
    spacing = span / n_spaces

    positions = []
    for i in range(n_spaces + 1):
        positions.append(round(start + i * spacing, 3))
    return positions


def _pick_window_block(width: float) -> str:
    if width >= 1.80:
        return "WINDOW_200x150"
    if width >= 1.30:
        return "WINDOW_150x150"
    if width >= 0.90:
        return "WINDOW_100x150"
    return "WINDOW_60x60"


def _pick_door_width(room_type: str) -> float:
    return {
        "wc": 0.70, "banyo": 0.80, "depo": 0.70,
        "mutfak": 0.90, "salon": 0.90,
        "yatak_odasi": 0.90, "hol": 1.00,
    }.get(room_type, 0.90)


def _pick_door_block(room_type: str) -> str:
    if room_type in ("wc", "depo"):
        return "DOOR_70"
    if room_type == "banyo":
        return "DOOR_80"
    if room_type == "hol":
        return "DOOR_100"
    return "DOOR_90"


# ══════════════════════════════════════════════════════════════════════════════
# Test
# ══════════════════════════════════════════════════════════════════════════════

def _test_planner() -> None:
    """Doğrudan çalıştırılabilir test."""
    from core.regulations import UnitSpec, RoomSpec, FloorSpec

    rooms_3_plus_1 = [
        RoomSpec(name="Salon", room_type="salon", area=25, width=5.0, depth=5.0),
        RoomSpec(name="Yatak 1", room_type="yatak_odasi", area=14, width=3.5, depth=4.0),
        RoomSpec(name="Yatak 2", room_type="yatak_odasi", area=12, width=3.0, depth=4.0),
        RoomSpec(name="Yatak 3", room_type="yatak_odasi", area=10, width=3.0, depth=3.3),
        RoomSpec(name="Mutfak", room_type="mutfak", area=10, width=3.3, depth=3.0),
        RoomSpec(name="Banyo", room_type="banyo", area=5, width=2.0, depth=2.5),
        RoomSpec(name="WC", room_type="wc", area=2, width=1.0, depth=2.0),
        RoomSpec(name="Hol", room_type="hol", area=4, width=2.0, depth=2.0),
    ]

    unit_a = UnitSpec(unit_id="A1", rooms=rooms_3_plus_1)
    unit_b = UnitSpec(unit_id="B1", rooms=rooms_3_plus_1)
    floor = FloorSpec(floor_number=1, floor_type="normal", units=[unit_a, unit_b])

    planner = FloorPlanner()
    plan = planner.plan_floor(floor, building_w=18.0, building_d=13.0, has_elevator=True)

    print(f"Duvar: {len(plan.walls)}, Oda: {len(plan.rooms)}, "
          f"Kapı: {len(plan.doors)}, Pencere: {len(plan.windows)}, "
          f"Kolon: {len(plan.columns)}, Aks: {len(plan.axes)}")

    print("\n── Odalar ─────────────────────────────────────────")
    for rm in plan.rooms:
        print(f"  {rm.unit_id:6s} | {rm.name:20s} | "
              f"{rm.width:5.2f}×{rm.depth:5.2f} = {rm.area:6.1f}m² | "
              f"({rm.x:.2f}, {rm.y:.2f})"
              f"{' [' + rm.hatch_pattern + ']' if rm.hatch_pattern else ''}")

    print("\n── Duvarlar (opening sayısı) ──────────────────────")
    for wall in plan.walls:
        openings = len(wall.openings)
        hatches = len(wall.hatch_polygons)
        print(f"  {wall.wall_type.value:8s} | {wall.layer:12s} | "
              f"t={wall.thickness:.2f}m | L={wall.length:.2f}m | "
              f"opens={openings} | hatch_poly={hatches}")

    print("\n── Aks Grid ──────────────────────────────────────")
    for ax in plan.axes:
        print(f"  {ax.label} ({ax.direction}) @ {ax.position:.2f}m")

    # Çakışma kontrolü
    print("\n── Çakışma Kontrolü ──────────────────────────────")
    rooms = [rm for rm in plan.rooms if rm.room_type not in ("koridor",)]
    overlaps = 0
    for i, ra in enumerate(rooms):
        for j, rb in enumerate(rooms):
            if j <= i:
                continue
            ax1, ay1, ax2, ay2 = ra.bounds
            bx1, by1, bx2, by2 = rb.bounds
            if ax1 < bx2 - 0.05 and ax2 > bx1 + 0.05 and ay1 < by2 - 0.05 and ay2 > by1 + 0.05:
                overlap_area = max(0, min(ax2, bx2) - max(ax1, bx1)) * max(0, min(ay2, by2) - max(ay1, by1))
                if overlap_area > 0.2:
                    print(f"  ⚠ ÇAKIŞMA: {ra.name} ∩ {rb.name} = {overlap_area:.2f}m²")
                    overlaps += 1
    if overlaps == 0:
        print("  ✓ Çakışma yok!")


if __name__ == "__main__":
    _test_planner()
