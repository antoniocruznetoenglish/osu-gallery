"""Integration tests for Phase 4: parse -> store -> render thumbnail -> display in grid."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from osu_gallery.db.database import GalleryDatabase
from osu_gallery.parser.osu_file import parse_osu_file
from osu_gallery.preview.thumbnail_renderer import render_pattern_preview, render_thumbnail
from osu_gallery.ui.main_window import MainWindow

SAMPLE_OSU = """[General]
AudioFilename: test.mp3

[Difficulty]
CircleSize: 5
SliderMultiplier: 1.4
SliderTickRate: 1

[HitObjects]
256,192,1000,5,0
384,256,1500,6,0,L|480:128,1,100
512,192,2000,5,0
"""

CIRCLES_ONLY = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1000,5,0
384,256,1500,5,0
512,192,2000,5,0
"""

SLIDERS_ONLY = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1000,6,0,L|480:128,1,100
384,256,1500,6,0,L|512:384,1,150
"""

WITH_COMBO_COLORS = """[General]
AudioFilename: test.mp3

[Colours]
Combo1Colour:255,0,0
Combo2Colour:0,255,0

[HitObjects]
256,192,1000,5,0
384,256,1500,6,0,L|480:128,1,100
512,192,2000,5,0
"""

EMPTY_HIT_OBJECTS = """[General]
AudioFilename: test.mp3

[Difficulty]
CircleSize: 5
SliderMultiplier: 1.4
SliderTickRate: 1
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
def sample_osu_content():
    """Return a valid .osu file string with circles and sliders."""
    return SAMPLE_OSU


@pytest.fixture
def parsed_file(sample_osu_content):
    """Parse the sample .osu content into an OsuFile."""
    return parse_osu_file(sample_osu_content)


@pytest.fixture
def saved_pattern(db, parsed_file):
    """Create a pattern in the database from parsed data."""
    return db.create_pattern(
        raw_code=sample_osu_content,
        object_count=len(parsed_file.hit_objects),
        timing_bpm=120.0,
    )


# -- Full flow tests --


def test_parse_store_render_flow(db, sample_osu_content, parsed_file):
    """Parse .osu content, store in DB, load from DB, re-parse, verify hit objects match."""
    pattern = db.create_pattern(
        raw_code=sample_osu_content,
        object_count=len(parsed_file.hit_objects),
    )

    fetched = db.get_pattern(pattern.id)
    assert fetched is not None
    assert fetched.raw_code == sample_osu_content
    assert fetched.object_count == len(parsed_file.hit_objects)

    reparsed = parse_osu_file(fetched.raw_code)
    assert len(reparsed.hit_objects) == len(parsed_file.hit_objects)

    for orig, rep in zip(parsed_file.hit_objects, reparsed.hit_objects, strict=True):
        assert abs(orig.x - rep.x) < 0.01
        assert abs(orig.y - rep.y) < 0.01
        assert orig.type == rep.type
        assert orig.time == rep.time
        assert orig.combo_colour == rep.combo_colour


def test_thumbnail_rendered_from_stored_code(db, sample_osu_content):
    """Save pattern to DB, load raw_code, parse it, render thumbnail, check not empty."""
    pattern = db.create_pattern(
        raw_code=sample_osu_content,
        object_count=3,
    )

    fetched = db.get_pattern(pattern.id)
    assert fetched is not None

    osu_file = parse_osu_file(fetched.raw_code)
    pixmap = render_thumbnail(osu_file, width=200, height=150)

    assert pixmap is not None
    assert not pixmap.isNull()
    assert pixmap.width() > 0
    assert pixmap.height() > 0


def test_thumbnail_contains_circles():
    """Render thumbnail from content with circles, verify the pixmap has non-white pixels."""
    osu_file = parse_osu_file(CIRCLES_ONLY)
    pixmap = render_thumbnail(osu_file, width=200, height=150)

    assert pixmap is not None
    assert not pixmap.isNull()

    image = pixmap.toImage()
    w, h = image.width(), image.height()

    has_non_white = False
    for y in range(h):
        for x in range(w):
            pixel = image.pixel(x, y)
            r = (pixel >> 16) & 0xFF
            g = (pixel >> 8) & 0xFF
            b = pixel & 0xFF
            if r < 250 or g < 250 or b < 250:
                has_non_white = True
                break
        if has_non_white:
            break

    assert has_non_white, "Rendered thumbnail should contain non-white pixels (hit circles drawn)"


