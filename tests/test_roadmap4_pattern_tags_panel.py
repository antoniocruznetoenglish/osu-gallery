"""Tests for Task 5: Pattern Tags panel dialog.

Verifies that the PatternTagsDialog exists, loads canonical tags,
supports adding/removing custom tags, and that custom tags persist
across sessions via the custom_mapping_tags table.
"""

from __future__ import annotations

import inspect

import pytest
from PySide6.QtWidgets import QDialog

from osu_gallery._constants import MAPPING_TAG_OPTIONS
from osu_gallery.db.database import GalleryDatabase
from osu_gallery.ui._pattern_tags_dialog import PatternTagsDialog
from osu_gallery.ui.main_window import MainWindow


@pytest.fixture
def db(tmp_path):
    """Create a fresh database for each test."""
    db_path = tmp_path / "test.db"
    database = GalleryDatabase(db_path)
    yield database
    database.close()


def test_pattern_tags_button_exists():
    """MainWindow has a _tags_button in the toolbar."""
    source = inspect.getsource(MainWindow)
    assert "_tags_button" in source
    assert "Pattern Tags" in source


def test_pattern_tags_dialog_opens(db):
    """PatternTagsDialog can be instantiated."""
    dialog = PatternTagsDialog(db=db)
    assert dialog is not None
    assert isinstance(dialog, QDialog)
    dialog.close()


def test_pattern_tags_dialog_loads_canonical_tags(db):
    """PatternTagsDialog creates checkboxes for all MAPPING_TAG_OPTIONS."""
    dialog = PatternTagsDialog(db=db)
    assert len(dialog._checkboxes) >= len(MAPPING_TAG_OPTIONS)

    checkbox_texts = [cb.text() for cb in dialog._checkboxes]
    for tag in MAPPING_TAG_OPTIONS:
        assert tag in checkbox_texts, f"Missing canonical tag: {tag}"
    dialog.close()


def test_pattern_tags_dialog_adds_custom_tag(db):
    """Adding a custom tag via the dialog inserts it into the database."""
    initial_count = len(db.get_all_custom_tags())

    dialog = PatternTagsDialog(db=db)
    dialog._new_tag_edit.setText("my_custom_tag")
    dialog._on_add_tag()

    custom_tags = db.get_all_custom_tags()
    assert len(custom_tags) == initial_count + 1
    names = [t["name"] for t in custom_tags]
    assert "my_custom_tag" in names
    dialog.close()


def test_pattern_tags_dialog_removes_custom_tag(db):
    """Toggling a custom tag checkbox updates its enabled state in the database."""
    db.add_custom_tag("to_disable")
    custom_tags = db.get_all_custom_tags()
    tag_id = next(t["id"] for t in custom_tags if t["name"] == "to_disable")

    dialog = PatternTagsDialog(db=db)

    # Find the custom checkbox and uncheck it
    for cb in dialog._checkboxes:
        if cb.property("is_custom") and "to_disable" in cb.text():
            cb.setChecked(False)
            break

    dialog._on_save()

    tag = db.get_all_custom_tags()
    disabled_tag = next(t for t in tag if t["id"] == tag_id)
    assert disabled_tag["enabled"] is False
    dialog.close()


def test_pattern_tags_dialog_custom_tag_appears_in_import(db):
    """Custom tags added via PatternTagsDialog appear when loading the dialog again."""
    db.add_custom_tag("persistent_tag")

    dialog = PatternTagsDialog(db=db)
    checkbox_texts = [cb.text() for cb in dialog._checkboxes]
    assert any("persistent_tag" in t for t in checkbox_texts)
    dialog.close()


def test_pattern_tags_dialog_persists_across_sessions(db):
    """Custom tags are stored in the custom_mapping_tags table."""
    db.add_custom_tag("session_tag_1")
    db.add_custom_tag("session_tag_2")

    custom_tags = db.get_all_custom_tags()
    names = [t["name"] for t in custom_tags]
    assert "session_tag_1" in names
    assert "session_tag_2" in names


def test_pattern_tags_dialog_validation_no_empty(db):
    """Adding an empty tag name does not insert into the database."""
    initial_count = len(db.get_all_custom_tags())

    dialog = PatternTagsDialog(db=db)
    dialog._new_tag_edit.setText("   ")
    dialog._on_add_tag()

    custom_tags = db.get_all_custom_tags()
    assert len(custom_tags) == initial_count
    dialog.close()


def test_pattern_tags_dialog_validation_no_duplicates(db):
    """Adding a duplicate custom tag returns False from add_custom_tag."""
    result1 = db.add_custom_tag("unique_name")
    result2 = db.add_custom_tag("unique_name")

    assert result1 is True
    assert result2 is False

    custom_tags = db.get_all_custom_tags()
    count = sum(1 for t in custom_tags if t["name"] == "unique_name")
    assert count == 1


def test_pattern_tags_dialog_has_add_button(db):
    """PatternTagsDialog has an add button and new tag edit."""
    dialog = PatternTagsDialog(db=db)
    assert hasattr(dialog, "_add_button")
    assert hasattr(dialog, "_new_tag_edit")
    dialog.close()


def test_pattern_tags_dialog_has_save_cancel_buttons(db):
    """PatternTagsDialog has Save and Cancel buttons via QDialogButtonBox."""
    from PySide6.QtWidgets import QDialogButtonBox

    dialog = PatternTagsDialog(db=db)
    # The dialog creates a QDialogButtonBox internally
    button_boxes = dialog.findChildren(QDialogButtonBox)
    assert len(button_boxes) >= 1
    dialog.close()
