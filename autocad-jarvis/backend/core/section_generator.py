"""
Profesyonel Kesit (Section) Üretici v4.0
=========================================
Kat planı verisinden bina enine/boyuna kesit çizer.

Sprint 3 iyileştirmeleri:
- Gerçek pencere sayısı (kat planından)
- Merdiven kesit profili (basamak çizgileri)
- Kiriş profili (döşeme altı)
- Yalıtım gösterimi (dış duvar)
- Zemin dolgu hatch
- Boyut zinciri (kat yükseklikleri)
"""

from __future__ import annotations

from typing import Literal

import ezdxf
from ezdxf.layouts import Modelspace

from core.floor_planner import FloorPlanResult


# ══════════════════════════════════════════════════════════════════════════════
# Sabitler
# ══════════════════════════════════════════════════════════════════════════════

FOUNDATION_DEPTH = 0.80       # m
FOUNDATION_WIDTH = 0.60       # m
SLAB_THICKNESS = 0.15         # m
FLOOR_FINISH = 0.05           # m
BEAM_HEIGHT = 0.50            # m
BEAM_WIDTH = 0.30             # m
EXT_WALL_T = 0.25             # m
PARAPET_H = 0.90              # m
ROOF_EAVE = 0.60              # m
WINDOW_SILL = 0.90            # m
WINDOW_HEIGHT = 1.50          # m
DOOR_HEIGHT = 2.10            # m
INSULATION_T = 0.05           # m
RISER_H = 0.175               # m — basamak yüksekliği
TREAD_D = 0.28                # m — basamak derinliği


# ══════════════════════════════════════════════════════════════════════════════
# SectionGenerator
# ══════════════════════════════════════════════════════════════════════════════

