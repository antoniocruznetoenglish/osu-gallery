"""Tests for Phase 7: click-to-expand preview pane."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QSplitter

from osu_gallery.db.database import GalleryDatabase
from osu_gallery.ui._preview_pane import _PreviewPane
from osu_gallery.ui.main_window import MainWindow
from osu_gallery.ui.thumbnail_widget import _ThumbnailWidget

SAMPLE_OSU = """[General]
AudioFilename: test.mp3

[Difficulty]
CircleSize: 5
SliderMultiplier: 1.4
SliderTickRate: 1

[Metadata]
Title:Test Song
Creator:TestMapper
Tags:slider circle_pattern

[HitObjects]
256,192,1,2,0,80,0
384,256,6,2,0,80,0,L|480:128,1,100
512,192,1,2,0,80,0
"""

CIRCLES_ONLY = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1,2,0,80,0
384,256,1,2,0,80,0
512,192,1,2,0,80,0
"""

WITH_COMBO_COLORS = """[General]
AudioFilename: test.mp3

[Colours]
Combo1Colour:255,0,0
Combo2Colour:0,255,0

[HitObjects]
256,192,1,2,0,0,0
384,256,6,2,0,1,0,L|480:128,1,100
512,192,1,2,0,0,0
"""


# -- Fixtures --


@pytest.fixture
def db(tmp_path):
    """Create a fresh database for each test."""
    db_path = tmp_path / "test.db"
    database = GalleryDatabase(db_path)
    yield database
    database.close()


@pytest.fixture
def window(db):
    """Create a MainWindow with a test database."""
    main_window = MainWindow(db_path=db.db_path)
    yield main_window
    main_window.close()


# -- PreviewPane unit tests --


def test_preview_pane_creation(db):
    """_PreviewPane can be created without errors."""
    pane = _PreviewPane(db=db)
    assert pane is not None
    assert pane.width() > 0
    pane.close()


def test_preview_pane_initially_empty(db):
    """_PreviewPane shows empty state on creation."""
    pane = _PreviewPane(db=db)
    assert pane._current_pattern_id is None
    assert pane._pixmap is None
    pane.close()


def test_preview_pane_load_pattern(db):
    """load_pattern renders a preview for a valid pattern."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3)
    pane = _PreviewPane(db=db)

    pane.load_pattern(pattern.id or 0)

    # Should have loaded the pattern
    assert pane._current_pattern_id == pattern.id
    assert pane._pixmap is not None
    assert not pane._pixmap.isNull()
    assert pane._osu_file is not None
    assert len(pane._osu_file.hit_objects) == 3

    pane.close()


def test_preview_pane_load_nonexistent_pattern(db):
    """load_pattern with invalid id shows error state."""
    pane = _PreviewPane(db=db)
    pane.load_pattern(99999)

    # Should have no pixmap since pattern wasn't found
    assert pane._pixmap is None

    pane.close()


def test_preview_pane_load_same_pattern_idempotent(db):
    """Loading the same pattern twice does not cause errors."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3)
    pane = _PreviewPane(db=db)

    pane.load_pattern(pattern.id or 0)
    pane.load_pattern(pattern.id or 0)

    labels = pane.findChildren(QLabel)
    preview_texts = [label.text() for label in labels]
    assert any("Objects: 3" in t for t in preview_texts)

    pane.close()


