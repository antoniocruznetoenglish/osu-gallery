"""Parser for osu! .osu beatmap files.

Parses the .osu file format into structured data, focusing on the [HitObjects]
section which contains circles, sliders, and spinners.
"""

from __future__ import annotations

import logging
import re

from osu_gallery.parser.models import (
    BeatmapDifficulty,
    BeatmapGeneral,
    BeatmapMetadata,
    HitObject,
    HitObjectType,
    ObjectSound,
    OsuFile,
    SliderData,
    SliderPath,
    TimingPoint,
)


class ParseError(Exception):
    """Raised when a .osu file cannot be parsed."""

logger = logging.getLogger(__name__)


def _parse_slider_path(path_string: str) -> list[SliderPath]:
    """Parse a slider path string into a list of path segments.

    Supports two coordinate formats:
    - Comma-separated: 'L|X1,Y1|X2,Y2|...' (standard osu!)
    - Colon-separated: 'L|X1:Y1|X2:Y2|...' (alternative format)

    Path types: L (linear), B (bezier), C (circle/arc), P (perfect circle)
    """
    segments: list[SliderPath] = []
    if not path_string.strip():
        return segments

    parts = path_string.strip().split("|")
    if not parts:
        return segments

    i = 0
    while i < len(parts):
        part = parts[i].strip()
        if not part:
            i += 1
            continue

        path_type = part[0]
        if path_type not in ("L", "B", "C", "P"):
            i += 1
            continue

        # Collect coordinate parts until we hit a non-coordinate part
        coord_parts: list[str] = []
        if path_type == "L":
            # Linear: each '|' separates a point (X,Y) or (X:Y)
            i += 1
            while i < len(parts):
                p = parts[i].strip()
                if not p:
                    i += 1
                    continue
                # Check if this looks like coordinates (contains comma or colon between numbers)
                if _is_coordinate_part(p):
                    coord_parts.append(p)
                    i += 1
                else:
                    break
        else:
            # Bezier/Circle/PerfectCircle: coordinates are comma/colon-separated within a segment,
            # segments are separated by '|'
            i += 1
            while i < len(parts):
                p = parts[i].strip()
                if not p:
                    i += 1
                    continue
                coord_parts.append(p)
                i += 1

        # Parse coordinates (support both , and : separators)
        all_coords: list[str] = []
        for cp in coord_parts:
            # Try comma first, then colon
            if "," in cp:
                all_coords.extend([c.strip() for c in cp.split(",")])
            elif ":" in cp:
                all_coords.extend([c.strip() for c in cp.split(":")])
            else:
                all_coords.append(cp)

        points: list[tuple[float, float]] = []
        if path_type == "L":
            # Linear: pairs of (X, Y)
            for j in range(0, len(all_coords), 2):
                if j + 1 < len(all_coords):
                    points.append((float(all_coords[j]), float(all_coords[j + 1])))
        elif path_type in ("B", "C", "P"):
            # Bezier/Circle/PerfectCircle: groups of 6 values (3 control points: x1,y1,x2,y2,x3,y3)
            for j in range(0, len(all_coords), 6):
                if j + 5 < len(all_coords):
                    points.append((float(all_coords[j]), float(all_coords[j + 1])))
                    points.append((float(all_coords[j + 2]), float(all_coords[j + 3])))
                    points.append((float(all_coords[j + 4]), float(all_coords[j + 5])))

        # Perfect-circle fallback: more than 3 path points degrades to bezier
        if path_type == "P" and len(points) != 3:
            path_type = "B"

        if points:
            segments.append(SliderPath(path_type=path_type, points=points))

    return segments


def _is_coordinate_part(s: str) -> bool:
    """Check if a string looks like a coordinate pair (X,Y) or (X:Y)."""
    if "," in s or ":" in s:
        # Try to parse as numbers
        for sep in [",", ":"]:
            parts = s.split(sep)
            if len(parts) == 2:
                try:
                    float(parts[0])
                    float(parts[1])
                    return True
                except ValueError:
                    continue
    return False


