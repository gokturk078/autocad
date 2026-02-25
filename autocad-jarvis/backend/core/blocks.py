"""
Profesyonel DXF Block Kütüphanesi
=================================
AutoCAD uyumlu parametrik block tanımları.
Kapı, pencere, mobilya, merdiven, asansör ve antetli bloklar.

Tüm ölçüler metre (m) cinsindendir.
Block origin noktası INSERT referansı için (0, 0) kabul edilir.
"""

from __future__ import annotations

import math

import ezdxf
from ezdxf.document import Drawing
from ezdxf.layouts import BlockLayout


# ══════════════════════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════════════════════

# Door dimensions (width in meters)
DOOR_SPECS = {
    "DOOR_80": {"width": 0.80, "label": "80cm WC/Banyo"},
    "DOOR_90": {"width": 0.90, "label": "90cm Oda"},
    "DOOR_100": {"width": 1.00, "label": "100cm Daire Giriş"},
    "DOOR_120": {"width": 1.20, "label": "120cm Bina Giriş"},
    "DOOR_DOUBLE_160": {"width": 1.60, "label": "160cm Çift Kanatlı"},
    "DOOR_SLIDING_90": {"width": 0.90, "label": "90cm Sürgülü"},
}

DOOR_HEIGHT = 2.10       # m
DOOR_FRAME_W = 0.05      # m — kasa kalınlığı
DOOR_LEAF_T = 0.04       # m — kanat kalınlığı

# Window dimensions
WINDOW_SPECS = {
    "WINDOW_100x150": {"width": 1.00, "height": 1.50, "panes": 1},
    "WINDOW_150x150": {"width": 1.50, "height": 1.50, "panes": 2},
    "WINDOW_200x150": {"width": 2.00, "height": 1.50, "panes": 3},
    "WINDOW_FRENCH_120x220": {"width": 1.20, "height": 2.20, "panes": 2},
}
WINDOW_SILL_HEIGHT = 0.90    # m — denizlik yüksekliği
WINDOW_FRAME_W = 0.05        # m

# Wall thicknesses
EXT_WALL_T = 0.25   # m
INT_WALL_T = 0.10   # m


# ══════════════════════════════════════════════════════════════════════════════
# BlockLibrary
# ══════════════════════════════════════════════════════════════════════════════

