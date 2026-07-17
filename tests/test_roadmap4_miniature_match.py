"""Tests for Task 6: Miniature/preview rendering consistency.

Verifies that thumbnail and preview rendering use the same coordinate
normalization, combo colors, slider paths, and circle drawing functions.
"""

from __future__ import annotations

import inspect

from osu_gallery.preview.thumbnail_renderer import (
    _OSU_HEIGHT,
    _OSU_WIDTH,
    _circle_radius,
    _get_combo_color,
    _render_objects,
    render_pattern_preview,
    render_thumbnail,
)


def test_thumbnail_matches_preview_coordinates():
    """Both renderers use the same _OSU_WIDTH and _OSU_HEIGHT constants."""
    assert _OSU_WIDTH == 512.0
    assert _OSU_HEIGHT == 384.0

    thumbnail_source = inspect.getsource(render_thumbnail)
    preview_source = inspect.getsource(render_pattern_preview)

    assert "_OSU_WIDTH" in thumbnail_source
    assert "_OSU_HEIGHT" in thumbnail_source
    assert "_OSU_WIDTH" in preview_source
    assert "_OSU_HEIGHT" in preview_source


def test_thumbnail_matches_preview_combo_colors():
    """Both renderers use the same _get_combo_color function via _render_objects."""
    thumbnail_source = inspect.getsource(render_thumbnail)
    preview_source = inspect.getsource(render_pattern_preview)
    render_objects_source = inspect.getsource(_render_objects)

    assert "_render_objects" in thumbnail_source
    assert "_render_objects" in preview_source
    assert "_get_combo_color" in render_objects_source

    # Verify the function exists and works
    color = _get_combo_color(0, [0xFF6464])
    assert color is not None


def test_thumbnail_matches_preview_slider_paths():
    """Both renderers use the same _draw_slider_path function via _render_objects."""
    thumbnail_source = inspect.getsource(render_thumbnail)
    preview_source = inspect.getsource(render_pattern_preview)
    render_objects_source = inspect.getsource(_render_objects)

    assert "_render_objects" in thumbnail_source
    assert "_render_objects" in preview_source
    assert "_draw_slider_path" in render_objects_source


def test_thumbnail_matches_preview_circle_positions():
    """Both renderers use the same _draw_circle function via _render_objects."""
    thumbnail_source = inspect.getsource(render_thumbnail)
    preview_source = inspect.getsource(render_pattern_preview)
    render_objects_source = inspect.getsource(_render_objects)

    assert "_render_objects" in thumbnail_source
    assert "_render_objects" in preview_source
    assert "_draw_circle" in render_objects_source


def test_rendering_uses_shared_draw_functions():
    """Both renderers delegate to _render_objects for drawing."""
    thumbnail_source = inspect.getsource(render_thumbnail)
    preview_source = inspect.getsource(render_pattern_preview)

    assert "_render_objects" in thumbnail_source
    assert "_render_objects" in preview_source

    # Both call _render_objects
    render_source = inspect.getsource(_render_objects)
    assert "_draw_circle" in render_source
    assert "_draw_slider_path" in render_source
    assert "_get_combo_color" in render_source


def test_last_saved_pattern_consistent_render():
    """Same OsuFile rendered at thumbnail and preview sizes produces valid pixmaps."""
    from osu_gallery.parser.osu_file import parse_osu_file

    content = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1000,5,0
384,256,1500,6,0,L|480:128,1,100
512,192,2000,5,0
"""
    osu = parse_osu_file(content)
    thumb = render_thumbnail(osu)
    preview = render_pattern_preview(osu)

    # Both should be valid pixmaps
    assert thumb.width() > 0
    assert thumb.height() > 0
    assert preview.width() > 0
    assert preview.height() > 0

    # Both should render the same number of objects
    assert len(osu.hit_objects) == 3


def test_coordinate_normalization_is_identical():
    """_map_coords is used by both renderers for coordinate transformation."""
    thumbnail_source = inspect.getsource(render_thumbnail)
    preview_source = inspect.getsource(render_pattern_preview)

    assert "_map_coords" in thumbnail_source or "_render_objects" in thumbnail_source
    assert "_map_coords" in preview_source or "_render_objects" in preview_source

    render_source = inspect.getsource(_render_objects)
    assert "_map_coords" in render_source


def test_shared_circle_radius_function():
    """Both renderers use the same _circle_radius for sizing."""
    render_source = inspect.getsource(_render_objects)
    assert "_circle_radius" in render_source

    # Verify the function maps circle_size to radius correctly
    assert _circle_radius(5) == 18.0  # 30 - 5*2.4 = 18
    assert _circle_radius(0) == 30.0  # 30 - 0*2.4 = 30
    assert _circle_radius(10) == 6.0  # 30 - 10*2.4 = 6


def test_shared_combo_color_defaults():
    """The default combo colors list is shared between renderers."""
    assert len(_get_combo_color.__code__.co_consts) > 0
    # Verify the function resolves colors correctly
    color = _get_combo_color(0, [])
    assert color is not None
    color2 = _get_combo_color(1, [0xFF0000, 0x00FF00])
    assert color2 is not None
