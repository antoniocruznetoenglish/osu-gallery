"""Tests for the osu gallery UI components (Phase 3)."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QWidget

from osu_gallery.db.database import GalleryDatabase, set_search_engine
from osu_gallery.search.engine import SearchEngine
from osu_gallery.ui._image_drop_target import ImageDropTarget
from osu_gallery.ui.edit_dialog import EditDialog
from osu_gallery.ui.import_dialog import ImportDialog
from osu_gallery.ui.main_window import MainWindow

VALID_OSU = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1000,5,0
"""

INVALID_CODE = """[General]
AudioFilename: test.mp3

[HitObjects]
this is not a valid hit object line
"""

SAMPLE_OSU = """[General]
AudioFilename: test.mp3

[Metadata]
Title:Test Song
Creator:TestMapper
Tags:slider circle_pattern

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


@pytest.fixture
def db(tmp_path):
    """Create a fresh database for each test."""
    db_path = tmp_path / "test.db"
    database = GalleryDatabase(db_path)
    search_engine = SearchEngine(database)
    set_search_engine(search_engine)
    yield database


@pytest.fixture
def window(db):
    """Create a MainWindow with a test database."""
    main_window = MainWindow(db_path=db.db_path)
    yield main_window
    main_window.close()


# -- MainWindow tests --


def test_main_window_creation(qtbot):
    """MainWindow can be created and shown without errors."""
    main_window = MainWindow()
    qtbot.addWidget(main_window)
    main_window.show()
    qtbot.wait(100)
    assert main_window.isVisible()
    main_window.close()


def test_main_window_empty_state(qtbot, window):
    """With an empty database, the empty state widget is visible."""
    qtbot.addWidget(window)
    window.show()
    qtbot.wait(100)

    empty_labels = window.findChildren(QLabel)
    pattern_labels = [w for w in empty_labels if "No patterns yet" in w.text()]
    assert len(pattern_labels) == 1
    assert pattern_labels[0].isVisible()


def test_main_window_with_patterns(qtbot, db):
    """Create patterns in DB, refresh, verify grid shows placeholder items."""
    window = MainWindow(db_path=db.db_path)
    qtbot.addWidget(window)
    qtbot.waitExposed(window)

    db.create_pattern("pattern_1", object_count=1)
    db.create_pattern("pattern_2", object_count=2)
    window.refresh()
    qtbot.wait(100)

    placeholders = window.findChildren(QWidget)
    assert len(placeholders) > 0
    window.close()


def test_main_window_search_bar_exists(qtbot, window):
    """MainWindow has a search bar."""
    qtbot.addWidget(window)
    window.show()
    qtbot.wait(100)
    assert window._search_edit is not None
    assert window._search_edit.placeholderText() == "Search patterns\u2026"


def test_main_window_import_button_exists(qtbot, window):
    """MainWindow has an import button."""
    qtbot.addWidget(window)
    window.show()
    qtbot.wait(100)
    assert window._import_button is not None
    assert window._import_button.text() == "Import Pattern"


# -- ImportDialog tests --


def test_import_dialog_creation(qtbot, db):
    """ImportDialog can be created and shown."""
    dialog = ImportDialog(db=db)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.wait(100)
    assert dialog.isVisible()
    dialog.close()


def test_import_dialog_cancel(qtbot, db):
    """Click Cancel, verify dialog rejects."""
    dialog = ImportDialog(db=db)
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)

    cancel_button = dialog._cancel_button
    qtbot.mouseClick(cancel_button, Qt.MouseButton.LeftButton)
    qtbot.wait(100)

    assert dialog.result() == QDialog.Rejected


def test_import_dialog_parse_and_save(qtbot, db):
    """Paste valid .osu code, click Parse & Save, verify dialog accepts and pattern is saved."""
    dialog = ImportDialog(db=db)
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)

    dialog._text_edit.setPlainText(VALID_OSU)
    parse_button = dialog._parse_button
    qtbot.mouseClick(parse_button, Qt.MouseButton.LeftButton)
    qtbot.wait(200)

    assert dialog.result() == QDialog.Accepted

    patterns = db.get_all_patterns()
    assert len(patterns) == 1
    assert patterns[0].object_count == 1


def test_import_dialog_parse_error(qtbot, db):
    """Paste invalid code, verify it gets parsed (parser is lenient)."""
    dialog = ImportDialog(db=db)
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)

    dialog._text_edit.setPlainText(INVALID_CODE)
    parse_button = dialog._parse_button
    qtbot.mouseClick(parse_button, Qt.MouseButton.LeftButton)
    qtbot.wait(200)

    assert dialog.result() == QDialog.Accepted
    patterns = db.get_all_patterns()
    assert len(patterns) == 1


def test_import_dialog_empty_input(qtbot, db):
    """Click Parse & Save with empty text, verify error is shown."""
    dialog = ImportDialog(db=db)
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)

    parse_button = dialog._parse_button
    qtbot.mouseClick(parse_button, Qt.MouseButton.LeftButton)
    qtbot.wait(500)

    assert dialog.result() == 0
    assert "paste" in dialog._error_label.text().lower()


def test_import_dialog_auto_tags(qtbot, db):
    """Verify object counts are auto-detected; metadata no longer auto-tagged."""
    osu_with_tags = """[General]
