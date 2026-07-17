"""Tests for Task 4: Search autocomplete suggestions."""

from __future__ import annotations

import pytest

from osu_gallery.db.database import GalleryDatabase, set_search_engine
from osu_gallery.search.engine import SearchEngine

SAMPLE_OSU = """[General]
AudioFilename: test.mp3

[Metadata]
Title:Test Song
Artist:Test Artist
Creator:TestMapper
Tags:slider circle

[HitObjects]
256,192,1000,5,0
384,256,1500,6,0,L|480:128,1,100
"""


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test.db"
    database = GalleryDatabase(db_path)
    yield database
    database.close()


@pytest.fixture
def engine(db):
    search_engine = SearchEngine(db)
    set_search_engine(search_engine)
    return search_engine


def test_search_suggestions_returns_tags(db, engine):
    """Tag names appear in suggestions."""
    db.create_tag("slider", "mapping")
    db.create_tag("circle_pattern", "mapping")
    suggestions = engine.get_search_suggestions("sli")
    assert "slider" in suggestions


def test_search_suggestions_returns_artists(db, engine):
    """Artist names appear in suggestions."""
    db.create_pattern(SAMPLE_OSU, artist="Hige Driver")
    engine.sync_fts_all()
    suggestions = engine.get_search_suggestions("Hige")
    assert "Hige Driver" in suggestions


def test_search_suggestions_returns_titles(db, engine):
    """Title names appear in suggestions."""
    db.create_pattern(SAMPLE_OSU, title="Cruel Angel's Thesis")
    engine.sync_fts_all()
    suggestions = engine.get_search_suggestions("Cruel")
    assert "Cruel Angel's Thesis" in suggestions


def test_search_suggestions_returns_mappers(db, engine):
    """Mapper names appear in suggestions."""
    db.create_pattern(SAMPLE_OSU, mapper="MapMaster42")
    engine.sync_fts_all()
    suggestions = engine.get_search_suggestions("MapMaster")
    assert "MapMaster42" in suggestions


def test_search_suggestions_prefix_match(db, engine):
    """Only prefix matches are returned."""
    db.create_tag("apple")
    db.create_tag("application")
    db.create_tag("banana")
    suggestions = engine.get_search_suggestions("app")
    assert "apple" in suggestions
    assert "application" in suggestions
    assert "banana" not in suggestions


def test_search_suggestions_limited_to_15(db, engine):
    """Results are capped at 15."""
    for i in range(20):
        db.create_tag(f"tag_{i:02d}")
    suggestions = engine.get_search_suggestions("tag")
    assert len(suggestions) <= 15


def test_search_suggestions_deduplicated(db, engine):
    """No duplicate terms in results."""
    db.create_tag("unique_tag")
    db.create_pattern(SAMPLE_OSU, artist="unique_tag", title="unique_tag", mapper="unique_tag")
    engine.sync_fts_all()
    suggestions = engine.get_search_suggestions("unique_tag")
    assert suggestions.count("unique_tag") == 1


def test_search_suggestions_empty_input(engine):
    """Empty input returns empty list."""
    assert engine.get_search_suggestions("") == []
    assert engine.get_search_suggestions("   ") == []


def test_search_suggestions_no_match(engine):
    """No matching terms returns empty list."""
    suggestions = engine.get_search_suggestions("zzzznonexistent")
    assert suggestions == []


def test_search_suggestions_sorted(db, engine):
    """Results are sorted alphabetically."""
    db.create_tag("cherry")
    db.create_tag("apple")
    db.create_tag("banana")
    suggestions = engine.get_search_suggestions("a")
    if len(suggestions) > 1:
        assert suggestions == sorted(suggestions)