def _parse_slider_data(
    path_data: str,
    repeats: int,
    pixel_length: float,
    edge_sounds_str: str,
    edge_additions_str: str,
) -> SliderData:
    """Parse the slider-specific fields into a SliderData object.

    Args:
        path_data: The slider path string (e.g., 'L|100:100').
        repeats: Number of repeats.
        pixel_length: Slider pixel length.
        edge_sounds_str: Comma-separated edge sound indices.
        edge_additions_str: Comma-separated edge addition names.

    Returns:
        A SliderData object with parsed slider information.
    """
    edge_sounds: list[int] = []
    if edge_sounds_str.strip():
        for s in edge_sounds_str.strip().split(","):
            try:
                edge_sounds.append(int(s.strip()))
            except ValueError:
                continue

    edge_additions: list[str] = []
    if edge_additions_str.strip():
        edge_additions = [s.strip() for s in edge_additions_str.strip().split(",") if s.strip()]

    return SliderData(
        path=_parse_slider_path(path_data),
        repeats=repeats,
        pixel_length=pixel_length,
        edge_sounds=edge_sounds,
        edge_additions=edge_additions,
    )


def _parse_hit_object(line: str) -> HitObject:
    """Parse a single hit object line from the [HitObjects] section.

    Real osu! format:
        x,y,time,type,hitSound,objectParams,hitSample

    Where:
        x, y: float coordinates (may be negative)
        time: int milliseconds
        type: int bitmask (1=circle, 2=slider, 4=new combo, 8=spinner,
            16=colour_skip_1, 32=colour_skip_2, 64=colour_skip_4, 128=mania_hold)
        hitSound: int bitmask (clap, finish, whistle, etc.)
        objectParams: varies by type (slider curve+slides+length, spinner endTime)
        hitSample: optional colon-separated string (normalSet:additionSet:index:volume:filename)
    """
    # The first 5 fields are simple comma-separated values.
    # After that, objectParams depends on the type and may contain commas/pipes.
    # We extract the first 5 fields via regex, then parse the rest based on type.
    match = re.match(
        r"^(-?[\d.]+),(-?[\d.]+),(\d+),(\d+),(\d+)(?:,(.*))?$", line
    )
    if not match:
        raise ParseError(f"Hit object line does not match expected format: {line!r}")

    x = float(match.group(1))
    y = float(match.group(2))
    time = int(match.group(3))
    type_bitmask = int(match.group(4))
    hit_sound = int(match.group(5))
    remainder = match.group(6) or ""

    hit_type = HitObjectType(type_bitmask)
    object_sound = ObjectSound(hit_sound)

    hit_object = HitObject(
        x=x,
        y=y,
        type=hit_type,
        sound_types=object_sound,
        time=time,
        combo_colour=0,
        hit_sample="",
    )

    if hit_type & HitObjectType.SLIDER:
        # Slider objectParams: curveType|curvePoints,slides,length[,edgeSounds,edgeSets]
        # We need to split carefully because curvePoints contain commas/pipes.
        # Format: <curve>|<points>,<slides>,<length>[,<edgeSounds>,<edgeSets>]
        if not remainder:
            raise ParseError(f"Slider missing object params: {line!r}")

        edge_sounds_str = ""
        edge_additions_str = ""
        slider_body = remainder

        # Robust approach: use regex to find the curve prefix, then parse the numeric tail.
        slider_match = re.match(
            r"^([LBCP]\|(?:[\d.:|]+)),(\d+),([\d.]+)(?:,(.*))?$",
            slider_body,
        )
        if not slider_match:
            raise ParseError(f"Slider path data malformed: {line!r}")

        path_data = slider_match.group(1)
        try:
            repeats = int(slider_match.group(2))
        except ValueError:
            repeats = 0

        try:
            pixel_length = float(slider_match.group(3))
        except ValueError:
            pixel_length = 0.0

        optional_str = slider_match.group(4) if slider_match.group(4) else ""
        edge_sounds_str = ""
        edge_additions_str = ""

        if optional_str:
            opt_parts = optional_str.split(",")
            edge_sounds_str = opt_parts[0] if len(opt_parts) > 0 else ""
            edge_additions_str = opt_parts[1] if len(opt_parts) > 1 else ""

        hit_object.slider = _parse_slider_data(
            path_data=path_data,
            repeats=repeats,
            pixel_length=pixel_length,
            edge_sounds_str=edge_sounds_str,
            edge_additions_str=edge_additions_str,
        )

    elif hit_type & HitObjectType.SPINNER:
        # Spinner objectParams: endTime
        if not remainder:
            raise ParseError(f"Spinner missing end time: {line!r}")
        end_time_str = remainder.split(",")[0]
        try:
            hit_object.spinner_end = int(end_time_str)
        except ValueError:
            raise ParseError(f"Spinner end time is not an integer: {end_time_str!r}") from None

    elif hit_type & HitObjectType.MANIA_HOLD:
        # Mania hold: endTime (stubbed for now)
        if remainder:
            end_time_str = remainder.split(",")[0]
            try:
                hit_object.spinner_end = int(end_time_str)
            except ValueError:
                logger.debug(
                    "Mania hold end time not an integer, ignoring: %s", end_time_str
                )

    # Parse optional trailing hitSample (colon-separated)
    # hitSample is appended after objectParams, separated by a comma.
    # Format: normalSet:additionSet:index:volume:filename
    # We need to check if there's a colon-separated string after the objectParams.
    # For circles, remainder is just the hitSample (or empty).
    is_circle = not (
        hit_type & (HitObjectType.SLIDER | HitObjectType.SPINNER | HitObjectType.MANIA_HOLD)
    )
    if is_circle and remainder and ":" in remainder:
        # Circle: remainder is just hitSample
        hit_object.hit_sample = remainder

    # Try to extract hitSample from the original line for all types.
    # The hitSample is the last colon-separated field after all comma-separated params.
    if not hit_object.hit_sample:
        _hit_sample = _extract_hit_sample(line, hit_type)
        if _hit_sample is not None:
            hit_object.hit_sample = _hit_sample

    return hit_object