AudioFilename: test.mp3

[Metadata]
Title:Test Song
Creator:TestMapper
Tags:slider circle_pattern

[HitObjects]
256,192,1000,6,0,L|100:100,1,100
"""
    dialog = ImportDialog(db=db)
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)

    dialog._text_edit.setPlainText(osu_with_tags)
    parse_button = dialog._parse_button
    qtbot.mouseClick(parse_button, Qt.MouseButton.LeftButton)
    qtbot.wait(200)

    assert dialog.result() == QDialog.Accepted

    tags = db.get_all_tags()
    tag_names = {t.name for t in tags}
    assert "1 slider" in tag_names
    assert "slider" not in tag_names
    assert "circle_pattern" not in tag_names
    assert "TestMapper" not in tag_names


# -- Search bar integration tests --


def test_main_window_search_filters_patterns(qtbot, db):
    """Search bar filters grid when text is entered."""
    db.create_pattern(SAMPLE_OSU, object_count=3)
    db.create_pattern(CIRCLES_ONLY, object_count=3)

    window = MainWindow(db_path=db.db_path)
    qtbot.addWidget(window)
    qtbot.waitExposed(window)

    window.refresh()
    qtbot.wait(200)

    assert window._flow_layout.count() == 2

    window._search_edit.setText("HitObjects")
    qtbot.wait(500)

    assert window._flow_layout.count() == 2


def test_main_window_search_clears_filter(qtbot, db):
    """Clearing search bar restores all patterns."""
    db.create_pattern(SAMPLE_OSU, object_count=3)
    db.create_pattern(CIRCLES_ONLY, object_count=3)

    window = MainWindow(db_path=db.db_path)
    qtbot.addWidget(window)
    qtbot.waitExposed(window)

    window.refresh()
    qtbot.wait(200)

    assert window._flow_layout.count() == 2

    window._search_edit.setText("nonexistent")
    qtbot.wait(500)

    assert window._flow_layout.count() == 0

    window._search_edit.setText("")
    qtbot.wait(500)

    assert window._flow_layout.count() == 2

    window.close()


def test_main_window_search_by_tag(qtbot, db):
    """search_by_tag method filters grid to only patterns with that tag."""
    p1 = db.create_pattern(SAMPLE_OSU, object_count=3)
    db.create_pattern(CIRCLES_ONLY, object_count=3)

    tag = db.create_tag("slider", "slider_type")
    db.add_tag_to_pattern(p1.id, tag.id)

    window = MainWindow(db_path=db.db_path)
    qtbot.addWidget(window)
    qtbot.waitExposed(window)

    window.refresh()
    qtbot.wait(200)

    assert window._flow_layout.count() == 2

    window.search_by_tag(tag.id)
    qtbot.wait(200)

    assert window._flow_layout.count() == 1
    assert window._flow_layout.itemAt(0).widget()._pattern_id == p1.id

    window.close()


# -- Drop target integration tests --


def test_import_dialog_has_drop_target(qtbot, db):
    """ImportDialog should have an _image_drop_target attribute of type ImageDropTarget."""
    dialog = ImportDialog(db=db)
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)

    assert hasattr(dialog, "_image_drop_target")
    assert isinstance(dialog._image_drop_target, ImageDropTarget)


def test_import_dialog_no_attach_button(qtbot, db):
    """ImportDialog should not have an _attach_image_button attribute."""
    dialog = ImportDialog(db=db)
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)

    assert not hasattr(dialog, "_attach_image_button")


def test_edit_dialog_has_drop_target(qtbot, db):
    """EditDialog should have an _image_drop_target attribute of type ImageDropTarget."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3)
    dialog = EditDialog(pattern=pattern, db=db)
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)

    assert hasattr(dialog, "_image_drop_target")
    assert isinstance(dialog._image_drop_target, ImageDropTarget)


def test_edit_dialog_no_attach_button(qtbot, db):
    """EditDialog should not have an _attach_image_button attribute."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3)
    dialog = EditDialog(pattern=pattern, db=db)
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)

    assert not hasattr(dialog, "_attach_image_button")
