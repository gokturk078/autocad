"""
Çok-Paftalı DXF Üretim Motoru (ArchitecturalDXFGenerator)
=========================================================
FAZ 3B ana modül — ProjectBuilder çıktısını alır,
tüm paftaları üretir, ZIP olarak paketler.

Üretilen Paftalar:
1. Vaziyet Planı
2. Kat Planları (her kat ayrı DXF)
3. Kesitler (A-A ve B-B)
4. Görünüşler (4 cephe)
5. Çatı Planı
6. Alan Hesap Tablosu
"""

from __future__ import annotations

import math
import os
import zipfile
from datetime import datetime
from pathlib import Path

import ezdxf
from ezdxf.document import Drawing
from ezdxf.layouts import Modelspace

from core.blocks import BlockLibrary, insert_door, insert_window, insert_furniture
from core.elevation_generator import ElevationGenerator
from core.floor_planner import FloorPlanResult, FloorPlanner
from core.regulations import BuildingSpec, FloorSpec, ParcelInfo, UnitSpec
from core.section_generator import SectionGenerator
from core.sheet_setup import (
    create_new_dxf,
    draw_sheet_border,
    draw_title_block,
)


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ══════════════════════════════════════════════════════════════════════════════
# ProjectOutput Dataclass
# ══════════════════════════════════════════════════════════════════════════════

class ProjectOutput:
    """Üretilen dosyaların listesi."""

    def __init__(self) -> None:
        self.files: dict[str, str] = {}     # sheet_name → file_path
        self.zip_path: str = ""

    def to_dict(self) -> dict:
        return {
            "files": self.files,
            "zip_path": self.zip_path,
            "file_count": len(self.files),
        }


# ══════════════════════════════════════════════════════════════════════════════
# ArchitecturalDXFGenerator
# ══════════════════════════════════════════════════════════════════════════════