def test_preview_pane_displays_tags(db):
    """load_pattern shows tags attached to the pattern."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3)
    tag = db.create_tag("slider", "slider_type")
    db.add_tag_to_pattern(pattern.id, tag.id)

    pane = _PreviewPane(db=db)
    pane.load_pattern(pattern.id or 0)

    labels = pane.findChildren(QLabel)
    tag_names = [label.text() for label in labels]
    assert "slider" in tag_names

    pane.close()


def test_preview_pane_displays_combo_colors(db):
    """load_pattern shows combo color indicators when present."""
    pattern = db.create_pattern(WITH_COMBO_COLORS, object_count=3)
    pane = _PreviewPane(db=db)

    pane.load_pattern(pattern.id or 0)

    # Should have rendered successfully
    assert pane._pixmap is not None
    assert not pane._pixmap.isNull()
    assert len(pane._combo_colors) > 0

    pane.close()


def test_preview_pane_close_button(db):
    """Close button emits closed signal and resets to empty state."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3)
    pane = _PreviewPane(db=db)

    pane.load_pattern(pattern.id or 0)

    closed_received = []

    def on_closed() -> None:
        closed_received.append(True)

    pane.closed.connect(on_closed)

    close_buttons = pane.findChildren(QPushButton)
    close_btn = [b for b in close_buttons if b.text() == "Close"]
    assert len(close_btn) == 1

    close_btn[0].click()

    assert len(closed_received) == 1

    # Should be back to empty state
    assert pane._current_pattern_id is None
    assert pane._pixmap is None

    pane.close()


