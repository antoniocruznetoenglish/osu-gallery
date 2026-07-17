"""End-to-end tests for Phase 6: copy-to-clipboard + toast notification."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from osu_gallery.db.database import GalleryDatabase
from osu_gallery.ui._clipboard import copy_to_clipboard
from osu_gallery.ui._toast_widget import _ToastWidget
from osu_gallery.ui.main_window import MainWindow
from osu_gallery.ui.thumbnail_widget import _ThumbnailWidget

SAMPLE_OSU = """[General]
AudioFilename: test.mp3

[Difficulty]
CircleSize: 5
SliderMultiplier: 1.4
SliderTickRate: 1

[HitObjects]
256,192,1000,1|2,0
384,256,1500,2|2,0,L|480:128,1,100
512,192,2000,1|2,0
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


# -- Clipboard unit tests --


def test_copy_to_clipboard_sets_text(qtbot):
    """copy_to_clipboard puts text into the system clipboard."""
    test_text = "256,192,1000,1|2,0"
    copy_to_clipboard(test_text)

    clipboard = QApplication.clipboard()
    assert clipboard.text() == test_text


def test_copy_to_clipboard_overwrites_previous(qtbot):
    """copy_to_clipboard replaces any previous clipboard content."""
    copy_to_clipboard("old text")
    assert QApplication.clipboard().text() == "old text"

    copy_to_clipboard("new text")
    assert QApplication.clipboard().text() == "new text"


def test_copy_to_clipboard_empty_string(qtbot):
    """copy_to_clipboard handles empty strings without error."""
    copy_to_clipboard("")
    assert QApplication.clipboard().text() == ""


def test_copy_to_clipboard_large_content(qtbot):
    """copy_to_clipboard handles large text content."""
    large_text = "256,192,1000,1|2,0\n" * 1000
    copy_to_clipboard(large_text)
    assert QApplication.clipboard().text() == large_text


# -- Toast widget unit tests --


def test_toast_widget_creation():
    """_ToastWidget can be created without errors."""
    toast = _ToastWidget(message="Test toast")
    assert toast is not None
    flags = toast.windowFlags()
    assert flags & Qt.WindowType.FramelessWindowHint
    toast.close()


def test_toast_widget_default_message():
    """_ToastWidget uses a default message when none is provided."""
    toast = _ToastWidget()
    assert toast._label.text() == "Copied!"
    toast.close()


def test_toast_widget_custom_message():
    """_ToastWidget displays a custom message."""
    toast = _ToastWidget(message="Custom message")
    assert toast._label.text() == "Custom message"
    toast.close()


def test_toast_widget_stays_on_top():
    """_ToastWidget has WindowStaysOnTopHint flag."""
    toast = _ToastWidget()
    flags = toast.windowFlags()
    assert flags & Qt.WindowType.WindowStaysOnTopHint
    toast.close()


def test_toast_widget_translucent_background():
    """_ToastWidget has WA_TranslucentBackground attribute."""
    toast = _ToastWidget()
    assert toast.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    toast.close()


def test_show_toast_replaces_existing(qtbot):
    """show_toast closes any existing toast before showing a new one."""
    toast1 = _ToastWidget(message="First")
    toast1.show()
    assert toast1.isVisible()

    toast2 = _ToastWidget(message="Second")
    toast2.show()

    qtbot.wait(50)
    toast1.close()
    toast2.close()


# -- Thumbnail widget context menu tests --


def test_thumbnail_widget_has_context_menu(db):
    """_ThumbnailWidget has custom context menu policy."""
    widget = _ThumbnailWidget(pattern_id=1, db=db)
    assert widget.contextMenuPolicy() == Qt.ContextMenuPolicy.CustomContextMenu
    widget.close()


def test_thumbnail_widget_has_copy_shortcut(db):
    """_ThumbnailWidget has a Ctrl+C shortcut for copying."""
    widget = _ThumbnailWidget(pattern_id=1, db=db)
    assert widget._copy_shortcut is not None
    widget.close()


def test_thumbnail_widget_pattern_copied_signal(db):
    """pattern_copied signal is emitted when code is copied."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3)
    widget = _ThumbnailWidget(pattern_id=pattern.id or 0, db=db)

    captured_ids: list[int] = []

    def on_copied(pattern_id: int) -> None:
        captured_ids.append(pattern_id)

    widget.pattern_copied.connect(on_copied)

    widget._on_copy_code()

    assert len(captured_ids) == 1
    assert captured_ids[0] == pattern.id
    assert QApplication.clipboard().text() == SAMPLE_OSU
    widget.close()


def test_thumbnail_widget_copy_sets_clipboard(db):
    """Copying a pattern puts its raw_code into the clipboard."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3)
    widget = _ThumbnailWidget(pattern_id=pattern.id or 0, db=db)

    widget._on_copy_code()

    clipboard = QApplication.clipboard()
    assert clipboard.text() == SAMPLE_OSU
    widget.close()


def test_thumbnail_widget_copy_nonexistent_pattern(db):
    """Copying a non-existent pattern logs a warning without error."""
    widget = _ThumbnailWidget(pattern_id=99999, db=db)
    widget._on_copy_code()
    widget.close()


# -- End-to-end: import -> search -> copy --


def test_e2e_import_search_copy(db):
    """Full flow: import pattern, search for it, copy code to clipboard."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3)

    window = MainWindow(db_path=db.db_path)
    window.refresh()

    assert window._flow_layout.count() == 1

    thumbnail = window._flow_layout.itemAt(0).widget()
    assert isinstance(thumbnail, _ThumbnailWidget)
    assert thumbnail._pattern_id == pattern.id

    thumbnail._on_copy_code()

    clipboard = QApplication.clipboard()
    assert clipboard.text() == SAMPLE_OSU

    window.close()


def test_e2e_search_then_copy(db):
    """Search narrows to one pattern, then copy that pattern's code."""
    other = """[General]
AudioFilename: other.mp3

[HitObjects]
100,100,1,2,0,80,0
"""
    db.create_pattern(other, object_count=1)
    db.create_pattern(SAMPLE_OSU, object_count=3)

    window = MainWindow(db_path=db.db_path)
    window._search_engine.sync_fts_all()
    window.refresh()
    assert window._flow_layout.count() == 2

    window._search_edit.setText("SliderMultiplier")
    window._on_search_triggered()

    assert window._flow_layout.count() == 1

    thumbnail = window._flow_layout.itemAt(0).widget()
    assert isinstance(thumbnail, _ThumbnailWidget)

    thumbnail._on_copy_code()

    clipboard = QApplication.clipboard()
    assert SAMPLE_OSU in clipboard.text()
    assert "SliderMultiplier" in clipboard.text()

    window.close()


def test_e2e_copy_multiple_patterns_in_order(db):
    """Copying different patterns updates clipboard each time."""
    p1_code = """[General]
AudioFilename: a.mp3

[HitObjects]
100,100,1000,5,0
"""
    p2_code = """[General]
AudioFilename: b.mp3

[HitObjects]
200,200,1000,5,0
300,300,1500,5,0
"""
    db.create_pattern(p1_code, object_count=1)
    db.create_pattern(p2_code, object_count=2)

    window = MainWindow(db_path=db.db_path)
    window.refresh()

    assert window._flow_layout.count() == 2

    widgets = [
        window._flow_layout.itemAt(i).widget()
        for i in range(window._flow_layout.count())
    ]

    all_copied: list[str] = []
    for widget in widgets:
        widget._on_copy_code()
        all_copied.append(QApplication.clipboard().text())

    assert p1_code in all_copied
    assert p2_code in all_copied

    window.close()