class BlockLibrary:
    """
    DXF block tanım kütüphanesi.
    Tüm block'lar bir DXF document'a register_all() ile eklenir.
    """

    def __init__(self) -> None:
        self.definitions: list[str] = []

    def register_all(self, doc: Drawing) -> None:
        """Tüm block tanımlarını DXF document'a ekle."""
        self._register_doors(doc)
        self._register_windows(doc)
        self._register_furniture(doc)
        self._register_stairs(doc)
        self._register_elevator(doc)
        self._register_misc(doc)

    # ── KAPILAR ──────────────────────────────────────────────────────────

    def _register_doors(self, doc: Drawing) -> None:
        """Tüm kapı block'larını tanımla."""
        for name, spec in DOOR_SPECS.items():
            if name in doc.blocks:
                continue

            w = spec["width"]

            if "SLIDING" in name:
                self._create_sliding_door(doc, name, w)
            elif "DOUBLE" in name:
                self._create_double_door(doc, name, w)
            else:
                self._create_single_door(doc, name, w)

            self.definitions.append(name)

    def _create_single_door(self, doc: Drawing, name: str, width: float) -> None:
        """
        Tek kanatlı kapı bloğu.
        Origin: duvar hattı üzerinde, kapı sol kenarı.

        Çizim:
          - Kasa: 2 kısa çizgi (duvar kalınlığında)
          - Kanat: açılış yayı (90° arc)
          - Eşik: duvar üzerinde boşluk çizgisi
        """
        blk: BlockLayout = doc.blocks.new(name=name)

        # Kasa sol
        blk.add_line((0, 0), (0, DOOR_FRAME_W), dxfattribs={"layer": "A-DOOR"})
        # Kasa sağ
        blk.add_line((width, 0), (width, DOOR_FRAME_W), dxfattribs={"layer": "A-DOOR"})

        # Kanat (çizgi — kapı kanadı)
        blk.add_line((0, DOOR_FRAME_W), (0, DOOR_FRAME_W + width), dxfattribs={"layer": "A-DOOR"})

        # Açılış yayı (90° arc)
        blk.add_arc(
            center=(0, DOOR_FRAME_W),
            radius=width,
            start_angle=0,
            end_angle=90,
            dxfattribs={"layer": "A-DOOR"},
        )

    def _create_double_door(self, doc: Drawing, name: str, width: float) -> None:
        """Çift kanatlı kapı bloğu."""
        blk: BlockLayout = doc.blocks.new(name=name)
        half = width / 2

        # Kasa sol
        blk.add_line((0, 0), (0, DOOR_FRAME_W), dxfattribs={"layer": "A-DOOR"})
        # Kasa sağ
        blk.add_line((width, 0), (width, DOOR_FRAME_W), dxfattribs={"layer": "A-DOOR"})

        # Sol kanat
        blk.add_line((0, DOOR_FRAME_W), (0, DOOR_FRAME_W + half), dxfattribs={"layer": "A-DOOR"})
        blk.add_arc(
            center=(0, DOOR_FRAME_W),
            radius=half,
            start_angle=0,
            end_angle=90,
            dxfattribs={"layer": "A-DOOR"},
        )

        # Sağ kanat
        blk.add_line((width, DOOR_FRAME_W), (width, DOOR_FRAME_W + half), dxfattribs={"layer": "A-DOOR"})
        blk.add_arc(
            center=(width, DOOR_FRAME_W),
            radius=half,
            start_angle=90,
            end_angle=180,
            dxfattribs={"layer": "A-DOOR"},
        )

    def _create_sliding_door(self, doc: Drawing, name: str, width: float) -> None:
        """Sürgülü kapı bloğu."""
        blk: BlockLayout = doc.blocks.new(name=name)

        # Duvar üstü ray çizgisi
        blk.add_line((0, 0), (width, 0), dxfattribs={"layer": "A-DOOR"})

        # Kanat (dolu dikdörtgen — sürgü yönünde)
        blk.add_line((0, 0.02), (width * 0.6, 0.02), dxfattribs={"layer": "A-DOOR"})
        blk.add_line((0, -0.02), (width * 0.6, -0.02), dxfattribs={"layer": "A-DOOR"})

        # Hareket oku
        arrow_x = width * 0.7
        blk.add_line((arrow_x, 0), (arrow_x + 0.15, 0), dxfattribs={"layer": "A-DOOR"})
        blk.add_line((arrow_x + 0.12, 0.03), (arrow_x + 0.15, 0), dxfattribs={"layer": "A-DOOR"})
        blk.add_line((arrow_x + 0.12, -0.03), (arrow_x + 0.15, 0), dxfattribs={"layer": "A-DOOR"})

    # ── PENCERELER ───────────────────────────────────────────────────────

    def _register_windows(self, doc: Drawing) -> None:
        """Tüm pencere block'larını tanımla."""
        for name, spec in WINDOW_SPECS.items():
            if name in doc.blocks:
                continue

            w = spec["width"]
            panes = spec["panes"]
            self._create_window_plan(doc, name, w, panes)
            self.definitions.append(name)

    def _create_window_plan(self, doc: Drawing, name: str, width: float, panes: int) -> None:
        """
        Pencere plan çizimi — duvar kalınlığı üzerinde.
        Dış çizgi + cam çizgisi + iç çizgi.
        """
        blk: BlockLayout = doc.blocks.new(name=name)
        t = EXT_WALL_T  # duvar kalınlığı baz

        # Dış duvar kenarı (üst çizgi)
        blk.add_line((0, t), (width, t), dxfattribs={"layer": "A-GLAZ"})
        # İç duvar kenarı (alt çizgi)
        blk.add_line((0, 0), (width, 0), dxfattribs={"layer": "A-GLAZ"})

        # Cam çizgi(ler)i — ortada, ince
        glass_y = t / 2
        if panes == 1:
            blk.add_line((WINDOW_FRAME_W, glass_y), (width - WINDOW_FRAME_W, glass_y),
                         dxfattribs={"layer": "A-GLAZ"})
        else:
            pane_w = (width - WINDOW_FRAME_W * 2) / panes
            for i in range(panes):
                x_start = WINDOW_FRAME_W + i * pane_w
                x_end = x_start + pane_w
                blk.add_line((x_start, glass_y - 0.01), (x_end, glass_y - 0.01),
                             dxfattribs={"layer": "A-GLAZ"})
                blk.add_line((x_start, glass_y + 0.01), (x_end, glass_y + 0.01),
                             dxfattribs={"layer": "A-GLAZ"})

        # Kasa çizgileri (sol/sağ dikey)
        blk.add_line((0, 0), (0, t), dxfattribs={"layer": "A-GLAZ"})
        blk.add_line((width, 0), (width, t), dxfattribs={"layer": "A-GLAZ"})

    # ── MOBİLYA ──────────────────────────────────────────────────────────

    def _register_furniture(self, doc: Drawing) -> None:
        """Mobilya block tanımları."""
        furn = {
            "SOFA_3":        (2.20, 0.85),
            "SOFA_L":        (2.50, 1.80),
            "TABLE_DINING_6": (1.80, 0.90),
            "TABLE_DINING_4": (1.20, 0.80),
            "BED_SINGLE":    (0.90, 2.00),
            "BED_DOUBLE":    (1.60, 2.00),
            "BED_KID":       (0.80, 1.80),
            "WARDROBE":      (1.80, 0.60),
            "DESK":          (1.20, 0.60),
        }

        for name, (w, d) in furn.items():
            if name in doc.blocks:
                continue
            blk = doc.blocks.new(name=name)
            # Basit dikdörtgen + çapraz
            pts = [(0, 0), (w, 0), (w, d), (0, d), (0, 0)]
            blk.add_lwpolyline(pts, dxfattribs={"layer": "A-FURN"})
            self.definitions.append(name)

        # ── Mutfak tezgahı
        if "KITCHEN_COUNTER" not in doc.blocks:
            blk = doc.blocks.new(name="KITCHEN_COUNTER")
            # Tezgah dikdörtgenler
            blk.add_lwpolyline([(0, 0), (2.40, 0), (2.40, 0.60), (0, 0.60), (0, 0)],
                               dxfattribs={"layer": "A-FURN"})
            # Ocak yuvası (2 daire)
            blk.add_circle((1.50, 0.30), 0.10, dxfattribs={"layer": "A-FURN"})
            blk.add_circle((1.90, 0.30), 0.10, dxfattribs={"layer": "A-FURN"})
            # Eviye
            blk.add_lwpolyline([(0.40, 0.10), (0.80, 0.10), (0.80, 0.50), (0.40, 0.50), (0.40, 0.10)],
                               dxfattribs={"layer": "A-FURN"})
            self.definitions.append("KITCHEN_COUNTER")

        # ── Banyo elemanları
        self._create_bathroom_fixtures(doc)

    def _create_bathroom_fixtures(self, doc: Drawing) -> None:
        """Banyo ekipmanları."""
        # Klozet
        if "TOILET" not in doc.blocks:
            blk = doc.blocks.new(name="TOILET")
            # Hazne dikdörtgen
            blk.add_lwpolyline([(0, 0), (0.40, 0), (0.40, 0.30), (0, 0.30), (0, 0)],
                               dxfattribs={"layer": "A-FURN"})
            # Oturak (elips benzeri)
            blk.add_ellipse(
                center=(0.20, 0.50),
                major_axis=(0.18, 0),
                ratio=0.7,
                dxfattribs={"layer": "A-FURN"},
            )
            self.definitions.append("TOILET")

        # Lavabo
        if "SINK" not in doc.blocks:
            blk = doc.blocks.new(name="SINK")
            blk.add_lwpolyline([(0, 0), (0.50, 0), (0.50, 0.40), (0, 0.40), (0, 0)],
                               dxfattribs={"layer": "A-FURN"})
            blk.add_ellipse(
                center=(0.25, 0.20),
                major_axis=(0.15, 0),
                ratio=0.6,
                dxfattribs={"layer": "A-FURN"},
            )
            self.definitions.append("SINK")

        # Duş teknesi (90x90)
        if "SHOWER_90" not in doc.blocks:
            blk = doc.blocks.new(name="SHOWER_90")
            blk.add_lwpolyline([(0, 0), (0.90, 0), (0.90, 0.90), (0, 0.90), (0, 0)],
                               dxfattribs={"layer": "A-FURN"})
            # Çapraz çizgi — duş sembolü
            blk.add_line((0, 0), (0.90, 0.90), dxfattribs={"layer": "A-FURN"})
            blk.add_line((0.90, 0), (0, 0.90), dxfattribs={"layer": "A-FURN"})
            self.definitions.append("SHOWER_90")

        # Küvet
        if "BATHTUB" not in doc.blocks:
            blk = doc.blocks.new(name="BATHTUB")
            # Dış dikdörtgen
            blk.add_lwpolyline([(0, 0), (1.70, 0), (1.70, 0.75), (0, 0.75), (0, 0)],
                               dxfattribs={"layer": "A-FURN"})
            # İç elips
            blk.add_ellipse(
                center=(0.85, 0.375),
                major_axis=(0.70, 0),
                ratio=0.45,
                dxfattribs={"layer": "A-FURN"},
            )
            self.definitions.append("BATHTUB")

        # Çamaşır makinesi
        if "WASHING_MACHINE" not in doc.blocks:
            blk = doc.blocks.new(name="WASHING_MACHINE")
            blk.add_lwpolyline([(0, 0), (0.60, 0), (0.60, 0.60), (0, 0.60), (0, 0)],
                               dxfattribs={"layer": "A-FURN"})
            blk.add_circle((0.30, 0.30), 0.20, dxfattribs={"layer": "A-FURN"})
            self.definitions.append("WASHING_MACHINE")

    # ── MERDİVEN ─────────────────────────────────────────────────────────

    def _register_stairs(self, doc: Drawing) -> None:
        """Merdiven blokları."""
        # U-tipi çift kollu merdiven
        if "STAIR_U" not in doc.blocks:
            blk = doc.blocks.new(name="STAIR_U")
            stair_w = 1.20      # kol genişliği
            gap = 0.10          # iki kol arası boşluk
            total_w = stair_w * 2 + gap
            riser_count = 8     # kol başına basamak
            tread = 0.28        # basamak derinliği
            run_length = riser_count * tread

            # Sol kol (yukarı çıkan)
            for i in range(riser_count):
                y = i * tread
                blk.add_line((0, y), (stair_w, y), dxfattribs={"layer": "A-STRS"})

            # Sahanlık
            landing_y = run_length
            blk.add_lwpolyline(
                [(0, landing_y), (total_w, landing_y),
                 (total_w, landing_y + stair_w), (0, landing_y + stair_w),
                 (0, landing_y)],
                dxfattribs={"layer": "A-STRS"},
            )

            # Sağ kol (inen)
            for i in range(riser_count):
                y = landing_y + stair_w + i * tread
                blk.add_line((stair_w + gap, y), (total_w, y), dxfattribs={"layer": "A-STRS"})

            # Dış sınır
            total_length = run_length + stair_w + run_length
            blk.add_lwpolyline(
                [(0, 0), (total_w, 0), (total_w, total_length),
                 (0, total_length), (0, 0)],
                dxfattribs={"layer": "A-STRS"},
            )

            # Çıkış yönü oku
            arrow_x = stair_w / 2
            arrow_y1 = run_length / 2
            arrow_y2 = arrow_y1 + 0.30
            blk.add_line((arrow_x, arrow_y1), (arrow_x, arrow_y2), dxfattribs={"layer": "A-STRS"})
            blk.add_line((arrow_x - 0.05, arrow_y2 - 0.05), (arrow_x, arrow_y2), dxfattribs={"layer": "A-STRS"})
            blk.add_line((arrow_x + 0.05, arrow_y2 - 0.05), (arrow_x, arrow_y2), dxfattribs={"layer": "A-STRS"})

            self.definitions.append("STAIR_U")

        # Düz merdiven
        if "STAIR_STRAIGHT" not in doc.blocks:
            blk = doc.blocks.new(name="STAIR_STRAIGHT")
            stair_w = 1.20
            riser_count = 16
            tread = 0.28
            total_length = riser_count * tread

            for i in range(riser_count):
                y = i * tread
                blk.add_line((0, y), (stair_w, y), dxfattribs={"layer": "A-STRS"})

            # Dış sınır
            blk.add_lwpolyline(
                [(0, 0), (stair_w, 0), (stair_w, total_length),
                 (0, total_length), (0, 0)],
                dxfattribs={"layer": "A-STRS"},
            )

            # Yön oku
            mid_x = stair_w / 2
            blk.add_line((mid_x, 0.50), (mid_x, 1.00), dxfattribs={"layer": "A-STRS"})
            blk.add_line((mid_x - 0.05, 0.95), (mid_x, 1.00), dxfattribs={"layer": "A-STRS"})
            blk.add_line((mid_x + 0.05, 0.95), (mid_x, 1.00), dxfattribs={"layer": "A-STRS"})

            self.definitions.append("STAIR_STRAIGHT")

    # ── ASANSÖR ──────────────────────────────────────────────────────────

    def _register_elevator(self, doc: Drawing) -> None:
        """Asansör kabini bloğu."""
        if "ELEVATOR_CABIN" not in doc.blocks:
            blk = doc.blocks.new(name="ELEVATOR_CABIN")
            w, d = 1.60, 1.80  # kabin boyutları

            # Kabin dikdörtgen
            blk.add_lwpolyline(
                [(0, 0), (w, 0), (w, d), (0, d), (0, 0)],
                dxfattribs={"layer": "A-ELEV"},
            )
            # Çapraz (asansör sembolü)
            blk.add_line((0, 0), (w, d), dxfattribs={"layer": "A-ELEV"})
            blk.add_line((w, 0), (0, d), dxfattribs={"layer": "A-ELEV"})

            # Kapı açıklığı (ön cephe ortası)
            door_w = 0.80
            door_x1 = (w - door_w) / 2
            door_x2 = door_x1 + door_w
            blk.add_line((door_x1, 0), (door_x2, 0), dxfattribs={"layer": "A-ELEV", "lineweight": 50})

            self.definitions.append("ELEVATOR_CABIN")

    # ── DİĞER ────────────────────────────────────────────────────────────

    def _register_misc(self, doc: Drawing) -> None:
        """Kuzey oku, ölçek barı, kolon blokları."""
        # Kuzey Oku
        if "NORTH_ARROW" not in doc.blocks:
            blk = doc.blocks.new(name="NORTH_ARROW")
            r = 0.50
            # Daire
            blk.add_circle((0, 0), r, dxfattribs={"layer": "A-ANNO"})
            # Ok
            blk.add_line((0, 0), (0, r * 0.8), dxfattribs={"layer": "A-ANNO"})
            blk.add_line((-0.05, r * 0.65), (0, r * 0.8), dxfattribs={"layer": "A-ANNO"})
            blk.add_line((0.05, r * 0.65), (0, r * 0.8), dxfattribs={"layer": "A-ANNO"})
            # N harfi
            blk.add_text("N", dxfattribs={"layer": "A-ANNO", "height": 0.20}).set_placement((0, r + 0.05))
            self.definitions.append("NORTH_ARROW")

        # Ölçek barı
        if "SCALE_BAR" not in doc.blocks:
            blk = doc.blocks.new(name="SCALE_BAR")
            # 5m ölçek barı
            blk.add_line((0, 0), (5.0, 0), dxfattribs={"layer": "A-ANNO"})
            for i in range(6):  # 0, 1, 2, 3, 4, 5m tick marks
                x = i * 1.0
                blk.add_line((x, -0.05), (x, 0.05), dxfattribs={"layer": "A-ANNO"})
                blk.add_text(f"{i}m", dxfattribs={"layer": "A-ANNO", "height": 0.08}).set_placement((x, -0.12))
            self.definitions.append("SCALE_BAR")

        # Kolonlar
        for name, (w, d) in [("COLUMN_40x40", (0.40, 0.40)), ("COLUMN_30x60", (0.30, 0.60))]:
            if name not in doc.blocks:
                blk = doc.blocks.new(name=name)
                hw, hd = w / 2, d / 2
                blk.add_lwpolyline(
                    [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd), (-hw, -hd)],
                    dxfattribs={"layer": "A-COLS"},
                )
                # Kolon hatch (solid fill)
                hatch = blk.add_hatch(dxfattribs={"layer": "A-COLS"})
                hatch.set_pattern_fill("SOLID")
                hatch.paths.add_polyline_path(
                    [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)],
                    is_closed=True,
                )
                self.definitions.append(name)


