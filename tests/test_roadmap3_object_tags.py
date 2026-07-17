"""Tests for Task 3: Auto-detection simplification."""

from __future__ import annotations

from osu_gallery._constants import MAPPING_TAG_OPTIONS
from osu_gallery.parser.osu_file import parse_osu_file
from osu_gallery.tags.mapping_tags import detect_object_tags

CIRCLES_ONLY = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1000,5,0
384,256,1500,5,0
512,192,2000,5,0
"""

SLIDERS_ONLY = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1000,6,0,L|480:128,1,100
384,256,1500,6,0,L|512:384,1,150
"""

MIXED = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1000,5,0
384,256,1500,6,0,L|480:128,1,100
512,192,2000,5,0
"""

WITH_SPINNERS = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1000,5,0
384,256,1500,12,0,3000
512,192,2500,5,0
"""


def test_detect_object_tags_only_counts():
    """Only circle/slider/spinner counts are auto-detected."""
    osu = parse_osu_file(CIRCLES_ONLY)
    tags = detect_object_tags(osu)
    assert "3 circles" in tags
    assert "0 sliders" not in tags


def test_detect_object_tags_circles_and_sliders():
    """Both circle and slider counts detected for mixed patterns."""
    osu = parse_osu_file(MIXED)
    tags = detect_object_tags(osu)
    assert "2 circles" in tags
    assert "1 sliders" in tags


def test_detect_object_tags_with_spinners():
    """Spinner count is auto-detected."""
    osu = parse_osu_file(WITH_SPINNERS)
    tags = detect_object_tags(osu)
    assert "2 circles" in tags
    assert "1 spinners" in tags


def test_no_slider_pattern_auto_detection():
    """Kickslider, angled patterns, etc. are NOT auto-detected."""
    content = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1000,6,0,L|256:50,1,100
384,256,1500,6,0,L|480:256,1,100
"""
    osu = parse_osu_file(content)
    tags = detect_object_tags(osu)
    assert "2 sliders" in tags
    assert "vertical slider" not in tags
    assert "horizontal slider" not in tags
    assert "kickslider" not in tags
    assert "15\u00b0 angled pattern" not in tags
    assert "full screen pattern" not in tags


def test_detect_object_tags_empty():
    """Empty patterns return no tags."""
    content = """[General]
AudioFilename: test.mp3

[HitObjects]
"""
    osu = parse_osu_file(content)
    tags = detect_object_tags(osu)
    assert tags == []


def test_mapping_tag_options_constant():
    """MAPPING_TAG_OPTIONS is defined with expected entries."""
    assert isinstance(MAPPING_TAG_OPTIONS, list)
    assert len(MAPPING_TAG_OPTIONS) > 10
    assert "Circle" in MAPPING_TAG_OPTIONS
    assert "Kickslider" in MAPPING_TAG_OPTIONS
    assert "15\u00b0 angled pattern" in MAPPING_TAG_OPTIONS
    assert "full screen pattern" in MAPPING_TAG_OPTIONS
    assert "circle triangle" in MAPPING_TAG_OPTIONS


def test_detect_mapping_tags_function_renamed():
    """Old detect_mapping_tags no longer exists; detect_object_tags is the new function."""
    from osu_gallery.tags import mapping_tags
    assert hasattr(mapping_tags, "detect_object_tags")
