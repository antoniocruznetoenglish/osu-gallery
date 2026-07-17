"""Tests for Task 5: Support patterns without [HitObjects] header."""

from __future__ import annotations

import pytest

from osu_gallery.db.database import GalleryDatabase
from osu_gallery.parser.osu_file import parse_osu_file

SAMPLE_WITH_HITOBJECTS = """[General]
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
256,192,1000,1,0
384,256,1500,2,0,L|480:128,1,100
512,192,2000,1,0
"""

SAMPLE_WITHOUT_HITOBJECTS = """256,192,1000,1,0
384,256,1500,2,0,L|480:128,1,100
512,192,2000,1,0"""

EXPECTED_OBJECTS_ONLY = "256,192,1000,1,0\n384,256,1500,2,0,L|480:128,1,100\n512,192,2000,1,0"


# -- Fixtures --


@pytest.fixture
def db(tmp_path):
    """Create a fresh database for each test."""
    db_path = tmp_path / "test.db"
    database = GalleryDatabase(db_path)
    yield database
    database.close()


# -- Helper method tests --


def test_has_hitobjects_section_true():
    """_has_hitobjects_section returns True when [HitObjects] is present."""
    from osu_gallery.ui.import_dialog import ImportDialog

    class _FakeDB:
        pass

    dialog = ImportDialog.__new__(ImportDialog)
    assert dialog._has_hitobjects_section(SAMPLE_WITH_HITOBJECTS) is True


def test_has_hitobjects_section_false():
    """_has_hitobjects_section returns False when [HitObjects] is absent."""
    from osu_gallery.ui.import_dialog import ImportDialog

    class _FakeDB:
        pass

    dialog = ImportDialog.__new__(ImportDialog)
    assert dialog._has_hitobjects_section(SAMPLE_WITHOUT_HITOBJECTS) is False


def test_has_hitobjects_section_case_insensitive():
    """_has_hitobjects_section matches [hitobjects] case-insensitively."""
    from osu_gallery.ui.import_dialog import ImportDialog

    class _FakeDB:
        pass

    dialog = ImportDialog.__new__(ImportDialog)
    content = "[hitobjects]\n256,192,1000,1|2,0"
    assert dialog._has_hitobjects_section(content) is True


def test_wrap_in_hitobjects_adds_header():
    """_wrap_in_hitobjects adds [HitObjects] header when missing."""
    from osu_gallery.ui.import_dialog import ImportDialog

    class _FakeDB:
        pass

    dialog = ImportDialog.__new__(ImportDialog)
    result = dialog._wrap_in_hitobjects(SAMPLE_WITHOUT_HITOBJECTS)
    assert result.startswith("[HitObjects]\n")
    assert SAMPLE_WITHOUT_HITOBJECTS in result


def test_wrap_in_hitobjects_preserves_existing():
    """_wrap_in_hitobjects does not double-wrap content that already has header."""
    from osu_gallery.ui.import_dialog import ImportDialog

    class _FakeDB:
        pass

    dialog = ImportDialog.__new__(ImportDialog)
    result = dialog._wrap_in_hitobjects(SAMPLE_WITH_HITOBJECTS)
    assert result == SAMPLE_WITH_HITOBJECTS


def test_extract_objects_only_without_header():
    """_extract_objects_only extracts lines when no [HitObjects] header exists."""
    from osu_gallery.ui.import_dialog import ImportDialog

    class _FakeDB:
        pass

    dialog = ImportDialog.__new__(ImportDialog)
    result = dialog._extract_objects_only(SAMPLE_WITHOUT_HITOBJECTS)
    assert result == EXPECTED_OBJECTS_ONLY


def test_extract_objects_only_with_header():
    """_extract_objects_only extracts lines when [HitObjects] header exists."""
    from osu_gallery.ui.import_dialog import ImportDialog

    class _FakeDB:
        pass

    dialog = ImportDialog.__new__(ImportDialog)
    result = dialog._extract_objects_only(SAMPLE_WITH_HITOBJECTS)
    assert result == EXPECTED_OBJECTS_ONLY


def test_extract_objects_only_without_header_skips_comments():
    """_extract_objects_only filters comments when no header is present."""
    from osu_gallery.ui.import_dialog import ImportDialog

    class _FakeDB:
        pass

    dialog = ImportDialog.__new__(ImportDialog)
    content = """// This is a comment
256,192,1000,1|2,0
# Another comment
384,256,1500,2|2,0"""
    expected = "256,192,1000,1|2,0\n384,256,1500,2|2,0"
    result = dialog._extract_objects_only(content)
    assert result == expected


def test_extract_objects_only_without_header_skips_blank_lines():
    """_extract_objects_only removes blank lines when no header is present."""
    from osu_gallery.ui.import_dialog import ImportDialog

    class _FakeDB:
        pass

    dialog = ImportDialog.__new__(ImportDialog)
    content = """
256,192,1000,1|2,0

384,256,1500,2|2,0
"""
    expected = "256,192,1000,1|2,0\n384,256,1500,2|2,0"
    result = dialog._extract_objects_only(content)
    assert result == expected


# -- Database layer tests --


