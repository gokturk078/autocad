"""DXF parser — reads a .dxf file with ezdxf and produces a ProjectModel."""

from __future__ import annotations

import logging
import math
import os
import time
import uuid
from datetime import datetime

import ezdxf
from ezdxf.math import area as shoelace_area

from models.project import ProjectModel, RoomModel

logger = logging.getLogger("jarvis")


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _clean_room_name(layer_name: str) -> str:
    """Turn an AutoCAD layer name like 'A-ROOM-SALON' into 'Salon'."""
    # Strip common prefixes
    name = layer_name.upper()
    for prefix in ("A-ROOM-", "A-WALL-", "A-", "ROOM-", "WALL-"):
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break
    # Replace dashes/underscores with spaces and title-case
    return name.replace("-", " ").replace("_", " ").strip().title()


class DXFParser:
    """Parses DXF files into structured ProjectModel instances."""

    def parse(self, filepath: str) -> ProjectModel:
        """Read a DXF file and return a fully populated ProjectModel."""
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"DXF file not found: {filepath}")

        start = time.perf_counter()

        try:
            doc = ezdxf.readfile(filepath)
        except ezdxf.DXFStructureError as exc:
            logger.error("[%s] [PARSER] DXF structure error: %s", _ts(), exc)
            return self._empty_project(filepath, time.perf_counter() - start)
        except Exception as exc:
            logger.error("[%s] [PARSER] Unexpected read error: %s", _ts(), exc)
            return self._empty_project(filepath, time.perf_counter() - start)

        msp = doc.modelspace()

        rooms = self._extract_rooms(msp)
        wall_count, total_wall_length = self._extract_walls(msp)
        door_count, window_count = self._count_openings(msp)
        layers = self._get_layers(doc)

        total_area = sum(r.area_m2 for r in rooms)
        elapsed_ms = (time.perf_counter() - start) * 1000

        project = ProjectModel(
            filename=os.path.basename(filepath),
            filepath=filepath,
            parsed_at=datetime.now(),
            total_area_m2=round(total_area, 2),
            room_count=len(rooms),
            rooms=rooms,
            wall_count=wall_count,
            total_wall_length_m=round(total_wall_length, 2),
            door_count=door_count,
            window_count=window_count,
            layers=layers,
            parse_duration_ms=round(elapsed_ms, 1),
        )

        logger.info(
            "[%s] [PARSER] Parse complete: %.1fm², %d rooms, %.0fms",
            _ts(),
            project.total_area_m2,
            project.room_count,
            project.parse_duration_ms,
        )
        return project

    # ── Room extraction ─────────────────────────────────────────────

    def _extract_rooms(self, msp) -> list[RoomModel]:  # noqa: ANN001
        """Extract rooms from closed LWPOLYLINE / POLYLINE entities."""
        rooms: list[RoomModel] = []

        for entity in msp:
            try:
                if entity.dxftype() == "LWPOLYLINE":
                    self._try_lwpolyline_room(entity, rooms)
                elif entity.dxftype() == "POLYLINE":
                    self._try_polyline_room(entity, rooms)
            except Exception as exc:
                logger.warning(
                    "[%s] [PARSER] Skipping entity: %s", _ts(), exc
                )
        return rooms

    def _try_lwpolyline_room(
        self, entity, rooms: list[RoomModel]  # noqa: ANN001
    ) -> None:
        points_raw = list(entity.get_points(format="xy"))
        if len(points_raw) < 3:
            return

        is_closed = entity.closed or (
            len(points_raw) >= 4
            and math.dist(points_raw[0], points_raw[-1]) < 0.01
        )
        if not is_closed and len(points_raw) < 4:
            return

        area = abs(shoelace_area(points_raw))
        if area < 4.0:
            return

        xs = [p[0] for p in points_raw]
        ys = [p[1] for p in points_raw]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        layer = entity.dxf.layer if hasattr(entity.dxf, "layer") else "0"
        rooms.append(
            RoomModel(
                id=str(uuid.uuid4())[:8],
                name=_clean_room_name(layer),
                area_m2=round(area, 2),
                width=round(max_x - min_x, 2),
                height=round(max_y - min_y, 2),
                x=round(min_x, 2),
                y=round(min_y, 2),
                layer=layer,
            )
        )

    def _try_polyline_room(
        self, entity, rooms: list[RoomModel]  # noqa: ANN001
    ) -> None:
        try:
            points_raw = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
        except Exception:
            return

        if len(points_raw) < 3:
            return

        area = abs(shoelace_area(points_raw))
        if area < 4.0:
            return

        xs = [p[0] for p in points_raw]
        ys = [p[1] for p in points_raw]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        layer = entity.dxf.layer if hasattr(entity.dxf, "layer") else "0"
        rooms.append(
            RoomModel(
                id=str(uuid.uuid4())[:8],
                name=_clean_room_name(layer),
                area_m2=round(area, 2),
                width=round(max_x - min_x, 2),
                height=round(max_y - min_y, 2),
                x=round(min_x, 2),
                y=round(min_y, 2),
                layer=layer,
            )
        )

    # ── Wall extraction ─────────────────────────────────────────────

    def _extract_walls(self, msp) -> tuple[int, float]:  # noqa: ANN001
        """Extract wall count and total wall length from LINE and LWPOLYLINE entities."""
        wall_count = 0
        total_length = 0.0
        wall_keywords = {"WALL", "DUVAR", "A-WALL", "S-WALL"}

        for entity in msp:
            try:
                layer = (
                    entity.dxf.layer.upper()
                    if hasattr(entity.dxf, "layer")
                    else ""
                )
                is_wall = any(kw in layer for kw in wall_keywords)
                if not is_wall:
                    continue

                if entity.dxftype() == "LINE":
                    start = entity.dxf.start
                    end = entity.dxf.end
                    length = math.dist(
                        (start.x, start.y), (end.x, end.y)
                    )
                    total_length += length
                    wall_count += 1

                elif entity.dxftype() == "LWPOLYLINE":
                    points = list(entity.get_points(format="xy"))
                    for i in range(len(points) - 1):
                        seg_len = math.dist(points[i], points[i + 1])
                        total_length += seg_len
                        wall_count += 1
                    if entity.closed and len(points) >= 2:
                        seg_len = math.dist(points[-1], points[0])
                        total_length += seg_len
                        wall_count += 1
            except Exception as exc:
                logger.warning(
                    "[%s] [PARSER] Skipping wall entity: %s", _ts(), exc
                )

        return wall_count, total_length

    # ── Door / Window counting ──────────────────────────────────────

    def _count_openings(self, msp) -> tuple[int, int]:  # noqa: ANN001
        """Count door and window INSERT blocks by name matching."""
        door_count = 0
        window_count = 0
        door_keywords = {"DOOR", "KAPI", "DR"}
        window_keywords = {"WIND", "PENCERE", "WIN"}

        for entity in msp:
            try:
                if entity.dxftype() != "INSERT":
                    continue
                block_name = entity.dxf.name.upper()

                if any(kw in block_name for kw in door_keywords):
                    door_count += 1
                elif any(kw in block_name for kw in window_keywords):
                    window_count += 1
            except Exception:
                pass

        return door_count, window_count

    # ── Layers ──────────────────────────────────────────────────────

    def _get_layers(self, doc) -> list[str]:  # noqa: ANN001
        """Return all layer names from the document."""
        try:
            return [layer.dxf.name for layer in doc.layers if layer.dxf.name != "0"]
        except Exception:
            return []

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _empty_project(filepath: str, elapsed: float) -> ProjectModel:
        return ProjectModel(
            filename=os.path.basename(filepath),
            filepath=filepath,
            parsed_at=datetime.now(),
            parse_duration_ms=round(elapsed * 1000, 1),
        )