def test_preview_pane_copy_button(db):
    """Copy Code button copies pattern raw_code to clipboard."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3)
    pane = _PreviewPane(db=db)

    pane.load_pattern(pattern.id or 0)

    copy_buttons = pane.findChildren(QPushButton)
    copy_btn = [b for b in copy_buttons if b.text() == "Copy Code"]
    assert len(copy_btn) == 1

    copy_btn[0].click()

    clipboard = QApplication.clipboard()
    assert SAMPLE_OSU in clipboard.text()

    pane.close()


# -- MainWindow integration tests --


def test_main_window_has_splitter(window):
    """MainWindow uses a QSplitter for grid/preview layout."""
    assert window._splitter is not None
    assert isinstance(window._splitter, QSplitter)


def test_main_window_has_preview_pane(window):
    """MainWindow has a _PreviewPane instance."""
    assert window._preview_pane is not None
    assert isinstance(window._preview_pane, _PreviewPane)


def test_main_window_preview_pane_starts_collapsed(window):
    """Preview pane starts collapsed (zero width in splitter)."""
    sizes = window._splitter.sizes()
    assert len(sizes) >= 2
    assert sizes[1] == 0


def test_main_window_preview_shows_on_click(qtbot, db):
    """Clicking a thumbnail shows the preview pane."""
    db.create_pattern(SAMPLE_OSU, object_count=3)

    main_window = MainWindow(db_path=db.db_path)
    qtbot.addWidget(main_window)
    qtbot.waitExposed(main_window)

    main_window.refresh()
    qtbot.wait(200)

    assert main_window._flow_layout.count() == 1

    thumbnail = main_window._flow_layout.itemAt(0).widget()
    assert isinstance(thumbnail, _ThumbnailWidget)

    # Click the thumbnail
    qtbot.mouseClick(thumbnail, Qt.MouseButton.LeftButton)
    qtbot.wait(200)

    # Preview pane should now be visible
    sizes = main_window._splitter.sizes()
    assert sizes[1] > 0

    # Preview pane should have loaded the pattern
    assert main_window._preview_pane._current_pattern_id is not None
    assert main_window._preview_pane._pixmap is not None

    main_window.close()


def test_main_window_preview_closes(qtbot, db):
    """Closing the preview pane collapses the splitter."""
    db.create_pattern(SAMPLE_OSU, object_count=3)

    main_window = MainWindow(db_path=db.db_path)
    qtbot.addWidget(main_window)
    qtbot.waitExposed(main_window)

    main_window.refresh()
    qtbot.wait(200)

    thumbnail = main_window._flow_layout.itemAt(0).widget()
    qtbot.mouseClick(thumbnail, Qt.MouseButton.LeftButton)
    qtbot.wait(200)

    sizes = main_window._splitter.sizes()
    assert sizes[1] > 0

    # Click close button in preview pane
    close_buttons = main_window._preview_pane.findChildren(QPushButton)
    close_btn = [b for b in close_buttons if b.text() == "Close"]
    assert len(close_btn) == 1
    close_btn[0].click()
    qtbot.wait(100)

    sizes = main_window._splitter.sizes()
    assert sizes[1] == 0

    main_window.close()


def test_main_window_preview_displays_metadata(qtbot, db):
    """Preview pane shows object count, tags, and combo colors."""
    pattern = db.create_pattern(WITH_COMBO_COLORS, object_count=3)
    tag = db.create_tag("slider", "slider_type")
    db.add_tag_to_pattern(pattern.id, tag.id)

    main_window = MainWindow(db_path=db.db_path)
    qtbot.addWidget(main_window)
    qtbot.waitExposed(main_window)

    main_window.refresh()
    qtbot.wait(200)

    thumbnail = main_window._flow_layout.itemAt(0).widget()
    qtbot.mouseClick(thumbnail, Qt.MouseButton.LeftButton)
    qtbot.wait(200)

    # Preview pane should have loaded the pattern with tags
    assert main_window._preview_pane._current_pattern_id == pattern.id
    assert len(main_window._preview_pane._tags) == 1
    assert main_window._preview_pane._tags[0].name == "slider"

    main_window.close()


def test_main_window_preview_copy_code(qtbot, db):
    """Copy Code in preview pane copies pattern raw_code to clipboard."""
    db.create_pattern(SAMPLE_OSU, object_count=3)

    main_window = MainWindow(db_path=db.db_path)
    qtbot.addWidget(main_window)
    qtbot.waitExposed(main_window)

    main_window.refresh()
    qtbot.wait(200)

    thumbnail = main_window._flow_layout.itemAt(0).widget()
    qtbot.mouseClick(thumbnail, Qt.MouseButton.LeftButton)
    qtbot.wait(200)

    copy_buttons = main_window._preview_pane.findChildren(QPushButton)
    copy_btn = [b for b in copy_buttons if b.text() == "Copy Code"]
    assert len(copy_btn) == 1
    copy_btn[0].click()

    clipboard = QApplication.clipboard()
    assert SAMPLE_OSU in clipboard.text()

    main_window.close()


def test_main_window_switching_patterns(qtbot, db):
    """Clicking different thumbnails updates the preview pane."""
    db.create_pattern(CIRCLES_ONLY, object_count=3)
    db.create_pattern(SAMPLE_OSU, object_count=3)

    main_window = MainWindow(db_path=db.db_path)
    qtbot.addWidget(main_window)
    qtbot.waitExposed(main_window)

    main_window.refresh()
    qtbot.wait(200)

    assert main_window._flow_layout.count() == 2

    # Click first pattern
    thumb1 = main_window._flow_layout.itemAt(0).widget()
    qtbot.mouseClick(thumb1, Qt.MouseButton.LeftButton)
    qtbot.wait(200)

    assert main_window._preview_pane._current_pattern_id is not None
    first_id = main_window._preview_pane._current_pattern_id

    # Click second pattern
    thumb2 = main_window._flow_layout.itemAt(1).widget()
    qtbot.mouseClick(thumb2, Qt.MouseButton.LeftButton)
    qtbot.wait(200)

    # Should have switched to the second pattern
    assert main_window._preview_pane._current_pattern_id != first_id

    main_window.close()


def test_main_window_empty_state_still_works(db):
    """Empty state still displays when no patterns exist."""
    main_window = MainWindow(db_path=db.db_path)

    # The page stack should show the empty state (second widget)
    assert main_window._page_stack.currentWidget() == main_window._empty_state

    main_window.close()


def test_preview_pane_rendered_pixmap_not_null(db):
    """Preview pane renders a non-null pixmap for valid pattern."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3)
    pane = _PreviewPane(db=db)

    pane.load_pattern(pattern.id or 0)

    assert pane._pixmap is not None
    assert not pane._pixmap.isNull()
    assert pane._pixmap.width() > 0
    assert pane._pixmap.height() > 0

    pane.close()