def _extract_hit_sample(line: str, hit_type: HitObjectType) -> str | None:
    """Extract the optional hitSample string from a hit object line.

    Dispatches to type-specific extraction based on whether the object is a
    circle (simple case) or slider/spinner/mania (complex case with objectParams).

    Args:
        line: The raw hit object line from the [HitObjects] section.
        hit_type: The HitObjectType flag indicating circle, slider, spinner, or mania.

    Returns:
        The hitSample string if found, otherwise None.
    """
    if not line:
        return None

    # Find the position after the first 5 comma-separated fields.
    match = re.match(
        r"^(-?[\d.]+),(-?[\d.]+),(\d+),(\d+),(\d+)(?:,(.*))?$", line
    )
    if not match:
        return None

    remainder = match.group(6)
    if not remainder:
        return None

    # Circles: remainder is the hitSample if it contains colons.
    if not (hit_type & (HitObjectType.SLIDER | HitObjectType.SPINNER | HitObjectType.MANIA_HOLD)):
        return _extract_hit_sample_for_circle(remainder)

    # Sliders/spinners/mania: hitSample is after objectParams.
    return _extract_hit_sample_for_complex(line)


def _extract_hit_sample_for_circle(remainder: str) -> str | None:
    """Extract hitSample from a circle hit object's remainder.

    For circles, the remainder after the first 5 comma-separated fields
    is the hitSample itself (a colon-separated string).

    Args:
        remainder: The text after the first 5 comma-separated fields.

    Returns:
        The hitSample string if it contains colons, otherwise None.
    """
    if ":" in remainder:
        return remainder
    return None


def _extract_hit_sample_for_complex(line: str) -> str | None:
    """Extract hitSample from slider/spinner/mania hit object lines.

    Walks backwards through comma-separated parts to find the rightmost
    colon-separated segment that matches the hitSample format (numeric
    sets/index/volume fields separated by colons).

    Args:
        line: The raw hit object line.

    Returns:
        The hitSample string if found, otherwise None.
    """
    parts = line.split(",")
    if len(parts) <= 5:
        return None

    # Walk backwards from the end to find the hitSample.
    # The hitSample contains colons but no commas or slider-specific chars.
    for i in range(len(parts) - 1, 4, -1):
        part = parts[i]
        if ":" in part and not any(c in part for c in "|.") and part.count(":") >= 1:
            colon_parts = part.split(":")
            if len(colon_parts) >= 2 and _looks_like_hit_sample(colon_parts):
                return part

    return None


def _looks_like_hit_sample(colon_parts: list[str]) -> bool:
    """Check if colon-separated parts match the hitSample format.

    A valid hitSample has numeric sets/index/volume fields (non-empty parts
    must be parseable as integers).

    Args:
        colon_parts: The parts split by colons.

    Returns:
        True if all non-empty parts are numeric.
    """
    for cp in colon_parts:
        if cp:
            try:
                int(cp)
            except ValueError:
                return False
    return True


