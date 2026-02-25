"""
Profesyonel Görünüş (Elevation) Üretici v4.0
==============================================
Kat planı verisinden 4 cephe görünüşü üretir.

Sprint 3 iyileştirmeleri:
- Gerçek giriş kapısı pozisyonu (plan'dan)
- Kat silme kalınlığı (5cm bant)
- Balkon profili (konsol + korkuluk)
- Malzeme notasyonu
- Yağmur oluğu
- Zemin çizgisi (doğal zemin seviyesi)
"""

from __future__ import annotations

from typing import Literal

import ezdxf
from ezdxf.layouts import Modelspace

from core.floor_planner import FloorPlanResult, PlacedWindow


# Sabitler
SLAB_T = 0.15
FLOOR_FINISH = 0.05
PARAPET_H = 0.90
SILME_H = 0.05    # kat silme boyu
SILME_OUT = 0.03  # silme çıkıntısı
EAVE_H = 0.04     # saçak kalınlığı
RAILING_H = 0.90  # balkon korkuluk yüksekliği
BALCONY_DEPTH = 1.50  # balkon çıkıntısı


class ElevationGenerator:
    """Profesyonel 4 cephe görünüşü üretir."""

    def draw_elevation(
        self,
        msp: Modelspace,
        floor_plans: list[FloorPlanResult],
        floor_height: float = 2.80,
        facade: Literal["south", "east", "north", "west"] = "south",
        offset_x: float = 0.0,
        offset_y: float = 0.0,
    ) -> None:
        """Tek cephe görünüşü çiz."""
        if not floor_plans:
            return

        ref = floor_plans[0]
        elev_width = ref.building_width if facade in ("south", "north") else ref.building_depth

        num_floors = len([fp for fp in floor_plans if fp.floor_type != "bodrum"])
        total_height = num_floors * floor_height

        ox, oy = offset_x, offset_y

        # ── 1. Zemin çizgisi ─────────────────────────────────────────
        self._draw_ground_line(msp, ox, oy, elev_width)

        # ── 2. Bina kontur ───────────────────────────────────────────
        self._draw_building_outline(msp, ox, oy, elev_width, total_height)

        # ── 3. Kat silmeleri (kalınlıklı) ────────────────────────────
        for i in range(1, num_floors):
            silme_y = oy + i * floor_height
            self._draw_silme(msp, ox, silme_y, elev_width)

        # ── 4. Çatı + parapet + yağmur oluğu ────────────────────────
        roof_y = oy + total_height
        self._draw_roof_elevation(msp, ox, roof_y, elev_width)

        # ── 5. Pencereler ────────────────────────────────────────────
        self._draw_elevation_windows(
            msp, floor_plans, floor_height,
            facade, ox, oy, elev_width,
        )

        # ── 6. Giriş kapısı (plan'dan gerçek pozisyon) ──────────────
        if facade == "south":
            self._draw_entrance(msp, ox, oy, elev_width, floor_plans)

        # ── 7. Balkon profili ────────────────────────────────────────
        self._draw_balcony_profiles(msp, floor_plans, floor_height,
                                     facade, ox, oy)

        # ── 8. Malzeme notasyonu ─────────────────────────────────────
        self._draw_material_annotations(msp, ox, oy, elev_width,
                                         total_height, roof_y)

        # ── 9. Kot etiketleri ────────────────────────────────────────
        label_x = ox + elev_width + 1.0
        self._kot_label(msp, label_x, oy + SLAB_T + FLOOR_FINISH, "±0.00")
        for i in range(1, num_floors + 1):
            level_y = oy + i * floor_height
            self._kot_label(msp, label_x, level_y + SLAB_T + FLOOR_FINISH,
                            f"+{i * floor_height:.2f}")

        # ── 10. Cephe başlığı ────────────────────────────────────────
        facade_names = {
            "south": "ÖN GÖRÜNÜŞ (GÜNEY)",
            "north": "ARKA GÖRÜNÜŞ (KUZEY)",
            "east": "SAĞ YAN GÖRÜNÜŞ (DOĞU)",
            "west": "SOL YAN GÖRÜNÜŞ (BATI)",
        }
        msp.add_text(
            facade_names[facade],
            dxfattribs={"layer": "A-ELEV-TEXT", "height": 0.20},
        ).set_placement(
            (ox + elev_width / 2, oy - 1.0),
            align=ezdxf.enums.TextEntityAlignment.CENTER,
        )

    # ══════════════════════════════════════════════════════════════════════
    # Alt Fonksiyonlar
    # ══════════════════════════════════════════════════════════════════════

    def _draw_ground_line(self, msp, ox, oy, width):
        """Doğal zemin seviyesi çizgisi."""
        msp.add_line(
            (ox - 2.0, oy), (ox + width + 2.0, oy),
            dxfattribs={"layer": "A-ELEV-WALL", "lineweight": 50},
        )
        # Zemin hatch (küçük eğik çizgiler — doğal zemin)
        for i in range(int(width + 4) * 3):
            x = ox - 2.0 + i * 0.33
            msp.add_line(
                (x, oy), (x - 0.15, oy - 0.10),
                dxfattribs={"layer": "A-ELEV-WALL", "lineweight": 9},
            )

    def _draw_building_outline(self, msp, ox, oy, width, height):
        """Bina dış kontur."""
        msp.add_lwpolyline([
            (ox, oy), (ox + width, oy), (ox + width, oy + height),
            (ox, oy + height), (ox, oy),
        ], dxfattribs={"layer": "A-ELEV-WALL", "lineweight": 70})

    def _draw_silme(self, msp, ox, silme_y, width):
        """Kat silmesi — 5cm kalınlık + 3cm çıkıntı."""
        # Alt çizgi
        msp.add_line(
            (ox - SILME_OUT, silme_y),
            (ox + width + SILME_OUT, silme_y),
            dxfattribs={"layer": "A-ELEV-WALL"},
        )
        # Üst çizgi
        msp.add_line(
            (ox - SILME_OUT, silme_y + SILME_H),
            (ox + width + SILME_OUT, silme_y + SILME_H),
            dxfattribs={"layer": "A-ELEV-WALL"},
        )
        # Sol/sağ kapama
        msp.add_line(
            (ox - SILME_OUT, silme_y), (ox - SILME_OUT, silme_y + SILME_H),
            dxfattribs={"layer": "A-ELEV-WALL"},
        )
        msp.add_line(
            (ox + width + SILME_OUT, silme_y),
            (ox + width + SILME_OUT, silme_y + SILME_H),
            dxfattribs={"layer": "A-ELEV-WALL"},
        )

    def _draw_roof_elevation(self, msp, ox, roof_y, width):
        """Çatı + parapet + yağmur oluğu."""
        # Parapet
        msp.add_lwpolyline([
            (ox, roof_y), (ox, roof_y + PARAPET_H),
            (ox + width, roof_y + PARAPET_H),
            (ox + width, roof_y),
        ], dxfattribs={"layer": "A-ELEV-WALL"})

        # Parapet üst kapak (düşey çizgi)
        msp.add_line(
            (ox, roof_y + PARAPET_H), (ox + width, roof_y + PARAPET_H),
            dxfattribs={"layer": "A-ELEV-WALL", "lineweight": 50},
        )

        # Yağmur oluğu (parapet alt köşelerinde küçük daire)
        for gutter_x in [ox, ox + width]:
            msp.add_circle(
                (gutter_x, roof_y + 0.05), radius=0.04,
                dxfattribs={"layer": "A-ELEV-WALL"},
            )
            # İniş borusu (dikey çizgi)
            msp.add_line(
                (gutter_x, roof_y + 0.05), (gutter_x, roof_y - 0.5),
                dxfattribs={"layer": "A-ELEV-WALL", "lineweight": 18},
            )

    def _draw_elevation_windows(self, msp, floor_plans, floor_height,
                                facade, ox, oy, elev_width):
        """Pencere pozisyonlarını kat planından çız."""
        for fp in floor_plans:
            if fp.floor_type == "bodrum":
                continue

            floor_idx = fp.floor_number
            if fp.floor_type == "zemin":
                floor_idx = 0

            base_y = oy + floor_idx * floor_height

            for win in fp.windows:
                if win.wall_side != facade:
                    continue

                if facade in ("south", "north"):
                    win_cx = ox + win.x + win.width / 2
                else:
                    win_cx = ox + win.y + win.width / 2

                win_w = win.width
                win_h = win.height
                sill_h = 0.90

                win_left = win_cx - win_w / 2
                win_bottom = base_y + SLAB_T + FLOOR_FINISH + sill_h

                # Pencere dikdörtgen
                msp.add_lwpolyline([
                    (win_left, win_bottom),
                    (win_left + win_w, win_bottom),
                    (win_left + win_w, win_bottom + win_h),
                    (win_left, win_bottom + win_h),
                    (win_left, win_bottom),
                ], dxfattribs={"layer": "A-ELEV-GLAZ"})

                # Cam çizgisi (çapraz)
                msp.add_line(
                    (win_left, win_bottom),
                    (win_left + win_w, win_bottom + win_h),
                    dxfattribs={"layer": "A-ELEV-GLAZ"},
                )
                msp.add_line(
                    (win_left + win_w, win_bottom),
                    (win_left, win_bottom + win_h),
                    dxfattribs={"layer": "A-ELEV-GLAZ"},
                )

                # Denizlik
                msp.add_line(
                    (win_left - 0.05, win_bottom - 0.02),
                    (win_left + win_w + 0.05, win_bottom - 0.02),
                    dxfattribs={"layer": "A-ELEV-WALL"},
                )

    def _draw_entrance(self, msp, ox, oy, elev_width, floor_plans):
        """Giriş kapısı — plan'dan gerçek pozisyon."""
        door_x = ox + elev_width / 2 - 0.60  # default
        door_w = 1.20
        door_h = 2.10

        # Plan'dan giriş kapısı pozisyonunu bul
        if floor_plans:
            for fp in floor_plans:
                if fp.floor_type in ("zemin", "normal") and fp.floor_number <= 1:
                    for door in fp.doors:
                        if door.is_exterior:
                            door_x = ox + door.x
                            door_w = door.width
                            break
                    break

        # Kapı dikdörtgen
        msp.add_lwpolyline([
            (door_x, oy), (door_x + door_w, oy),
            (door_x + door_w, oy + door_h),
            (door_x, oy + door_h),
            (door_x, oy),
        ], dxfattribs={"layer": "A-ELEV-DOOR"})

        # Kapı paneli (çift kanatlı — dikey bölme)
        mid_x = door_x + door_w / 2
        msp.add_line(
            (mid_x, oy), (mid_x, oy + door_h),
            dxfattribs={"layer": "A-ELEV-DOOR"},
        )

        # Kapı kemerli üst panel (süsleme)
        msp.add_line(
            (door_x, oy + door_h), (door_x + door_w, oy + door_h),
            dxfattribs={"layer": "A-ELEV-DOOR", "lineweight": 50},
        )

    def _draw_balcony_profiles(self, msp, floor_plans, floor_height,
                                facade, ox, oy):
        """Balkon profili — konsol döşeme + korkuluk."""
        if facade not in ("south", "north"):
            return

        for fp in floor_plans:
            if fp.floor_type == "bodrum":
                continue

            floor_idx = fp.floor_number if fp.floor_type != "zemin" else 0
            if floor_idx == 0:
                continue  # Zemin katta balkon yok

            # Balkon odası var mı kontrol et
            has_balcony = any(
                room.room_type == "balkon"
                for room in fp.rooms
            )

            if not has_balcony:
                # Salon/yatak dışa bakıyorsa basit balkon ekle
                facade_rooms = []
                for room in fp.rooms:
                    if room.room_type in ("salon",) and room.unit_id != "COMMON":
                        facade_rooms.append(room)

                if not facade_rooms:
                    continue

                room = facade_rooms[0]
                balc_x = ox + room.x + room.width * 0.2
                balc_w = room.width * 0.6
            else:
                balc_x = ox + fp.building_width * 0.2
                balc_w = fp.building_width * 0.3

            base_y = oy + floor_idx * floor_height

            # Konsol döşeme
            slab_bottom = base_y
            msp.add_lwpolyline([
                (balc_x, slab_bottom),
                (balc_x + balc_w, slab_bottom),
                (balc_x + balc_w, slab_bottom + SLAB_T),
                (balc_x, slab_bottom + SLAB_T),
                (balc_x, slab_bottom),
            ], dxfattribs={"layer": "A-ELEV-WALL"})

            # Korkuluk
            rail_bottom = slab_bottom + SLAB_T
            # Sol dikey
            msp.add_line(
                (balc_x, rail_bottom), (balc_x, rail_bottom + RAILING_H),
                dxfattribs={"layer": "A-ELEV-WALL"},
            )
            # Sağ dikey
            msp.add_line(
                (balc_x + balc_w, rail_bottom),
                (balc_x + balc_w, rail_bottom + RAILING_H),
                dxfattribs={"layer": "A-ELEV-WALL"},
            )
            # Üst yatay (küpeşte)
            msp.add_line(
                (balc_x, rail_bottom + RAILING_H),
                (balc_x + balc_w, rail_bottom + RAILING_H),
                dxfattribs={"layer": "A-ELEV-WALL", "lineweight": 35},
            )
            # Dikey çubuklar (10cm aralıklı)
            bar_spacing = 0.12
            n_bars = int(balc_w / bar_spacing)
            for j in range(1, n_bars):
                bar_x = balc_x + j * bar_spacing
                msp.add_line(
                    (bar_x, rail_bottom), (bar_x, rail_bottom + RAILING_H),
                    dxfattribs={"layer": "A-ELEV-WALL", "lineweight": 9},
                )

    def _draw_material_annotations(self, msp, ox, oy, elev_width,
                                    total_height, roof_y):
        """Cephe malzeme notasyonu."""
        annotations = [
            ("Dış cephe sıva", ox - 2.5, oy + total_height * 0.55),
            ("Alüminyum doğrama", ox + elev_width + 0.5,
             oy + total_height * 0.45),
            ("Parapet", ox + elev_width / 2, roof_y + PARAPET_H + 0.25),
        ]

        for text, ax, ay in annotations:
            msp.add_text(
                text,
                dxfattribs={"layer": "A-ELEV-TEXT", "height": 0.10},
            ).set_placement((ax, ay))

            # Kısa çizgi (pointer)
            if ax < ox:
                # Sol taraftaysa sağa doğru çizgi
                msp.add_line(
                    (ax + len(text) * 0.05, ay),
                    (ox, ay),
                    dxfattribs={"layer": "A-ELEV-TEXT", "lineweight": 9},
                )

    def _kot_label(self, msp, x, y, text):
        """Kot etiketi."""
        s = 0.08
        msp.add_lwpolyline([
            (x, y), (x + s, y + s), (x + 2 * s, y), (x, y),
        ], dxfattribs={"layer": "A-ELEV-DIM"})
        msp.add_line(
            (x + 2 * s, y), (x + 1.5, y),
            dxfattribs={"layer": "A-ELEV-DIM"},
        )
        msp.add_text(
            text,
            dxfattribs={"layer": "A-ELEV-DIM", "height": 0.10},
        ).set_placement((x + 1.6, y - 0.05))
