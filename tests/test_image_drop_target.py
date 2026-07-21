"""Tests for the ImageDropTarget widget.

Tests the validation logic of ImageDropTarget by directly calling
_validate_mime_data with mock QMimeData.
"""

from pathlib import Path

from PySide6.QtCore import QMimeData, QUrl

from osu_gallery.ui._image_drop_target import ImageDropTarget


def _make_mime_data(urls: list[QUrl]) -> QMimeData:
    """Create a QMimeData with the given URLs.

    Args:
        urls: List of QUrl objects to add to the mime data.

    Returns:
        A QMimeData instance with the given URLs.
    """
    mime_data = QMimeData()
    mime_data.setUrls(urls)
    return mime_data


def test_drop_target_accepts_valid_png(qtbot, tmp_path):
    """Dropping a valid .png file should emit image_selected and update label."""
    png_file = tmp_path / "test.png"
    png_file.write_bytes(b"fake png data")

    drop_target = ImageDropTarget()
    qtbot.addWidget(drop_target)

    received_paths: list[str] = []
    drop_target.image_selected.connect(received_paths.append)

    url = QUrl.fromLocalFile(str(png_file))
    mime_data = _make_mime_data([url])

    result = drop_target._validate_mime_data(mime_data)
    assert result["valid"] is True

    drop_target._label.setText(result["path"].name)
    drop_target.image_selected.emit(result["file_path"])

    assert len(received_paths) == 1
    assert Path(received_paths[0]).name == "test.png"
    assert "test.png" in drop_target._label.text()


def test_drop_target_accepts_valid_jpg(qtbot, tmp_path):
    """Dropping a valid .jpg file should emit image_selected and update label."""
    jpg_file = tmp_path / "photo.jpg"
    jpg_file.write_bytes(b"fake jpg data")

    drop_target = ImageDropTarget()
    qtbot.addWidget(drop_target)

    received_paths: list[str] = []
    drop_target.image_selected.connect(received_paths.append)

    url = QUrl.fromLocalFile(str(jpg_file))
    mime_data = _make_mime_data([url])

    result = drop_target._validate_mime_data(mime_data)
    assert result["valid"] is True

    drop_target._label.setText(result["path"].name)
    drop_target.image_selected.emit(result["file_path"])

    assert len(received_paths) == 1
    assert Path(received_paths[0]).name == "photo.jpg"
    assert "photo.jpg" in drop_target._label.text()


def test_drop_target_rejects_unsupported_extension(qtbot, tmp_path):
    """Dropping a .txt file should be rejected with an error message."""
    txt_file = tmp_path / "readme.txt"
    txt_file.write_text("not an image")

    drop_target = ImageDropTarget()
    qtbot.addWidget(drop_target)

    url = QUrl.fromLocalFile(str(txt_file))
    mime_data = _make_mime_data([url])

    result = drop_target._validate_mime_data(mime_data)
    assert result["valid"] is False

    drop_target._show_error(result["error"])

    error_text = drop_target._label.text().lower()
    assert "unsupported" in error_text or "not a valid" in error_text or "only local" in error_text


def test_drop_target_rejects_directory(qtbot, tmp_path):
    """Dropping a directory should be rejected."""
    drop_target = ImageDropTarget()
    qtbot.addWidget(drop_target)

    url = QUrl.fromLocalFile(str(tmp_path))
    mime_data = _make_mime_data([url])

    result = drop_target._validate_mime_data(mime_data)
    assert result["valid"] is False

    drop_target._show_error(result["error"])

    error_text = drop_target._label.text().lower()
    assert "directory" in error_text or "not a valid" in error_text or "unsupported" in error_text


def test_drop_target_rejects_multiple_files(qtbot, tmp_path):
    """Dropping multiple files should be rejected."""
    file1 = tmp_path / "a.png"
    file2 = tmp_path / "b.png"
    file1.write_bytes(b"fake")
    file2.write_bytes(b"fake")

    drop_target = ImageDropTarget()
    qtbot.addWidget(drop_target)

    urls = [
        QUrl.fromLocalFile(str(file1)),
        QUrl.fromLocalFile(str(file2)),
    ]
    mime_data = _make_mime_data(urls)

    result = drop_target._validate_mime_data(mime_data)
    assert result["valid"] is False

    drop_target._show_error(result["error"])

    error_text = drop_target._label.text().lower()
    assert "one" in error_text or "exactly" in error_text


def test_drop_target_rejects_remote_url(qtbot):
    """Dropping a remote URL should be rejected."""
    drop_target = ImageDropTarget()
    qtbot.addWidget(drop_target)

    url = QUrl("https://example.com/image.png")
    mime_data = _make_mime_data([url])

    result = drop_target._validate_mime_data(mime_data)
    assert result["valid"] is False

    drop_target._show_error(result["error"])

    error_text = drop_target._label.text().lower()
    assert "local" in error_text


def test_drop_target_case_insensitive_extension(qtbot, tmp_path):
    """Dropping a .PNG file (uppercase) should be accepted."""
    png_file = tmp_path / "test.PNG"
    png_file.write_bytes(b"fake png data")

    drop_target = ImageDropTarget()
    qtbot.addWidget(drop_target)

    received_paths: list[str] = []
    drop_target.image_selected.connect(received_paths.append)

    url = QUrl.fromLocalFile(str(png_file))
    mime_data = _make_mime_data([url])

    result = drop_target._validate_mime_data(mime_data)
    assert result["valid"] is True

    drop_target._label.setText(result["path"].name)
    drop_target.image_selected.emit(result["file_path"])

    assert len(received_paths) == 1
    assert Path(received_paths[0]).name == "test.PNG"


def test_drop_target_rejects_empty_mime_data(qtbot):
    """Dropping with no URLs in mime data should be rejected."""
    drop_target = ImageDropTarget()
    qtbot.addWidget(drop_target)

    mime_data = QMimeData()

    result = drop_target._validate_mime_data(mime_data)
    assert result["valid"] is False

    drop_target._show_error(result["error"])

    error_text = drop_target._label.text().lower()
    assert "one" in error_text or "exactly" in error_text
