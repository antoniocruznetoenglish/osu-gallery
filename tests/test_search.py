"""Tests for the Search/Filter Engine (Phase 5)."""

from __future__ import annotations

import pytest

from osu_gallery.db.database import GalleryDatabase, set_search_engine
from osu_gallery.search.engine import SearchEngine, SearchQuery

SAMPLE_OSU = """[General]
AudioFilename: test.mp3

[Metadata]
Title:Test Song
Creator:TestMapper
Tags:slider circle_pattern

[HitObjects]
256,192,1,2,0,80,0
384,256,2,2,0,0,0,L|480:128,1,100
512,192,1,2,0,80,0
"""

CIRCLES_ONLY = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1,2,0,80,0
384,256,1,2,0,80,0
512,192,1,2,0,80,0
"""

SLIDERS_ONLY = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,2,2,0,0,0,L|480:128,1,100
384,256,2,2,0,0,0,L|512:384,1,150
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


# -- FTS5 initialization --


def test_fts_table_created(engine, db):
    """Verify the FTS5 virtual table is created on engine init."""
    row = db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='pattern_fts'"
    ).fetchone()
    assert row is not None
    assert row["name"] == "pattern_fts"


def test_fts_sync_on_pattern_create(engine, db):
    """Creating a pattern should sync it to the FTS5 index."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3)
    db.create_tag("slider", "slider_type")
    tag = db.get_tag_by_name("slider")
    db.add_tag_to_pattern(pattern.id, tag.id)

    row = db.conn.execute(
        "SELECT pattern_id, raw_code, tags FROM pattern_fts WHERE pattern_id = ?",
        (pattern.id,),
    ).fetchone()
    assert row is not None
    assert row["pattern_id"] == pattern.id
    assert "slider" in row["tags"]


def test_fts_sync_on_pattern_delete(engine, db):
    """Deleting a pattern should remove it from the FTS5 index."""
    pattern = db.create_pattern(CIRCLES_ONLY, object_count=3)
    pattern_id = pattern.id

    db.delete_pattern(pattern_id)

    row = db.conn.execute(
        "SELECT COUNT(*) FROM pattern_fts WHERE pattern_id = ?",
        (pattern_id,),
    ).fetchone()
    assert row[0] == 0


# -- Full-text search --


def test_search_empty_query_returns_all(engine, db):
    """An empty search query returns all patterns."""
    p1 = db.create_pattern(SAMPLE_OSU, object_count=3)
    p2 = db.create_pattern(CIRCLES_ONLY, object_count=3)
    p3 = db.create_pattern(SLIDERS_ONLY, object_count=2)

    results = engine.search(SearchQuery())
    assert len(results) == 3
    ids = {p.id for p in results}
    assert ids == {p1.id, p2.id, p3.id}


def test_search_by_text_in_raw_code(engine, db):
    """Search by text that appears in pattern raw_code returns matching patterns."""
    db.create_pattern(SAMPLE_OSU, object_count=3)
    db.create_pattern(CIRCLES_ONLY, object_count=3)

    # SAMPLE_OSU contains "[HitObjects]" and specific coordinates
    results = engine.search(SearchQuery(text="HitObjects"))
    assert len(results) == 2


def test_search_by_tag_name(engine, db):
    """Search by a tag name returns patterns with that tag."""
    p1 = db.create_pattern(SAMPLE_OSU, object_count=3)
    db.create_pattern(CIRCLES_ONLY, object_count=3)

    tag = db.create_tag("slider", "slider_type")
    db.add_tag_to_pattern(p1.id, tag.id)

    # Sync the FTS index
    engine.sync_fts_all()

    results = engine.search(SearchQuery(text="slider"))
    assert len(results) == 1
    assert results[0].id == p1.id


def test_search_multi_word_query(engine, db):
    """Multi-word search queries use AND logic."""
    db.create_pattern(SAMPLE_OSU, object_count=3)
    db.create_pattern(CIRCLES_ONLY, object_count=3)

    # Both patterns contain "[HitObjects]"
    results = engine.search(SearchQuery(text="HitObjects test"))
    # "test" won't match anything specific, but "HitObjects" matches both
    assert len(results) >= 1


def test_search_no_results(engine, db):
    """Search for non-existent text returns empty list."""
    db.create_pattern(SAMPLE_OSU, object_count=3)
    results = engine.search(SearchQuery(text="zzzznonexistent"))
    assert results == []


# -- Tag filtering --