class SectionGenerator:
    """Profesyonel bina kesit çizimi."""

    def draw_section(
        self,
        msp: Modelspace,
        floor_plans: list[FloorPlanResult],
        floor_height: float = 2.80,
        section_type: Literal["A-A", "B-B"] = "A-A",
        offset_x: float = 0.0,
        offset_y: float = 0.0,
    ) -> None:
        """
        Kesit çizimini modelspace'e ekle.

        A-A: Enine kesit (bina genişliği boyunca)
        B-B: Boyuna kesit (bina derinliği boyunca)
        """
        if not floor_plans:
            return

        ref = floor_plans[0]
        section_width = ref.building_width if section_type == "A-A" else ref.building_depth
        num_floors = len([fp for fp in floor_plans if fp.floor_type != "bodrum"])
        num_basement = len([fp for fp in floor_plans if fp.floor_type == "bodrum"])

        ox, oy = offset_x, offset_y

        # ── 1. Zemin dolgu hatch ─────────────────────────────────────
        self._draw_ground_fill(msp, ox, oy, section_width)

        # ── 2. Temel ─────────────────────────────────────────────────
        self._draw_foundation(msp, ox, oy, section_width)

        # ── 3. Bodrum katlar ─────────────────────────────────────────
        current_y = oy
        for i in range(num_basement):
            self._draw_floor_section(
                msp, ox, current_y, section_width, floor_height,
                is_basement=True, floor_label=f"B{num_basement - i}. Bodrum",
                floor_plan=None, section_type=section_type,
            )
            current_y += floor_height

        # ── 4. Normal katlar ─────────────────────────────────────────
        ground_y = current_y
        for fp in floor_plans:
            if fp.floor_type == "bodrum":
                continue

            label = "Zemin Kat" if fp.floor_type == "zemin" else f"{fp.floor_number}. Kat"
            self._draw_floor_section(
                msp, ox, current_y, section_width, floor_height,
                is_basement=False, floor_label=label,
                floor_plan=fp, section_type=section_type,
            )

            # ── 4a. Kiriş profili ────────────────────────────────────
            self._draw_beam_profile(msp, ox, current_y, section_width)

            # ── 4b. Merdiven kesit profili ───────────────────────────
            self._draw_stair_section(msp, ox, current_y, floor_height, section_width)

            current_y += floor_height

        # ── 5. Çatı ──────────────────────────────────────────────────
        self._draw_roof(msp, ox, current_y, section_width)

        # ── 6. Yalıtım ──────────────────────────────────────────────
        self._draw_insulation(msp, ox, ground_y, section_width,
                              num_floors * floor_height)

        # ── 7. Kot etiketleri ────────────────────────────────────────
        self._draw_level_labels(
            msp, ox, oy, section_width,
            ground_y, floor_height, num_floors, num_basement,
        )

        # ── 8. Boyut zinciri ─────────────────────────────────────────
        self._draw_section_dims(msp, ox, section_width,
                                ground_y, floor_height, num_floors)

        # ── 9. Kesit başlığı ─────────────────────────────────────────
        title = f"KESİT {section_type}"
        msp.add_text(
            title,
            dxfattribs={"layer": "A-SECT-TEXT", "height": 0.20},
        ).set_placement(
            (ox + section_width / 2, oy - 1.5),
            align=ezdxf.enums.TextEntityAlignment.CENTER,
        )

    # ══════════════════════════════════════════════════════════════════════
    # Alt Fonksiyonlar
    # ══════════════════════════════════════════════════════════════════════

    def _draw_ground_fill(self, msp, ox, oy, width):
        """Zemin dolgu — temel altı zemin hatch'i."""
        ground_depth = FOUNDATION_DEPTH + 0.30
        try:
            hatch = msp.add_hatch(dxfattribs={"layer": "A-SECT-HATCH"})
            hatch.set_pattern_fill("ANSI32", scale=0.04, color=8)
            hatch.paths.add_polyline_path([
                (ox - 1.0, oy - ground_depth),
                (ox + width + 1.0, oy - ground_depth),
                (ox + width + 1.0, oy - FOUNDATION_DEPTH),
                (ox - 1.0, oy - FOUNDATION_DEPTH),
            ], is_closed=True)
        except Exception:
            pass

        # Doğal zemin çizgisi
        msp.add_line(
            (ox - 1.5, oy), (ox + width + 1.5, oy),
            dxfattribs={"layer": "A-SECT", "lineweight": 50},
        )

    def _draw_foundation(self, msp, ox, oy, width):
        """Şerit temel çiz."""
        fd = FOUNDATION_DEPTH
        fw = FOUNDATION_WIDTH

        for side_x in [ox, ox + width]:
            pts = [
                (side_x - fw / 2, oy - fd),
                (side_x + fw / 2, oy - fd),
                (side_x + fw / 2, oy),
                (side_x - fw / 2, oy),
                (side_x - fw / 2, oy - fd),
            ]
            msp.add_lwpolyline(pts, dxfattribs={"layer": "A-SECT"})

            # Temel hatch
            hatch = msp.add_hatch(dxfattribs={"layer": "A-SECT-HATCH"})
            hatch.set_pattern_fill("ANSI31", scale=0.02)
            hatch.paths.add_polyline_path([
                (side_x - fw / 2, oy - fd),
                (side_x + fw / 2, oy - fd),
                (side_x + fw / 2, oy),
                (side_x - fw / 2, oy),
            ], is_closed=True)

        # Temel altı dolgu çizgi
        msp.add_line(
            (ox - fw, oy - fd - 0.05), (ox + width + fw, oy - fd - 0.05),
            dxfattribs={"layer": "A-SECT", "linetype": "DASHED"},
        )

    def _draw_floor_section(self, msp, ox, oy, width, height,
                            is_basement=False, floor_label="",
                            floor_plan=None, section_type="A-A"):
        """Tek kat kesit çiz — gerçek pencere sayısıyla."""
        t = EXT_WALL_T

        # Sol duvar
        msp.add_lwpolyline([
            (ox, oy), (ox + t, oy), (ox + t, oy + height), (ox, oy + height), (ox, oy),
        ], dxfattribs={"layer": "A-SECT"})

        # Sağ duvar
        msp.add_lwpolyline([
            (ox + width - t, oy), (ox + width, oy),
            (ox + width, oy + height), (ox + width - t, oy + height),
            (ox + width - t, oy),
        ], dxfattribs={"layer": "A-SECT"})

        # Duvar hatch (ANSI31)
        for wall_pts in [
            [(ox, oy), (ox + t, oy), (ox + t, oy + height), (ox, oy + height)],
            [(ox + width - t, oy), (ox + width, oy),
             (ox + width, oy + height), (ox + width - t, oy + height)],
        ]:
            try:
                hatch = msp.add_hatch(dxfattribs={"layer": "A-SECT-HATCH"})
                hatch.set_pattern_fill("ANSI31", scale=0.015, color=8)
                hatch.paths.add_polyline_path(wall_pts, is_closed=True)
            except Exception:
                pass

        # Döşeme
        slab_y = oy
        msp.add_lwpolyline([
            (ox, slab_y), (ox + width, slab_y),
            (ox + width, slab_y + SLAB_THICKNESS),
            (ox, slab_y + SLAB_THICKNESS), (ox, slab_y),
        ], dxfattribs={"layer": "A-SECT-SLAB"})

        # Döşeme hatch
        hatch = msp.add_hatch(dxfattribs={"layer": "A-SECT-HATCH"})
        hatch.set_pattern_fill("ANSI31", scale=0.015)
        hatch.paths.add_polyline_path([
            (ox, slab_y), (ox + width, slab_y),
            (ox + width, slab_y + SLAB_THICKNESS),
            (ox, slab_y + SLAB_THICKNESS),
        ], is_closed=True)

        # ── Pencereler (kat planından gerçek sayı) ───────────────────
        if not is_basement and floor_plan is not None:
            win_base_y = slab_y + SLAB_THICKNESS + FLOOR_FINISH + WINDOW_SILL

            # A-A kesiti: east/west pencereleri gösterir
            # B-B kesiti: south/north pencereleri gösterir
            if section_type == "A-A":
                target_sides = ("west", "east")
            else:
                target_sides = ("south", "north")

            windows_drawn = {"left": False, "right": False}

            for win in floor_plan.windows:
                if win.wall_side not in target_sides:
                    continue

                # Sol mu sağ mı?
                if win.wall_side in ("west", "south"):
                    side_x = ox
                    side = "left"
                else:
                    side_x = ox + width - t
                    side = "right"

                if not windows_drawn[side]:
                    # Pencere boşluğu
                    msp.add_lwpolyline([
                        (side_x, win_base_y), (side_x + t, win_base_y),
                        (side_x + t, win_base_y + WINDOW_HEIGHT),
                        (side_x, win_base_y + WINDOW_HEIGHT),
                        (side_x, win_base_y),
                    ], dxfattribs={"layer": "A-SECT", "linetype": "CONTINUOUS"})

                    # Cam çizgisi
                    glass_x = side_x + t / 2
                    msp.add_line(
                        (glass_x, win_base_y), (glass_x, win_base_y + WINDOW_HEIGHT),
                        dxfattribs={"layer": "A-ELEV-GLAZ"},
                    )
                    windows_drawn[side] = True
        elif not is_basement:
            # Fallback: her duvara 1 pencere
            win_y = slab_y + SLAB_THICKNESS + FLOOR_FINISH + WINDOW_SILL
            for side_x in [ox, ox + width - t]:
                msp.add_lwpolyline([
                    (side_x, win_y), (side_x + t, win_y),
                    (side_x + t, win_y + WINDOW_HEIGHT),
                    (side_x, win_y + WINDOW_HEIGHT),
                    (side_x, win_y),
                ], dxfattribs={"layer": "A-SECT"})
                glass_x = side_x + t / 2
                msp.add_line(
                    (glass_x, win_y), (glass_x, win_y + WINDOW_HEIGHT),
                    dxfattribs={"layer": "A-ELEV-GLAZ"},
                )

        # Kat etiketi
        if floor_label:
            msp.add_text(
                floor_label,
                dxfattribs={"layer": "A-SECT-TEXT", "height": 0.15},
            ).set_placement(
                (ox + width / 2, oy + height / 2),
                align=ezdxf.enums.TextEntityAlignment.CENTER,
            )

    def _draw_beam_profile(self, msp, ox, slab_y, width):
        """Döşeme altı kiriş profili — orta açıklıkta."""
        beam_x = ox + width / 2 - BEAM_WIDTH / 2
        beam_bottom = slab_y - BEAM_HEIGHT + SLAB_THICKNESS

        pts = [
            (beam_x, beam_bottom),
            (beam_x + BEAM_WIDTH, beam_bottom),
            (beam_x + BEAM_WIDTH, slab_y),
            (beam_x, slab_y),
            (beam_x, beam_bottom),
        ]
        msp.add_lwpolyline(pts, dxfattribs={"layer": "A-SECT"})

        # Kiriş hatch
        try:
            hatch = msp.add_hatch(dxfattribs={"layer": "A-SECT-HATCH"})
            hatch.set_pattern_fill("ANSI31", scale=0.015, color=8)
            hatch.paths.add_polyline_path([
                (beam_x, beam_bottom),
                (beam_x + BEAM_WIDTH, beam_bottom),
                (beam_x + BEAM_WIDTH, slab_y),
                (beam_x, slab_y),
            ], is_closed=True)
        except Exception:
            pass

    def _draw_stair_section(self, msp, ox, floor_y, floor_height, section_width):
        """U-tipi merdiven kesit profili — basamak çizgileri."""
        stair_x = ox + section_width * 0.12
        num_steps = int(floor_height / RISER_H)
        half_steps = num_steps // 2

        # Alt kol (yukarı çıkan)
        for i in range(half_steps):
            step_y = floor_y + SLAB_THICKNESS + i * RISER_H
            step_x = stair_x + i * TREAD_D

            # Riser (dikey)
            msp.add_line(
                (step_x, step_y), (step_x, step_y + RISER_H),
                dxfattribs={"layer": "A-STRS"},
            )
            # Tread (yatay)
            msp.add_line(
                (step_x, step_y + RISER_H), (step_x + TREAD_D, step_y + RISER_H),
                dxfattribs={"layer": "A-STRS"},
            )

        # Sahanlık çizgisi
        sahanlık_y = floor_y + SLAB_THICKNESS + half_steps * RISER_H
        sahanlık_x = stair_x + half_steps * TREAD_D
        msp.add_line(
            (sahanlık_x, sahanlık_y), (sahanlık_x + 1.0, sahanlık_y),
            dxfattribs={"layer": "A-STRS"},
        )

        # Bel plağı (alt eğimli çizgi)
        msp.add_line(
            (stair_x, floor_y + SLAB_THICKNESS),
            (sahanlık_x, sahanlık_y - 0.12),
            dxfattribs={"layer": "A-STRS", "linetype": "DASHED"},
        )

    def _draw_insulation(self, msp, ox, ground_y, width, total_height):
        """Dış duvar yalıtımı — zigzag çizgileri."""
        ins_t = INSULATION_T
        top_y = ground_y + total_height

        for side_x in [ox - ins_t, ox + width]:
            # Yalıtım dış çizgisi
            msp.add_line(
                (side_x, ground_y), (side_x, top_y),
                dxfattribs={"layer": "A-SECT", "lineweight": 18},
            )
            msp.add_line(
                (side_x + ins_t, ground_y), (side_x + ins_t, top_y),
                dxfattribs={"layer": "A-SECT", "lineweight": 18},
            )

            # Zigzag pattern (basit sinüzoidal benzeri)
            seg_h = 0.30
            mid_x = side_x + ins_t / 2
            n_segs = int(total_height / seg_h)
            for i in range(n_segs):
                y1 = ground_y + i * seg_h
                y2 = y1 + seg_h / 2
                y3 = y1 + seg_h
                # Zigzag: sol→sağ→sol
                msp.add_line(
                    (side_x, y1), (side_x + ins_t, y2),
                    dxfattribs={"layer": "A-SECT", "lineweight": 9},
                )
                msp.add_line(
                    (side_x + ins_t, y2), (side_x, y3),
                    dxfattribs={"layer": "A-SECT", "lineweight": 9},
                )

    def _draw_roof(self, msp, ox, oy, width):
        """Teras çatı — parapet + eğim."""
        t = EXT_WALL_T

        # Son döşeme
        msp.add_lwpolyline([
            (ox, oy), (ox + width, oy),
            (ox + width, oy + SLAB_THICKNESS),
            (ox, oy + SLAB_THICKNESS), (ox, oy),
        ], dxfattribs={"layer": "A-SECT-SLAB"})

        # Döşeme hatch
        try:
            hatch = msp.add_hatch(dxfattribs={"layer": "A-SECT-HATCH"})
            hatch.set_pattern_fill("ANSI31", scale=0.015)
            hatch.paths.add_polyline_path([
                (ox, oy), (ox + width, oy),
                (ox + width, oy + SLAB_THICKNESS),
                (ox, oy + SLAB_THICKNESS),
            ], is_closed=True)
        except Exception:
            pass

        # Parapet
        for px, pw_dir in [(ox, 1), (ox + width - t, 1)]:
            msp.add_lwpolyline([
                (px, oy + SLAB_THICKNESS),
                (px + t, oy + SLAB_THICKNESS),
                (px + t, oy + SLAB_THICKNESS + PARAPET_H),
                (px, oy + SLAB_THICKNESS + PARAPET_H),
                (px, oy + SLAB_THICKNESS),
            ], dxfattribs={"layer": "A-SECT"})

        # Çatı eğim çizgisi
        msp.add_line(
            (ox + t, oy + SLAB_THICKNESS + 0.10),
            (ox + width / 2, oy + SLAB_THICKNESS + 0.20),
            dxfattribs={"layer": "A-ROOF-SLOPE"},
        )
        msp.add_line(
            (ox + width - t, oy + SLAB_THICKNESS + 0.10),
            (ox + width / 2, oy + SLAB_THICKNESS + 0.20),
            dxfattribs={"layer": "A-ROOF-SLOPE"},
        )

        # "% 2" eğim notu
        msp.add_text(
            "% 2",
            dxfattribs={"layer": "A-SECT-TEXT", "height": 0.10},
        ).set_placement(
            (ox + width * 0.35, oy + SLAB_THICKNESS + 0.25),
        )

    def _draw_level_labels(self, msp, ox, oy, width,
                           ground_y, floor_height, num_floors, num_basement):
        """Kot etiketlerini çiz."""
        label_x = ox + width + 1.0

        # ±0.00
        z_level = ground_y + SLAB_THICKNESS + FLOOR_FINISH
        self._kot_label(msp, label_x, z_level, "±0.00")

        # Normal katlar
        for i in range(1, num_floors):
            level_y = ground_y + i * floor_height + SLAB_THICKNESS + FLOOR_FINISH
            self._kot_label(msp, label_x, level_y, f"+{i * floor_height:.2f}")

        # Çatı
        roof_y = ground_y + num_floors * floor_height + SLAB_THICKNESS
        self._kot_label(msp, label_x, roof_y, f"+{num_floors * floor_height:.2f}")

        # Bodrum
        for i in range(num_basement):
            level_y = ground_y - (i + 1) * floor_height + SLAB_THICKNESS + FLOOR_FINISH
            self._kot_label(msp, label_x, level_y, f"-{(i + 1) * floor_height:.2f}")

    def _draw_section_dims(self, msp, ox, width, ground_y,
                           floor_height, num_floors):
        """Boyut zinciri — dikey kat yükseklikleri."""
        dim_x = ox - 1.5

        for i in range(num_floors):
            p1_y = ground_y + i * floor_height
            p2_y = ground_y + (i + 1) * floor_height

            try:
                msp.add_aligned_dim(
                    p1=(dim_x, p1_y),
                    p2=(dim_x, p2_y),
                    distance=-0.5,
                    dimstyle="ARCH_DIM",
                    dxfattribs={"layer": "A-SECT-DIM"},
                ).render()
            except Exception:
                # Fallback: metin
                msp.add_text(
                    f"{floor_height:.2f}",
                    dxfattribs={"layer": "A-SECT-DIM", "height": 0.10},
                ).set_placement((dim_x - 0.6, (p1_y + p2_y) / 2))

        # Toplam yükseklik
        total_h = num_floors * floor_height
        try:
            msp.add_aligned_dim(
                p1=(dim_x - 1.2, ground_y),
                p2=(dim_x - 1.2, ground_y + total_h),
                distance=-0.5,
                dimstyle="ARCH_DIM",
                dxfattribs={"layer": "A-SECT-DIM"},
            ).render()
        except Exception:
            msp.add_text(
                f"Toplam: {total_h:.2f}m",
                dxfattribs={"layer": "A-SECT-DIM", "height": 0.12},
            ).set_placement((dim_x - 2.0, ground_y + total_h / 2))

    def _kot_label(self, msp, x, y, text):
        """Tek kot etiketi — üçgen + çizgi + metin."""
        s = 0.08
        msp.add_lwpolyline([
            (x, y), (x + s, y + s), (x + 2 * s, y), (x, y),
        ], dxfattribs={"layer": "A-SECT-DIM"})

        msp.add_line(
            (x + 2 * s, y), (x + 1.5, y),
            dxfattribs={"layer": "A-SECT-DIM"},
        )

        msp.add_text(
            text,
            dxfattribs={"layer": "A-SECT-DIM", "height": 0.10},
        ).set_placement((x + 1.6, y - 0.05))
