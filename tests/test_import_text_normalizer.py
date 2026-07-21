"""Tests for the Discord-collapsed .osu text normalizer."""

from __future__ import annotations

import re

from osu_gallery.parser.osu_file import parse_osu_file
from osu_gallery.ui._osu_text_normalizer import normalize_osu_text

NORMAL_OSU = (
    "osu file format v14\n"
    "\n"
    "[General]\n"
    "AudioFilename: test.mp3\n"
    "\n"
    "[Metadata]\n"
    "Title:Test Song\n"
    "Creator:TestMapper\n"
    "\n"
    "[HitObjects]\n"
    "256,192,1000,5,0\n"
    "384,256,1500,6,0,L|480:128,1,100\n"
    "512,192,2000,5,0"
)

COLLAPSED_OSU = (
    "osu file format v14[General]AudioFilename: test.mp3"
    "[Metadata]Title:Test Song[HitObjects]"
    "256,192,1000,5,0 384,256,1500,6,0,L|480:128,1,100 512,192,2000,5,0"
)

_OBJ_ONLY_RE = re.compile(r"^\[HitObjects\]\s*$", re.MULTILINE | re.IGNORECASE)
_NEXT_SECTION_RE = re.compile(r"^\[[^\]]+\]\s*$", re.MULTILINE)


def _extract_objects(text: str) -> list[str]:
    """Extract hit object lines from .osu content."""
    section_match = _OBJ_ONLY_RE.search(text)
    if section_match is None:
        return []
    start = section_match.end()
    remaining = text[start:]
    next_match = _NEXT_SECTION_RE.search(remaining)
    objects_content = (
        remaining[:next_match.start()] if next_match else remaining
    )
    return [
        line.strip()
        for line in objects_content.splitlines()
        if line.strip()
    ]


def _hitobject_lines(text: str) -> list[str]:
    """Get non-section, non-empty lines from text."""
    return [
        line
        for line in text.split("\n")
        if line.strip() and not line.strip().startswith("[")
    ]


def test_normal_multiline_content_unchanged():
    """Properly formatted .osu content should pass through unchanged."""
    result = normalize_osu_text(NORMAL_OSU)
    assert result == NORMAL_OSU


def test_crlf_normalized_to_lf():
    """\\r\\n line endings should be normalized to \\n."""
    content = NORMAL_OSU.replace("\n", "\r\n")
    result = normalize_osu_text(content)
    assert "\r" not in result
    assert result == NORMAL_OSU


def test_leading_trailing_whitespace_stripped():
    """Outer whitespace should be trimmed."""
    content = "   \n  " + NORMAL_OSU + "  \n   "
    result = normalize_osu_text(content)
    assert result == NORMAL_OSU


def test_collapsed_sections_restored():
    """Collapsed content should have section headers restored to own lines."""
    result = normalize_osu_text(COLLAPSED_OSU)
    for header in ("[General]", "[Metadata]", "[HitObjects]"):
        assert header + "\n" in result
        lines = result.split("\n")
        header_lines = [ln for ln in lines if ln.strip() == header]
        assert len(header_lines) >= 1, f"Section header {header} not on its own line"


def test_collapsed_hit_objects_split():
    """Hit objects in collapsed content should be split onto separate lines."""
    result = normalize_osu_text(COLLAPSED_OSU)
    hitobjects_idx = result.find("[HitObjects]")
    assert hitobjects_idx != -1
    remaining = result[hitobjects_idx + len("[HitObjects]\n"):]
    next_section = re.search(r"^\[", remaining, re.MULTILINE)
    objects_part = (
        remaining[:next_section.start()] if next_section else remaining
    )
    object_lines = [
        ln.strip() for ln in objects_part.split("\n") if ln.strip()
    ]
    assert len(object_lines) == 3
    assert object_lines[0] == "256,192,1000,5,0"
    assert object_lines[1] == "384,256,1500,6,0,L|480:128,1,100"
    assert object_lines[2] == "512,192,2000,5,0"


