"""Tests for Task 1: Pattern delete functionality."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QMessageBox

from osu_gallery.db.database import GalleryDatabase
from osu_gallery.ui.main_window import MainWindow
from osu_gallery.ui.thumbnail_widget import _ThumbnailWidget

SAMPLE_OSU = """[General]
AudioFilename: test.mp3

[Difficulty]
CircleSize: 5
SliderMultiplier: 1.4
SliderTickRate: 1

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
    yield database
    database.close()


@pytest.fixture
def main_window_with_patterns(qtbot, db):
    """Create a MainWindow with three patterns loaded."""
    p1 = db.create_pattern(SAMPLE_OSU, object_count=3)
    p2 = db.create_pattern(SAMPLE_OSU, object_count=3)
    p3 = db.create_pattern(SAMPLE_OSU, object_count=3)

    window = MainWindow(db_path=db.db_path)
    qtbot.addWidget(window)
    qtbot.waitExposed(window)
    window.refresh()
    qtbot.wait(200)

    yield window, [p1, p2, p3]

    window.close()


def test_delete_pattern_from_context_menu(qtbot, main_window_with_patterns):
    """Verify delete action appears in the context menu of a thumbnail widget."""
    window, patterns = main_window_with_patterns

    flow_layout = window._flow_layout
    item = flow_layout.itemAt(0)
    thumbnail_widget = item.widget() if item else None
    assert thumbnail_widget is not None
    assert isinstance(thumbnail_widget, _ThumbnailWidget)

    menu = thumbnail_widget._build_menu()
    menu_actions = [action.text() for action in menu.actions()]

    assert any("Delete" in text for text in menu_actions), \
        "Context menu should contain a Delete action"
    assert any("Copy" in text for text in menu_actions), \
        "Context menu should contain a Copy action"


def test_delete_pattern_confirms_dialog(qtbot, main_window_with_patterns, monkeypatch):
    """Verify confirmation dialog shows when delete is requested."""
    window, patterns = main_window_with_patterns

    flow_layout = window._flow_layout
    item = flow_layout.itemAt(0)
    thumbnail_widget = item.widget() if item else None
    assert thumbnail_widget is not None

    confirmed = [None]

    def mock_question(*args, **kwargs):
        confirmed[0] = True
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", mock_question)

    thumbnail_widget._on_delete_requested()

    assert confirmed[0] is True, "Confirmation dialog should be shown"


def test_delete_pattern_removes_from_db_and_grid(qtbot, main_window_with_patterns, monkeypatch):
    """Verify pattern is removed from database and grid after confirmation."""
    window, patterns = main_window_with_patterns

    initial_count = len(window._db.get_all_patterns())
    assert initial_count == 3, f"Should start with 3 patterns, got {initial_count}"

    pattern_to_delete = patterns[0]
    pattern_to_delete_id = pattern_to_delete.id

    def mock_question(*args, **kwargs):
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", mock_question)

    window._db.delete_pattern(pattern_to_delete_id)

    pattern = window._db.get_pattern(pattern_to_delete_id)
    assert pattern is None, "Pattern should be removed from database after deletion"

    remaining_count = len(window._db.get_all_patterns())
    assert remaining_count == 2, f"Grid should have 2 patterns remaining, got {remaining_count}"


def test_delete_pattern_cancel(qtbot, main_window_with_patterns, monkeypatch):
    """Verify cancel aborts deletion — pattern remains in database and grid."""
    window, patterns = main_window_with_patterns

    flow_layout = window._flow_layout
    item = flow_layout.itemAt(0)
    thumbnail_widget = item.widget() if item else None
    assert thumbnail_widget is not None

    pattern_to_delete_id = patterns[0].id

    def mock_question(*args, **kwargs):
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", mock_question)

    thumbnail_widget._on_delete_requested()

    pattern = window._db.get_pattern(pattern_to_delete_id)
    assert pattern is not None, "Pattern should remain in database when user cancels"

    remaining_count = window._db.get_all_patterns().__len__()
    assert remaining_count == 3, f"Grid should still have 3 patterns, got {remaining_count}"


def test_delete_pattern_signal_emitted(qtbot, main_window_with_patterns, monkeypatch):
    """Verify pattern_deleted signal is emitted with correct pattern_id."""
    window, patterns = main_window_with_patterns

    flow_layout = window._flow_layout
    item = flow_layout.itemAt(0)
    thumbnail_widget = item.widget() if item else None
    assert thumbnail_widget is not None

    expected_id = thumbnail_widget._pattern_id

    deleted_ids = []

    def on_deleted(pid):
        deleted_ids.append(pid)

    def mock_question(*args, **kwargs):
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", mock_question)

    thumbnail_widget.pattern_deleted.connect(on_deleted)
    thumbnail_widget._on_delete_requested()

    assert len(deleted_ids) == 1
    assert deleted_ids[0] == expected_id


def test_delete_last_pattern_shows_empty_state(qtbot, main_window_with_patterns, monkeypatch):
    """Verify empty state is shown when all patterns are deleted."""
    window, patterns = main_window_with_patterns

    def mock_question(*args, **kwargs):
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", mock_question)

    for _ in range(len(patterns)):
        flow_layout = window._flow_layout
        item = flow_layout.itemAt(0)
        thumbnail_widget = item.widget() if item else None
        if thumbnail_widget is None:
            break
        thumbnail_widget._on_delete_requested()
        qtbot.wait(100)

    assert window._page_stack.currentWidget() is window._empty_state, \
        "Empty state should be shown when all patterns are deleted"
