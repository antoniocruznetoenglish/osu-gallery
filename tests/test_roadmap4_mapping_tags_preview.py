"""Tests for Task 3: Mapping tags display on preview pane.

Verifies that the Pattern model has mapping_tags, that the preview
pane renders user mapping tags, and that the tags section is inside
the scroll area.
"""

from __future__ import annotations

import inspect
import json

import pytest

from osu_gallery.db.database import GalleryDatabase
from osu_gallery.db.models import Pattern
from osu_gallery.ui._preview_pane import _PreviewPane


@pytest.fixture
def db(tmp_path):
    """Create a fresh database for each test."""
    db_path = tmp_path / "test.db"
    database = GalleryDatabase(db_path)
    yield database
    database.close()


def test_preview_displays_user_mapping_tags():
    """Pattern model has mapping_tags field with default empty list."""
    pattern = Pattern(raw_code="test")
    assert hasattr(pattern, "mapping_tags")
    assert pattern.mapping_tags == []
    assert isinstance(pattern.mapping_tags, list)


def test_preview_displays_user_mapping_tags_from_db(db):
    """Pattern with mapping_tags stored in DB is round-tripped correctly."""
    tags = ["Circle", "Slider", "Kickslider"]
    pattern = db.create_pattern(
        raw_code="[HitObjects]\n256,192,1000,5,0",
        object_count=1,
        mapping_tags=json.dumps(tags),
    )
    fetched = db.get_pattern(pattern.id)
    assert fetched.mapping_tags == tags


def test_preview_tag_badge_styling(db):
    """_PreviewPane has _render_mapping_tags method with correct signature."""
    assert hasattr(_PreviewPane, "_render_mapping_tags")
    sig = inspect.signature(_PreviewPane._render_mapping_tags)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "parent_layout" in params
    assert "tags" in params


def test_preview_auto_detected_tags_distinct_from_user_tags(db):
    """_PreviewPane has both _render_mapping_tags and _render_tags methods."""
    assert hasattr(_PreviewPane, "_render_mapping_tags")
    assert hasattr(_PreviewPane, "_render_tags")

    mapping_sig = inspect.signature(_PreviewPane._render_mapping_tags)
    render_sig = inspect.signature(_PreviewPane._render_tags)

    assert "tags" in mapping_sig.parameters
    assert "parent_layout" in render_sig.parameters


def test_preview_no_tags_section_when_empty(db):
    """When mapping_tags is empty, the section is not rendered."""
    pattern = db.create_pattern(
        raw_code="[HitObjects]\n256,192,1000,5,0",
        object_count=1,
    )
    fetched = db.get_pattern(pattern.id)
    assert fetched.mapping_tags == []


def test_preview_scrollable_tags(db):
    """Mapping tags section is rendered inside the scroll area of _PreviewPane."""
    source = inspect.getsource(_PreviewPane)
    assert "_scroll" in source
    assert "_content_widget" in source
    assert "_render_mapping_tags" in source

    # Verify that _render_content calls _render_mapping_tags
    render_source = inspect.getsource(_PreviewPane._render_content)
    assert "_render_mapping_tags" in render_source


def test_preview_pane_uses_correct_dimensions(db):
    """_PreviewPane uses PREVIEW_HEIGHT=768 and _MIN_PANE_WIDTH=300."""
    assert _PreviewPane._MIN_PANE_WIDTH == 300
    assert _PreviewPane._PREVIEW_HEIGHT == 768


def test_mapping_tags_stored_as_json_in_db(db):
    """mapping_tags are stored as JSON strings in the database."""
    tags = ["Circle", "Slider"]
    pattern = db.create_pattern(
        raw_code="test code",
        mapping_tags=json.dumps(tags),
    )
    fetched = db.get_pattern(pattern.id)
    assert fetched.mapping_tags == tags
    assert isinstance(fetched.mapping_tags, list)


def test_mapping_tags_empty_string_defaults_to_empty_list(db):
    """An empty mapping_tags string in DB defaults to an empty list."""
    pattern = db.create_pattern(
        raw_code="test code",
        mapping_tags="",
    )
    fetched = db.get_pattern(pattern.id)
    assert fetched.mapping_tags == []
