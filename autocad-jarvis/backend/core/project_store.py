"""
In-Memory Proje Deposu
=======================
Üretilen projelerin bilgilerini bellekte saklar.
UUID ile tanımlanır, dosya yolları + metadata tutulur.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class StoredProject:
    """Üretilen bir projenin tüm bilgileri."""
    project_id: str
    project_name: str
    building_type: str
    created_at: str
    output_dir: str
    zip_path: str
    files: dict[str, str]          # label → file_path
    compliance: dict               # mevzuat sonucu
    cost: dict                     # maliyet tahmini
    area_table: dict               # alan hesap
    staircase: dict                # merdiven bilgisi
    file_count: int = 0

    def to_summary(self) -> dict:
        """Proje özeti (liste endpoint'i için)."""
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "building_type": self.building_type,
            "created_at": self.created_at,
            "file_count": self.file_count,
            "files": list(self.files.keys()),
            "zip_available": bool(self.zip_path and os.path.exists(self.zip_path)),
            "download_url": f"/project/download-zip/{self.project_id}",
        }

    def to_full(self) -> dict:
        """Tam proje detayı."""
        return {
            **self.to_summary(),
            "compliance": self.compliance,
            "cost": self.cost,
            "area_table": self.area_table,
            "staircase": self.staircase,
            "dxf_files": {
                label: {
                    "filename": os.path.basename(path),
                    "size_bytes": os.path.getsize(path) if os.path.exists(path) else 0,
                    "download_url": f"/project/download/{self.project_id}/{os.path.basename(path)}",
                }
                for label, path in self.files.items()
            },
        }


class ProjectStore:
    """In-memory proje deposu."""

    def __init__(self) -> None:
        self._projects: dict[str, StoredProject] = {}

    def add(
        self,
        project_name: str,
        building_type: str,
        output_dir: str,
        zip_path: str,
        files: dict[str, str],
        compliance: dict,
        cost: dict,
        area_table: dict,
        staircase: dict,
    ) -> StoredProject:
        """Yeni proje ekle, UUID oluştur."""
        project_id = uuid.uuid4().hex[:12]
        project = StoredProject(
            project_id=project_id,
            project_name=project_name,
            building_type=building_type,
            created_at=datetime.now().isoformat(),
            output_dir=output_dir,
            zip_path=zip_path,
            files=files,
            compliance=compliance,
            cost=cost,
            area_table=area_table,
            staircase=staircase,
            file_count=len(files),
        )
        self._projects[project_id] = project
        return project

    def get(self, project_id: str) -> Optional[StoredProject]:
        """Proje ID ile bul."""
        return self._projects.get(project_id)

    def list_all(self) -> list[dict]:
        """Tüm projelerin özetlerini döndür (son eklenen önce)."""
        sorted_projects = sorted(
            self._projects.values(),
            key=lambda p: p.created_at,
            reverse=True,
        )
        return [p.to_summary() for p in sorted_projects]

    def cleanup_old(self, max_count: int = 20) -> int:
        """En fazla max_count proje tut, eskileri sil."""
        if len(self._projects) <= max_count:
            return 0

        sorted_ids = sorted(
            self._projects.keys(),
            key=lambda pid: self._projects[pid].created_at,
        )
        to_remove = sorted_ids[: len(sorted_ids) - max_count]
        for pid in to_remove:
            del self._projects[pid]
        return len(to_remove)

    @property
    def count(self) -> int:
        return len(self._projects)
