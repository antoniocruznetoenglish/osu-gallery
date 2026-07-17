"""Tests for tag category functionality (Task 6).

Verifies that metadata tags (.osu file tags) and mapping tags (auto-detected
from hit objects) are properly separated, stored, and searchable.
"""

from __future__ import annotations

import pytest

from osu_gallery.db.database import GalleryDatabase, set_search_engine
from osu_gallery.parser.osu_file import parse_osu_file
from osu_gallery.search.engine import SearchEngine, SearchQuery
from osu_gallery.tags import TAG_CATEGORY_MAPPING, TAG_CATEGORY_METADATA
from osu_gallery.tags.mapping_tags import detect_object_tags

SAMPLE_WITH_TAGS = """[General]
AudioFilename: test.mp3

[Metadata]
Title:Test Song
Creator:TestMapper
Tags:magical girl jpop

[HitObjects]
256,192,1000,5,0
384,256,1500,6,0,L|480:128,1,100
512,192,2000,5,0
"""

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

FULL_SCREEN_PATTERN = """[General]
AudioFilename: test.mp3

[HitObjects]
10,10,1000,5,0
500,370,1500,6,0,L|480:128,1,100
256,192,2000,5,0
50,350,2500,5,0
480,30,3000,6,0,L|100:300,1,100
"""


@pytest.fixture
def db(tmp_path):
    """Create a fresh database for each test."""
    db_path = tmp_path / "test.db"
    database = GalleryDatabase(db_path)
    yield database
    database.close()


@pytest.fixture
def engine(db):
    """Create a SearchEngine with a test database."""
    search_engine = SearchEngine(db)
    set_search_engine(search_engine)
    return search_engine


# -- Mapping tag detection --


def test_detect_object_tags_circles():
    """Auto-detection creates circle count tag for circle patterns."""
    osu_file = parse_osu_file(CIRCLES_ONLY)
    tags = detect_object_tags(osu_file)
    assert "3 circles" in tags


def test_detect_object_tags_sliders():
    """Auto-detection creates slider count tag for slider patterns."""
    osu_file = parse_osu_file(SLIDERS_ONLY)
    tags = detect_object_tags(osu_file)
    assert "2 sliders" in tags


def test_detect_object_tags_circles_and_sliders():
    """Auto-detection creates both circle and slider count tags."""
    osu_file = parse_osu_file(SAMPLE_WITH_TAGS)
    tags = detect_object_tags(osu_file)
    assert "2 circles" in tags
    assert "1 sliders" in tags


def test_detect_object_tags_spinners():
    """Auto-detection creates spinner count tag."""
    content = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1000,5,0
384,256,1500,12,0,3000
"""
    osu_file = parse_osu_file(content)
    tags = detect_object_tags(osu_file)
    assert "1 circles" in tags
    assert "1 spinners" in tags


def test_detect_object_tags_no_slider_pattern_auto_detection():
    """Kickslider, angled patterns, etc. are NOT auto-detected."""
    content = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1000,6,0,L|256:50,1,100
384,256,1500,6,0,L|480:256,1,100
"""
    osu_file = parse_osu_file(content)
    tags = detect_object_tags(osu_file)
    assert "2 sliders" in tags
    assert "vertical slider" not in tags
    assert "horizontal slider" not in tags
    assert "full screen pattern" not in tags


def test_detect_object_tags_empty():
    """Auto-detection returns empty list for empty patterns."""
    content = """[General]
AudioFilename: test.mp3

[HitObjects]
"""
    osu_file = parse_osu_file(content)
    tags = detect_object_tags(osu_file)
    assert tags == []


# -- Tag category constants --


def test_tag_category_constants_defined():
    """Tag category constants are defined and have expected values."""
    assert TAG_CATEGORY_METADATA == "metadata"
    assert TAG_CATEGORY_MAPPING == "mapping"


# -- Database: tags stored with correct categories --


def test_metadata_tags_separate_from_mapping_tags(db):
    """Metadata tags and mapping tags are stored with different categories."""
    db.create_tag("jpop", category=TAG_CATEGORY_METADATA)
    db.create_tag("3 circles", category=TAG_CATEGORY_MAPPING)

    meta_tags = db.conn.execute(
        "SELECT name, category FROM tag WHERE category = ?",
        (TAG_CATEGORY_METADATA,),
    ).fetchall()
    mapping_tags = db.conn.execute(
        "SELECT name, category FROM tag WHERE category = ?",
        (TAG_CATEGORY_MAPPING,),
    ).fetchall()

    assert len(meta_tags) == 1
    assert meta_tags[0]["name"] == "jpop"
    assert meta_tags[0]["category"] == "metadata"

    assert len(mapping_tags) == 1
    assert mapping_tags[0]["name"] == "3 circles"
    assert mapping_tags[0]["category"] == "mapping"


def test_create_tag_with_metadata_category(db):
    """Tags can be created with the metadata category."""
    tag = db.create_tag("magical girl", category=TAG_CATEGORY_METADATA)
    assert tag.category == "metadata"
    fetched = db.get_tag(tag.id)
    assert fetched.category == "metadata"


def test_create_tag_with_mapping_category(db):
    """Tags can be created with the mapping category."""
    tag = db.create_tag("2 circles", category=TAG_CATEGORY_MAPPING)
    assert tag.category == "mapping"
    fetched = db.get_tag(tag.id)
    assert fetched.category == "mapping"


# -- Search: filtering by tag category --


def test_search_filters_by_tag_category(engine, db):
    """Search with category filter returns only patterns with tags in that category."""
    p1 = db.create_pattern(SAMPLE_WITH_TAGS, object_count=3)
    db.create_pattern(CIRCLES_ONLY, object_count=3)

    db.create_tag("jpop", category=TAG_CATEGORY_METADATA)
    tag_jpop = db.get_tag_by_name("jpop")
    db.add_tag_to_pattern(p1.id, tag_jpop.id)

    db.create_tag("3 circles", category=TAG_CATEGORY_MAPPING)
    tag_circles = db.get_tag_by_name("3 circles")
    db.add_tag_to_pattern(p1.id, tag_circles.id)
    db.add_tag_to_pattern(2, tag_circles.id)

    engine.sync_fts_all()

    results = engine.search(SearchQuery(category=TAG_CATEGORY_MAPPING))
    assert len(results) == 2
    ids = {p.id for p in results}
    assert ids == {1, 2}

    results_meta = engine.search(SearchQuery(category=TAG_CATEGORY_METADATA))
    assert len(results_meta) == 1
    assert results_meta[0].id == 1


def test_search_category_empty_returns_all(engine, db):
    """Search without category filter returns all patterns."""
    db.create_pattern(SAMPLE_WITH_TAGS, object_count=3)
    db.create_pattern(CIRCLES_ONLY, object_count=3)

    results = engine.search(SearchQuery())
    assert len(results) == 2
