"""Data models for the gallery database."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Tag:
    """A tag that can be attached to patterns (e.g., 'slider', 'circle_pattern')."""

    id: int | None = None
    name: str = ""
    category: str = ""

    def __post_init__(self) -> None:
        if self.name:
            self.name = self.name.strip()
        if self.category:
            self.category = self.category.strip()


@dataclass
class Pattern:
    """A stored beatmap pattern (parsed from .osu code)."""

    id: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    raw_code: str = ""
    objects_only: str = ""
    object_count: int = 0
    circle_count: int = 0
    slider_count: int = 0
    timing_bpm: float = 0.0
    artist: str = ""
    title: str = ""
    mapper: str = ""
    mapping_tags: list[str] = field(default_factory=list)
    tag_ids: list[int] = field(default_factory=list)
    user_image: bytes = b""
    user_image_filename: str = ""
