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
256,192,1000,1|2,0
384,256,1500,2|2,0,L|480:128,1,100
512,192,2000,1|2,0
"""

CIRCLES_ONLY = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1000,1|2,0
384,256,1500,1|2,0
512,192,2000,1|2,0
"""

SLIDERS_ONLY = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1000,2|2,0,L|480:128,1,100
384,256,1500,2|2,0,L|512:384,1,150
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


def test_fts_self_heals_on_schema_mismatch(monkeypatch):
    """Pre-creating pattern_fts with wrong columns triggers self-heal.

    Regression test for BUG-122: FTS5 virtual tables cannot be ALTER'd, so
    any database last touched by an older version of this code with a
    different pattern_fts column layout would keep that incompatible schema
    forever under CREATE ... IF NOT EXISTS. The fix: _init_fts() validates
    the live schema and drops + recreates the table if the required `content`
    column is missing, then rebuilds the index from source data.
    """
    from osu_gallery.search.engine import SearchEngine

    tmp_path = pytest.importorskip("pathlib").Path(
        __import__("tempfile").mkdtemp()
    )
    db_path = tmp_path / "test.db"

    # Build a database with the pattern table but a deliberately wrong FTS
    # schema (only `old_col`, no `content`).
    db = GalleryDatabase(db_path)
    db.conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS pattern_fts USING fts5(old_col);"
    )
    db.conn.commit()

    # Verify the wrong schema is in place before we touch the engine.
    pragma_rows = db.conn.execute("PRAGMA table_info(pattern_fts)").fetchall()
    col_names = {r["name"] for r in pragma_rows}
    assert "content" not in col_names
    assert "old_col" in col_names

    # Create a pattern in the database so sync_fts_all has something to index.
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3)

    # Now initialize SearchEngine — this must self-heal instead of throwing
    # on the next write.
    engine = SearchEngine(db)

    # The table should now have the correct schema.
    pragma_rows = db.conn.execute("PRAGMA table_info(pattern_fts)").fetchall()
    col_names = {r["name"] for r in pragma_rows}
    assert "content" in col_names
    assert "pattern_id" in col_names

    # sync_fts must work without OperationalError.
    engine.sync_fts(pattern.id)

    row = db.conn.execute(
        "SELECT pattern_id, content FROM pattern_fts WHERE pattern_id = ?",
        (pattern.id,),
    ).fetchone()
    assert row is not None
    assert row["pattern_id"] == pattern.id


def test_fts_self_heals_with_no_content_column_at_all(tmp_path):
    """Even a table with zero matching columns triggers self-heal."""
    from osu_gallery.search.engine import SearchEngine

    db_path = tmp_path / "test.db"

    db = GalleryDatabase(db_path)
    # Table exists but has completely different columns (none of which are
    # `content`).
    db.conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS pattern_fts USING fts5(foo, bar);"
    )
    db.conn.commit()

    pattern = db.create_pattern(SAMPLE_OSU, object_count=3)

    engine = SearchEngine(db)

    # After init, the table must have been replaced with the correct schema.
    pragma_rows = db.conn.execute("PRAGMA table_info(pattern_fts)").fetchall()
    col_names = {r["name"] for r in pragma_rows}
    assert col_names == {"pattern_id", "content"}

    # And the existing pattern is now searchable.
    results = engine.search(SearchQuery(text="Test Song"))
    assert len(results) >= 1
    assert results[0].id == pattern.id


