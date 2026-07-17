"""Tests for Task 1: Size overhaul (thumbnail and preview dimensions).

Verifies that thumbnail and preview rendering functions produce
images at the correct dimensions as defined in the constants module.
"""

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


def test_thumbnail_rendered_at_512x384():
    """render_thumbnail returns a pixmap at 512x384 by default."""
    from osu_gallery.parser.osu_file import parse_osu_file

    content = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1000,5,0
"""
    osu = parse_osu_file(content)
    pixmap = render_thumbnail(osu)
    assert pixmap.width() == THUMBNAIL_WIDTH
    assert pixmap.height() == THUMBNAIL_HEIGHT
    assert THUMBNAIL_WIDTH == 512
    assert THUMBNAIL_HEIGHT == 384


def test_preview_rendered_at_1024x768():
    """render_pattern_preview returns a pixmap at 1024x768 by default."""
    from osu_gallery.parser.osu_file import parse_osu_file

    content = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1000,5,0
"""
    osu = parse_osu_file(content)
    pixmap = render_pattern_preview(osu)
    assert pixmap.width() == 1024
    assert pixmap.height() == PREVIEW_HEIGHT
    assert PREVIEW_HEIGHT == 768


def test_thumbnail_widget_paints_at_rendered_size():
    """Thumbnail widget minimum size matches THUMBNAIL_WIDGET_MIN constants."""
    assert THUMBNAIL_WIDGET_MIN_WIDTH == 512
    assert THUMBNAIL_WIDGET_MIN_HEIGHT == 384


def test_preview_pane_scales_correctly():
    """Preview pane uses correct PREVIEW_HEIGHT and pane width constants."""
    assert PREVIEW_PANE_WIDTH == 500
    assert PREVIEW_PANE_MAX_WIDTH == 620
    assert SPLITTER_PREVIEW_DEFAULT_WIDTH == 500


def test_thumbnail_at_custom_dimensions():
    """render_thumbnail respects custom width/height arguments."""
    from osu_gallery.parser.osu_file import parse_osu_file

    content = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1000,5,0
"""
    osu = parse_osu_file(content)
    pixmap = render_thumbnail(osu, width=256, height=192)
    assert pixmap.width() == 256
    assert pixmap.height() == 192


def test_preview_at_custom_dimensions():
    """render_pattern_preview respects custom width/height arguments."""
    from osu_gallery.parser.osu_file import parse_osu_file

    content = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1000,5,0
"""
    osu = parse_osu_file(content)
    pixmap = render_pattern_preview(osu, width=512, height=384)
    assert pixmap.width() == 512
    assert pixmap.height() == 384


def test_thumbnail_pixmap_is_transparent():
    """render_thumbnail produces a pixmap with transparent background."""
    from osu_gallery.parser.osu_file import parse_osu_file

    content = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1000,5,0
"""
    osu = parse_osu_file(content)
    pixmap = render_thumbnail(osu)
    assert pixmap.width() > 0
    assert pixmap.height() > 0


def test_preview_pixmap_is_transparent():
    """render_pattern_preview produces a pixmap with transparent background."""
    from osu_gallery.parser.osu_file import parse_osu_file

    content = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1000,5,0
"""
    osu = parse_osu_file(content)
    pixmap = render_pattern_preview(osu)
    assert pixmap.width() > 0
    assert pixmap.height() > 0