def test_thumbnail_contains_sliders():
    """Render thumbnail from content with sliders, verify pixmap has content."""
    osu_file = parse_osu_file(SLIDERS_ONLY)
    pixmap = render_thumbnail(osu_file, width=200, height=150)

    assert pixmap is not None
    assert not pixmap.isNull()

    image = pixmap.toImage()
    w, h = image.width(), image.height()

    has_content = False
    for y in range(h):
        for x in range(w):
            pixel = image.pixel(x, y)
            r = (pixel >> 16) & 0xFF
            g = (pixel >> 8) & 0xFF
            b = pixel & 0xFF
            if r < 250 or g < 250 or b < 250:
                has_content = True
                break
        if has_content:
            break

    assert has_content, "Rendered thumbnail should contain non-white pixels (sliders drawn)"


def test_thumbnail_scaling():
    """Render at different sizes, verify dimensions match requested size."""
    osu_file = parse_osu_file(CIRCLES_ONLY)

    sizes = [(100, 75), (200, 150), (400, 300)]
    for w, h in sizes:
        pixmap = render_thumbnail(osu_file, width=w, height=h)
        assert pixmap is not None
        assert not pixmap.isNull()
        assert pixmap.width() == w, f"Expected width {w}, got {pixmap.width()}"
        assert pixmap.height() == h, f"Expected height {h}, got {pixmap.height()}"


def test_combo_colors_applied():
    """Render thumbnail with combo colors, verify the rendered image uses the combo colors."""
    osu_file = parse_osu_file(WITH_COMBO_COLORS)
    pixmap = render_thumbnail(osu_file, width=200, height=150)

    assert pixmap is not None
    assert not pixmap.isNull()

    image = pixmap.toImage()
    w, h = image.width(), image.height()

    red_pixels = 0
    green_pixels = 0
    threshold = 60

    for y in range(h):
        for x in range(w):
            pixel = image.pixel(x, y)
            r = (pixel >> 16) & 0xFF
            g = (pixel >> 8) & 0xFF
            b = pixel & 0xFF

            if abs(r - 255) < threshold and abs(g) < threshold and abs(b) < threshold:
                red_pixels += 1
            if abs(g - 255) < threshold and abs(r) < threshold and abs(b) < threshold:
                green_pixels += 1

    assert red_pixels > 0, "Combo 1 color (red) should appear in rendered thumbnail"
    assert green_pixels > 0, "Combo 2 color (green) should appear in rendered thumbnail"


def test_empty_pattern_thumbnail():
    """Render thumbnail from pattern with no hit objects, verify it's a blank/transparent pixmap."""
    osu_file = parse_osu_file(EMPTY_HIT_OBJECTS)
    pixmap = render_thumbnail(osu_file, width=200, height=150)

    assert pixmap is not None
    assert not pixmap.isNull()

    image = pixmap.toImage()
    w, h = image.width(), image.height()

    has_content = False
    for y in range(h):
        for x in range(w):
            pixel = image.pixel(x, y)
            r = (pixel >> 16) & 0xFF
            g = (pixel >> 8) & 0xFF
            b = pixel & 0xFF
            a = (pixel >> 24) & 0xFF
            if a < 250 and r < 200 and g < 200 and b < 200:
                continue
            if a >= 250 and r < 240 and g < 240 and b < 240:
                has_content = True
                break
        if has_content:
            break

    assert not has_content, "Thumbnail with no hit objects should have no colored content"


def test_full_grid_integration(qtbot, db):
    """Create MainWindow, add patterns via DB, refresh grid, verify thumbnail widgets appear."""
    p1 = db.create_pattern(SAMPLE_OSU, object_count=3)
    p2 = db.create_pattern(CIRCLES_ONLY, object_count=3)
    p3 = db.create_pattern(SLIDERS_ONLY, object_count=2)

    main_window = MainWindow(db_path=db.db_path)
    qtbot.addWidget(main_window)
    qtbot.waitExposed(main_window)

    main_window.refresh()
    qtbot.wait(200)

    flow_layout = main_window._flow_layout
    assert flow_layout.count() == 3

    widgets = []
    for i in range(flow_layout.count()):
        item = flow_layout.itemAt(i)
        if item and item.widget():
            widgets.append(item.widget())

    assert len(widgets) == 3
    pattern_ids = {w._pattern_id for w in widgets if hasattr(w, "_pattern_id")}
    assert pattern_ids == {p1.id, p2.id, p3.id}

    main_window.close()