class ArchitecturalDXFGenerator:
    """
    Tam mimari proje DXF seti üretir.

    Kullanım:
        gen = ArchitecturalDXFGenerator()
        output = gen.generate_project(project_data, "/output/dir")
    """

    def __init__(self) -> None:
        self.blocks = BlockLibrary()
        self.planner = FloorPlanner()
        self.section_gen = SectionGenerator()
        self.elevation_gen = ElevationGenerator()

    def generate_project(
        self,
        project_data: dict,
        output_dir: str,
        project_name: str = "Mimari Proje",
        city: str = "İstanbul",
    ) -> ProjectOutput:
        """
        Tam proje DXF setini üret.

        Args:
            project_data: ProjectBuilder.build() çıktısı
            output_dir: Dosyaların kaydedileceği klasör
            project_name: Proje adı (islik kutusunda)
            city: Şehir (islik kutusunda)

        Returns:
            ProjectOutput — dosya yolları + ZIP yolu
        """
        print(f"[{_ts()}] [DXF-GEN] ═══ Proje üretimi başlıyor: {project_name} ═══")

        os.makedirs(output_dir, exist_ok=True)
        output = ProjectOutput()

        parcel: ParcelInfo = project_data["parcel"]
        building: BuildingSpec = project_data["building"]
        report = project_data["report"]

        # ── Kat planlarını hesapla ────────────────────────────────────
        bw = building.footprint_width
        bd = building.footprint_depth
        has_elevator = any(f.elevator_area > 0 for f in building.floors)

        floor_plans: list[FloorPlanResult] = []
        for floor in building.floors:
            if floor.floor_type == "bodrum":
                # Bodrum basit plan
                plan = FloorPlanResult(
                    floor_number=floor.floor_number,
                    floor_type="bodrum",
                    building_width=bw,
                    building_depth=bd,
                )
                floor_plans.append(plan)
            else:
                plan = self.planner.plan_floor(
                    floor, bw, bd, has_elevator=has_elevator,
                )
                floor_plans.append(plan)

        print(f"[{_ts()}] [DXF-GEN] Kat planları hesaplandı: {len(floor_plans)} kat")

        # ── 1. Vaziyet Planı ─────────────────────────────────────────
        vp_path = os.path.join(output_dir, "vaziyet_plani.dxf")
        self._generate_site_plan(vp_path, parcel, building, project_name, city)
        output.files["Vaziyet Planı"] = vp_path
        print(f"[{_ts()}] [DXF-GEN] ✓ Vaziyet planı")

        # ── 2. Kat Planları ──────────────────────────────────────────
        sheet_num = 2
        for fp in floor_plans:
            if fp.floor_type == "bodrum":
                fname = f"kat_plani_bodrum_{abs(fp.floor_number)}.dxf"
                label = f"B{abs(fp.floor_number)}. Bodrum Kat Planı"
            elif fp.floor_type == "zemin":
                fname = "kat_plani_zemin.dxf"
                label = "Zemin Kat Planı"
            elif fp.floor_type == "cati":
                fname = "kat_plani_cati.dxf"
                label = "Çatı Katı Planı"
            else:
                fname = f"kat_plani_{fp.floor_number}.dxf"
                label = f"{fp.floor_number}. Kat Planı"

            fp_path = os.path.join(output_dir, fname)
            self._generate_floor_plan(
                fp_path, fp, project_name, label,
                f"A-{sheet_num:02d}", city,
            )
            output.files[label] = fp_path
            sheet_num += 1

        print(f"[{_ts()}] [DXF-GEN] ✓ Kat planları ({len(floor_plans)} adet)")

        # ── 3. Kesitler ──────────────────────────────────────────────
        for section_type in ["A-A", "B-B"]:
            s_path = os.path.join(output_dir, f"kesit_{section_type.replace('-', '_')}.dxf")
            self._generate_section(
                s_path, floor_plans, building,
                section_type, project_name, f"A-{sheet_num:02d}", city,
            )
            output.files[f"Kesit {section_type}"] = s_path
            sheet_num += 1

        print(f"[{_ts()}] [DXF-GEN] ✓ Kesitler (A-A, B-B)")

        # ── 4. Görünüşler ────────────────────────────────────────────
        facades = ["south", "east", "north", "west"]
        facade_labels = {
            "south": "Ön Görünüş", "east": "Sağ Yan Görünüş",
            "north": "Arka Görünüş", "west": "Sol Yan Görünüş",
        }
        for facade in facades:
            e_path = os.path.join(output_dir, f"gorunus_{facade}.dxf")
            self._generate_elevation(
                e_path, floor_plans, building,
                facade, project_name, f"A-{sheet_num:02d}", city,
            )
            output.files[facade_labels[facade]] = e_path
            sheet_num += 1

        print(f"[{_ts()}] [DXF-GEN] ✓ Görünüşler (4 cephe)")

        # ── 5. Çatı Planı ────────────────────────────────────────────
        cp_path = os.path.join(output_dir, "cati_plani.dxf")
        self._generate_roof_plan(cp_path, building, project_name, f"A-{sheet_num:02d}", city)
        output.files["Çatı Planı"] = cp_path
        sheet_num += 1
        print(f"[{_ts()}] [DXF-GEN] ✓ Çatı planı")

        # ── 6. Alan Hesap Tablosu ────────────────────────────────────
        ah_path = os.path.join(output_dir, "alan_hesap.dxf")
        self._generate_area_table(ah_path, project_data, project_name, f"A-{sheet_num:02d}", city)
        output.files["Alan Hesap Tablosu"] = ah_path
        print(f"[{_ts()}] [DXF-GEN] ✓ Alan hesap tablosu")

        # ── 7. ZIP Paketleme ─────────────────────────────────────────
        zip_path = os.path.join(output_dir, f"{project_name.replace(' ', '_')}_proje_paketi.zip")
        _create_zip(zip_path, output.files)
        output.zip_path = zip_path

        total = len(output.files)
        print(f"[{_ts()}] [DXF-GEN] ═══ Proje tamamlandı: {total} pafta + ZIP ═══")

        return output

    # ══════════════════════════════════════════════════════════════════════
    # Pafta Üreticiler
    # ══════════════════════════════════════════════════════════════════════

    # ── Vaziyet Planı ───────────────────────────────────────────────────

    def _generate_site_plan(self, path, parcel, building, project_name, city):
        """Vaziyet planı DXF üret."""
        doc = create_new_dxf()
        self.blocks.register_all(doc)
        msp = doc.modelspace()

        scale = 200.0   # 1/200
        area = draw_sheet_border(msp, "A2", scale)

        # Parsel sınırı
        pw, pd = parcel.width, parcel.depth
        # Parsel orijini — pafta ortasında
        cx = (area[0] + area[2]) / 2 - pw / 2
        cy = (area[1] + area[3]) / 2 - pd / 2

        msp.add_lwpolyline([
            (cx, cy), (cx + pw, cy), (cx + pw, cy + pd), (cx, cy + pd), (cx, cy),
        ], dxfattribs={"layer": "A-SITE", "lineweight": 70})

        # Çekme mesafeleri çizgileri (dashed)
        fs = parcel.front_setback
        ss = parcel.side_setback
        rs = parcel.rear_setback

        msp.add_lwpolyline([
            (cx + ss, cy + fs), (cx + pw - ss, cy + fs),
            (cx + pw - ss, cy + pd - rs), (cx + ss, cy + pd - rs),
            (cx + ss, cy + fs),
        ], dxfattribs={"layer": "A-SITE", "lineweight": 18})

        # Çekme ölçüleri (metin)
        msp.add_text(f"Ön: {fs}m", dxfattribs={"layer": "A-SITE-DIM", "height": 0.30}).set_placement(
            (cx + pw / 2, cy + fs / 2), align=ezdxf.enums.TextEntityAlignment.CENTER)
        msp.add_text(f"Yan: {ss}m", dxfattribs={"layer": "A-SITE-DIM", "height": 0.30}).set_placement(
            (cx + ss / 2, cy + pd / 2), align=ezdxf.enums.TextEntityAlignment.CENTER)
        msp.add_text(f"Arka: {rs}m", dxfattribs={"layer": "A-SITE-DIM", "height": 0.30}).set_placement(
            (cx + pw / 2, cy + pd - rs / 2), align=ezdxf.enums.TextEntityAlignment.CENTER)

        # Bina oturum
        bw, bd = building.footprint_width, building.footprint_depth
        bx = cx + ss + (pw - 2 * ss - bw) / 2
        by = cy + fs + (pd - fs - rs - bd) / 2

        msp.add_lwpolyline([
            (bx, by), (bx + bw, by), (bx + bw, by + bd), (bx, by + bd), (bx, by),
        ], dxfattribs={"layer": "A-BNDRY", "lineweight": 70})

        # Bina bilgileri
        msp.add_text(
            f"TAKS: {building.footprint_area / parcel.area:.3f}",
            dxfattribs={"layer": "A-TEXT", "height": 0.25},
        ).set_placement((bx + bw / 2, by + bd / 2 + 0.5), align=ezdxf.enums.TextEntityAlignment.CENTER)

        msp.add_text(
            f"{building.above_ground_floors} Kat",
            dxfattribs={"layer": "A-TEXT", "height": 0.25},
        ).set_placement((bx + bw / 2, by + bd / 2 - 0.2), align=ezdxf.enums.TextEntityAlignment.CENTER)

        # Kuzey oku
        msp.add_blockref("NORTH_ARROW", insert=(cx + pw - 1.5, cy + pd - 1.5),
                         dxfattribs={"layer": "A-ANNO"})

        # Yol
        msp.add_lwpolyline([
            (cx - 3, cy - 4), (cx + pw + 3, cy - 4),
            (cx + pw + 3, cy), (cx - 3, cy), (cx - 3, cy - 4),
        ], dxfattribs={"layer": "A-SITE-ROAD"})
        msp.add_text("YOL", dxfattribs={"layer": "A-SITE-ROAD", "height": 0.40}).set_placement(
            (cx + pw / 2, cy - 2), align=ezdxf.enums.TextEntityAlignment.CENTER)

        draw_title_block(msp, area, scale, project_name, "Vaziyet Planı", "1/200", "A-01",
                         sheet_num_total(building), city=city)
        doc.saveas(path)

    # ── Kat Planı ───────────────────────────────────────────────────────

    def _generate_floor_plan(self, path, plan: FloorPlanResult,
                             project_name, sheet_title, sheet_number, city):
        """Tek kat planı DXF üret — Sprint 7 ultra profesyonel kalite."""
        doc = create_new_dxf()
        self.blocks.register_all(doc)
        msp = doc.modelspace()

        scale = 100.0   # 1/100
        area = draw_sheet_border(msp, "A2", scale)

        # Orijin — çizim alanının merkezine hizala
        cx = (area[0] + area[2]) / 2 - plan.building_width / 2
        cy = (area[1] + area[3]) / 2 - plan.building_depth / 2

        # ── 1. Aks grid sistemi (arka plan) ──────────────────────────
        self._draw_axis_grid(msp, plan, cx, cy)

        # ── 2. Çift çizgi duvarlar ───────────────────────────────────
        self._draw_walls(msp, plan, cx, cy)

        # ── 3. Duvar kesit hatch (ANSI31) ────────────────────────────
        self._draw_wall_hatches(msp, plan, cx, cy)

        # ── 4. Islak hacim hatch (ANSI37/DOTS) ──────────────────────
        self._draw_room_hatches(msp, plan, cx, cy)

        # ── 5. Kolonlar ──────────────────────────────────────────────
        for col in plan.columns:
            msp.add_blockref("COLUMN_40x40", insert=(cx + col.x, cy + col.y),
                             dxfattribs={"layer": "A-COLS"})

        # ── 6. Merdiven ──────────────────────────────────────────────
        msp.add_blockref(plan.stair_block, insert=(cx + plan.stair_x, cy + plan.stair_y),
                         dxfattribs={"layer": "A-STRS"})

        # ── 7. Asansör ───────────────────────────────────────────────
        if plan.has_elevator:
            msp.add_blockref("ELEVATOR_CABIN",
                             insert=(cx + plan.elevator_x, cy + plan.elevator_y),
                             dxfattribs={"layer": "A-ELEV"})

        # ── 8. Kapılar ───────────────────────────────────────────────
        for door in plan.doors:
            insert_door(msp, door.block_name,
                        (cx + door.x, cy + door.y),
                        rotation=door.rotation, mirror=door.mirror)

        # ── 9. Pencereler ────────────────────────────────────────────
        for win in plan.windows:
            insert_window(msp, win.block_name,
                          (cx + win.x, cy + win.y),
                          rotation=win.rotation)

        # ── 10. Oda isimleri + alanlar + birim kodu ──────────────────
        self._draw_room_labels(msp, plan, cx, cy)

        # ── 11. İç oda ölçüleri ──────────────────────────────────────
        self._draw_room_dims(msp, plan, cx, cy)

        # ── 12. 3 seviye dış ölçüler (genel→aks→detay) ──────────────
        self._draw_3level_dims(msp, plan, cx, cy)

        # ── 13. Mobilya yerleşimi ────────────────────────────────────
        self._draw_furniture(msp, plan, cx, cy)

        # ── 14. Kapı kodları (K1, K2, ...) ───────────────────────────
        self._draw_door_labels(msp, plan, cx, cy)

        # ── 15. Pencere kodları (P1, P2, ...) ────────────────────────
        self._draw_window_labels(msp, plan, cx, cy)

        # ── 16. Kat kotu ─────────────────────────────────────────────
        floor_label = "±0.00" if plan.floor_number == 0 else f"+{plan.floor_number * 2.80:.2f}"
        self._draw_floor_level_mark(msp, cx, cy, plan.building_depth, floor_label)

        # ── 17. Kuzey oku ────────────────────────────────────────────
        self._draw_north_arrow(msp, cx, cy, plan.building_width, plan.building_depth)

        # ── 18. Ölçek barı ───────────────────────────────────────────
        self._draw_scale_bar(msp, cx, cy)

        draw_title_block(msp, area, scale, project_name, sheet_title, "1/100",
                         sheet_number, sheet_num_total(None), city=city)
        doc.saveas(path)

    # ── Yeni yardımcı: Çift çizgi duvarlar ──────────────────────────────

    def _draw_walls(self, msp, plan: FloorPlanResult, cx: float, cy: float) -> None:
        """Duvarları çift çizgi (iç+dış polyline) olarak çiz. Opening gap'ler uygulanır."""
        for wall in plan.walls:
            layer = wall.layer
            lw = 70 if wall.wall_type.value == "exterior" else 35

            # İç yüz segmentleri
            for seg in wall.inner_lines:
                p1 = (cx + seg[0][0], cy + seg[0][1])
                p2 = (cx + seg[1][0], cy + seg[1][1])
                msp.add_line(p1, p2, dxfattribs={"layer": layer, "lineweight": lw})

            # Dış yüz segmentleri
            for seg in wall.outer_lines:
                p1 = (cx + seg[0][0], cy + seg[0][1])
                p2 = (cx + seg[1][0], cy + seg[1][1])
                msp.add_line(p1, p2, dxfattribs={"layer": layer, "lineweight": lw})

            # Duvar uçlarını kapat (opening olmayan bölgelerde)
            inner = wall.inner_lines
            outer = wall.outer_lines
            if inner and outer:
                # Başlangıç kapanış
                msp.add_line(
                    (cx + inner[0][0][0], cy + inner[0][0][1]),
                    (cx + outer[0][0][0], cy + outer[0][0][1]),
                    dxfattribs={"layer": layer, "lineweight": lw},
                )
                # Bitiş kapanış
                msp.add_line(
                    (cx + inner[-1][1][0], cy + inner[-1][1][1]),
                    (cx + outer[-1][1][0], cy + outer[-1][1][1]),
                    dxfattribs={"layer": layer, "lineweight": lw},
                )

    # ── Yeni yardımcı: Duvar kesit hatch ────────────────────────────────

    def _draw_wall_hatches(self, msp, plan: FloorPlanResult, cx: float, cy: float) -> None:
        """Dış duvarların kesit alanını ANSI31 hatch ile doldur."""
        for wall in plan.walls:
            if wall.wall_type.value != "exterior":
                continue  # Sadece dış duvarlar hatch alır

            polygons = wall.hatch_polygons
            if not polygons:
                continue

            for poly in polygons:
                try:
                    hatch = msp.add_hatch(dxfattribs={"layer": "A-WALL-HATCH"})
                    hatch.set_pattern_fill("ANSI31", scale=0.02, color=8)
                    offset_poly = [(cx + p[0], cy + p[1]) for p in poly]
                    hatch.paths.add_polyline_path(offset_poly, is_closed=True)
                except Exception:
                    pass  # Hatch uygulanamazsa sessizce devam et

    # ── Yeni yardımcı: Islak hacim hatch ────────────────────────────────

    def _draw_room_hatches(self, msp, plan: FloorPlanResult, cx: float, cy: float) -> None:
        """Banyo/WC/Mutfak zemin hatch'i uygula."""
        for room in plan.rooms:
            if not room.hatch_pattern:
                continue

            try:
                hatch = msp.add_hatch(dxfattribs={"layer": "A-FLOR-HATCH"})
                hatch.set_pattern_fill(room.hatch_pattern, scale=0.03, color=253)
                vertices = [
                    (cx + room.x, cy + room.y),
                    (cx + room.x + room.width, cy + room.y),
                    (cx + room.x + room.width, cy + room.y + room.depth),
                    (cx + room.x, cy + room.y + room.depth),
                ]
                hatch.paths.add_polyline_path(vertices, is_closed=True)
            except Exception:
                pass

    # ── Yeni yardımcı: İç oda ölçüleri ──────────────────────────────────

    def _draw_room_dims(self, msp, plan: FloorPlanResult, cx: float, cy: float) -> None:
        """Her odanın iç genişlik ve derinlik ölçülerini çiz."""
        for room in plan.rooms:
            if room.room_type in ("koridor",):
                continue
            if room.width < 1.5 or room.depth < 1.5:
                continue

            rx = cx + room.x
            ry = cy + room.y
            rw = room.width
            rd = room.depth

            # Genişlik ölçüsü (alt kenar boyunca, iç tarafa)
            try:
                msp.add_aligned_dim(
                    p1=(rx, ry),
                    p2=(rx + rw, ry),
                    distance=0.25,
                    dimstyle="ARCH_DIM",
                    dxfattribs={"layer": "A-DIMS"},
                ).render()
            except Exception:
                # Fallback: basit text ölçü
                msp.add_text(
                    f"{rw:.2f}",
                    dxfattribs={"layer": "A-DIMS", "height": 0.08},
                ).set_placement(
                    (rx + rw / 2, ry + 0.15),
                    align=ezdxf.enums.TextEntityAlignment.CENTER,
                )

            # Derinlik ölçüsü (sol kenar boyunca, iç tarafa)
            try:
                msp.add_aligned_dim(
                    p1=(rx, ry),
                    p2=(rx, ry + rd),
                    distance=-0.25,
                    dimstyle="ARCH_DIM",
                    dxfattribs={"layer": "A-DIMS"},
                ).render()
            except Exception:
                msp.add_text(
                    f"{rd:.2f}",
                    dxfattribs={"layer": "A-DIMS", "height": 0.08},
                ).set_placement((rx + 0.15, ry + rd / 2))

    # ── Yeni yardımcı: Aks grid sistemi ─────────────────────────────────

    def _draw_axis_grid(self, msp, plan: FloorPlanResult, cx: float, cy: float) -> None:
        """Aks çizgileri (A-B-C / 1-2-3) + balon daireleri çiz."""
        bubble_r = 0.40  # balon yarıçapı (m)

        for axis in plan.axes:
            if axis.direction == "vertical":
                # Dikey aks çizgisi
                x = cx + axis.position
                y1 = cy + axis.start
                y2 = cy + axis.end

                msp.add_line(
                    (x, y1), (x, y2),
                    dxfattribs={"layer": "A-GRID", "linetype": "CENTER2"},
                )

                # Üst balon
                bubble_center = (x, y2 + bubble_r + 0.3)
                msp.add_circle(
                    bubble_center, radius=bubble_r,
                    dxfattribs={"layer": "A-GRID"},
                )
                msp.add_text(
                    axis.label,
                    dxfattribs={"layer": "A-GRID", "height": 0.30},
                ).set_placement(bubble_center, align=ezdxf.enums.TextEntityAlignment.MIDDLE)

                # Alt balon
                bubble_center_b = (x, y1 - bubble_r - 0.3)
                msp.add_circle(
                    bubble_center_b, radius=bubble_r,
                    dxfattribs={"layer": "A-GRID"},
                )
                msp.add_text(
                    axis.label,
                    dxfattribs={"layer": "A-GRID", "height": 0.30},
                ).set_placement(bubble_center_b, align=ezdxf.enums.TextEntityAlignment.MIDDLE)

            else:
                # Yatay aks çizgisi
                y = cy + axis.position
                x1 = cx + axis.start
                x2 = cx + axis.end

                msp.add_line(
                    (x1, y), (x2, y),
                    dxfattribs={"layer": "A-GRID", "linetype": "CENTER2"},
                )

                # Sol balon
                bubble_center = (x1 - bubble_r - 0.3, y)
                msp.add_circle(
                    bubble_center, radius=bubble_r,
                    dxfattribs={"layer": "A-GRID"},
                )
                msp.add_text(
                    axis.label,
                    dxfattribs={"layer": "A-GRID", "height": 0.30},
                ).set_placement(bubble_center, align=ezdxf.enums.TextEntityAlignment.MIDDLE)

                # Sağ balon
                bubble_center_r = (x2 + bubble_r + 0.3, y)
                msp.add_circle(
                    bubble_center_r, radius=bubble_r,
                    dxfattribs={"layer": "A-GRID"},
                )
                msp.add_text(
                    axis.label,
                    dxfattribs={"layer": "A-GRID", "height": 0.30},
                ).set_placement(bubble_center_r, align=ezdxf.enums.TextEntityAlignment.MIDDLE)

    # ── Yeni yardımcı: Mobilya yerleşimi ────────────────────────────────

    def _draw_furniture(self, msp, plan: FloorPlanResult, cx: float, cy: float) -> None:
        """Oda tipine göre otomatik mobilya blokları yerleştir."""
        for room in plan.rooms:
            if room.unit_id == "COMMON":
                continue

            rx = cx + room.x
            ry = cy + room.y
            rw = room.width
            rd = room.depth
            rcx_abs = rx + rw / 2
            rcy_abs = ry + rd / 2

            try:
                if room.room_type == "salon":
                    # Koltuk takımı — oda merkezinin alt kısmında
                    insert_furniture(msp, "SOFA_3SEAT", (rcx_abs - 0.85, ry + 0.3))
                    # Sehpa
                    insert_furniture(msp, "TABLE_COFFEE", (rcx_abs - 0.50, ry + 1.3))

                elif room.room_type == "yatak_odasi":
                    # Yatak — üst duvara yaslanmış
                    if rw >= 3.0:
                        insert_furniture(msp, "BED_DOUBLE", (rcx_abs - 0.70, ry + rd - 2.1))
                    else:
                        insert_furniture(msp, "BED_SINGLE", (rcx_abs - 0.45, ry + rd - 2.1))
                    # Komodin
                    insert_furniture(msp, "TABLE_NIGHT", (rx + 0.1, ry + rd - 0.5))

                elif room.room_type == "mutfak":
                    # Mutfak tezgahı — üst duvar boyunca
                    insert_furniture(msp, "KITCHEN_COUNTER", (rx + 0.1, ry + rd - 0.7))

                elif room.room_type == "banyo":
                    # Lavabo + Duş
                    insert_furniture(msp, "LAVABO", (rx + 0.3, ry + rd - 0.6))
                    if rw >= 2.0:
                        insert_furniture(msp, "DUSCH_CABIN", (rx + rw - 1.0, ry + 0.1))

                elif room.room_type == "wc":
                    # Klozet
                    insert_furniture(msp, "KLOZET", (rcx_abs - 0.20, ry + rd - 0.7))
                    # Lavabo (küçük)
                    insert_furniture(msp, "LAVABO", (rx + 0.2, ry + 0.2))

            except Exception:
                pass  # Blok bulunamazsa sessizce devam et

    # ── Kesit ───────────────────────────────────────────────────────────

    def _generate_section(self, path, floor_plans, building,
                          section_type, project_name, sheet_number, city):
        """Kesit DXF üret."""
        doc = create_new_dxf()
        msp = doc.modelspace()

        scale = 100.0
        area = draw_sheet_border(msp, "A2", scale)

        ox = (area[0] + area[2]) / 2 - (floor_plans[0].building_width if section_type == "A-A" else floor_plans[0].building_depth) / 2
        oy = area[1] + 3.0  # alttan 3m boşluk

        floor_h = 2.80  # default
        for f in building.floors:
            if f.height_gross > 0:
                floor_h = f.height_gross
                break

        self.section_gen.draw_section(msp, floor_plans, floor_h, section_type, ox, oy)

        draw_title_block(msp, area, scale, project_name, f"Kesit {section_type}",
                         "1/100", sheet_number, sheet_num_total(None), city=city)
        doc.saveas(path)

    # ── Görünüş ─────────────────────────────────────────────────────────

    def _generate_elevation(self, path, floor_plans, building,
                            facade, project_name, sheet_number, city):
        """Görünüş DXF üret."""
        doc = create_new_dxf()
        msp = doc.modelspace()

        scale = 100.0
        area = draw_sheet_border(msp, "A2", scale)

        ref = floor_plans[0]
        elev_w = ref.building_width if facade in ("south", "north") else ref.building_depth

        ox = (area[0] + area[2]) / 2 - elev_w / 2
        oy = area[1] + 3.0

        floor_h = 2.80
        for f in building.floors:
            if f.height_gross > 0:
                floor_h = f.height_gross
                break

        self.elevation_gen.draw_elevation(msp, floor_plans, floor_h, facade, ox, oy)

        facade_labels = {
            "south": "Ön Görünüş", "east": "Sağ Yan",
            "north": "Arka Görünüş", "west": "Sol Yan",
        }
        draw_title_block(msp, area, scale, project_name, facade_labels[facade],
                         "1/100", sheet_number, sheet_num_total(None), city=city)
        doc.saveas(path)

    # ── Çatı Planı ──────────────────────────────────────────────────────

    def _generate_roof_plan(self, path, building, project_name, sheet_number, city):
        """Çatı planı DXF üret."""
        doc = create_new_dxf()
        msp = doc.modelspace()

        scale = 100.0
        area = draw_sheet_border(msp, "A2", scale)

        bw, bd = building.footprint_width, building.footprint_depth
        cx = (area[0] + area[2]) / 2 - bw / 2
        cy = (area[1] + area[3]) / 2 - bd / 2

        # Bina konturu
        msp.add_lwpolyline([
            (cx, cy), (cx + bw, cy), (cx + bw, cy + bd), (cx, cy + bd), (cx, cy),
        ], dxfattribs={"layer": "A-ROOF", "lineweight": 70})

        # Parapet
        msp.add_lwpolyline([
            (cx + 0.25, cy + 0.25), (cx + bw - 0.25, cy + 0.25),
            (cx + bw - 0.25, cy + bd - 0.25), (cx + 0.25, cy + bd - 0.25),
            (cx + 0.25, cy + 0.25),
        ], dxfattribs={"layer": "A-ROOF"})

        # Eğim çizgileri (merkeze doğru)
        mid_x, mid_y = cx + bw / 2, cy + bd / 2
        for corner in [(cx + 0.25, cy + 0.25), (cx + bw - 0.25, cy + 0.25),
                       (cx + bw - 0.25, cy + bd - 0.25), (cx + 0.25, cy + bd - 0.25)]:
            msp.add_line(corner, (mid_x, mid_y), dxfattribs={"layer": "A-ROOF-SLOPE"})

        # Eğim yönü oku + metin
        msp.add_text("% 2", dxfattribs={"layer": "A-ROOF", "height": 0.15}).set_placement(
            (mid_x, mid_y + 0.5), align=ezdxf.enums.TextEntityAlignment.CENTER)

        # Kuzey oku
        msp.add_blockref("NORTH_ARROW", insert=(cx + bw - 1.5, cy + bd - 1.5),
                         dxfattribs={"layer": "A-ANNO"})

        draw_title_block(msp, area, scale, project_name, "Çatı Planı", "1/100",
                         sheet_number, sheet_num_total(None), city=city)
        doc.saveas(path)

    # ── Alan Hesap Tablosu ──────────────────────────────────────────────

    def _generate_area_table(self, path, project_data, project_name, sheet_number, city):
        """Alan hesap tablosu DXF üret."""
        doc = create_new_dxf()
        msp = doc.modelspace()

        scale = 100.0
        area = draw_sheet_border(msp, "A2", scale)

        # Tablo başlangıç
        tx = area[0] + 2.0
        ty = area[3] - 2.0
        row_h = 0.60
        col_widths = [6.0, 4.0, 4.0, 4.0, 4.0]  # Kat, Brüt, Net, Daire, Ortak
        total_w = sum(col_widths)

        headers = ["KAT", "BRÜT ALAN", "NET ALAN", "DAİRE ALAN", "ORTAK ALAN"]

        # Başlık satırı
        self._table_row(msp, tx, ty, col_widths, headers, header=True)
        ty -= row_h

        # Tablo verileri
        building: BuildingSpec = project_data["building"]
        area_table = project_data.get("area_table", {})

        total_gross = 0
        total_net = 0
        total_unit = 0
        total_common = 0

        for floor in building.floors:
            if floor.floor_type == "bodrum":
                label = f"B{abs(floor.floor_number)}. Bodrum"
            elif floor.floor_type == "zemin":
                label = "Zemin Kat"
            else:
                label = f"{floor.floor_number}. Kat"

            gross = floor.gross_area
            unit_a = sum(u.gross_area for u in floor.units)
            common = floor.staircase_area + floor.elevator_area + floor.corridor_area
            net = unit_a + common

            total_gross += gross
            total_net += net
            total_unit += unit_a
            total_common += common

            self._table_row(msp, tx, ty, col_widths, [
                label, f"{gross:.1f} m²", f"{net:.1f} m²",
                f"{unit_a:.1f} m²", f"{common:.1f} m²",
            ])
            ty -= row_h

        # Toplam satırı
        self._table_row(msp, tx, ty, col_widths, [
            "TOPLAM", f"{total_gross:.1f} m²", f"{total_net:.1f} m²",
            f"{total_unit:.1f} m²", f"{total_common:.1f} m²",
        ], header=True)
        ty -= row_h * 2

        # TAKS / KAKS bilgileri
        report = project_data["report"]
        info_lines = [
            f"TAKS: {report.taks_actual:.3f} / {report.taks_limit} {'✓' if report.taks_actual <= report.taks_limit else '✗'}",
            f"KAKS: {report.kaks_actual:.3f} / {report.kaks_limit} {'✓' if report.kaks_actual <= report.kaks_limit else '✗'}",
            f"Bina Yüksekliği: {report.building_height:.2f} m (max {report.max_height} m)",
            f"Otopark: {report.parking_required} gerekli",
        ]
        for line in info_lines:
            msp.add_text(line, dxfattribs={"layer": "A-TEXT", "height": 0.15}).set_placement((tx, ty))
            ty -= 0.40

        # Maliyet
        cost = project_data.get("cost", {})
        if cost:
            ty -= 0.30
            msp.add_text(
                f"Yaklaşık Maliyet: {cost.get('estimates_tl', {}).get('mid', 0):,.0f} TL",
                dxfattribs={"layer": "A-TEXT", "height": 0.18},
            ).set_placement((tx, ty))

        draw_title_block(msp, area, scale, project_name, "Alan Hesap Tablosu", "—",
                         sheet_number, sheet_num_total(None), city=city)
        doc.saveas(path)

    # ── Yardımcılar ─────────────────────────────────────────────────────

    def _table_row(self, msp, x, y, col_widths, values, header=False):
        """Tablo satırı çiz."""
        row_h = 0.60
        cx = x
        for i, (w, val) in enumerate(zip(col_widths, values)):
            # Hücre çerçevesi
            msp.add_lwpolyline([
                (cx, y), (cx + w, y), (cx + w, y - row_h), (cx, y - row_h), (cx, y),
            ], dxfattribs={"layer": "A-TEXT"})
            # Metin
            th = 0.14 if header else 0.12
            msp.add_text(
                val,
                dxfattribs={"layer": "A-TEXT", "height": th},
            ).set_placement((cx + w / 2, y - row_h / 2), align=ezdxf.enums.TextEntityAlignment.CENTER)
            cx += w

    def _draw_outer_dims(self, msp, plan, cx, cy):
        """Kat planı dış ölçülerini çiz."""
        bw = plan.building_width
        bd = plan.building_depth
        offset = 1.0  # ölçü çizgisi bina dışından mesafe

        # Genişlik (alt)
        try:
            msp.add_linear_dim(
                base=(cx, cy - offset),
                p1=(cx, cy),
                p2=(cx + bw, cy),
                dimstyle="ARCH_DIM",
                dxfattribs={"layer": "A-DIMS"},
            ).render()
        except Exception:
            # Fallback — basit metin
            msp.add_text(
                f"{bw:.2f}",
                dxfattribs={"layer": "A-DIMS", "height": 0.10},
            ).set_placement((cx + bw / 2, cy - offset - 0.15), align=ezdxf.enums.TextEntityAlignment.CENTER)

        # Derinlik (sol)
        try:
            msp.add_linear_dim(
                base=(cx - offset, cy),
                p1=(cx, cy),
                p2=(cx, cy + bd),
                angle=90,
                dimstyle="ARCH_DIM",
                dxfattribs={"layer": "A-DIMS"},
            ).render()
        except Exception:
            msp.add_text(
                f"{bd:.2f}",
                dxfattribs={"layer": "A-DIMS", "height": 0.10},
            ).set_placement((cx - offset - 0.15, cy + bd / 2))

    # ══════════════════════════════════════════════════════════════════════
    # Sprint 7 — New Professional Drawing Methods
    # ══════════════════════════════════════════════════════════════════════

    def _draw_room_labels(self, msp, plan: FloorPlanResult, cx: float, cy: float) -> None:
        """Oda isim + alan + birim kodu etiketi."""
        for room in plan.rooms:
            rcx, rcy = room.center
            abs_x = cx + rcx
            abs_y = cy + rcy

            # Oda ismi (büyük)
            msp.add_text(
                room.name.upper(),
                dxfattribs={"layer": "A-ANNO", "height": 0.20},
            ).set_placement((abs_x, abs_y + 0.25), align=ezdxf.enums.TextEntityAlignment.CENTER)

            # Alan (m²)
            msp.add_text(
                f"{room.area:.2f} m²",
                dxfattribs={"layer": "A-ANNO", "height": 0.15},
            ).set_placement((abs_x, abs_y - 0.05), align=ezdxf.enums.TextEntityAlignment.CENTER)

            # Birim kodu (daire ID)
            if room.unit_id and room.unit_id != "COMMON":
                msp.add_text(
                    f"[{room.unit_id}]",
                    dxfattribs={"layer": "A-ANNO", "height": 0.10, "color": 8},
                ).set_placement((abs_x, abs_y - 0.30), align=ezdxf.enums.TextEntityAlignment.CENTER)

    def _draw_3level_dims(self, msp, plan: FloorPlanResult, cx: float, cy: float) -> None:
        """
        3 seviye ölçülendirme zinciri:
         1. Seviye (en dışta, 2.0m offset): genel boyutlar (bina genişlik/derinlik)
         2. Seviye (1.5m offset): aks aralıkları
         3. Seviye (1.0m offset): detay — pencere/kapı pozisyonları
        """
        bw = plan.building_width
        bd = plan.building_depth

        # ── Seviye 1: Genel boyutlar (en dışta) ──────────────────────
        offset1 = 2.5
        # Genişlik (alt)
        try:
            msp.add_linear_dim(
                base=(cx, cy - offset1),
                p1=(cx, cy), p2=(cx + bw, cy),
                dimstyle="ARCH_DIM",
                dxfattribs={"layer": "A-DIMS"},
            ).render()
        except Exception:
            msp.add_text(f"{bw:.2f}", dxfattribs={"layer": "A-DIMS", "height": 0.12})\
                .set_placement((cx + bw / 2, cy - offset1 - 0.15),
                               align=ezdxf.enums.TextEntityAlignment.CENTER)

        # Derinlik (sol)
        try:
            msp.add_linear_dim(
                base=(cx - offset1, cy),
                p1=(cx, cy), p2=(cx, cy + bd),
                angle=90,
                dimstyle="ARCH_DIM",
                dxfattribs={"layer": "A-DIMS"},
            ).render()
        except Exception:
            msp.add_text(f"{bd:.2f}", dxfattribs={"layer": "A-DIMS", "height": 0.12})\
                .set_placement((cx - offset1 - 0.15, cy + bd / 2))

        # ── Seviye 2: Aks aralıkları ─────────────────────────────────
        offset2 = 1.5
        v_axes = sorted([a for a in plan.axes if a.direction == "vertical"],
                        key=lambda a: a.position)
        h_axes = sorted([a for a in plan.axes if a.direction == "horizontal"],
                        key=lambda a: a.position)

        # Dikey aks aralıkları (alt boyut çizgisi)
        for i in range(len(v_axes) - 1):
            x1 = v_axes[i].position
            x2 = v_axes[i + 1].position
            try:
                msp.add_linear_dim(
                    base=(cx + x1, cy - offset2),
                    p1=(cx + x1, cy), p2=(cx + x2, cy),
                    dimstyle="ARCH_DIM",
                    dxfattribs={"layer": "A-DIMS"},
                ).render()
            except Exception:
                dist = x2 - x1
                msp.add_text(f"{dist:.2f}", dxfattribs={"layer": "A-DIMS", "height": 0.10})\
                    .set_placement((cx + (x1 + x2) / 2, cy - offset2 - 0.10),
                                   align=ezdxf.enums.TextEntityAlignment.CENTER)

        # Yatay aks aralıkları (sol boyut çizgisi)
        for i in range(len(h_axes) - 1):
            y1 = h_axes[i].position
            y2 = h_axes[i + 1].position
            try:
                msp.add_linear_dim(
                    base=(cx - offset2, cy + y1),
                    p1=(cx, cy + y1), p2=(cx, cy + y2),
                    angle=90,
                    dimstyle="ARCH_DIM",
                    dxfattribs={"layer": "A-DIMS"},
                ).render()
            except Exception:
                dist = y2 - y1
                msp.add_text(f"{dist:.2f}", dxfattribs={"layer": "A-DIMS", "height": 0.10})\
                    .set_placement((cx - offset2 - 0.10, cy + (y1 + y2) / 2))

        # ── Seviye 3: Pencere/kapı pozisyonları (en yakın) ───────────
        offset3 = 1.0
        # Dış duvardaki pencere pozisyonları
        for win in plan.windows:
            if win.wall_side in ("south",):
                try:
                    msp.add_linear_dim(
                        base=(cx + win.x, cy - offset3),
                        p1=(cx + win.x, cy), p2=(cx + win.x + win.width, cy),
                        dimstyle="ARCH_DIM",
                        dxfattribs={"layer": "A-DIMS"},
                    ).render()
                except Exception:
                    pass

    def _draw_door_labels(self, msp, plan: FloorPlanResult, cx: float, cy: float) -> None:
        """Kapı kodları: K1, K2, K3... daire içinde."""
        for i, door in enumerate(plan.doors, 1):
            code = f"K{i}"
            dx = cx + door.x
            dy = cy + door.y

            # Kod dairesi
            label_x = dx + 0.3
            label_y = dy + 0.3
            msp.add_circle(
                (label_x, label_y), radius=0.15,
                dxfattribs={"layer": "A-DOOR"},
            )
            msp.add_text(
                code,
                dxfattribs={"layer": "A-DOOR", "height": 0.10},
            ).set_placement((label_x, label_y), align=ezdxf.enums.TextEntityAlignment.MIDDLE)

    def _draw_window_labels(self, msp, plan: FloorPlanResult, cx: float, cy: float) -> None:
        """Pencere kodları: P1, P2, P3... daire içinde."""
        for i, win in enumerate(plan.windows, 1):
            code = f"P{i}"
            wx = cx + win.x + win.width / 2

            # Pencere kodu — dış tarafa (duvar yönüne göre)
            if win.wall_side == "south":
                wy = cy + win.y - 0.5
            elif win.wall_side == "north":
                wy = cy + win.y + 0.5
            elif win.wall_side == "west":
                wy = cy + win.y
                wx = cx + win.x - 0.5
            else:
                wy = cy + win.y
                wx = cx + win.x + win.width + 0.5

            msp.add_circle(
                (wx, wy), radius=0.15,
                dxfattribs={"layer": "A-GLAZ"},
            )
            msp.add_text(
                code,
                dxfattribs={"layer": "A-GLAZ", "height": 0.10},
            ).set_placement((wx, wy), align=ezdxf.enums.TextEntityAlignment.MIDDLE)

            # Pencere boyut etiketi (genişlik × yükseklik)
            dim_text = f"{int(win.width * 100)}×{int(win.height * 100)}"
            msp.add_text(
                dim_text,
                dxfattribs={"layer": "A-GLAZ", "height": 0.08, "color": 8},
            ).set_placement((wx, wy - 0.25), align=ezdxf.enums.TextEntityAlignment.CENTER)

    def _draw_floor_level_mark(self, msp, cx: float, cy: float,
                                bd: float, level_text: str) -> None:
        """
        Kat kotu göstergesi — profesyonel üçgen + çizgi + kot.
        ┌─┐
        │▽│ ±0.00
        └─┘
        """
        # Kot simgesi: üçgen + etiket
        mark_x = cx - 2.0
        mark_y = cy + bd / 2

        # Üçgen (aşağı bakan)
        tri_size = 0.20
        msp.add_lwpolyline([
            (mark_x, mark_y + tri_size),
            (mark_x - tri_size, mark_y + tri_size * 2),
            (mark_x + tri_size, mark_y + tri_size * 2),
            (mark_x, mark_y + tri_size),
        ], dxfattribs={"layer": "A-ANNO"})

        # Yatay çizgi
        msp.add_line(
            (mark_x - 0.5, mark_y + tri_size),
            (mark_x + 0.5, mark_y + tri_size),
            dxfattribs={"layer": "A-ANNO"},
        )

        # Kot metni
        msp.add_text(
            level_text,
            dxfattribs={"layer": "A-ANNO", "height": 0.18},
        ).set_placement((mark_x + 0.6, mark_y + tri_size - 0.05))

        # "KAT KOTU" alt etiket
        msp.add_text(
            "KAT KOTU",
            dxfattribs={"layer": "A-ANNO", "height": 0.10, "color": 8},
        ).set_placement((mark_x + 0.6, mark_y - 0.05))

    def _draw_north_arrow(self, msp, cx: float, cy: float,
                           bw: float, bd: float) -> None:
        """Kuzey oku — pafta sağ üst köşesine yerleştir."""
        try:
            arrow_x = cx + bw + 3.0
            arrow_y = cy + bd - 1.0
            msp.add_blockref("NORTH_ARROW", insert=(arrow_x, arrow_y),
                             dxfattribs={"layer": "A-ANNO"})
        except Exception:
            # Blok yoksa elle çiz
            arrow_x = cx + bw + 3.0
            arrow_y = cy + bd - 1.0
            msp.add_circle((arrow_x, arrow_y), radius=0.50,
                           dxfattribs={"layer": "A-ANNO"})
            msp.add_line((arrow_x, arrow_y), (arrow_x, arrow_y + 0.40),
                         dxfattribs={"layer": "A-ANNO"})
            msp.add_text("N", dxfattribs={"layer": "A-ANNO", "height": 0.20})\
                .set_placement((arrow_x, arrow_y + 0.55),
                               align=ezdxf.enums.TextEntityAlignment.CENTER)

    def _draw_scale_bar(self, msp, cx: float, cy: float) -> None:
        """Ölçek barı — pafta sol alt."""
        try:
            msp.add_blockref("SCALE_BAR", insert=(cx - 1.0, cy - 3.0),
                             dxfattribs={"layer": "A-ANNO"})
        except Exception:
            pass
        # Ölçek yazısı
        msp.add_text(
            "ÖLÇEK: 1/100",
            dxfattribs={"layer": "A-ANNO", "height": 0.15},
        ).set_placement((cx - 1.0, cy - 3.5))


