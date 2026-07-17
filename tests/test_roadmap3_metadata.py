"""Tests for Task 2: Structured metadata fields (artist/title/mapper)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from osu_gallery.db.database import GalleryDatabase, set_search_engine
from osu_gallery.db.models import Pattern
from osu_gallery.search.engine import SearchEngine, SearchQuery

SAMPLE_OSU = """[General]
AudioFilename: test.mp3

[Metadata]
Title:Test Song
Artist:Test Artist
Creator:TestMapper
Tags:slider circle

[HitObjects]
256,192,1000,5,0
384,256,1500,5,0
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


def test_pattern_has_artist_title_mapper_fields():
    """Pattern dataclass has artist, title, mapper fields with defaults."""
    p = Pattern()
    assert p.artist == ""
    assert p.title == ""
    assert p.mapper == ""


def test_database_stores_artist_title_mapper(db):
    """Database CRUD round-trips artist, title, mapper."""
    pattern = db.create_pattern(
        raw_code=SAMPLE_OSU,
        artist="My Artist",
        title="My Song",
        mapper="MyMapper",
    )
    fetched = db.get_pattern(pattern.id)
    assert fetched is not None
    assert fetched.artist == "My Artist"
    assert fetched.title == "My Song"
    assert fetched.mapper == "MyMapper"


def test_database_default_empty_artist_title_mapper(db):
    """Patterns created without artist/title/mapper get empty strings."""
    pattern = db.create_pattern(raw_code=SAMPLE_OSU)
    fetched = db.get_pattern(pattern.id)
    assert fetched.artist == ""
    assert fetched.title == ""
    assert fetched.mapper == ""


def test_database_update_artist_title_mapper(db):
    """Updating artist/title/mapper persists correctly."""
    pattern = db.create_pattern(raw_code=SAMPLE_OSU)
    pattern.artist = "New Artist"
    pattern.title = "New Song"
    pattern.mapper = "NewMapper"
    db.update_pattern(pattern)
    fetched = db.get_pattern(pattern.id)
    assert fetched.artist == "New Artist"
    assert fetched.title == "New Song"
    assert fetched.mapper == "NewMapper"


def test_get_all_patterns_includes_artist_title_mapper(db):
    """get_all_patterns returns artist, title, mapper for each pattern."""
    db.create_pattern(SAMPLE_OSU, artist="A1", title="T1", mapper="M1")
    db.create_pattern(SAMPLE_OSU, artist="A2", title="T2", mapper="M2")
    patterns = db.get_all_patterns()
    for p in patterns:
        assert p.artist in ("A1", "A2")
        assert p.title in ("T1", "T2")
        assert p.mapper in ("M1", "M2")


def test_get_patterns_by_tag_includes_artist_title_mapper(db):
    """get_patterns_by_tag returns artist, title, mapper."""
    tag = db.create_tag("test")
    p1 = db.create_pattern(SAMPLE_OSU, artist="ArtistX", title="SongX", mapper="MapperX")
    db.add_tag_to_pattern(p1.id, tag.id)
    patterns = db.get_patterns_by_tag(tag.id)
    assert len(patterns) == 1
    assert patterns[0].artist == "ArtistX"
    assert patterns[0].title == "SongX"
    assert patterns[0].mapper == "MapperX"


def test_schema_migration_adds_new_columns(tmp_path):
    """Migration adds artist/title/mapper columns to existing DB schema."""
    db_path = tmp_path / "old.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
        CREATE TABLE tag (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE pattern (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            raw_code TEXT NOT NULL,
            objects_only TEXT NOT NULL DEFAULT '',
            object_count INTEGER NOT NULL DEFAULT 0,
            circle_count INTEGER NOT NULL DEFAULT 0,
            slider_count INTEGER NOT NULL DEFAULT 0,
            timing_bpm REAL NOT NULL DEFAULT 0.0
        );
        CREATE TABLE pattern_tag (
            pattern_id INTEGER NOT NULL REFERENCES pattern(id) ON DELETE CASCADE,
            tag_id INTEGER NOT NULL REFERENCES tag(id) ON DELETE CASCADE,
            PRIMARY KEY (pattern_id, tag_id)
        );
    """)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO pattern (created_at, updated_at, raw_code) VALUES (?, ?, ?)",
        (now, now, "old pattern"),
    )
    conn.commit()
    conn.close()

    database = GalleryDatabase(db_path)
    conn = database.conn
    columns = conn.execute("PRAGMA table_info(pattern)").fetchall()
    col_names = [c["name"] for c in columns]
    assert "artist" in col_names
    assert "title" in col_names
    assert "mapper" in col_names

    row = conn.execute("SELECT artist, title, mapper FROM pattern").fetchone()
    assert row["artist"] == ""
    assert row["title"] == ""
    assert row["mapper"] == ""
    database.close()


def test_search_indexes_artist_title_mapper(engine, db):
    """FTS5 index includes artist, title, mapper in searchable content."""
    db.create_pattern(
        SAMPLE_OSU,
        artist="UniqueArtist123",
        title="UniqueSong456",
        mapper="UniqueMapper789",
    )
    engine.sync_fts_all()
    row = db.conn.execute(
        "SELECT content FROM pattern_fts"
    ).fetchone()
    assert row is not None
    content = row["content"]
    assert "UniqueArtist123" in content
    assert "UniqueSong456" in content
    assert "UniqueMapper789" in content


def test_search_finds_by_artist(engine, db):
    """Search can find patterns by artist name."""
    db.create_pattern(SAMPLE_OSU, artist="FindMeArtist")
    db.create_pattern(SAMPLE_OSU, artist="OtherArtist")
    engine.sync_fts_all()
    results = engine.search(SearchQuery(text="FindMeArtist"))
    assert len(results) == 1
    assert results[0].artist == "FindMeArtist"


def test_search_finds_by_title(engine, db):
    """Search can find patterns by song title."""
    db.create_pattern(SAMPLE_OSU, title="MySpecialSong")
    db.create_pattern(SAMPLE_OSU, title="AnotherSong")
    engine.sync_fts_all()
    results = engine.search(SearchQuery(text="MySpecialSong"))
    assert len(results) == 1
    assert results[0].title == "MySpecialSong"


def test_search_finds_by_mapper(engine, db):
    """Search can find patterns by mapper name."""
    db.create_pattern(SAMPLE_OSU, mapper="TopMapper99")
    db.create_pattern(SAMPLE_OSU, mapper="OtherMapper")
    engine.sync_fts_all()
    results = engine.search(SearchQuery(text="TopMapper99"))
    assert len(results) == 1
    assert results[0].mapper == "TopMapper99"
