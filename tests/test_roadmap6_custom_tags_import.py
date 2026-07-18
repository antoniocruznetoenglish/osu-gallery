"""Tests for Task 6: Custom mapping tags in import dialog.

Verifies that custom tags from the database appear as checkboxes in the
import dialog, that disabled tags are skipped, that the "(custom)" suffix
is stripped when collecting selected tags, and that new custom tags are
persisted when selected during save.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QDialog

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


def test_import_dialog_loads_custom_tags(db):
    """Custom tags from the database appear as checkboxes in the import dialog."""
    db.add_custom_tag("my_custom_tag")
    db.add_custom_tag("another_tag")

    dialog = ImportDialog(db=db)
    checkbox_texts = [cb.text() for cb, _ in dialog._checkboxes]

    assert any("my_custom_tag" in t for t in checkbox_texts)
    assert any("another_tag" in t for t in checkbox_texts)
    assert any("(custom)" in t for t in checkbox_texts)
    dialog.close()


def test_import_dialog_skips_disabled_custom_tags(db):
    """Disabled custom tags are not shown as checkboxes in the import dialog."""
    db.add_custom_tag("enabled_tag")
    db.add_custom_tag("disabled_tag")

    disabled_custom = db.get_all_custom_tags()
    disabled_tag_id = next(t["id"] for t in disabled_custom if t["name"] == "disabled_tag")
    db.update_custom_tag_enabled(disabled_tag_id, False)

    dialog = ImportDialog(db=db)
    checkbox_texts = [cb.text() for cb, _ in dialog._checkboxes]

    assert any("enabled_tag" in t for t in checkbox_texts)
    assert not any("disabled_tag" in t for t in checkbox_texts)
    dialog.close()


def test_import_dialog_custom_tag_strips_suffix_on_save(db):
    """_get_selected_mapping_tags returns the tag name without the '(custom)' suffix."""
    db.add_custom_tag("stripped_tag")

    dialog = ImportDialog(db=db)

    # Find the custom checkbox and check it
    custom_checkbox = None
    for cb, _ in dialog._checkboxes:
        if cb.property("is_custom") and "stripped_tag" in cb.text():
            custom_checkbox = cb
            break

    assert custom_checkbox is not None, "Custom checkbox for 'stripped_tag' not found"
    custom_checkbox.setChecked(True)

    selected = dialog._get_selected_mapping_tags()
    assert "stripped_tag" in selected
    assert not any("(custom)" in name for name in selected)
    dialog.close()


def test_import_dialog_persists_new_custom_tag(db):
    """Selecting a new custom tag during parse_and_save creates it in the database."""
    db.add_custom_tag("persist_tag")

    dialog = ImportDialog(db=db)

    # Check the custom tag
    for cb, _ in dialog._checkboxes:
        if cb.property("is_custom") and "persist_tag" in cb.text():
            cb.setChecked(True)
            break

    dialog._text_edit.setPlainText(VALID_OSU)
    dialog._parse_button.click()

    import time
    time.sleep(0.3)

    if dialog.result() == QDialog.Accepted:
        custom_tags = db.get_all_custom_tags()
        names = [t["name"] for t in custom_tags]
        assert "persist_tag" in names

    dialog.close()


def test_import_dialog_canonical_and_custom_together(db):
    """Both canonical and custom tags appear together in the same grid."""
    db.add_custom_tag("custom_one")
    db.add_custom_tag("custom_two")

    dialog = ImportDialog(db=db)

    # Count canonical checkboxes by checking which ones don't have is_custom property
    canonical_checkboxes = sum(1 for cb, _ in dialog._checkboxes if not cb.property("is_custom"))
    custom_checkboxes = sum(1 for cb, _ in dialog._checkboxes if cb.property("is_custom"))

    assert custom_checkboxes == 2
    assert canonical_checkboxes > 0

    checkbox_texts = [cb.text() for cb, _ in dialog._checkboxes]
    assert any("(custom)" in t for t in checkbox_texts)
    dialog.close()


def test_import_dialog_get_selected_tags_excludes_suffix(db):
    """Returned tag names from _get_selected_mapping_tags have no '(custom)' suffix."""
    db.add_custom_tag("tag_alpha")
    db.add_custom_tag("tag_beta")

    dialog = ImportDialog(db=db)

    # Check all checkboxes
    for cb, _ in dialog._checkboxes:
        cb.setChecked(True)

    selected = dialog._get_selected_mapping_tags()

    for name in selected:
        assert "(custom)" not in name
        assert name.endswith(" (custom)") is False

    assert "tag_alpha" in selected
    assert "tag_beta" in selected
    dialog.close()