def sheet_num_total(building) -> int:
    """Toplam pafta sayısını hesapla."""
    if building is None:
        return 10  # fallback
    floors = len(building.floors)
    return 1 + floors + 2 + 4 + 1 + 1  # vaziyet + katlar + 2 kesit + 4 görünüş + çatı + alan


def _create_zip(zip_path: str, files: dict[str, str]) -> None:
    """DXF dosyalarını ZIP'e paketle."""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for label, fpath in files.items():
            if os.path.exists(fpath):
                zf.write(fpath, os.path.basename(fpath))


# ══════════════════════════════════════════════════════════════════════════════
# FAZ 2 Geriye Uyumluluk — eski DXFGenerator ve create_test_dxf
# ══════════════════════════════════════════════════════════════════════════════

# ezdxf modül seviyesinde her zaman import edilebilir
from core.blocks import EXT_WALL_T as _EXT_WALL_T  # noqa: E402


class RoomLayout:
    """Eski FAZ 2 uyumluluk."""
    def __init__(self, name, x, y, w, h):
        self.name = name; self.x = x; self.y = y
        self.w = w; self.h = h; self.area = w * h


class DXFGenerator:
    """FAZ 2 basit DXF generator — geriye uyumluluk."""

    def generate(self, request, output_path: str) -> str:
        doc = ezdxf.new("R2013")
        doc.header["$INSUNITS"] = 6
        msp = doc.modelspace()

        for name, props in [("A-WALL", 7), ("A-DOOR", 4), ("A-WIND", 5),
                            ("A-TEXT", 7), ("A-DIMS", 1), ("A-FURN", 3)]:
            if name not in doc.layers:
                doc.layers.add(name, color=props)

        # Simple grid layout
        rooms = getattr(request, "rooms", [])
        total_area = getattr(request, "area_m2", 100)
        cols = 2
        rows_count = math.ceil(len(rooms) / cols)
        cell_w = math.sqrt(total_area) / cols * 1.2
        cell_h = math.sqrt(total_area) / rows_count * 1.2

        layouts = []
        for i, room in enumerate(rooms):
            r = i // cols
            c = i % cols
            a = getattr(room, "min_area_m2", 12)
            w = math.sqrt(a * 1.2)
            h = a / w
            layouts.append(RoomLayout(
                name=getattr(room, "name", f"Oda {i+1}"),
                x=c * (cell_w + 0.10), y=r * (cell_h + 0.10), w=w, h=h,
            ))

        for rl in layouts:
            msp.add_lwpolyline(
                [(rl.x, rl.y), (rl.x + rl.w, rl.y), (rl.x + rl.w, rl.y + rl.h),
                 (rl.x, rl.y + rl.h), (rl.x, rl.y)],
                dxfattribs={"layer": "A-WALL"},
            )
            msp.add_text(
                f"{rl.name}\n{rl.area:.1f}m²",
                dxfattribs={"layer": "A-TEXT", "height": 0.15},
            ).set_placement((rl.x + rl.w / 2, rl.y + rl.h / 2),
                            align=ezdxf.enums.TextEntityAlignment.CENTER)

        doc.saveas(output_path)
        return output_path


