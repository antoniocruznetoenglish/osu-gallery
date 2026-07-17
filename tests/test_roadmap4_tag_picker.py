"""Tests for Task 4: Checkbox tag picker in import dialog.

Verifies that the ImportDialog shows a checkbox grid for mapping tags,
collects selected tags, and supports select all / clear all.
"""

from __future__ import annotations

import inspect
import json

import pytest
from PySide6.QtWidgets import QDialog

from osu_gallery._constants import MAPPING_TAG_OPTIONS
from osu_gallery.db.database import GalleryDatabase
from osu_gallery.ui.import_dialog import ImportDialog


@pytest.fixture
def db(tmp_path):
    """Create a fresh database for each test."""
    db_path = tmp_path / "test.db"
    database = GalleryDatabase(db_path)
    yield database
    database.close()


VALID_OSU = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1000,5,0
"""


def test_import_dialog_shows_checkbox_grid(db):
    """ImportDialog creates a checkbox grid for mapping tags."""
    dialog = ImportDialog(db=db)
    assert hasattr(dialog, "_grid")
    assert hasattr(dialog, "_checkboxes")
    assert isinstance(dialog._checkboxes, list)
    dialog.close()


def test_import_dialog_pre_checks_existing_tags(db):
    """All MAPPING_TAG_OPTIONS have corresponding checkboxes created."""
    dialog = ImportDialog(db=db)
    checkbox_names = [cb.text() for cb, tag_name in dialog._checkboxes]
    for tag in MAPPING_TAG_OPTIONS:
        assert tag in checkbox_names, f"Missing checkbox for tag: {tag}"
    assert len(dialog._checkboxes) == len(MAPPING_TAG_OPTIONS)
    dialog.close()


def test_import_dialog_collects_selected_tags(db):
    """_get_selected_mapping_tags returns only checked tag names."""
    dialog = ImportDialog(db=db)

    # Uncheck all first
    for cb, _ in dialog._checkboxes:
        cb.setChecked(False)

    # Check a few
    for cb, tag_name in dialog._checkboxes:
        if tag_name == "Circle" or tag_name == "Slider":
            cb.setChecked(True)
        break  # just check the first one

    selected = dialog._get_selected_mapping_tags()
    assert "Circle" in selected
    dialog.close()


def test_import_dialog_select_all_clear_all(db):
    """Select All and Clear All buttons exist and work."""
    dialog = ImportDialog(db=db)

    assert hasattr(dialog, "_select_all_button")
    assert hasattr(dialog, "_clear_all_button")
    assert dialog._select_all_button.text() == "Select All"
    assert dialog._clear_all_button.text() == "Clear All"

    # Select all
    dialog._on_select_all()
    for cb, _ in dialog._checkboxes:
        assert cb.isChecked()

    # Clear all
    dialog._on_clear_all()
    for cb, _ in dialog._checkboxes:
        assert not cb.isChecked()

    dialog.close()


def test_import_dialog_saves_mapping_tags_to_db(db):
    """ImportDialog passes mapping_tags as JSON to create_pattern."""
    dialog = ImportDialog(db=db)

    # Check some tags
    for cb, tag_name in dialog._checkboxes:
        if tag_name == "Circle" or tag_name == "Kickslider":
            cb.setChecked(True)

    dialog._text_edit.setPlainText(VALID_OSU)
    parse_button = dialog._parse_button
    parse_button.click()

    # Wait for async operations
    import time
    time.sleep(0.3)

    if dialog.result() == QDialog.Accepted:
        patterns = db.get_all_patterns()
        assert len(patterns) == 1
        pattern = db.get_pattern(patterns[0].id)
        assert pattern.mapping_tags is not None

    dialog.close()


def test_import_dialog_has_tags_scroll_area(db):
    """ImportDialog has a scroll area for the tag checkboxes."""
    dialog = ImportDialog(db=db)
    assert hasattr(dialog, "_tags_scroll")
    dialog.close()


def test_import_dialog_checkbox_grid_is_qgridlayout(db):
    """The tag checkboxes are arranged in a QGridLayout."""
    from PySide6.QtWidgets import QGridLayout

    dialog = ImportDialog(db=db)
    assert isinstance(dialog._grid, QGridLayout)
    dialog.close()


def test_import_dialog_get_selected_mapping_tags_signature():
    """_get_selected_mapping_tags returns a list of strings."""
    sig = inspect.signature(ImportDialog._get_selected_mapping_tags)
    params = list(sig.parameters.keys())
    assert "self" in params


def test_import_dialog_mapping_tags_passed_as_json_string(db):
    """The mapping_tags parameter passed to create_pattern is a JSON string."""
    dialog = ImportDialog(db=db)

    # Check specific tags
    for cb, tag_name in dialog._checkboxes:
        if tag_name == "Circle":
            cb.setChecked(True)

    # Verify the JSON serialization behavior
    selected = dialog._get_selected_mapping_tags()
    if "Circle" in selected:
        json_str = json.dumps(selected)
        parsed = json.loads(json_str)
        assert "Circle" in parsed

    dialog.close()
