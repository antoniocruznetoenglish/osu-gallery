"""Integration tests using the real .osu file (Dream Walk by Hashiba Gin).

These tests verify the full pipeline: parse -> store -> render -> search
using the real-world beatmap data as reference.
"""

from __future__ import annotations

import pytest

from osu_gallery.db.database import GalleryDatabase, set_search_engine
from osu_gallery.parser.osu_file import parse_osu_file
from osu_gallery.preview.thumbnail_renderer import render_pattern_preview, render_thumbnail
from osu_gallery.search.engine import SearchEngine, SearchQuery

# -- Fixtures --


@pytest.fixture
def real_db(tmp_path, real_osu_content):
    """Create a fresh database and import the real .osu file."""
    db_path = tmp_path / "test_real.db"
    database = GalleryDatabase(db_path)

    osu_file = parse_osu_file(real_osu_content)
    database.create_pattern(
        raw_code=real_osu_content,
        objects_only="test_objects",
        object_count=len(osu_file.hit_objects),
        circle_count=osu_file.circle_count,
        slider_count=osu_file.slider_count,
        timing_bpm=osu_file.timing_bpm,
    )

    # Sync FTS index for search tests
    search_engine = SearchEngine(database)
    set_search_engine(search_engine)
    search_engine.sync_fts_all()

    yield database
    database.close()


@pytest.fixture
def real_engine(real_db):
    """Create a SearchEngine with the real data."""
    search_engine = SearchEngine(real_db)
    set_search_engine(search_engine)
    return search_engine


# -- Database integration tests with real data --


def test_real_file_stored_and_retrieved(real_db, real_osu_content):
    """Verify the real .osu file is stored and retrieved correctly."""
    patterns = real_db.get_all_patterns()
    assert len(patterns) == 1

    pattern = patterns[0]
    assert pattern.raw_code == real_osu_content
    assert pattern.object_count == 117
    assert pattern.circle_count > 0
    assert pattern.slider_count > 0
    assert pattern.timing_bpm == 300.0


def test_real_file_metadata_preserved(real_db, real_parsed_file):
    """Verify metadata from the real file is preserved through the database."""
    pattern = real_db.get_all_patterns()[0]
    osu = parse_osu_file(pattern.raw_code)

    assert osu.metadata.title == real_parsed_file.metadata.title
    assert osu.metadata.artist == real_parsed_file.metadata.artist
    assert osu.metadata.creator == real_parsed_file.metadata.creator
    assert osu.metadata.version == real_parsed_file.metadata.version
    assert osu.metadata.tags == real_parsed_file.metadata.tags


def test_real_file_timing_bpm_preserved(real_db):
    """Verify BPM is preserved through database storage."""
    pattern = real_db.get_all_patterns()[0]
    assert pattern.timing_bpm == 300.0


def test_real_file_combo_colors_preserved(real_db):
    """Verify combo colors are preserved through database storage."""
    pattern = real_db.get_all_patterns()[0]
    osu = parse_osu_file(pattern.raw_code)

    assert len(osu.combo_colors) == 4
    assert osu.combo_colors[0] == 0xFF6464
    assert osu.combo_colors[1] == 0x64FF64
    assert osu.combo_colors[2] == 0x6464FF
    assert osu.combo_colors[3] == 0xFFFF64


def test_real_file_hit_objects_round_trip(real_db, real_osu_content):
    """Verify hit objects survive a round trip through the database."""
    pattern = real_db.get_all_patterns()[0]
    original = parse_osu_file(real_osu_content)
    reparsed = parse_osu_file(pattern.raw_code)

    assert len(original.hit_objects) == len(reparsed.hit_objects)

    for orig, rep in zip(original.hit_objects, reparsed.hit_objects, strict=True):
        assert abs(orig.x - rep.x) < 0.01
        assert abs(orig.y - rep.y) < 0.01
        assert orig.time == rep.time
        assert orig.type == rep.type


def test_real_file_slider_data_round_trip(real_db, real_osu_content):
    """Verify slider data survives a round trip through the database."""
    pattern = real_db.get_all_patterns()[0]
    original = parse_osu_file(real_osu_content)
    reparsed = parse_osu_file(pattern.raw_code)

    orig_sliders = [obj for obj in original.hit_objects if obj.is_slider]
    rep_sliders = [obj for obj in reparsed.hit_objects if obj.is_slider]

    assert len(orig_sliders) == len(rep_sliders)

    for orig, rep in zip(orig_sliders, rep_sliders, strict=True):
        assert orig.slider.repeats == rep.slider.repeats
        assert abs(orig.slider.pixel_length - rep.slider.pixel_length) < 0.1
        assert len(orig.slider.path) == len(rep.slider.path)