def test_objects_only_stored_separately(db):
    """Both raw_code and objects_only are stored independently."""
    pattern = db.create_pattern(
        raw_code=SAMPLE_WITH_HITOBJECTS,
        objects_only=EXPECTED_OBJECTS_ONLY,
        object_count=3,
    )
    retrieved = db.get_pattern(pattern.id)
    assert retrieved is not None
    assert retrieved.raw_code == SAMPLE_WITH_HITOBJECTS
    assert retrieved.objects_only == EXPECTED_OBJECTS_ONLY
    assert retrieved.raw_code != retrieved.objects_only


def test_import_pattern_without_hitobjects_header(db):
    """Pattern with raw object lines (no header) imports and stores correctly."""
    from osu_gallery.ui.import_dialog import ImportDialog

    class _FakeDB:
        pass

    dialog = ImportDialog.__new__(ImportDialog)

    objects_only = dialog._extract_objects_only(SAMPLE_WITHOUT_HITOBJECTS)
    raw_code = dialog._wrap_in_hitobjects(SAMPLE_WITHOUT_HITOBJECTS)

    assert raw_code.startswith("[HitObjects]\n")
    assert objects_only == EXPECTED_OBJECTS_ONLY

    osu_file = parse_osu_file(raw_code)
    pattern = db.create_pattern(
        raw_code=raw_code,
        objects_only=objects_only,
        object_count=len(osu_file.hit_objects),
        circle_count=osu_file.circle_count,
        slider_count=osu_file.slider_count,
        timing_bpm=osu_file.timing_bpm,
    )

    retrieved = db.get_pattern(pattern.id)
    assert retrieved is not None
    assert retrieved.objects_only == EXPECTED_OBJECTS_ONLY
    assert retrieved.raw_code.startswith("[HitObjects]\n")
    assert retrieved.object_count == 3


def test_import_pattern_with_hitobjects_header(db):
    """Pattern with [HitObjects] header imports and stores correctly (regression)."""
    from osu_gallery.ui.import_dialog import ImportDialog

    class _FakeDB:
        pass

    dialog = ImportDialog.__new__(ImportDialog)

    assert dialog._has_hitobjects_section(SAMPLE_WITH_HITOBJECTS) is True

    objects_only = dialog._extract_objects_only(SAMPLE_WITH_HITOBJECTS)
    raw_code = dialog._wrap_in_hitobjects(SAMPLE_WITH_HITOBJECTS)

    assert raw_code == SAMPLE_WITH_HITOBJECTS
    assert objects_only == EXPECTED_OBJECTS_ONLY

    osu_file = parse_osu_file(raw_code)
    pattern = db.create_pattern(
        raw_code=raw_code,
        objects_only=objects_only,
        object_count=len(osu_file.hit_objects),
        circle_count=osu_file.circle_count,
        slider_count=osu_file.slider_count,
        timing_bpm=osu_file.timing_bpm,
    )

    retrieved = db.get_pattern(pattern.id)
    assert retrieved is not None
    assert retrieved.raw_code == SAMPLE_WITH_HITOBJECTS
    assert retrieved.objects_only == EXPECTED_OBJECTS_ONLY


def test_copy_code_excludes_header(db):
    """Copy code returns only object lines, not section headers."""
    pattern = db.create_pattern(
        raw_code=SAMPLE_WITH_HITOBJECTS,
        objects_only=EXPECTED_OBJECTS_ONLY,
        object_count=3,
    )
    assert "[HitObjects]" not in pattern.objects_only
    assert "256,192,1000,1,0" in pattern.objects_only


def test_copy_code_fallback_to_raw_code(db):
    """When objects_only is empty, copy uses raw_code as fallback."""
    pattern = db.create_pattern(
        raw_code=SAMPLE_WITH_HITOBJECTS,
        objects_only="",
        object_count=3,
    )
    assert pattern.objects_only == ""


def test_pattern_without_header_still_parsable(db):
    """Pattern stored with wrapped raw_code can be parsed for rendering."""
    from osu_gallery.ui.import_dialog import ImportDialog

    class _FakeDB:
        pass

    dialog = ImportDialog.__new__(ImportDialog)
    raw_code = dialog._wrap_in_hitobjects(SAMPLE_WITHOUT_HITOBJECTS)

    osu_file = parse_osu_file(raw_code)
    assert len(osu_file.hit_objects) == 3
    assert osu_file.circle_count == 2
    assert osu_file.slider_count == 1


def test_pattern_without_header_tags_extracted(db):
    """Tags from metadata are still extracted even without [HitObjects] header."""
    content_with_meta = """[General]
AudioFilename: test.mp3

[Metadata]
Title:Test Song
Artist:Test Artist
Tags:easy hard

256,192,1000,1|2,0
384,256,1500,2|2,0,L|480:128,1,100"""

    from osu_gallery.ui.import_dialog import ImportDialog

    class _FakeDB:
        pass

    dialog = ImportDialog.__new__(ImportDialog)

    has_header = dialog._has_hitobjects_section(content_with_meta)
    assert has_header is False

    parse_content = dialog._wrap_in_hitobjects(content_with_meta)
    osu_file = parse_osu_file(parse_content)

    assert osu_file.metadata.artist == "Test Artist"
    assert "easy" in osu_file.metadata.tags
    assert "hard" in osu_file.metadata.tags
