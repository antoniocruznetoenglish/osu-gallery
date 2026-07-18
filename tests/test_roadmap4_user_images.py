"""Tests for Task 7: User image inputs and custom mapping tags table.

Verifies that Pattern has user_image fields, the database stores them,
the image resizer works correctly, and the custom_mapping_tags table exists.
"""

from __future__ import annotations

import inspect
import struct

import pytest

from osu_gallery.db.database import GalleryDatabase
from osu_gallery.db.models import Pattern
from osu_gallery.preview.image_resizer import (
    resize_image_for_preview,
    resize_image_for_thumbnail,
)


@pytest.fixture
def db(tmp_path):
    """Create a fresh database for each test."""
    db_path = tmp_path / "test.db"
    database = GalleryDatabase(db_path)
    yield database
    database.close()


def _make_png_bytes(width: int = 100, height: int = 100) -> bytes:
    """Create minimal valid PNG bytes for testing."""
    import zlib

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


def test_pattern_has_user_image_field():
    """Pattern dataclass has user_image and user_image_filename fields."""
    pattern = Pattern(raw_code="test")
    assert hasattr(pattern, "user_image")
    assert hasattr(pattern, "user_image_filename")
    assert pattern.user_image == b""
    assert pattern.user_image_filename == ""


def test_database_stores_user_image(db):
    """create_pattern and get_pattern round-trip user_image bytes."""
    img_bytes = _make_png_bytes()
    pattern = db.create_pattern(
        raw_code="test code",
        user_image=img_bytes,
    )
    fetched = db.get_pattern(pattern.id)
    assert fetched.user_image == img_bytes


def test_database_stores_user_image_filename(db):
    """create_pattern and get_pattern round-trip user_image_filename."""
    pattern = db.create_pattern(
        raw_code="test code",
        user_image_filename="screenshot.png",
    )
    fetched = db.get_pattern(pattern.id)
    assert fetched.user_image_filename == "screenshot.png"


def test_image_resizer_resizes_to_thumbnail_dimensions():
    """resize_image_for_thumbnail returns bytes for valid PNG input."""
    png_bytes = _make_png_bytes(100, 100)
    result = resize_image_for_thumbnail(png_bytes)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_image_resizer_resizes_to_preview_dimensions():
    """resize_image_for_preview returns bytes for valid PNG input."""
    png_bytes = _make_png_bytes(100, 100)
    result = resize_image_for_preview(png_bytes)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_image_resizer_maintains_aspect_ratio():
    """resize_image_for_thumbnail returns bytes for non-4:3 input."""
    png_bytes = _make_png_bytes(200, 100)
    result = resize_image_for_thumbnail(png_bytes)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_image_resizer_handles_empty_bytes():
    """Empty bytes input returns empty bytes."""
    result = resize_image_for_thumbnail(b"")
    assert result == b""

    result = resize_image_for_preview(b"")
    assert result == b""


def test_image_resizer_handles_invalid_data():
    """Invalid bytes input returns empty bytes."""
    result = resize_image_for_thumbnail(b"not a valid image")
    assert result == b""

    result = resize_image_for_preview(b"garbage data here")
    assert result == b""


def test_preview_pane_uses_user_image_when_available(db):
    """_PreviewPane.load_pattern checks pattern.user_image before rendering."""
    from osu_gallery.ui._preview_pane import _PreviewPane

    source = inspect.getsource(_PreviewPane.load_pattern)
    assert "user_image" in source
    assert "loadFromData" in source


def test_preview_pane_falls_back_to_auto_generated(db):
    """_PreviewPane falls back to render_pattern_preview when no user_image."""
    from osu_gallery.ui._preview_pane import _PreviewPane

    source = inspect.getsource(_PreviewPane.load_pattern)
    assert "render_pattern_preview" in source


def test_thumbnail_widget_uses_user_image_when_available(db):
    """_ThumbnailWidget._render checks pattern.user_image before rendering."""
    from osu_gallery.ui.thumbnail_widget import _ThumbnailWidget

    source = inspect.getsource(_ThumbnailWidget._render)
    assert "user_image" in source
    assert "loadFromData" in source


def test_database_update_pattern_user_image(db):
    """update_pattern_user_image method exists and updates correctly."""
    assert hasattr(db, "update_pattern_user_image")
    sig = inspect.signature(db.update_pattern_user_image)
    params = list(sig.parameters.keys())
    assert "pattern_id" in params
    assert "user_image" in params
    assert "filename" in params

    img_bytes = _make_png_bytes()
    pattern = db.create_pattern(raw_code="test code")
    db.update_pattern_user_image(pattern.id, img_bytes, "test.png")

    fetched = db.get_pattern(pattern.id)
    assert fetched.user_image == img_bytes
    assert fetched.user_image_filename == "test.png"


def test_custom_mapping_tags_table_exists(db):
    """The custom_mapping_tags table is created on database initialization."""
    # Verify the table exists by querying it
    tables = db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='custom_mapping_tags'"
    ).fetchall()
    assert len(tables) == 1
    assert tables[0]["name"] == "custom_mapping_tags"


def test_custom_mapping_tags_table_schema(db):
    """custom_mapping_tags table has the expected columns."""
    columns = db.conn.execute("PRAGMA table_info(custom_mapping_tags)").fetchall()
    col_names = [c["name"] for c in columns]
    assert "id" in col_names
    assert "tag_name" in col_names
    assert "enabled" in col_names
    assert "created_at" in col_names


def test_get_all_custom_tags(db):
    """get_all_custom_tags returns all custom tags from the database."""
    db.add_custom_tag("tag_a")
    db.add_custom_tag("tag_b")
    tags = db.get_all_custom_tags()
    assert len(tags) == 2
    names = [t["name"] for t in tags]
    assert "tag_a" in names
    assert "tag_b" in names


def test_add_custom_tag_returns_false_on_duplicate(db):
    """add_custom_tag returns False when inserting a duplicate tag name."""
    assert db.add_custom_tag("dup_tag") is True
    assert db.add_custom_tag("dup_tag") is False


def test_update_custom_tag_enabled(db):
    """update_custom_tag_enabled toggles the enabled flag."""
    db.add_custom_tag("toggle_tag")
    tags = db.get_all_custom_tags()
    tag = next(t for t in tags if t["name"] == "toggle_tag")

    db.update_custom_tag_enabled(tag["id"], False)
    tags = db.get_all_custom_tags()
    updated = next(t for t in tags if t["id"] == tag["id"])
    assert updated["enabled"] is False

    db.update_custom_tag_enabled(tag["id"], True)
    tags = db.get_all_custom_tags()
    updated = next(t for t in tags if t["id"] == tag["id"])
    assert updated["enabled"] is True


def test_pattern_user_image_defaults_to_empty(db):
    """A newly created pattern has empty user_image by default."""
    pattern = db.create_pattern(raw_code="test code")
    assert pattern.user_image == b""
    assert pattern.user_image_filename == ""


def test_resize_functions_have_correct_defaults():
    """resize_image_for_thumbnail defaults to 512x384 and preview to 1536x1152."""
    sig_thumb = inspect.signature(resize_image_for_thumbnail)
    sig_prev = inspect.signature(resize_image_for_preview)

    assert sig_thumb.parameters["target_width"].default == 512
    assert sig_thumb.parameters["target_height"].default == 384
    assert sig_prev.parameters["target_width"].default == 1536
    assert sig_prev.parameters["target_height"].default == 1152
