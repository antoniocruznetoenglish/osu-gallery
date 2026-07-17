"""Parser for osu! .osu beatmap files.

Parses the .osu file format into structured data, focusing on the [HitObjects]
section which contains circles, sliders, and spinners.
"""

from __future__ import annotations

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
)


class ParseError(Exception):
    """Raised when a .osu file cannot be parsed."""


def _parse_slider_path(path_string: str) -> list[SliderPath]:
    """Parse a slider path string into a list of path segments.

    Supports two coordinate formats:
    - Comma-separated: 'L|X1,Y1|X2,Y2|...' (standard osu!)
    - Colon-separated: 'L|X1:Y1|X2:Y2|...' (alternative format)

    Path types: L (linear), B (bezier), C (circle/arc)
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
        if path_type not in ("L", "B", "C"):
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
            # Bezier/Circle: coordinates are comma/colon-separated within a segment,
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
        elif path_type in ("B", "C"):
            # Bezier/Circle: groups of 6 values (3 control points: x1,y1,x2,y2,x3,y3)
            for j in range(0, len(all_coords), 6):
                if j + 5 < len(all_coords):
                    points.append((float(all_coords[j]), float(all_coords[j + 1])))
                    points.append((float(all_coords[j + 2]), float(all_coords[j + 3])))
                    points.append((float(all_coords[j + 4]), float(all_coords[j + 5])))

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
    multiplier_str: str,
    tick_rate_str: str,
) -> SliderData:
    """Parse the slider-specific fields into a SliderData object."""
    try:
        multiplier = float(multiplier_str) if multiplier_str else 1.0
    except ValueError:
        multiplier = 1.0

    try:
        tick_rate = int(tick_rate_str) if tick_rate_str else 1
    except ValueError:
        tick_rate = 1

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
        multiplier=multiplier,
        tick_rate=tick_rate,
    )


def _parse_hit_object(line: str) -> HitObject:
    """Parse a single hit object line from the [HitObjects] section.

    Format:
        X,Y,type,object_type,time,combo_colour,sound_index[,slider_data...]

    Where:
        X, Y: float coordinates
        type: int bitmask (1=circle, 2=slider, 4=new combo, 8=spinner)
        object_type: int bitmask (clap, finish, whistle, etc.)
        time: int milliseconds
        combo_colour: int 0-6
        sound_index: int
    """
    # For sliders, the path_data contains commas and pipes, so we can't
    # simply split by commas. Instead, extract the first 7 fields manually,
    # then parse the remainder based on object type.
    # Use a regex to extract the first 7 comma-separated numeric fields.
    match = re.match(
        r"^([\d.]+),([\d.]+),(\d+),(\d+),(\d+),(\d+),(\d+)(.*)$", line
    )
    if not match:
        raise ParseError(f"Hit object line does not match expected format: {line!r}")

    x = float(match.group(1))
    y = float(match.group(2))
    type_bitmask = int(match.group(3))
    sound_types = int(match.group(4))
    time = int(match.group(5))
    combo_colour = int(match.group(6))
    sound_index = int(match.group(7))
    remainder = match.group(8).lstrip(",") if match.group(8) else ""

    hit_type = HitObjectType(type_bitmask)
    object_sound = ObjectSound(sound_types)

    hit_object = HitObject(
        x=x,
        y=y,
        type=hit_type,
        sound_types=object_sound,
        time=time,
        combo_colour=combo_colour,
        sound_index=sound_index,
    )

    if hit_type & HitObjectType.SLIDER:
        # Slider: remainder contains path_data followed by repeats,pixel_length and optional fields
        if not remainder:
            raise ParseError(f"Slider missing path data: {line!r}")

        # For MVP, handle simple slider format: path_data,repeats,pixel_length[,optional...]
        # where path_data is L|X1,Y1|X2,Y2|... or B|X1,Y1,X2,Y2,X3,Y3|...
        # Use a regex that matches: type_prefix|coordinates,repeats,pixel_length
        # Match path_data (digits, colons, dots, pipes) followed by
        # ,repeats,pixel_length and optional trailing fields.
        # [LBCO]\| prefix + coordinate chars, then the numeric fields.
        slider_match = re.match(
            r"^([LBCO]\|(?:[\d.:|]+)),(\d+),([\d.]+)(?:,(.*))?$",
            remainder,
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
        multiplier_str = "1"
        tick_rate_str = "1"

        if optional_str:
            opt_parts = optional_str.split(",")
            edge_sounds_str = opt_parts[0] if len(opt_parts) > 0 else ""
            edge_additions_str = opt_parts[1] if len(opt_parts) > 1 else ""
            # opt_parts[2] is custom_audio_offset (skip)
            multiplier_str = opt_parts[3] if len(opt_parts) > 3 else "1"
            tick_rate_str = opt_parts[4] if len(opt_parts) > 4 else "1"

        hit_object.slider = _parse_slider_data(
            path_data=path_data,
            repeats=repeats,
            pixel_length=pixel_length,
            edge_sounds_str=edge_sounds_str,
            edge_additions_str=edge_additions_str,
            multiplier_str=multiplier_str,
            tick_rate_str=tick_rate_str,
        )

    elif hit_type & HitObjectType.SPINNER:
        # Spinner: end_time after sound_index
        if not remainder:
            raise ParseError(f"Spinner missing end time: {line!r}")
        # The remainder starts with ',' followed by end_time
        end_time_str = remainder.lstrip(",").split(",")[0]
        try:
            hit_object.spinner_end = int(end_time_str)
        except ValueError:
            raise ParseError(f"Spinner end time is not an integer: {end_time_str!r}") from None

    return hit_object


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
        X,Y,type,object_type,time,combo_colour,sound_index,...

    We extract everything between [HitObjects] and the next section header.
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

    for line in section_content.splitlines():
        line = line.strip()
        if not line or line.startswith("//") or line.startswith("#"):
            continue

        try:
            obj = _parse_hit_object(line)
            objects.append(obj)
        except ParseError:
            # Skip malformed lines rather than failing the entire parse
            continue

    return objects
