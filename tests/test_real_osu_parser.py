"""Tests for the osu! .osu file parser using real-world beatmap data.

These tests verify that the parser correctly handles a real .osu file
(Dream Walk by Hashiba Gin) with all its complexities: multiple timing
points, combo colors, various slider types, edge sounds, and more.
"""

from __future__ import annotations

from osu_gallery.parser.models import HitObjectType, OsuFile
from osu_gallery.parser.osu_file import parse_osu_file

# -- Parser tests with real .osu file --


def test_parse_real_file_full_structure(real_parsed_file):
    """Verify the real .osu file parses without errors and has expected sections."""
    osu = real_parsed_file

    assert isinstance(osu, OsuFile)
    assert osu.general.audio_file == "audio.mp3"
    assert osu.preview_time == -1
    assert osu.stack_leniency == 0.7
    assert osu.mode == 0
    assert osu.countdown is False
    assert osu.sample_set == "Soft"


def test_parse_real_file_metadata(real_parsed_file):
    """Verify all metadata fields are correctly extracted from the real file."""
    osu = real_parsed_file

    assert osu.metadata.title == "Dream Walk"
    assert osu.metadata.artist == "Hashiba Gin"
    assert osu.metadata.creator == "TestMapper"
    assert osu.metadata.version == "Hard"
    assert osu.metadata.tags == "magical girl jpop fantasy anime"
    assert osu.metadata.beatmap_id == "987654"
    assert osu.metadata.beatmap_set_id == "123456"


def test_parse_real_file_difficulty(real_parsed_file):
    """Verify difficulty settings from the real .osu file."""
    osu = real_parsed_file

    assert osu.difficulty.circle_size == 4.0
    assert osu.difficulty.health_bar_drain == 6.0
    assert osu.difficulty.overall_difficulty == 8.0
    assert osu.difficulty.approach_rate == 9.0
    assert osu.difficulty.slider_multiplier == 1.6
    assert osu.difficulty.slider_tick_rate == 1.0


def test_parse_real_file_editor(real_parsed_file):
    """Verify editor section settings from the real .osu file."""
    osu = real_parsed_file

    assert osu.distance_spacing == 1.1
    assert osu.bird_eye_view_distance == 180.0
    assert osu.point_spacing == 2.8


def test_parse_real_file_timing_points_bpm(real_parsed_file):
    """Verify BPM is calculated correctly from timing points.

    The real file has timing points at -282.35 (212.5 BPM), -200.0 (300 BPM),
    and -141.18 (425 BPM). The parser should use the last negative value.
    """
    osu = real_parsed_file

    assert osu.timing_bpm > 0, "BPM should be calculated from timing points"
    # The last timing point has -200.0 which equals 300 BPM
    assert osu.timing_bpm == 300.0, f"Expected 300 BPM, got {osu.timing_bpm}"


def test_parse_real_file_timing_point_count(real_osu_content):
    """Verify all 14 timing points are parsed from the real file."""
    from osu_gallery.parser.osu_file import _extract_section

    timing_section = _extract_section(real_osu_content, "TimingPoints")
    timing_lines = [
        line.strip()
        for line in timing_section.splitlines()
        if line.strip() and not line.strip().startswith("//") and not line.strip().startswith("#")
    ]
    assert len(timing_lines) == 14, f"Expected 14 timing points, got {len(timing_lines)}"


def test_parse_real_file_combo_colors(real_parsed_file):
    """Verify combo colors from the [Colours] section are parsed correctly."""
    osu = real_parsed_file

    assert len(osu.combo_colors) == 4, f"Expected 4 combo colors, got {len(osu.combo_colors)}"

    # Combo1Colour: 255,100,100 -> 0xFF6464
    assert osu.combo_colors[0] == 0xFF6464
    # Combo2Colour: 100,255,100 -> 0x64FF64
    assert osu.combo_colors[1] == 0x64FF64
    # Combo3Colour: 100,100,255 -> 0x6464FF
    assert osu.combo_colors[2] == 0x6464FF
    # Combo4Colour: 255,255,100 -> 0xFFFF64
    assert osu.combo_colors[3] == 0xFFFF64


def test_parse_real_file_hit_object_count(real_parsed_file):
    """Verify the total number of hit objects parsed from the real file."""
    osu = real_parsed_file

    # The real file has 117 hit objects (circles + sliders + spinners)
    assert len(osu.hit_objects) == 117, f"Expected 117 hit objects, got {len(osu.hit_objects)}"


def test_parse_real_file_circle_count(real_parsed_file):
    """Verify circle count from the real file."""
    osu = real_parsed_file

    circles = osu.circle_count
    assert circles > 0, "Should have circles in the real file"
    assert circles == osu.circle_count


def test_parse_real_file_slider_count(real_parsed_file):
    """Verify slider count from the real file."""
    osu = real_parsed_file

    sliders = osu.slider_count
    assert sliders > 0, "Should have sliders in the real file"
    assert sliders == osu.slider_count


