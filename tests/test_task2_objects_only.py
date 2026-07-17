"""Tests for Task 2: objects_only field for copy-code functionality."""

from __future__ import annotations

import pytest

from osu_gallery.db.database import GalleryDatabase

SAMPLE_OSU_WITH_HEADERS = """[General]
AudioFilename: test.mp3

[Metadata]
Title:Test Song
Artist:Test Artist
Tags:test jpop

[Difficulty]
CircleSize: 5
SliderMultiplier: 1.4
SliderTickRate: 1

[HitObjects]
256,192,1000,1|2,0
384,256,1500,2|2,0,L|480:128,1,100
512,192,2000,1|2,0
"""

EXPECTED_OBJECTS_ONLY = """256,192,1000,1|2,0
384,256,1500,2|2,0,L|480:128,1,100
512,192,2000,1|2,0"""


# -- Fixtures --


@pytest.fixture
def db(tmp_path):
    """Create a fresh database for each test."""
    db_path = tmp_path / "test.db"
    database = GalleryDatabase(db_path)
    yield database
    database.close()


# -- Database layer tests --


def test_create_pattern_stores_objects_only(db):
    """create_pattern stores objects_only alongside raw_code."""
    pattern = db.create_pattern(
        raw_code=SAMPLE_OSU_WITH_HEADERS,
        objects_only=EXPECTED_OBJECTS_ONLY,
        object_count=3,
    )
    assert pattern.objects_only == EXPECTED_OBJECTS_ONLY
    assert pattern.raw_code == SAMPLE_OSU_WITH_HEADERS


def test_get_pattern_retrieves_objects_only(db):
    """get_pattern returns the objects_only field."""
    pattern = db.create_pattern(
        raw_code=SAMPLE_OSU_WITH_HEADERS,
        objects_only=EXPECTED_OBJECTS_ONLY,
    )
    retrieved = db.get_pattern(pattern.id)
    assert retrieved is not None
    assert retrieved.objects_only == EXPECTED_OBJECTS_ONLY


def test_get_all_patterns_includes_objects_only(db):
    """get_all_patterns returns objects_only for all patterns."""
    db.create_pattern(
        raw_code=SAMPLE_OSU_WITH_HEADERS,
        objects_only=EXPECTED_OBJECTS_ONLY,
    )
    patterns = db.get_all_patterns()
    assert len(patterns) == 1
    assert patterns[0].objects_only == EXPECTED_OBJECTS_ONLY


def test_update_pattern_updates_objects_only(db):
    """update_pattern persists changes to objects_only."""
    pattern = db.create_pattern(
        raw_code=SAMPLE_OSU_WITH_HEADERS,
        objects_only="",
    )
    pattern.objects_only = "updated objects"
    db.update_pattern(pattern)

    retrieved = db.get_pattern(pattern.id)
    assert retrieved.objects_only == "updated objects"


def test_get_patterns_by_tag_includes_objects_only(db):
    """get_patterns_by_tag returns patterns with objects_only."""
    tag = db.create_tag("test")
    pattern = db.create_pattern(
        raw_code=SAMPLE_OSU_WITH_HEADERS,
        objects_only=EXPECTED_OBJECTS_ONLY,
    )
    db.add_tag_to_pattern(pattern.id, tag.id)

    patterns = db.get_patterns_by_tag(tag.id)
    assert len(patterns) == 1
    assert patterns[0].objects_only == EXPECTED_OBJECTS_ONLY


def test_objects_only_defaults_to_empty_string(db):
    """create_pattern without objects_only defaults to empty string."""
    pattern = db.create_pattern(raw_code="some code", object_count=1)
    assert pattern.objects_only == ""


def test_pattern_dataclass_has_objects_only_field():
    """Pattern dataclass includes objects_only with default empty string."""
    from osu_gallery.db.models import Pattern

    pattern = Pattern()
    assert pattern.objects_only == ""


# -- Import dialog extraction tests --


def test_extract_objects_only_from_full_content():
    """_extract_objects_only extracts only hit object lines from full .osu content."""
    from osu_gallery.ui.import_dialog import ImportDialog

    class _FakeDB:
        pass

    dialog = ImportDialog.__new__(ImportDialog)
    result = dialog._extract_objects_only(SAMPLE_OSU_WITH_HEADERS)
    assert result == EXPECTED_OBJECTS_ONLY


def test_extract_objects_only_no_hitobjects_section():
    """_extract_objects_only returns non-header lines when no [HitObjects] section exists."""
    from osu_gallery.ui.import_dialog import ImportDialog

    class _FakeDB:
        pass

    dialog = ImportDialog.__new__(ImportDialog)
    content = """[General]
AudioFilename: test.mp3

[Metadata]
Title:Test
"""
    result = dialog._extract_objects_only(content)
    assert "[General]" in result
    assert "AudioFilename: test.mp3" in result
    assert "[Metadata]" in result
    assert "Title:Test" in result


def test_extract_objects_only_skips_comments():
    """_extract_objects_only skips comment lines in hit objects section."""
    from osu_gallery.ui.import_dialog import ImportDialog

    class _FakeDB:
        pass

    dialog = ImportDialog.__new__(ImportDialog)
    content = """[HitObjects]
// This is a comment
256,192,1000,1|2,0
# Another comment
384,256,1500,2|2,0
"""
    expected = "256,192,1000,1|2,0\n384,256,1500,2|2,0"
    result = dialog._extract_objects_only(content)
    assert result == expected


def test_extract_objects_only_stops_at_next_section():
    """_extract_objects_only stops extracting at the next section header."""
    from osu_gallery.ui.import_dialog import ImportDialog

    class _FakeDB:
        pass

    dialog = ImportDialog.__new__(ImportDialog)
    content = """[HitObjects]
256,192,1000,1|2,0
384,256,1500,2|2,0

[Colours]
Combo1Colour:255,100,100
"""
    expected = "256,192,1000,1|2,0\n384,256,1500,2|2,0"
    result = dialog._extract_objects_only(content)
    assert result == expected
