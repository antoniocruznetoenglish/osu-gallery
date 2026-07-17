"""Data models for parsed .osu file data."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntFlag


class HitObjectType(IntFlag):
    """Bitmask flags for osu! hit object types."""

    NONE = 0
    CIRCLE = 1
    SLIDER = 2
    NEW_COMBO = 4
    SPINNER = 8
    TABLET = 16
    SPECIAL = 32


class ObjectSound(IntFlag):
    """Bitmask flags for object sound types."""

    NONE = 0
    CLAP = 1
    FINISH = 2
    WHISTLE = 4
    NEW_COMBO = 8
    NORMAL = 16


@dataclass
class SliderPath:
    """A single path segment within a slider."""

    path_type: str  # 'B' (bezier), 'L' (linear), 'C' (circle/arc)
    points: list[tuple[float, float]]


@dataclass
class SliderData:
    """Parsed slider-specific data."""

    path: list[SliderPath]
    repeats: int
    pixel_length: float
    edge_sounds: list[int] = field(default_factory=list)
    edge_additions: list[str] = field(default_factory=list)
    sample_set: str = "Normal"
    sample_index: int = 0
    addition_info: str = ""
    multiplier: float = 1.0
    tick_rate: int = 1


@dataclass
class HitObject:
    """A single hit object (circle, slider, or spinner)."""

    x: float
    y: float
    type: HitObjectType
    sound_types: ObjectSound
    time: int  # milliseconds
    combo_colour: int
    sound_index: int
    slider: SliderData | None = None
    spinner_end: int | None = None

    @property
    def is_circle(self) -> bool:
        return bool(self.type & HitObjectType.CIRCLE) and not (self.type & HitObjectType.SLIDER)

    @property
    def is_slider(self) -> bool:
        return bool(self.type & HitObjectType.SLIDER)

    @property
    def is_spinner(self) -> bool:
        return bool(self.type & HitObjectType.SPINNER)

    @property
    def is_new_combo(self) -> bool:
        return bool(self.type & HitObjectType.NEW_COMBO)


@dataclass
class BeatmapMetadata:
    """Metadata from the [Metadata] section."""

    title: str = ""
    title_unicode: str = ""
    artist: str = ""
    artist_unicode: str = ""
    creator: str = ""
    version: str = ""
    source: str = ""
    tags: str = ""
    beatmap_id: str = ""
    beatmap_set_id: str = ""


@dataclass
class BeatmapDifficulty:
    """Difficulty settings from the [Difficulty] section."""

    circle_size: float = 5.0
    health_bar_drain: float = 5.0
    overall_difficulty: float = 5.0
    approach_rate: float = 5.0
    slider_multiplier: float = 1.4
    slider_tick_rate: float = 1.0


@dataclass
class BeatmapGeneral:
    """General settings from the [General] section."""

    audio_file: str = ""
    title: str = ""
    title_unicode: str = ""
    artist: str = ""
    artist_unicode: str = ""
    creator: str = ""
    version: str = ""
    source: str = ""
    tags: str = ""
    beatmap_id: str = ""
    beatmap_set_id: str = ""


@dataclass
class OsuFile:
    """A fully parsed .osu file."""

    metadata: BeatmapMetadata = field(default_factory=BeatmapMetadata)
    difficulty: BeatmapDifficulty = field(default_factory=BeatmapDifficulty)
    general: BeatmapGeneral = field(default_factory=BeatmapGeneral)
    hit_objects: list[HitObject] = field(default_factory=list)
    combo_colors: list[int] = field(default_factory=list)
    preview_time: int = -1
    stack_leniency: float = 0.7
    mode: int = 0  # 0=osu, 1=taiko, 2=ctb, 3=mania
    countdown: bool = True
    sample_set: str = "Normal"
    original_speed: float = 1.0
    distance_spacing: float = 1.0
    bird_eye_view_distance: float = 0.0
    timer: int = 0
    point_spacing: float = 3.0