def test_fts_sync_on_pattern_create(engine, db):
    """Creating a pattern should sync it to the FTS5 index."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3)
    db.create_tag("slider", "slider_type")
    tag = db.get_tag_by_name("slider")
    db.add_tag_to_pattern(pattern.id, tag.id)

    row = db.conn.execute(
        "SELECT pattern_id, content FROM pattern_fts WHERE pattern_id = ?",
        (pattern.id,),
    ).fetchone()
    assert row is not None
    assert row["pattern_id"] == pattern.id
    assert "slider" in row["content"]


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


def test_search_slash_in_tag_text(engine, db):
    """Search for a tag containing '/' (e.g. '1/1 slider') returns matching patterns.

    Regression test for BUG-120 / BUG-113: FTS5 terms containing '/'
    must be quoted so the query parser doesn't reject them.
    """
    p1 = db.create_pattern(SAMPLE_OSU, object_count=3)
    db.create_pattern(CIRCLES_ONLY, object_count=3)

    tag = db.create_tag("1/1 slider", "mapping")
    db.add_tag_to_pattern(p1.id, tag.id)

    engine.sync_fts_all()

    results = engine.search(SearchQuery(text="1/1 slider"))
    assert len(results) == 1
    assert results[0].id == p1.id


def test_search_quoted_term_with_embedded_quotes(engine, db):
    """Terms containing literal double-quotes are escaped by doubling them."""
    p1 = db.create_pattern(SAMPLE_OSU, object_count=3)
    db.create_pattern(CIRCLES_ONLY, object_count=3)

    tag = db.create_tag('test"quoted', "mapping")
    db.add_tag_to_pattern(p1.id, tag.id)

    engine.sync_fts_all()

    results = engine.search(SearchQuery(text='test"quoted'))
    assert len(results) == 1
    assert results[0].id == p1.id


# -- BUG-121 / BUG-114: per-pattern sync isolation + single-pattern threading --


def test_sync_fts_all_continues_after_one_pattern_fails(monkeypatch, engine, db):
    """sync_fts_all isolates per-pattern failures: one bad pattern doesn't abort the loop."""
    p1 = db.create_pattern(SAMPLE_OSU, object_count=3)
    p2 = db.create_pattern(CIRCLES_ONLY, object_count=3)
    p3 = db.create_pattern(SLIDERS_ONLY, object_count=2)

    # Make one pattern's _upsert_fts raise — simulates corrupt data
    call_order: list[int] = []
    original_upsert = engine._upsert_fts

    def failing_upsert(pid, content):
        call_order.append(pid)
        if pid == p2.id:
            raise ValueError("simulated corrupt data")
        return original_upsert(pid, content)

    monkeypatch.setattr(engine, "_upsert_fts", failing_upsert)

    # Should not raise; loop should continue past p2
    engine.sync_fts_all()

    # All three patterns should have been visited
    assert p1.id in call_order
    assert p2.id in call_order
    assert p3.id in call_order

    # p1 and p3 should be indexed (p2's upsert failed but loop continued)
    indexed = {
        r["pattern_id"]
        for r in db.conn.execute("SELECT pattern_id FROM pattern_fts").fetchall()
    }
    assert p1.id in indexed
    assert p3.id in indexed


def test_notify_search_sync_threads_pattern_id(monkeypatch, engine, db):
    """_notify_search_sync passes pattern_id to sync_fts when available."""
    p1 = db.create_pattern(SAMPLE_OSU, object_count=3)

    synced_ids: list[int] = []
    original_sync_fts = engine.sync_fts

    def track_sync(pid):
        synced_ids.append(pid)
        return original_sync_fts(pid)

    monkeypatch.setattr(engine, "sync_fts", track_sync)

    db.update_pattern(p1)

    assert synced_ids == [p1.id], "Expected sync_fts to be called with the updated pattern_id"


def test_find_missing_fts_entries_diagnostic(engine, db):
    """find_missing_fts_entries returns pattern IDs without FTS rows."""
    # Create patterns without triggering sync (bypass _notify_search_sync)
    db.conn.execute(
        "INSERT INTO pattern (created_at, updated_at, raw_code, object_count) "
        "VALUES (?, ?, ?, ?)",
        ("2026-01-01T00:00:00", "2026-01-01T00:00:00", SAMPLE_OSU, 3),
    )
    db.conn.execute(
        "INSERT INTO pattern (created_at, updated_at, raw_code, object_count) "
        "VALUES (?, ?, ?, ?)",
        ("2026-01-01T00:00:00", "2026-01-01T00:00:00", CIRCLES_ONLY, 3),
    )
    db.conn.commit()

    p1 = db.get_pattern(1)
    p2 = db.get_pattern(2)

    # Initially neither has an FTS row
    missing = engine.find_missing_fts_entries()
    assert set(missing) == {p1.id, p2.id}

    # After syncing one, only the other is missing
    engine.sync_fts(p1.id)
    missing = engine.find_missing_fts_entries()
    assert missing == [p2.id]

    # After syncing all, none missing
    engine.sync_fts(p2.id)
    missing = engine.find_missing_fts_entries()
    assert missing == []