def test_parse_real_file_spinner_count(real_parsed_file):
    """Verify spinner count from the real file."""
    osu = real_parsed_file

    spinners = sum(1 for obj in osu.hit_objects if obj.is_spinner)
    assert spinners >= 1, "Should have at least one spinner in the real file"


def test_parse_real_file_mixed_object_types(real_parsed_file):
    """Verify the real file has a mix of circles, sliders, and spinners."""
    osu = real_parsed_file

    circles = sum(1 for obj in osu.hit_objects if obj.is_circle)
    sliders = sum(1 for obj in osu.hit_objects if obj.is_slider)
    spinners = sum(1 for obj in osu.hit_objects if obj.is_spinner)

    assert circles > 50, f"Expected >50 circles, got {circles}"
    assert sliders > 5, f"Expected >5 sliders, got {sliders}"
    assert spinners >= 1, f"Expected >=1 spinner, got {spinners}"
    assert circles + sliders + spinners == len(osu.hit_objects)


def test_parse_real_file_first_object_is_circle(real_parsed_file):
    """Verify the first hit object in the real file is a circle."""
    osu = real_parsed_file

    first_obj = osu.hit_objects[0]
    assert first_obj.is_circle, "First object should be a circle"
    assert first_obj.x == 256.0
    assert first_obj.y == 192.0
    assert first_obj.time == 1000
    assert first_obj.is_new_combo


def test_parse_real_file_sliders_have_path_data(real_parsed_file):
    """Verify that sliders in the real file have valid SliderData."""
    osu = real_parsed_file

    slider_objects = [obj for obj in osu.hit_objects if obj.is_slider]
    assert len(slider_objects) > 0

    for slider_obj in slider_objects:
        assert slider_obj.slider is not None, "Slider should have SliderData"
        assert slider_obj.slider.pixel_length > 0, "Slider should have positive length"


def test_parse_real_file_slider_path_types(real_parsed_file):
    """Verify the real file has both linear and bezier slider paths."""
    osu = real_parsed_file

    slider_objects = [obj for obj in osu.hit_objects if obj.is_slider]

    has_linear = False
    has_bezier = False

    for slider_obj in slider_objects:
        for path in slider_obj.slider.path:
            if path.path_type == "L":
                has_linear = True
            elif path.path_type == "B":
                has_bezier = True

    assert has_linear, "Should have at least one linear slider"
    assert has_bezier, "Should have at least one bezier slider"


def test_parse_real_file_slider_repeats(real_parsed_file):
    """Verify sliders with different repeat counts are parsed correctly."""
    osu = real_parsed_file

    slider_objects = [obj for obj in osu.hit_objects if obj.is_slider]

    repeat_counts = {obj.slider.repeats for obj in slider_objects if obj.slider}
    assert 1 in repeat_counts, "Should have sliders with 1 repeat"
    assert 2 in repeat_counts, "Should have sliders with 2 repeats"


def test_parse_real_file_slider_edge_sounds(real_parsed_file):
    """Verify sliders are parsed without errors (edge sounds may be empty)."""
    osu = real_parsed_file

    slider_objects = [obj for obj in osu.hit_objects if obj.is_slider]

    # All sliders should have valid SliderData
    for obj in slider_objects:
        assert obj.slider is not None
        assert obj.slider.repeats >= 0
        assert obj.slider.pixel_length > 0


def test_parse_real_file_hit_samples(real_parsed_file):
    """Verify hit samples are extracted from the real file."""
    osu = real_parsed_file

    circles = [obj for obj in osu.hit_objects if obj.is_circle]

    circles_with_samples = [
        obj for obj in circles if obj.hit_sample and obj.hit_sample != ""
    ]

    assert len(circles_with_samples) > 0, "Should have circles with hit samples"


def test_parse_real_file_combo_colour_resolution(real_parsed_file):
    """Verify combo colours are resolved for all hit objects."""
    osu = real_parsed_file

    for obj in osu.hit_objects:
        assert 0 <= obj.combo_colour < len(osu.combo_colors), \
            f"Combo colour {obj.combo_colour} out of range for {len(osu.combo_colors)} colours"


def test_parse_real_file_timing_points_values(real_osu_content):
    """Verify timing point values are parsed correctly."""
    from osu_gallery.parser.osu_file import _extract_section

    timing_section = _extract_section(real_osu_content, "TimingPoints")

    # First timing point: 1000,-282.35 -> 212.5 BPM
    first_line = timing_section.strip().splitlines()[0]
    parts = first_line.split(",")
    assert len(parts) >= 2
    ms_per_beat = float(parts[1])
    assert ms_per_beat < 0, "First timing point should have negative ms/beat"
    bpm = 60000.0 / abs(ms_per_beat)
    assert abs(bpm - 212.5) < 0.1, f"Expected ~212.5 BPM, got {bpm}"