def test_thumbnail_widget_click_signal(qtbot, db):
    """Verify clicking a thumbnail widget emits pattern_clicked signal with correct pattern_id."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3)

    main_window = MainWindow(db_path=db.db_path)
    qtbot.addWidget(main_window)
    qtbot.waitExposed(main_window)

    main_window.refresh()
    qtbot.wait(200)

    flow_layout = main_window._flow_layout
    item = flow_layout.itemAt(0)
    thumbnail_widget = item.widget() if item else None
    assert thumbnail_widget is not None
    assert hasattr(thumbnail_widget, "_pattern_id")
    assert thumbnail_widget._pattern_id == pattern.id

    clicked_id = [None]

    def on_clicked(pid):
        clicked_id[0] = pid

    thumbnail_widget.pattern_clicked.connect(on_clicked)

    qtbot.mouseClick(thumbnail_widget, Qt.MouseButton.LeftButton)
    qtbot.wait(100)

    assert clicked_id[0] == pattern.id

    main_window.close()


def test_multiple_patterns_different_thumbnails():
    """Create two patterns with different hit objects, render thumbnails, verify they differ."""
    osu_a = parse_osu_file(CIRCLES_ONLY)
    osu_b = parse_osu_file(SLIDERS_ONLY)

    pixmap_a = render_thumbnail(osu_a, width=200, height=150)
    pixmap_b = render_thumbnail(osu_b, width=200, height=150)

    assert pixmap_a.size() == pixmap_b.size()

    img_a = pixmap_a.toImage()
    img_b = pixmap_b.toImage()
    w, h = img_a.width(), img_a.height()

    pixels_identical = True
    for y in range(h):
        for x in range(w):
            if img_a.pixel(x, y) != img_b.pixel(x, y):
                pixels_identical = False
                break
        if not pixels_identical:
            break

    assert not pixels_identical, "Different hit object layouts should produce different thumbnails"


def test_preview_aspect_ratio_4_3():
    """Render preview at native osu! resolution, verify dimensions are 4:3 (512x384)."""
    osu_file = parse_osu_file(CIRCLES_ONLY)
    pixmap = render_pattern_preview(osu_file, width=512, height=384)

    assert pixmap is not None
    assert not pixmap.isNull()
    assert pixmap.width() == 512, f"Expected width 512, got {pixmap.width()}"
    assert pixmap.height() == 384, f"Expected height 384, got {pixmap.height()}"
    assert pixmap.width() / pixmap.height() == 4 / 3, "Preview must be 4:3 aspect ratio"


def test_preview_scaled_proportionally_to_pane_width():
    """When preview is scaled to fit a 380px-wide pane, verify 4:3 ratio is preserved."""
    osu_file = parse_osu_file(CIRCLES_ONLY)
    pixmap = render_pattern_preview(osu_file, width=512, height=384)

    pane_width = 380
    expected_height = int(pane_width * 384 / 512)

    scaled = pixmap.scaled(
        pane_width,
        expected_height,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )

    assert scaled.width() == pane_width
    assert scaled.width() / scaled.height() == 4 / 3, \
        "Scaled preview must preserve 4:3 aspect ratio"


def test_thumbnail_aspect_ratio_4_3():
    """Render thumbnail at standard size, verify dimensions are 4:3 (200x150)."""
    osu_file = parse_osu_file(CIRCLES_ONLY)
    pixmap = render_thumbnail(osu_file, width=200, height=150)

    assert pixmap is not None
    assert not pixmap.isNull()
    assert pixmap.width() == 200, f"Expected width 200, got {pixmap.width()}"
    assert pixmap.height() == 150, f"Expected height 150, got {pixmap.height()}"
    assert pixmap.width() / pixmap.height() == 4 / 3, "Thumbnail must be 4:3 aspect ratio"


def test_thumbnail_different_sizes_preserve_ratio():
    """Render thumbnails at various sizes, verify all maintain 4:3 ratio."""
    osu_file = parse_osu_file(CIRCLES_ONLY)

    sizes = [(100, 75), (200, 150), (400, 300), (512, 384)]
    for w, h in sizes:
        pixmap = render_thumbnail(osu_file, width=w, height=h)
        assert pixmap.width() == w, f"Expected width {w}, got {pixmap.width()}"
        assert pixmap.height() == h, f"Expected height {h}, got {pixmap.height()}"
        assert pixmap.width() / pixmap.height() == 4 / 3, f"Size {w}x{h} must be 4:3"
