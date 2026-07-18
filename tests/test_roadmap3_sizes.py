"""Tests for Task 1: Size overhaul."""

from __future__ import annotations

from osu_gallery._constants import (
    PREVIEW_HEIGHT,
    PREVIEW_PANE_MAX_WIDTH,
    PREVIEW_PANE_WIDTH,
    SPLITTER_PREVIEW_DEFAULT_WIDTH,
    THUMBNAIL_HEIGHT,
    THUMBNAIL_WIDGET_MIN_HEIGHT,
    THUMBNAIL_WIDGET_MIN_WIDTH,
    THUMBNAIL_WIDTH,
)
from osu_gallery.preview.thumbnail_renderer import render_pattern_preview, render_thumbnail


def test_thumbnail_default_size_is_512x384():
    """Thumbnails are now rendered at 512x384."""
    assert THUMBNAIL_WIDTH == 512
    assert THUMBNAIL_HEIGHT == 384


def test_preview_default_height_is_1152():
    """Preview height is 1152."""
    assert PREVIEW_HEIGHT == 1152


def test_preview_pane_width_is_900():
    """Preview pane width increased to 900."""
    assert PREVIEW_PANE_WIDTH == 900


def test_preview_pane_max_width_is_1000():
    """Preview pane max width increased to 1000."""
    assert PREVIEW_PANE_MAX_WIDTH == 1000


def test_splitter_default_width_is_900():
    """Splitter default preview width is 900."""
    assert SPLITTER_PREVIEW_DEFAULT_WIDTH == 900


def test_thumbnail_widget_min_size():
    """Thumbnail widget minimum size matches render size."""
    assert THUMBNAIL_WIDGET_MIN_WIDTH == 220
    assert THUMBNAIL_WIDGET_MIN_HEIGHT == 165


def test_render_thumbnail_returns_correct_size():
    """render_thumbnail returns a pixmap at the requested size."""
    from osu_gallery.parser.osu_file import parse_osu_file
    content = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1000,5,0
"""
    osu = parse_osu_file(content)
    pixmap = render_thumbnail(osu, width=512, height=384)
    assert pixmap.width() == 512
    assert pixmap.height() == 384


def test_render_pattern_preview_returns_correct_size():
    """render_pattern_preview returns a pixmap at the requested size."""
    from osu_gallery.parser.osu_file import parse_osu_file
    content = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1000,5,0
"""
    osu = parse_osu_file(content)
    pixmap = render_pattern_preview(osu, width=1024, height=768)
    assert pixmap.width() == 1024
    assert pixmap.height() == 768
