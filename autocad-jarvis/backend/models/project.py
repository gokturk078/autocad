"""Pydantic v2 models for DXF project data."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RoomModel(BaseModel):
    """Single room extracted from a DXF polyline."""

    id: str
    name: str
    area_m2: float
    width: float
    height: float
    x: float
    y: float
    layer: str


class ProjectModel(BaseModel):
    """Parsed representation of a complete DXF project."""

    filename: str
    filepath: str
    parsed_at: datetime = Field(default_factory=datetime.now)
    total_area_m2: float = 0.0
    room_count: int = 0
    rooms: list[RoomModel] = Field(default_factory=list)
    wall_count: int = 0
    total_wall_length_m: float = 0.0
    door_count: int = 0
    window_count: int = 0
    layers: list[str] = Field(default_factory=list)
    parse_duration_ms: float = 0.0


class AnalysisResult(BaseModel):
    """AI-generated analysis of a parsed DXF project."""

    summary_tr: str
    quick_stats: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.now)
    model_used: str = "gpt-4o"
    tokens_used: int = 0