def test_collapsed_parses_correctly():
    """Normalized collapsed content should parse to same object count
    as normal content."""
    normal_parsed = parse_osu_file(NORMAL_OSU)
    collapsed_normalized = normalize_osu_text(COLLAPSED_OSU)
    collapsed_parsed = parse_osu_file(collapsed_normalized)
    assert len(collapsed_parsed.hit_objects) == len(normal_parsed.hit_objects)
    assert collapsed_parsed.metadata.title == normal_parsed.metadata.title
    assert collapsed_parsed.metadata.artist == normal_parsed.metadata.artist


def test_collapsed_objects_only_copy_ready():
    """After normalization, extracting objects_only yields one object
    per line."""
    result = normalize_osu_text(COLLAPSED_OSU)
    lines = _extract_objects(result)
    assert len(lines) == 3
    for line in lines:
        assert "," in line


def test_normal_content_unchanged_by_normalizer():
    """Properly formatted content should not be altered by the normalizer."""
    result = normalize_osu_text(NORMAL_OSU)
    assert result == NORMAL_OSU


def test_empty_input():
    """Empty string should return empty string."""
    assert normalize_osu_text("") == ""
    assert normalize_osu_text("   ") == ""
    assert normalize_osu_text("\n\n") == ""


def test_only_section_header():
    """Content with only a section header should return with newline."""
    result = normalize_osu_text("[General]")
    assert result == "[General]\n"

    result = normalize_osu_text("[HitObjects]")
    assert result == "[HitObjects]\n"


def test_hit_object_with_slider_path_preserved():
    """Slider paths with commas inside records should not be split."""
    content = (
        "[HitObjects]\n"
        "256,192,1000,6,0,L|480:128,1,100\n"
        "384,256,1500,5,0"
    )
    result = normalize_osu_text(content)
    assert result == content

    collapsed = (
        "[HitObjects]256,192,1000,6,0,L|480:128,1,100 384,256,1500,5,0"
    )
    result = normalize_osu_text(collapsed)
    lines = _hitobject_lines(result)
    assert len(lines) == 2
    assert "L|480:128,1,100" in lines[0]
    assert lines[1] == "384,256,1500,5,0"


def test_malformed_input_unchanged():
    """Completely unrecognizable content returns with only line-ending
    normalization."""
    malformed = "hello world this is not an osu file at all"
    result = normalize_osu_text(malformed)
    assert result == "hello world this is not an osu file at all"

    malformed_crlf = "hello\r\nworld"
    result = normalize_osu_text(malformed_crlf)
    assert result == "hello\nworld"


def test_collapsed_with_timing_points():
    """Timing points section should not be affected by hit object splitting."""
    content = (
        "[General]\n"
        "AudioFilename: test.mp3\n"
        "\n"
        "[TimingPoints]\n"
        "0,333.33,4,0,0,100,1,0\n"
        "5000,-50,4,0,0,100,0,0\n"
        "\n"
        "[HitObjects]\n"
        "256,192,1000,5,0\n"
        "384,256,1500,5,0"
    )
    result = normalize_osu_text(content)
    assert result == content


def test_collapsed_timing_points_unchanged():
    """Timing points should not be split by the hit-object regex."""
    collapsed = (
        "[TimingPoints]0,333.33,4,0,0,100,1,0 5000,-50,4,0,0,100,0,0\n"
        "[HitObjects]256,192,1000,5,0 384,256,1500,5,0"
    )
    result = normalize_osu_text(collapsed)
    tp_lines = []
    ho_lines = []
    in_tp = False
    in_ho = False
    for line in result.split("\n"):
        if line.strip() == "[TimingPoints]":
            in_tp = True
            in_ho = False
            continue
        elif line.strip() == "[HitObjects]":
            in_tp = False
            in_ho = True
            continue
        if in_tp:
            tp_lines.append(line.strip())
        elif in_ho:
            ho_lines.append(line.strip())
    assert len(tp_lines) == 1
    assert tp_lines[0] == "0,333.33,4,0,0,100,1,0 5000,-50,4,0,0,100,0,0"
    assert len(ho_lines) == 2
    assert ho_lines[0] == "256,192,1000,5,0"
    assert ho_lines[1] == "384,256,1500,5,0"