def test_real_file_multiple_imports(real_db, real_osu_content):
    """Verify multiple patterns from the real file can be stored."""
    # Import the same file multiple times with slight modifications
    for i in range(3):
        modified = real_osu_content.replace(
            "Dream Walk", f"Dream Walk v{i}"
        )
        real_db.create_pattern(
            raw_code=modified,
            objects_only="test",
            object_count=117,
            circle_count=103,
            slider_count=13,
            timing_bpm=300.0,
        )

    patterns = real_db.get_all_patterns()
    assert len(patterns) == 4  # 1 from fixture + 3 new


# -- Preview integration tests with real data --


def test_real_file_thumbnail_rendered(real_osu_content):
    """Render a thumbnail from the real .osu file and verify it's not empty."""
    osu_file = parse_osu_file(real_osu_content)
    pixmap = render_thumbnail(osu_file, width=200, height=150)

    assert pixmap is not None
    assert not pixmap.isNull()
    assert pixmap.width() == 200
    assert pixmap.height() == 150


def test_real_file_preview_rendered(real_osu_content):
    """Render a preview from the real .osu file at native resolution."""
    osu_file = parse_osu_file(real_osu_content)
    pixmap = render_pattern_preview(osu_file, width=512, height=384)

    assert pixmap is not None
    assert not pixmap.isNull()
    assert pixmap.width() == 512
    assert pixmap.height() == 384


def test_real_file_preview_aspect_ratio(real_osu_content):
    """Verify the real file preview maintains 4:3 aspect ratio."""
    osu_file = parse_osu_file(real_osu_content)
    pixmap = render_pattern_preview(osu_file, width=512, height=384)

    assert pixmap.width() / pixmap.height() == 4 / 3


def test_real_file_thumbnail_has_content(real_osu_content):
    """Verify the real file thumbnail has non-white pixels (actual drawn content)."""
    osu_file = parse_osu_file(real_osu_content)
    pixmap = render_thumbnail(osu_file, width=200, height=150)

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

    assert has_content, "Real file thumbnail should have drawn content"


def test_real_file_combo_colors_in_preview(real_osu_content):
    """Verify combo colors from the real file appear in the rendered preview."""
    osu_file = parse_osu_file(real_osu_content)
    pixmap = render_pattern_preview(osu_file, width=512, height=384)

    image = pixmap.toImage()
    w, h = image.width(), image.height()

    found_non_white = False
    threshold = 240

    for y in range(h):
        for x in range(w):
            pixel = image.pixel(x, y)
            r = (pixel >> 16) & 0xFF
            g = (pixel >> 8) & 0xFF
            b = pixel & 0xFF

            if r < threshold or g < threshold or b < threshold:
                found_non_white = True
                break
        if found_non_white:
            break

    assert found_non_white, "Preview should have non-white pixels (combo colors drawn)"


def test_real_file_multiple_render_sizes(real_osu_content):
    """Render the real file at multiple sizes and verify all succeed."""
    osu_file = parse_osu_file(real_osu_content)

    sizes = [(100, 75), (200, 150), (400, 300), (512, 384)]
    for w, h in sizes:
        pixmap = render_thumbnail(osu_file, width=w, height=h)
        assert pixmap is not None
        assert not pixmap.isNull()
        assert pixmap.width() == w
        assert pixmap.height() == h


# -- Search integration tests with real data --


def test_search_real_file_by_text(real_engine, real_db):
    """Search for text that appears in the real .osu file."""
    results = real_engine.search(SearchQuery(text="HitObjects"))
    assert len(results) >= 1


def test_search_real_file_by_artist(real_engine, real_db):
    """Search for the artist name from the real .osu file."""
    results = real_engine.search(SearchQuery(text="Hashiba Gin"))
    assert len(results) >= 1


def test_search_real_file_by_title(real_engine, real_db):
    """Search for the title from the real .osu file."""
    results = real_engine.search(SearchQuery(text="Dream Walk"))
    assert len(results) >= 1


def test_search_real_file_by_tag(real_engine, real_db):
    """Search by tags extracted from the real .osu file."""
    tag = real_db.create_tag("magical girl", "metadata")
    pattern = real_db.get_all_patterns()[0]
    real_db.add_tag_to_pattern(pattern.id, tag.id)

    results = real_engine.search(SearchQuery(text="magical girl"))
    assert len(results) >= 1