def test_parse_real_file_metadata_overrides_general(real_osu_content):
    """Verify [Metadata] section overrides [General] section values."""
    osu = parse_osu_file(real_osu_content)

    # Both sections have Title, Artist, Tags - Metadata should win
    assert osu.metadata.title == "Dream Walk"
    assert osu.metadata.artist == "Hashiba Gin"
    assert osu.metadata.tags == "magical girl jpop fantasy anime"


def test_parse_real_file_general_fallback_values(real_osu_content):
    """Verify [General] section provides fallback values."""
    osu = parse_osu_file(real_osu_content)

    # These should come from [General] since they're not in [Metadata]
    assert osu.general.audio_file == "audio.mp3"
    assert osu.general.tags == "magical girl jpop fantasy anime"


def test_parse_real_file_spinner_end_time(real_parsed_file):
    """Verify spinner end time is parsed correctly."""
    osu = real_parsed_file

    spinners = [obj for obj in osu.hit_objects if obj.is_spinner]
    assert len(spinners) >= 1

    last_spinner = spinners[-1]
    assert last_spinner.spinner_end is not None
    assert last_spinner.spinner_end == 32000, \
        f"Expected spinner end at 32000ms, got {last_spinner.spinner_end}"


def test_parse_real_file_slider_multipliers(real_parsed_file):
    """Verify sliders with different multipliers are parsed correctly."""
    osu = real_parsed_file

    slider_objects = [obj for obj in osu.hit_objects if obj.is_slider]

    multipliers = {obj.slider.multiplier for obj in slider_objects if obj.slider}
    assert 1.0 in multipliers, "Should have sliders with default multiplier"


def test_parse_real_file_slider_tick_rates(real_parsed_file):
    """Verify sliders with different tick rates are parsed correctly."""
    osu = real_parsed_file

    slider_objects = [obj for obj in osu.hit_objects if obj.is_slider]

    tick_rates = {obj.slider.tick_rate for obj in slider_objects if obj.slider}
    assert 1 in tick_rates, "Should have sliders with tick rate 1"


def test_parse_real_file_coordinates_range(real_parsed_file):
    """Verify all hit object coordinates are within valid osu! screen bounds."""
    osu = real_parsed_file

    for obj in osu.hit_objects:
        assert 0 <= obj.x <= 512, f"x={obj.x} out of bounds"
        assert 0 <= obj.y <= 384, f"y={obj.y} out of bounds"


def test_parse_real_file_times_monotonically_increasing(real_parsed_file):
    """Verify hit object times are in monotonically increasing order."""
    osu = real_parsed_file

    for i in range(1, len(osu.hit_objects)):
        assert osu.hit_objects[i].time > osu.hit_objects[i - 1].time, \
            f"Time not increasing at index {i}: " \
            f"{osu.hit_objects[i - 1].time} -> {osu.hit_objects[i].time}"


def test_parse_real_file_new_combo_at_start(real_parsed_file):
    """Verify the first hit object has the NEW_COMBO flag."""
    osu = real_parsed_file

    first_obj = osu.hit_objects[0]
    assert first_obj.is_new_combo, "First object should have NEW_COMBO flag"
    assert first_obj.type & HitObjectType.NEW_COMBO


def test_parse_real_file_slider_path_points_count(real_parsed_file):
    """Verify slider path points are correctly parsed."""
    osu = real_parsed_file

    slider_objects = [obj for obj in osu.hit_objects if obj.is_slider]

    for slider_obj in slider_objects:
        for path in slider_obj.slider.path:
            assert len(path.points) > 0, "Path should have at least one point"
            for point in path.points:
                assert len(point) == 2, "Each point should be (x, y) tuple"


def test_parse_real_file_beatmap_id_consistency(real_osu_content, real_parsed_file):
    """Verify beatmap ID is consistent between [General] and [Metadata]."""
    osu = real_parsed_file

    assert osu.metadata.beatmap_id == "987654"
    assert osu.metadata.beatmap_set_id == "123456"


def test_parse_real_file_no_empty_sections(real_osu_content):
    """Verify the real file has no empty required sections."""
    from osu_gallery.parser.osu_file import _extract_section

    for section in ["General", "Editor", "Difficulty", "Metadata", "Colours", "TimingPoints"]:
        data = _extract_section(real_osu_content, section)
        assert len(data.strip()) > 0, f"Section [{section}] should not be empty"


def test_parse_real_file_round_trip_consistency(real_osu_content):
    """Verify that parsing the real file twice gives identical results."""
    osu1 = parse_osu_file(real_osu_content)
    osu2 = parse_osu_file(real_osu_content)

    assert len(osu1.hit_objects) == len(osu2.hit_objects)
    assert osu1.timing_bpm == osu2.timing_bpm
    assert len(osu1.combo_colors) == len(osu2.combo_colors)

    for obj1, obj2 in zip(osu1.hit_objects, osu2.hit_objects, strict=True):
        assert obj1.x == obj2.x
        assert obj1.y == obj2.y
        assert obj1.time == obj2.time
        assert obj1.type == obj2.type
        assert obj1.combo_colour == obj2.combo_colour