def test_multiple_sliders_preserved():
    """Multiple sliders with complex paths should be preserved intact."""
    content = (
        "[HitObjects]\n"
        "256,192,1000,6,0,L|100:100,1,100\n"
        "384,256,1500,6,0,B|100:100:200:200:300:300,2,100\n"
        "512,192,2000,6,0,P|100:100|200:200|300:300,1,100"
    )
    result = normalize_osu_text(content)
    assert result == content

    collapsed = (
        "[HitObjects]256,192,1000,6,0,L|100:100,1,100 "
        "384,256,1500,6,0,B|100:100:200:200:300:300,2,100 "
        "512,192,2000,6,0,P|100:100|200:200|300:300,1,100"
    )
    result = normalize_osu_text(collapsed)
    lines = _hitobject_lines(result)
    assert len(lines) == 3
    assert "L|100:100,1,100" in lines[0]
    assert "B|100:100:200:200:300:300,2,100" in lines[1]
    assert "P|100:100|200:200|300:300,1,100" in lines[2]


def test_spinner_preserved():
    """Spinner objects should be preserved intact."""
    content = "[HitObjects]\n256,192,1000,12,0,3000"
    result = normalize_osu_text(content)
    assert result == content

    collapsed = "[HitObjects]256,192,1000,12,0,3000 384,256,1500,5,0"
    result = normalize_osu_text(collapsed)
    lines = _hitobject_lines(result)
    assert len(lines) == 2
    assert lines[0] == "256,192,1000,12,0,3000"
    assert lines[1] == "384,256,1500,5,0"


def test_all_section_headers_restored():
    """All known section headers should be restored to own lines."""
    collapsed = (
        "osu file format v14[General]AudioFilename: test.mp3"
        "[Editor]DistanceSpacing: 1.2"
        "[Metadata]Title:Test"
        "[Difficulty]CircleSize: 4"
        "[Events]//Background,0,bg.jpg,0,0"
        "[TimingPoints]0,333.33,4,0,0,100,1,0"
        "[Colours]Combo1Colour:255,0,0"
        "[HitObjects]256,192,1000,5,0"
    )
    result = normalize_osu_text(collapsed)
    for header in (
        "[General]", "[Editor]", "[Metadata]", "[Difficulty]",
        "[Events]", "[TimingPoints]", "[Colours]", "[HitObjects]",
    ):
        assert header + "\n" in result, f"{header} not on its own line"


def test_content_with_no_hitobjects_section():
    """Content without [HitObjects] section should only restore section
    headers."""
    content = "[General]AudioFilename: test.mp3\n[Difficulty]CircleSize: 4"
    result = normalize_osu_text(content)
    assert "[General]\n" in result
    assert "[Difficulty]\n" in result


def test_partial_collapse():
    """Partially collapsed content should have only collapsed parts fixed."""
    content = (
        "osu file format v14\n\n"
        "[General]\n"
        "AudioFilename: test.mp3\n\n"
        "[HitObjects]256,192,1000,5,0 384,256,1500,5,0"
    )
    expected = (
        "osu file format v14\n\n"
        "[General]\n"
        "AudioFilename: test.mp3\n\n"
        "[HitObjects]\n"
        "256,192,1000,5,0\n"
        "384,256,1500,5,0"
    )
    result = normalize_osu_text(content)
    assert result == expected


def test_negative_coordinates():
    """Hit objects with negative coordinates should be handled."""
    collapsed = "[HitObjects]-5,192,1000,5,0 256,-10,1500,5,0"
    result = normalize_osu_text(collapsed)
    lines = _hitobject_lines(result)
    assert len(lines) == 2
    assert lines[0] == "-5,192,1000,5,0"
    assert lines[1] == "256,-10,1500,5,0"


def test_decimal_coordinates():
    """Hit objects with decimal coordinates should be handled."""
    collapsed = (
        "[HitObjects]256.5,192.5,1000,5,0 384.0,256.0,1500,5,0"
    )
    result = normalize_osu_text(collapsed)
    lines = _hitobject_lines(result)
    assert len(lines) == 2
    assert lines[0] == "256.5,192.5,1000,5,0"
    assert lines[1] == "384.0,256.0,1500,5,0"


def test_objects_only_extraction_after_normalization():
    """objects_only extraction should work correctly after normalization."""
    result = normalize_osu_text(COLLAPSED_OSU)
    lines = _extract_objects(result)
    assert len(lines) == 3
    assert all("," in line for line in lines)
