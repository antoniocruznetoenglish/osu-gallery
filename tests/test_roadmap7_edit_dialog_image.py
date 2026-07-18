"""Tests for EditDialog screenshot attach/replace functionality."""

from __future__ import annotations

import os
import struct
import tempfile
import zlib

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

from osu_gallery.db.database import GalleryDatabase
from osu_gallery.ui.edit_dialog import EditDialog

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


def _make_png_bytes(width: int = 100, height: int = 100) -> bytes:
    """Create minimal valid PNG bytes for testing."""
    def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        chunk = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + chunk + crc

    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw_rows = b""
    for _ in range(height):
        raw_rows += b"\x00" + b"\xff\xff\xff" * width  # filter byte + RGB
    compressed = zlib.compress(raw_rows)

    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(b"IHDR", ihdr_data)
    png += _png_chunk(b"IDAT", compressed)
    png += _png_chunk(b"IEND", b"")
    return png


@pytest.fixture
def db(tmp_path):
    """Create a fresh database for each test."""
    db_path = tmp_path / "test.db"
    database = GalleryDatabase(db_path)
    yield database


def test_edit_dialog_has_attach_image_button(qtbot, db):
    """EditDialog has an attach image button that is wired to _on_attach_image."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3)
    dialog = EditDialog(pattern=pattern, db=db)
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)

    assert hasattr(dialog, "_attach_image_button")
    assert dialog._attach_image_button.text() == "Attach Screenshot"

    assert hasattr(dialog, "_image_filename_label")
    assert hasattr(dialog, "_on_attach_image")
    assert callable(dialog._on_attach_image)
    dialog.close()


def test_edit_dialog_shows_current_image_status(qtbot, db):
    """EditDialog filename label reflects whether the pattern has an image."""
    pattern_no_image = db.create_pattern(SAMPLE_OSU, object_count=3)
    dialog_no_image = EditDialog(pattern=pattern_no_image, db=db)
    qtbot.addWidget(dialog_no_image)
    qtbot.waitExposed(dialog_no_image)

    assert "No screenshot attached" in dialog_no_image._image_filename_label.text()
    dialog_no_image.close()

    img_bytes = _make_png_bytes()
    pattern_with_image = db.create_pattern(
        SAMPLE_OSU, object_count=3, user_image=img_bytes, user_image_filename="test.png"
    )
    dialog_with_image = EditDialog(pattern=pattern_with_image, db=db)
    qtbot.addWidget(dialog_with_image)
    qtbot.waitExposed(dialog_with_image)

    assert "Screenshot attached" in dialog_with_image._image_filename_label.text()
    assert "test.png" in dialog_with_image._image_filename_label.text()
    dialog_with_image.close()


def test_edit_dialog_replaces_existing_image(qtbot, db):
    """Attaching a new image to a pattern with an existing image replaces it."""
    original_img = _make_png_bytes(100, 100)
    pattern = db.create_pattern(
        SAMPLE_OSU, object_count=3, user_image=original_img, user_image_filename="old.png"
    )

    new_img = _make_png_bytes(200, 200)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(new_img)
        tmp_path = tmp.name

    try:
        dialog = EditDialog(pattern=pattern, db=db)
        qtbot.addWidget(dialog)
        qtbot.waitExposed(dialog)

        dialog._selected_image_path = tmp_path
        dialog._image_filename_label.setText(tmp_path)

        save_button = dialog._save_button
        qtbot.mouseClick(save_button, Qt.MouseButton.LeftButton)
        qtbot.wait(200)

        assert dialog.result() == QDialog.Accepted

        updated = db.get_pattern(pattern.id)
        assert updated.user_image != original_img
        assert len(updated.user_image) > 0
        assert updated.user_image_filename != ""
    finally:
        os.unlink(tmp_path)
        dialog.close()
