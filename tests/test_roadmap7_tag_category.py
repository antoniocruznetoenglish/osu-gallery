"""Tests for import dialog tag category fix (Task 7).

Verifies that manually-checked mapping tags in the ImportDialog are stored
with the 'mapping' category instead of incorrectly being stored as 'metadata'.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from osu_gallery.db.database import GalleryDatabase, set_search_engine
from osu_gallery.search.engine import SearchEngine, SearchQuery
from osu_gallery.tags import TAG_CATEGORY_MAPPING
from osu_gallery.ui.import_dialog import ImportDialog

SAMPLE_OSU = """[General]
AudioFilename: test.mp3

[Metadata]
Title:Test Song
Creator:TestMapper

[HitObjects]
256,192,1000,5,0
384,256,1500,5,0
512,192,2000,6,0,L|480:128,1,100
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


def test_import_manual_tags_linked_as_mapping_category(db):
    """Manually-checked tags in ImportDialog end up with category 'mapping' in DB."""
    with (
        patch.object(ImportDialog, "__init__", lambda self, db, parent=None: None),
        patch.object(ImportDialog, "_setup_ui"),
        patch.object(ImportDialog, "_setup_connections"),
        patch.object(ImportDialog, "accept"),
    ):
        dialog = ImportDialog.__new__(ImportDialog)
        dialog.db = db
        dialog._checkboxes = [
            (MagicMock(checkBox=True, isChecked=lambda: True), "Circle"),
            (MagicMock(checkBox=True, isChecked=lambda: False), "Slider"),
            (MagicMock(checkBox=True, isChecked=lambda: True), "Full Screen Pattern"),
        ]
        dialog._text_edit = MagicMock(toPlainText=lambda: SAMPLE_OSU)
        dialog._error_label = MagicMock(
            setText=MagicMock(),
            show=MagicMock(),
            hide=MagicMock(),
            clear=MagicMock(),
        )
        dialog._success_label = MagicMock(
            setText=MagicMock(),
            show=MagicMock(),
            hide=MagicMock(),
            clear=MagicMock(),
        )

        dialog._on_parse_and_save()

    manual_tag_names = {"Circle", "Full Screen Pattern"}

    for tag_name in manual_tag_names:
        tag = db.get_tag_by_name(tag_name)
        assert tag is not None, f"Tag '{tag_name}' was not created in the database"
        assert tag.category == TAG_CATEGORY_MAPPING, (
            f"Tag '{tag_name}' has category '{tag.category}' instead of '{TAG_CATEGORY_MAPPING}'"
        )


def test_import_category_search_finds_manually_tagged_pattern(db, engine):
    """SearchQuery(category='mapping') finds patterns tagged via manual checkbox."""
    with (
        patch.object(ImportDialog, "__init__", lambda self, db, parent=None: None),
        patch.object(ImportDialog, "_setup_ui"),
        patch.object(ImportDialog, "_setup_connections"),
        patch.object(ImportDialog, "accept"),
    ):
        dialog = ImportDialog.__new__(ImportDialog)
        dialog.db = db
        dialog._checkboxes = [
            (MagicMock(checkBox=True, isChecked=lambda: True), "Circle"),
        ]
        dialog._text_edit = MagicMock(toPlainText=lambda: SAMPLE_OSU)
        dialog._error_label = MagicMock(
            setText=MagicMock(),
            show=MagicMock(),
            hide=MagicMock(),
            clear=MagicMock(),
        )
        dialog._success_label = MagicMock(
            setText=MagicMock(),
            show=MagicMock(),
            hide=MagicMock(),
            clear=MagicMock(),
        )

        dialog._on_parse_and_save()

    engine.sync_fts_all()

    results = engine.search(SearchQuery(category=TAG_CATEGORY_MAPPING))
    assert len(results) >= 1
    pattern_ids = {p.id for p in results}

    circle_tag = db.get_tag_by_name("Circle")
    assert circle_tag is not None
    pattern_links = db.conn.execute(
        "SELECT pattern_id FROM pattern_tag WHERE tag_id = ?",
        (circle_tag.id,),
    ).fetchall()
    linked_pattern_ids = {row["pattern_id"] for row in pattern_links}

    assert pattern_ids & linked_pattern_ids, (
        "Search results for category='mapping' should include patterns with manually-tagged items"
    )