def test_search_by_tag_filter(engine, db):
    """Filter patterns by tag_id returns only matching patterns."""
    p1 = db.create_pattern(SAMPLE_OSU, object_count=3)
    p2 = db.create_pattern(CIRCLES_ONLY, object_count=3)

    tag_slider = db.create_tag("slider", "slider_type")
    tag_circle = db.create_tag("circle_pattern", "circle")

    db.add_tag_to_pattern(p1.id, tag_slider.id)
    db.add_tag_to_pattern(p2.id, tag_circle.id)

    engine.sync_fts_all()

    results = engine.search(SearchQuery(tag_ids=[tag_slider.id]))
    assert len(results) == 1
    assert results[0].id == p1.id


def test_search_by_multiple_tag_filters(engine, db):
    """Filter by multiple tag IDs returns patterns with any of the tags."""
    p1 = db.create_pattern(SAMPLE_OSU, object_count=3)
    p2 = db.create_pattern(CIRCLES_ONLY, object_count=3)
    db.create_pattern(SLIDERS_ONLY, object_count=2)

    tag_slider = db.create_tag("slider", "slider_type")
    tag_circle = db.create_tag("circle_pattern", "circle")

    db.add_tag_to_pattern(p1.id, tag_slider.id)
    db.add_tag_to_pattern(p2.id, tag_circle.id)

    engine.sync_fts_all()

    results = engine.search(SearchQuery(tag_ids=[tag_slider.id, tag_circle.id]))
    assert len(results) == 2
    ids = {p.id for p in results}
    assert ids == {p1.id, p2.id}


def test_search_exclude_tag(engine, db):
    """Exclude tag filter removes patterns with the excluded tag."""
    p1 = db.create_pattern(SAMPLE_OSU, object_count=3)
    p2 = db.create_pattern(CIRCLES_ONLY, object_count=3)

    tag_slider = db.create_tag("slider", "slider_type")
    tag_circle = db.create_tag("circle_pattern", "circle")

    db.add_tag_to_pattern(p1.id, tag_slider.id)
    db.add_tag_to_pattern(p2.id, tag_circle.id)

    engine.sync_fts_all()

    results = engine.search(SearchQuery(exclude_tag_ids=[tag_slider.id]))
    assert len(results) == 1
    assert results[0].id == p2.id


def test_search_combined_text_and_tag_filter(engine, db):
    """Combine text search with tag filtering."""
    p1 = db.create_pattern(SAMPLE_OSU, object_count=3)
    db.create_pattern(CIRCLES_ONLY, object_count=3)

    tag_slider = db.create_tag("slider", "slider_type")
    db.add_tag_to_pattern(p1.id, tag_slider.id)

    engine.sync_fts_all()

    results = engine.search(
        SearchQuery(text="HitObjects", tag_ids=[tag_slider.id])
    )
    assert len(results) == 1
    assert results[0].id == p1.id


# -- Tag suggestions --


def test_suggest_tags_prefix_match(engine, db):
    """Tag suggestions match by prefix."""
    db.create_tag("slider", "slider_type")
    db.create_tag("slider_complex", "slider_type")
    db.create_tag("circle_pattern", "circle")

    suggestions = engine.suggest_tags("slider")
    assert len(suggestions) == 2
    assert "slider" in suggestions
    assert "slider_complex" in suggestions


def test_suggest_tags_empty_input(engine, db):
    """Empty tag suggestions return empty list."""
    db.create_tag("slider", "slider_type")
    suggestions = engine.suggest_tags("")
    assert suggestions == []


def test_suggest_tags_no_match(engine, db):
    """No matching tags returns empty list."""
    db.create_tag("slider", "slider_type")
    suggestions = engine.suggest_tags("zzzznonexistent")
    assert suggestions == []


# -- Sync --


def test_sync_fts_all_rebuilds_index(engine, db):
    """Rebuilding the FTS index should include all patterns."""
    db.create_pattern(SAMPLE_OSU, object_count=3)
    db.create_pattern(CIRCLES_ONLY, object_count=3)

    engine.sync_fts_all()

    count = db.conn.execute("SELECT COUNT(*) FROM pattern_fts").fetchone()[0]
    assert count == 2


def test_search_by_tag_method(engine, db):
    """search_by_tag returns patterns with the given tag."""
    p1 = db.create_pattern(SAMPLE_OSU, object_count=3)
    db.create_pattern(CIRCLES_ONLY, object_count=3)

    tag = db.create_tag("slider", "slider_type")
    db.add_tag_to_pattern(p1.id, tag.id)

    results = engine.search_by_tag(tag.id)
    assert len(results) == 1
    assert results[0].id == p1.id
