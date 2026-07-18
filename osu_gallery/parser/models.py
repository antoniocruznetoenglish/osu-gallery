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
    COLOUR_SKIP_1 = 16
    COLOUR_SKIP_2 = 32
    COLOUR_SKIP_4 = 64
    MANIA_HOLD = 128


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

    path_type: str  # 'B' (bezier), 'L' (linear), 'C' (circle/arc), 'P' (perfect circle)
    points: list[tuple[float, float]]


@dataclass
class TimingPoint:
    """A single timing point from the [TimingPoints] section."""

    offset: float = 0.0
    beat_length: float = 0.0
    bpm: float = 0.0
    is_uninherited: bool = True
    meter: int = 4
    sample_set: int = 0
    sample_index: int = 0
    volume: int = 100
    effects: int = 0


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


@dataclass
class HitObject:
    """A single hit object (circle, slider, or spinner)."""

    x: float
    y: float
    type: HitObjectType
    sound_types: ObjectSound
    time: int  # milliseconds
    combo_colour: int
    hit_sample: str = ""
    slider: SliderData | None = None
    spinner_end: int | None = None
    _raw_combo_index: int | None = None
    combo_order: int = 0

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
    timing_bpm: float = 0.0
    bpm_min: float = 0.0
    bpm_max: float = 0.0
    _timing_points: list[TimingPoint] = field(default_factory=list)

    def resolve_combo_colours(self) -> None:
        """Resolve raw combo indices to actual combo colour values.

        Must be called after combo_colors is populated (e.g., after parsing
        the [Colours] section). Sets HitObject.combo_colour on each object.
        """
        colour_count = max(1, len(self.combo_colors))
        for obj in self.hit_objects:
            raw = obj._raw_combo_index
            if raw is not None:
                obj.combo_colour = raw % colour_count
            obj._raw_combo_index = None

    @property
    def circle_count(self) -> int:
        """Count of circle hit objects (excludes sliders, spinners, mania holds)."""
        return sum(1 for obj in self.hit_objects if obj.is_circle)

    @property
    def slider_count(self) -> int:
        """Count of slider hit objects (excludes circles, spinners, mania holds)."""
        return sum(1 for obj in self.hit_objects if obj.is_slider)

    def effective_sv_at(self, time_ms: int) -> float:
        """Find the effective slider velocity multiplier at a given time.

        Walks backwards through the timing point list to find the most recent
        timing point at or before time_ms. If it is an inherited point, the
        SV is computed from its negative beatLength (SV = 100 / |beatLength|).
        Otherwise SV = 1.0.

        This is groundwork for accurate slider duration computation;
        not currently consumed by the static thumbnail renderer.

        Args:
            time_ms: The time in milliseconds to query.

        Returns:
            The effective SV multiplier at that time.
        """
        if not self._timing_points:
            return 1.0

        effective_tp: TimingPoint | None = None
        for tp in self._timing_points:
            if tp.offset > time_ms:
                break
            effective_tp = tp

        if effective_tp is None:
            return 1.0

        if effective_tp.is_uninherited:
            return 1.0

        if effective_tp.beat_length < 0:
            return 100.0 / abs(effective_tp.beat_length)

        return 1.0