def _parse_ini_section(content: str, section: str) -> dict[str, str]:
    """Extract key=value pairs from a specific INI-style section."""
    result: dict[str, str] = {}
    section_pattern = re.compile(
        rf"^\[{re.escape(section)}\]\s*$", re.MULTILINE | re.IGNORECASE
    )
    next_section_pattern = re.compile(
        r"^\[[^\]]+\]\s*$", re.MULTILINE
    )

    section_match = section_pattern.search(content)
    if not section_match:
        return result

    start = section_match.end()
    remaining = content[start:]

    next_match = next_section_pattern.search(remaining)
    section_content = remaining[:next_match.start()] if next_match else remaining

    for line in section_content.splitlines():
        line = line.strip()
        if not line or line.startswith("//") or line.startswith("#"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()

    return result


def _parse_metadata(raw: dict[str, str], general: BeatmapGeneral) -> BeatmapMetadata:
    """Parse the [Metadata] section, falling back to [General] values."""
    meta = BeatmapMetadata()
    meta.title = raw.get("Title", general.title)
    meta.title_unicode = raw.get("TitleUnicode", general.title_unicode)
    meta.artist = raw.get("Artist", general.artist)
    meta.artist_unicode = raw.get("ArtistUnicode", general.artist_unicode)
    meta.creator = raw.get("Creator", general.creator)
    meta.version = raw.get("Version", general.version)
    meta.source = raw.get("Source", general.source)
    meta.tags = raw.get("Tags", general.tags)
    meta.beatmap_id = raw.get("BeatmapID", general.beatmap_id)
    meta.beatmap_set_id = raw.get("BeatmapSetID", general.beatmap_set_id)
    return meta


def _parse_difficulty(raw: dict[str, str]) -> BeatmapDifficulty:
    """Parse the [Difficulty] section."""
    diff = BeatmapDifficulty()
    diff.circle_size = _safe_float(raw.get("CircleSize", "5"), 5.0)
    diff.health_bar_drain = _safe_float(raw.get("HPDrainRate", "5"), 5.0)
    diff.overall_difficulty = _safe_float(raw.get("OverallDifficulty", "5"), 5.0)
    diff.approach_rate = _safe_float(raw.get("ApproachRate", "5"), 5.0)
    diff.slider_multiplier = _safe_float(raw.get("SliderMultiplier", "1.4"), 1.4)
    diff.slider_tick_rate = _safe_float(raw.get("SliderTickRate", "1"), 1.0)
    return diff


def _safe_float(value: str | None, default: float) -> float:
    """Safely parse a float, returning default on failure."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _parse_timing_points(content: str) -> list[TimingPoint]:
    """Parse the [TimingPoints] section into a list of TimingPoint objects.

    Per the osu! spec:
    - Uninherited timing points have positive beatLength and define the BPM.
    - Inherited timing points have negative beatLength and represent
      slider-velocity multipliers (not BPM).
    - The 7th field (index 6) is the explicit uninherited flag (0 or 1).

    Args:
        content: The raw .osu file content.

    Returns:
        An ordered list of TimingPoint objects.
    """
    timing_section = _extract_section(content, "TimingPoints")
    if not timing_section:
        return []

    timing_points: list[TimingPoint] = []
    for line in timing_section.splitlines():
        line = line.strip()
        if not line or line.startswith("//") or line.startswith("#"):
            continue

        parts = line.split(",")
        if len(parts) < 2:
            continue

        # Safe indexed access with per-field defaults for optional trailing fields
        offset = _safe_float(parts[0] if len(parts) > 0 else None, 0.0)
        beat_length = _safe_float(parts[1] if len(parts) > 1 else None, 0.0)
        meter = int(parts[2]) if len(parts) > 2 else 4
        sample_set = int(parts[3]) if len(parts) > 3 else 0
        sample_index = int(parts[4]) if len(parts) > 4 else 0
        volume = int(parts[5]) if len(parts) > 5 else 100

        # Read uninherited flag (7th field, index 6) directly
        uninherited_flag: int | None = None
        if len(parts) > 6:
            try:
                uninherited_flag = int(parts[6])
            except ValueError:
                uninherited_flag = None

        effects = int(parts[7]) if len(parts) > 7 else 0

        # Determine if uninherited: prefer explicit flag, fall back to sign
        is_uninherited = bool(uninherited_flag) if uninherited_flag is not None else beat_length > 0

        # Guard against beatLength == 0 (division by zero)
        if beat_length == 0:
            tp = TimingPoint(
                offset=offset,
                beat_length=beat_length,
                bpm=0.0,
                is_uninherited=is_uninherited,
                meter=meter,
                sample_set=sample_set,
                sample_index=sample_index,
                volume=volume,
                effects=effects,
            )
            timing_points.append(tp)
            continue

        # Only compute BPM from uninherited timing points.
        # Use abs(beat_length) because some real maps have uninherited TPs
        # with negative beatLength (first TP establishes BPM + SV simultaneously).
        bpm = round(60000.0 / abs(beat_length), 2) if is_uninherited else 0.0

        tp = TimingPoint(
            offset=offset,
            beat_length=beat_length,
            bpm=bpm,
            is_uninherited=is_uninherited,
            meter=meter,
            sample_set=sample_set,
            sample_index=sample_index,
            volume=volume,
            effects=effects,
        )
        timing_points.append(tp)

    return timing_points


def _extract_section(content: str, section: str) -> str:
    """Extract the content of a specific section from .osu file content.

    Returns the raw text between the section header and the next section
    header (or end of file).

    Args:
        content: The raw .osu file content.
        section: The section name to extract (e.g., "TimingPoints").

    Returns:
        The section content as a string, or empty string if not found.
    """
    pattern_str = r"^\[" + re.escape(section) + r"\]\s*$"
    section_pattern = re.compile(pattern_str, re.MULTILINE | re.IGNORECASE)
    next_section_pattern = re.compile(r"^\[[^\]]+\]\s*$", re.MULTILINE)

    section_match = section_pattern.search(content)
    if not section_match:
        return ""

    start = section_match.end()
    remaining = content[start:]

    next_match = next_section_pattern.search(remaining)
    return remaining[:next_match.start()] if next_match else remaining


def _parse_colours(raw: dict[str, str]) -> list[int]:
    """Parse combo colours from the [Colours] section.

    Keys: Combo1Colour through Combo6Colour, values are either:
    - Comma-separated RGB decimals: "255,100,100"
    - Hex string (with or without #): "FF6464" or "#FF6464"
    Returns a list of int (parsed as hex colour values).
    """
    colours: list[int] = []
    for i in range(1, 7):
        key = f"Combo{i}Colour"
        colour_str = raw.get(key, "")
        if not colour_str:
            continue

        # Try decimal RGB format first (e.g., "255,100,100")
        if "," in colour_str:
            try:
                parts = [int(p.strip()) for p in colour_str.split(",")]
                if len(parts) == 3 and all(0 <= p <= 255 for p in parts):
                    colours.append((parts[0] << 16) | (parts[1] << 8) | parts[2])
                    continue
            except ValueError:
                continue

        # Try hex format (e.g., "FF6464" or "#FF6464")
        hex_str = colour_str.lstrip("#")
        try:
            colours.append(int(hex_str, 16))
        except ValueError:
            continue
    return colours


def parse_osu_file(content: str) -> OsuFile:
    """Parse the full content of a .osu file into an OsuFile object.

    Args:
        content: The raw text content of a .osu file.

    Returns:
        An OsuFile object with all parsed data.

    Raises:
        ParseError: If the file content is malformed.
    """
    if not content or not content.strip():
        raise ParseError("Empty .osu file content")

    osu = OsuFile()

    # Parse [General] section
    general_raw = _parse_ini_section(content, "General")
    osu.general.audio_file = general_raw.get("AudioFilename", "")
    osu.preview_time = _safe_int(general_raw.get("PreviewTime", "-1"), -1)
    osu.stack_leniency = _safe_float(general_raw.get("StackLeniency", "0.7"), 0.7)
    osu.mode = _safe_int(general_raw.get("Mode", "0"), 0)
    osu.countdown = general_raw.get("Countdown", "0") == "1"
    osu.sample_set = general_raw.get("SampleSet", "Normal")
    osu.original_speed = _safe_float(general_raw.get("OriginalSpeed", "1"), 1.0)

    # Also pull metadata-like fields from [General] for fallback
    osu.general.title = general_raw.get("Title", "")
    osu.general.title_unicode = general_raw.get("TitleUnicode", "")
    osu.general.artist = general_raw.get("Artist", "")
    osu.general.artist_unicode = general_raw.get("ArtistUnicode", "")
    osu.general.creator = general_raw.get("Creator", "")
    osu.general.version = general_raw.get("Version", "")
    osu.general.source = general_raw.get("Source", "")
    osu.general.tags = general_raw.get("Tags", "")
    osu.general.beatmap_id = general_raw.get("BeatmapID", "")
    osu.general.beatmap_set_id = general_raw.get("BeatmapSetID", "")

    # Parse [Editor] section
    editor_raw = _parse_ini_section(content, "Editor")
    osu.distance_spacing = _safe_float(editor_raw.get("DistanceSpacing", "1"), 1.0)
    osu.bird_eye_view_distance = _safe_float(editor_raw.get("BirdEyeViewDistance", "0"), 0.0)
    osu.timer = _safe_int(editor_raw.get("Timer", "0"), 0)
    osu.point_spacing = _safe_float(editor_raw.get("PointSpacing", "3"), 3.0)

    # Parse [Difficulty] section
    difficulty_raw = _parse_ini_section(content, "Difficulty")
    osu.difficulty = _parse_difficulty(difficulty_raw)

    # Parse [Metadata] section
    metadata_raw = _parse_ini_section(content, "Metadata")
    osu.metadata = _parse_metadata(metadata_raw, osu.general)

    # Parse [Colours] section
    colours_raw = _parse_ini_section(content, "Colours")
    osu.combo_colors = _parse_colours(colours_raw)

    # Parse [HitObjects] section (special format: lines without keys)
    osu.hit_objects = _parse_hit_objects_section(content)

    # Resolve combo colours now that we know the colour count
    osu.resolve_combo_colours()

    # Parse [TimingPoints] section and compute BPM
    timing_points = _parse_timing_points(content)
    osu._timing_points = timing_points

    uninherited_bpm_values = [
        tp.bpm for tp in timing_points if tp.is_uninherited and tp.bpm > 0
    ]
    if uninherited_bpm_values:
        osu.timing_bpm = uninherited_bpm_values[0]
        osu.bpm_min = min(uninherited_bpm_values)
        osu.bpm_max = max(uninherited_bpm_values)

    return osu


def _safe_int(value: str | None, default: int) -> int:
    """Safely parse an int, returning default on failure."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _parse_hit_objects_section(content: str) -> list[HitObject]:
    """Parse the [HitObjects] section from raw file content.

    The HitObjects section in .osu files uses lines without keys:
        x,y,time,type,hitSound,objectParams,hitSample

    We extract everything between [HitObjects] and the next section header.
    Combo colours are derived from a running combo index based on the
    NEW_COMBO flag and colour-skip bits (4-6) in the type bitmask.
    """
    objects: list[HitObject] = []
    section_pattern = re.compile(r"^\[HitObjects\]\s*$", re.MULTILINE | re.IGNORECASE)
    next_section_pattern = re.compile(r"^\[[^\]]+\]\s*$", re.MULTILINE)

    section_match = section_pattern.search(content)
    if not section_match:
        return objects

    start = section_match.end()
    remaining = content[start:]

    next_match = next_section_pattern.search(remaining)
    section_content = remaining[:next_match.start()] if next_match else remaining

    # First pass: parse all objects to get raw combo indices.
    raw_objects: list[HitObject] = []
    for line in section_content.splitlines():
        line = line.strip()
        if not line or line.startswith("//") or line.startswith("#"):
            continue

        try:
            obj = _parse_hit_object(line)
            raw_objects.append(obj)
        except ParseError:
            continue

    # Second pass: compute combo colour from running combo index.
    # Combo colour is 0-indexed. First object is always colour 0.
    combo_index = 0
    for obj in raw_objects:
        # Assign current combo index before processing flags
        obj._raw_combo_index = combo_index
        obj.combo_order = combo_index + 1  # 1-based
        type_val = int(obj.type)
        # Check NEW_COMBO bit (bit 2, value 4)
        if type_val & HitObjectType.NEW_COMBO:
            combo_index += 1
        # Check colour-skip bits (bits 4-6, values 16, 32, 64)
        colour_skip = (type_val >> 4) & 0x7
        if colour_skip:
            combo_index += colour_skip

    # Third pass: resolve combo_colour once we know the combo_colors list.
    # We don't have access to combo_colors here, so store raw index.
    # The OsuFile.combo_colors will be used later to resolve.
    # For now, store the raw combo index on each object.
    objects = raw_objects

    return objects