# ══════════════════════════════════════════════════════════════════════════════
# Yardımcı Fonksiyonlar — Block INSERT
# ══════════════════════════════════════════════════════════════════════════════

def insert_door(
    msp,
    block_name: str,
    position: tuple[float, float],
    rotation: float = 0.0,
    mirror: bool = False,
) -> None:
    """Kapı block'unu belirtilen pozisyona ekle."""
    scale_x = -1.0 if mirror else 1.0
    msp.add_blockref(
        block_name,
        insert=position,
        dxfattribs={
            "layer": "A-DOOR",
            "rotation": rotation,
            "xscale": scale_x,
            "yscale": 1.0,
        },
    )


def insert_window(
    msp,
    block_name: str,
    position: tuple[float, float],
    rotation: float = 0.0,
) -> None:
    """Pencere block'unu belirtilen pozisyona ekle."""
    msp.add_blockref(
        block_name,
        insert=position,
        dxfattribs={
            "layer": "A-GLAZ",
            "rotation": rotation,
        },
    )


def insert_furniture(
    msp,
    block_name: str,
    position: tuple[float, float],
    rotation: float = 0.0,
) -> None:
    """Mobilya block'unu belirtilen pozisyona ekle."""
    msp.add_blockref(
        block_name,
        insert=position,
        dxfattribs={
            "layer": "A-FURN",
            "rotation": rotation,
        },
    )