def create_test_dxf(output_path: str) -> str:
    """FAZ 2 test DXF — geriye uyumluluk."""
    doc = ezdxf.new("R2013")
    doc.header["$INSUNITS"] = 6
    msp = doc.modelspace()

    for name, color in [("A-WALL", 7), ("A-DOOR", 4), ("A-WIND", 5), ("A-TEXT", 7)]:
        doc.layers.add(name, color=color)

    rooms = [
        ("Salon", 0, 0, 5.5, 4.5),
        ("Mutfak", 5.6, 0, 3.5, 3.0),
        ("Yatak Odası 1", 0, 4.6, 4.0, 3.5),
        ("Yatak Odası 2", 4.1, 4.6, 3.5, 3.5),
        ("Banyo", 5.6, 3.1, 3.5, 2.5),
    ]
    for name, x, y, w, h in rooms:
        msp.add_lwpolyline(
            [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)],
            dxfattribs={"layer": "A-WALL"},
        )
        msp.add_text(
            f"{name}\n{w * h:.1f}m²",
            dxfattribs={"layer": "A-TEXT", "height": 0.20},
        ).set_placement((x + w / 2, y + h / 2), align=ezdxf.enums.TextEntityAlignment.CENTER)

    doc.saveas(output_path)
    return output_path