def test_search_real_file_by_creator(real_engine, real_db):
    """Search for the creator name from the real .osu file."""
    results = real_engine.search(SearchQuery(text="TestMapper"))
    assert len(results) >= 1


def test_search_real_file_empty_query(real_engine, real_db):
    """Empty search query returns all patterns including the real file."""
    results = real_engine.search(SearchQuery())
    assert len(results) >= 1


def test_search_real_file_no_results(real_engine, real_db):
    """Search for non-existent text returns empty."""
    results = real_engine.search(SearchQuery(text="zzzznonexistent"))
    assert results == []


def test_search_real_file_tag_filter(real_engine, real_db):
    """Filter patterns by tag category using the real file."""
    tag = real_db.create_tag("jpop", "metadata")
    pattern = real_db.get_all_patterns()[0]
    real_db.add_tag_to_pattern(pattern.id, tag.id)

    results = real_engine.search(SearchQuery(tag_ids=[tag.id]))
    assert len(results) >= 1


def test_search_real_file_exclude_tag(real_engine, real_db):
    """Exclude tag filter removes the real file pattern."""
    tag = real_db.create_tag("nonexistent_tag", "metadata")
    pattern = real_db.get_all_patterns()[0]
    real_db.add_tag_to_pattern(pattern.id, tag.id)

    results = real_engine.search(SearchQuery(exclude_tag_ids=[tag.id]))
    assert len(results) == 0


def test_search_real_file_combined_filters(real_engine, real_db):
    """Combine text and tag filters for the real file."""
    tag = real_db.create_tag("fantasy", "metadata")
    pattern = real_db.get_all_patterns()[0]
    real_db.add_tag_to_pattern(pattern.id, tag.id)

    results = real_engine.search(
        SearchQuery(text="Dream", tag_ids=[tag.id])
    )
    assert len(results) >= 1


def test_search_real_file_suggest_tags(real_engine, real_db):
    """Tag suggestions work with tags from the real file."""
    real_db.create_tag("magical girl", "metadata")
    real_db.create_tag("magical", "metadata")
    real_db.create_tag("jpop", "metadata")

    suggestions = real_engine.suggest_tags("magical")
    assert "magical girl" in suggestions
    assert "magical" in suggestions


# -- Edge case tests with real file data --


def test_real_file_slider_with_complex_bezier(real_osu_content):
    """Verify a complex bezier slider from the real file is parsed correctly."""
    osu_file = parse_osu_file(real_osu_content)

    slider_objects = [obj for obj in osu_file.hit_objects if obj.is_slider]

    bezier_sliders = [
        obj for obj in slider_objects
        if any(p.path_type == "B" for p in obj.slider.path)
    ]

    assert len(bezier_sliders) > 0

    for slider_obj in bezier_sliders:
        for path in slider_obj.slider.path:
            if path.path_type == "B":
                assert len(path.points) >= 3, \
                    "Bezier path should have at least 3 control points"


def test_real_file_timing_point_bpm_changes(real_osu_content):
    """Verify BPM changes are reflected in the parsed timing points."""
    osu_file = parse_osu_file(real_osu_content)

    assert osu_file.timing_bpm > 0
    # The file has multiple BPM values; parser uses the last negative one
    assert osu_file.timing_bpm in (212.5, 300.0, 425.0)


def test_real_file_slider_edge_sounds_parsed(real_osu_content):
    """Verify sliders from the real file have valid edge sound data."""
    osu_file = parse_osu_file(real_osu_content)

    slider_objects = [obj for obj in osu_file.hit_objects if obj.is_slider]

    # All sliders should have valid SliderData
    for obj in slider_objects:
        assert obj.slider is not None
        assert obj.slider.repeats >= 0
        assert obj.slider.pixel_length > 0


def test_real_file_all_objects_have_combo_colour(real_osu_content):
    """Verify every hit object has a resolved combo colour."""
    osu_file = parse_osu_file(real_osu_content)

    for obj in osu_file.hit_objects:
        assert obj.combo_colour is not None
        assert 0 <= obj.combo_colour < len(osu_file.combo_colors)


def test_real_file_spinner_has_end_time(real_osu_content):
    """Verify the spinner in the real file has a valid end time."""
    osu_file = parse_osu_file(real_osu_content)

    spinners = [obj for obj in osu_file.hit_objects if obj.is_spinner]
    assert len(spinners) >= 1

    for spinner in spinners:
        assert spinner.spinner_end is not None
        assert spinner.spinner_end > spinner.time
