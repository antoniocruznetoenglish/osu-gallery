"""Tests for the ImageDropTarget widget — actual Qt drag/drop event behavior.

Exercises real ``dragEnterEvent`` / ``dragMoveEvent`` / ``dropEvent`` through
the widget rather than calling ``_validate_mime_data`` / ``_show_error``
directly.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMimeData, QPoint, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication

from osu_gallery.ui._image_drop_target import ImageDropTarget

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mime_data(urls: list[QUrl]) -> QMimeData:
    mime_data = QMimeData()
    mime_data.setUrls(urls)
    return mime_data


def _make_drag_enter_event(urls: list[QUrl]) -> QDragEnterEvent:
    mime_data = _make_mime_data(urls)
    event = QDragEnterEvent(
        QPoint(0, 0),
        Qt.DropAction.CopyAction,
        mime_data,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    event._mime_data = mime_data
    return event


def _make_drop_event(urls: list[QUrl]) -> QDropEvent:
    mime_data = _make_mime_data(urls)
    event = QDropEvent(
        QPoint(0, 0),
        Qt.DropAction.CopyAction,
        mime_data,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    event._mime_data = mime_data
    return event


# ---------------------------------------------------------------------------
# Tests — unsupported extension (.txt)
# ---------------------------------------------------------------------------

def test_txt_extension_drag_enter_accepted():
    """dragEnterEvent should accept URL-bearing events (including .txt)."""
    drop_target = ImageDropTarget()
    url = QUrl.fromLocalFile("C:/readme.txt")
    event = _make_drag_enter_event([url])
    QApplication.sendEvent(drop_target, event)
    assert event.isAccepted() is True


def test_txt_extension_drop_rejected(qtbot, tmp_path):
    """Dropping a .txt file shows an error on the label and does NOT emit
    ``image_selected``.
    """
    txt_file = tmp_path / "readme.txt"
    txt_file.write_text("not an image")

    drop_target = ImageDropTarget()
    qtbot.addWidget(drop_target)

    received_paths: list[str] = []
    drop_target.image_selected.connect(received_paths.append)

    url = QUrl.fromLocalFile(str(txt_file))
    event = _make_drop_event([url])
    drop_target.dropEvent(event)

    assert len(received_paths) == 0, (
        "image_selected must NOT be emitted for unsupported extensions"
    )
    error_text = drop_target._label.text().lower()
    assert "unsupported" in error_text or "not a valid" in error_text


# ---------------------------------------------------------------------------
# Tests — directory
# ---------------------------------------------------------------------------

def test_directory_drag_enter_accepted():
    """dragEnterEvent should accept URL-bearing events (including directories)."""
    drop_target = ImageDropTarget()
    url = QUrl.fromLocalFile(str(Path.home()))
    event = _make_drag_enter_event([url])
    QApplication.sendEvent(drop_target, event)
    assert event.isAccepted() is True


def test_directory_drop_rejected(qtbot, tmp_path):
    """Dropping a directory shows an error and does NOT emit ``image_selected``."""
    drop_target = ImageDropTarget()
    qtbot.addWidget(drop_target)

    received_paths: list[str] = []
    drop_target.image_selected.connect(received_paths.append)

    url = QUrl.fromLocalFile(str(tmp_path))
    event = _make_drop_event([url])
    drop_target.dropEvent(event)

    assert len(received_paths) == 0, (
        "image_selected must NOT be emitted for directories"
    )
    error_text = drop_target._label.text().lower()
    assert "directory" in error_text or "not a valid" in error_text


# ---------------------------------------------------------------------------
# Tests — multiple files
# ---------------------------------------------------------------------------

def test_multiple_files_drag_enter_accepted():
    """dragEnterEvent should accept URL-bearing events (including multiple URLs)."""
    drop_target = ImageDropTarget()
    urls = [
        QUrl.fromLocalFile("C:/a.png"),
        QUrl.fromLocalFile("C:/b.png"),
    ]
    event = _make_drag_enter_event(urls)
    QApplication.sendEvent(drop_target, event)
    assert event.isAccepted() is True


def test_multiple_files_drop_rejected(qtbot, tmp_path):
    """Dropping two files shows an error and does NOT emit ``image_selected``."""
    file1 = tmp_path / "a.png"
    file2 = tmp_path / "b.png"
    file1.write_bytes(b"fake")
    file2.write_bytes(b"fake")

    drop_target = ImageDropTarget()
    qtbot.addWidget(drop_target)

    received_paths: list[str] = []
    drop_target.image_selected.connect(received_paths.append)

    urls = [
        QUrl.fromLocalFile(str(file1)),
        QUrl.fromLocalFile(str(file2)),
    ]
    event = _make_drop_event(urls)
    drop_target.dropEvent(event)

    assert len(received_paths) == 0, (
        "image_selected must NOT be emitted for multiple files"
    )
    error_text = drop_target._label.text().lower()
    assert "one" in error_text or "exactly" in error_text


# ---------------------------------------------------------------------------
# Tests — remote URL
# ---------------------------------------------------------------------------

def test_remote_url_drag_enter_accepted():
    """dragEnterEvent should accept URL-bearing events (including https://)."""
    drop_target = ImageDropTarget()
    url = QUrl("https://example.com/image.png")
    event = _make_drag_enter_event([url])
    QApplication.sendEvent(drop_target, event)
    assert event.isAccepted() is True


def test_remote_url_drop_rejected(qtbot):
    """Dropping an ``https://`` URL shows an error and does NOT emit
    ``image_selected``.
    """
    drop_target = ImageDropTarget()
    qtbot.addWidget(drop_target)

    received_paths: list[str] = []
    drop_target.image_selected.connect(received_paths.append)

    url = QUrl("https://example.com/image.png")
    event = _make_drop_event([url])
    drop_target.dropEvent(event)

    assert len(received_paths) == 0, (
        "image_selected must NOT be emitted for remote URLs"
    )
    error_text = drop_target._label.text().lower()
    assert "local" in error_text


# ---------------------------------------------------------------------------
# Tests — valid local image
# ---------------------------------------------------------------------------

def test_valid_png_drag_enter_accepted(qtbot, tmp_path):
    """dragEnterEvent with a single valid image URL is accepted."""
    png_file = tmp_path / "test.png"
    png_file.write_bytes(b"fake png data")

    drop_target = ImageDropTarget()
    qtbot.addWidget(drop_target)

    url = QUrl.fromLocalFile(str(png_file))
    event = _make_drag_enter_event([url])
    QApplication.sendEvent(drop_target, event)
    assert event.isAccepted() is True


def test_valid_png_drop_emits_signal(qtbot, tmp_path):
    """Dropping a valid ``.png`` file emits ``image_selected`` exactly once and
    shows the basename on the label.
    """
    png_file = tmp_path / "test.png"
    png_file.write_bytes(b"fake png data")

    drop_target = ImageDropTarget()
    qtbot.addWidget(drop_target)

    received_paths: list[str] = []
    drop_target.image_selected.connect(received_paths.append)

    url = QUrl.fromLocalFile(str(png_file))
    event = _make_drop_event([url])
    drop_target.dropEvent(event)

    assert len(received_paths) == 1, (
        "image_selected must be emitted exactly once"
    )
    assert Path(received_paths[0]).name == "test.png"
    assert "test.png" in drop_target._label.text()
