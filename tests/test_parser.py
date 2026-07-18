"""Tests for the osu! .osu file parser."""

import pytest

from osu_gallery.parser.models import HitObjectType, OsuFile
from osu_gallery.parser.osu_file import ParseError, parse_osu_file

SAMPLE_OSU = """[General]
AudioFilename: audio.mp3
LeadIn: 1000
PreviewTime: -1
Countdown: 0
SampleSet: Soft
StackLeniency: 0.7
Mode: 0
LetterboxInBreaks: 0
SpecialStyle: 0
WidescreenStoryboard: 0
SampleSetOverride:

[Editor]
DistanceSpacing: 1.2
BirdEyeViewDistance: 200
OriginalSpeed: 1.0
Timer: 0
PointSpacing: 3.0

[Difficulty]
HPDrainRate: 5
CircleSize: 4
OverallDifficulty: 7
ApproachRate: 8
SliderMultiplier: 1.4
SliderTickRate: 1

[Metadata]
Title:Test Song
TitleUnicode:Test Song
Artist:Test Artist
ArtistUnicode:Test Artist
Creator:TestMapper
Version:Easy
Source:
Tags:test tag1 tag2
BeatmapID:12345
BeatmapSetID:67890

[Events]
//Background,0,background.jpg,0,0
//Audio,0,audio.mp3,0,0

[Colours]
Combo1Colour:255,100,100
Combo2Colour:100,255,100
Combo3Colour:100,100,255

[HitObjects]
256,192,100,6,0,L|480:128,1,100,Normal:Normal:0::
384,256,300,6,0,B|100:100:200:200:300:300,2,100,0,1,,0,|,0
512,320,500,5,0,,Normal:Clap:0::
256,192,700,12,0,2000,Normal:Whistle:0::
"""


def test_parse_full_file():
    osu = parse_osu_file(SAMPLE_OSU)

    assert isinstance(osu, OsuFile)
    assert osu.general.audio_file == "audio.mp3"
    assert osu.preview_time == -1
    assert osu.stack_leniency == 0.7
    assert osu.mode == 0
    assert osu.countdown is False
    assert osu.sample_set == "Soft"


def test_parse_metadata():
    osu = parse_osu_file(SAMPLE_OSU)

    assert osu.metadata.title == "Test Song"
    assert osu.metadata.artist == "Test Artist"
    assert osu.metadata.creator == "TestMapper"
    assert osu.metadata.version == "Easy"
    assert osu.metadata.tags == "test tag1 tag2"
    assert osu.metadata.beatmap_id == "12345"
    assert osu.metadata.beatmap_set_id == "67890"


def test_parse_difficulty():
    osu = parse_osu_file(SAMPLE_OSU)

    assert osu.difficulty.circle_size == 4.0
    assert osu.difficulty.health_bar_drain == 5.0
    assert osu.difficulty.overall_difficulty == 7.0
    assert osu.difficulty.approach_rate == 8.0
    assert osu.difficulty.slider_multiplier == 1.4
    assert osu.difficulty.slider_tick_rate == 1.0


def test_parse_editor():
    osu = parse_osu_file(SAMPLE_OSU)

    assert osu.distance_spacing == 1.2
    assert osu.bird_eye_view_distance == 200.0
    assert osu.point_spacing == 3.0


def test_parse_colours():
    osu = parse_osu_file(SAMPLE_OSU)

    assert len(osu.combo_colors) == 3
    assert osu.combo_colors[0] == 0xFF6464  # 255,100,100
    assert osu.combo_colors[1] == 0x64FF64  # 100,255,100
    assert osu.combo_colors[2] == 0x6464FF  # 100,100,255


def test_parse_hit_objects_basic():
    osu = parse_osu_file(SAMPLE_OSU)

    assert len(osu.hit_objects) == 4

    # First object: slider at (256, 192) with type=6 (slider + new_combo)
    obj0 = osu.hit_objects[0]
    assert obj0.x == 256.0
    assert obj0.y == 192.0
    assert obj0.time == 100
    assert not obj0.is_circle
    assert obj0.is_slider
    assert not obj0.is_spinner
    assert obj0.is_new_combo


def test_parse_hit_objects_slider():
    osu = parse_osu_file(SAMPLE_OSU)

    # Second object: slider at (384, 256) with type=2|2 (slider + new_combo)
    obj1 = osu.hit_objects[1]
    assert obj1.is_slider
    assert obj1.slider is not None
    assert obj1.x == 384.0
    assert obj1.y == 256.0
    assert obj1.slider.repeats == 2
    assert obj1.slider.pixel_length == 100.0
    assert len(obj1.slider.path) > 0


def test_parse_hit_objects_spinner():
    osu = parse_osu_file(SAMPLE_OSU)

    # Last object: spinner at (256, 192) with type=8|4 (spinner + new_combo)
    obj3 = osu.hit_objects[3]
    assert obj3.is_spinner
    assert obj3.spinner_end == 2000


def test_parse_slider_path_linear():
    osu = parse_osu_file(SAMPLE_OSU)

    obj0 = osu.hit_objects[0]
    slider = obj0.slider
    assert slider is not None

    # Find the linear path segment
    linear_paths = [p for p in slider.path if p.path_type == "L"]
    assert len(linear_paths) > 0

    linear_path = linear_paths[0]
    assert len(linear_path.points) >= 1
    assert linear_path.points[0] == (480.0, 128.0)


def test_parse_slider_path_bezier():
    osu = parse_osu_file(SAMPLE_OSU)

    obj1 = osu.hit_objects[1]
    slider = obj1.slider
    assert slider is not None

    bezier_paths = [p for p in slider.path if p.path_type == "B"]
    assert len(bezier_paths) > 0


def test_parse_empty_content():
    with pytest.raises(ParseError, match="Empty"):
        parse_osu_file("")

    with pytest.raises(ParseError, match="Empty"):
        parse_osu_file("   ")

    with pytest.raises(ParseError, match="Empty"):
        parse_osu_file(None)  # type: ignore


def test_parse_minimal_file():
    minimal = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1000,5,0
"""
    osu = parse_osu_file(minimal)

    assert osu.general.audio_file == "test.mp3"
    assert len(osu.hit_objects) == 1
    assert osu.hit_objects[0].x == 256.0
    assert osu.hit_objects[0].y == 192.0
    assert osu.hit_objects[0].is_circle
    assert osu.hit_objects[0].is_new_combo


def test_parse_no_hit_objects():
    minimal = """[General]
AudioFilename: test.mp3

[Difficulty]
CircleSize: 4
"""
    osu = parse_osu_file(minimal)
    assert len(osu.hit_objects) == 0


def test_parse_comments_skipped():
    content = """[General]
AudioFilename: test.mp3

[HitObjects]
// This is a comment
256,192,1000,5,0
# Another comment
384,256,1500,5,0
"""
    osu = parse_osu_file(content)
    assert len(osu.hit_objects) == 2


def test_parse_default_difficulty_values():
    minimal = """[General]
AudioFilename: test.mp3

[HitObjects]
256,192,1000,5,0
"""
    osu = parse_osu_file(minimal)

    assert osu.difficulty.circle_size == 5.0
    assert osu.difficulty.health_bar_drain == 5.0
    assert osu.difficulty.overall_difficulty == 5.0
    assert osu.difficulty.approach_rate == 5.0
    assert osu.difficulty.slider_multiplier == 1.4
    assert osu.difficulty.slider_tick_rate == 1.0


def test_parse_new_combo_flag():
    content = """[General]

[HitObjects]
256,192,1000,5,0
"""
    osu = parse_osu_file(content)
    obj = osu.hit_objects[0]
    assert obj.is_new_combo
    assert obj.type & HitObjectType.NEW_COMBO


def test_parse_slider_with_edge_sounds():
    content = """[General]

[HitObjects]
256,192,1000,6,0,L|100:100,1,100,0,1,,0,|,0
"""
    osu = parse_osu_file(content)
    obj = osu.hit_objects[0]
    assert obj.is_slider
    assert obj.slider is not None
    assert 0 in obj.slider.edge_sounds


def test_parse_perfect_circle_slider():
    """A 3-control-point P slider parses with path_type == 'P'."""
    content = """[General]

[HitObjects]
256,192,1000,6,0,P|100:100|200:200|300:300,1,100
"""
    osu = parse_osu_file(content)
    obj = osu.hit_objects[0]
    assert obj.is_slider
    assert obj.slider is not None
    p_paths = [p for p in obj.slider.path if p.path_type == "P"]
    assert len(p_paths) == 1
    assert len(p_paths[0].points) == 3


def test_perfect_circle_more_than_3_points_degrades_to_bezier():
    """A P slider with more than 3 control points degrades to B."""
    content = """[General]

[HitObjects]
256,192,1000,6,0,P|100:100|200:200|300:300|400:400|500:500|600:600,1,100
"""
    osu = parse_osu_file(content)
    obj = osu.hit_objects[0]
    assert obj.is_slider
    assert obj.slider is not None
    b_paths = [p for p in obj.slider.path if p.path_type == "B"]
    assert len(b_paths) == 1


def test_perfect_circle_with_2_points_is_still_valid():
    """A 2-control-point P slider doesn't crash the parser."""
    content = """[General]

[HitObjects]
256,192,1000,6,0,P|100:100|200:200,1,100
"""
    osu = parse_osu_file(content)
    obj = osu.hit_objects[0]
    assert obj.is_slider
    assert obj.slider is not None
    assert len(obj.slider.path) == 0


def test_bpm_single_uninherited_timing_point():
    """A single uninherited timing point with beatLength=333.33 gives BPM ~180."""
    content = """[General]

[TimingPoints]
0,333.33,4,0,0,100,1,0

[HitObjects]
256,192,1000,5,0
"""
    osu = parse_osu_file(content)
    assert abs(osu.timing_bpm - 180.0) < 1.0


def test_bpm_ignores_inherited_negative_timing_points():
    """Inherited (negative beatLength) timing points don't affect BPM."""
    content = """[General]

[TimingPoints]
0,333.33,4,0,0,100,1,0
5000,-50,4,0,0,100,0,0

[HitObjects]
256,192,1000,5,0
"""
    osu = parse_osu_file(content)
    assert abs(osu.timing_bpm - 180.0) < 1.0


def test_bpm_uses_uninherited_flag_over_sign_when_present():
    """When uninherited flag is present, it takes precedence over sign."""
    content = """[General]

[TimingPoints]
0,333.33,4,0,0,100,0,0

[HitObjects]
256,192,1000,5,0
"""
    osu = parse_osu_file(content)
    assert osu.timing_bpm == 0.0


def test_bpm_zero_beatlength_does_not_crash():
    """Malformed beatLength=0 doesn't crash the parser."""
    content = """[General]

[TimingPoints]
0,0,4,0,0,100,1,0

[HitObjects]
256,192,1000,5,0
"""
    osu = parse_osu_file(content)
    assert osu.timing_bpm == 0.0


def test_bpm_range_single_bpm_map():
    """Single-BPM map has bpm_min == bpm_max == timing_bpm."""
    content = """[General]

[TimingPoints]
0,333.33,4,0,0,100,1,0

[HitObjects]
256,192,1000,5,0
"""
    osu = parse_osu_file(content)
    assert osu.bpm_min == osu.bpm_max == osu.timing_bpm


def test_bpm_range_multi_bpm_map():
    """Multi-BPM map reports correct min/max."""
    content = """[General]

[TimingPoints]
0,375.0,4,0,0,100,1,0
10000,300.0,4,0,0,100,1,0

[HitObjects]
256,192,1000,5,0
"""
    osu = parse_osu_file(content)
    assert osu.bpm_min == 160.0
    assert osu.bpm_max == 200.0
    assert osu.timing_bpm == 160.0


def test_slider_velocity_no_inherited_point():
    """A slider with no covering inherited timing point uses SV = 1."""
    content = """[General]

[TimingPoints]
0,333.33,4,0,0,100,1,0

[HitObjects]
256,192,1000,6,0,L|100:100,1,100
"""
    osu = parse_osu_file(content)
    obj = osu.hit_objects[0]
    assert obj.is_slider
    assert osu.effective_sv_at(1000) == 1.0


def test_slider_velocity_with_inherited_point():
    """An inherited timing point with beatLength=-50 computes SV=2.0."""
    content = """[General]

[TimingPoints]
0,333.33,4,0,0,100,1,0
5000,-50,4,0,0,100,0,0

[HitObjects]
256,192,6000,6,0,L|100:100,1,100
"""
    osu = parse_osu_file(content)
    assert osu.effective_sv_at(6000) == 2.0


def test_slider_data_no_longer_has_fake_multiplier_field():
    """Regression test: SliderData no longer has fake multiplier/tick_rate."""
    content = """[General]

[HitObjects]
256,192,1000,6,0,L|100:100,1,100
"""
    osu = parse_osu_file(content)
    obj = osu.hit_objects[0]
    assert obj.is_slider
    slider = obj.slider
    assert slider is not None
    assert not hasattr(slider, "multiplier")
    assert not hasattr(slider, "tick_rate")


def test_hit_object_negative_x_coordinate():
    """A hit object with negative x coordinate parses successfully."""
    content = """[General]

[HitObjects]
-5,192,1000,5,0
"""
    osu = parse_osu_file(content)
    assert len(osu.hit_objects) == 1
    assert osu.hit_objects[0].x == -5.0
    assert osu.hit_objects[0].y == 192.0


def test_hit_object_negative_y_coordinate():
    """A hit object with negative y coordinate parses successfully."""
    content = """[General]

[HitObjects]
256,-10,1000,5,0
"""
    osu = parse_osu_file(content)
    assert len(osu.hit_objects) == 1
    assert osu.hit_objects[0].x == 256.0
    assert osu.hit_objects[0].y == -10.0


def test_timing_point_missing_trailing_fields():
    """A timing point line with only time,beatLength parses with defaults."""
    content = """[General]

[TimingPoints]
0,333.33

[HitObjects]
256,192,1000,5,0
"""
    osu = parse_osu_file(content)
    assert abs(osu.timing_bpm - 180.0) < 1.0


def test_parse_spinner_with_end_time():
    content = """[General]

[HitObjects]
256,192,1000,12,0,3000
"""
    osu = parse_osu_file(content)
    obj = osu.hit_objects[0]
    assert obj.is_spinner
    assert obj.spinner_end == 3000


def test_parse_malformed_hit_object_skipped():
    content = """[General]

[HitObjects]
256,192,1000,5,0
not,a,valid,line
384,256,1500,5,0
"""
    osu = parse_osu_file(content)
    assert len(osu.hit_objects) == 2


def test_parse_multiple_sliders():
    content = """[General]

[HitObjects]
256,192,1000,6,0,L|100:100,1,100
384,256,1500,6,0,L|500:300:600:200,2,200
"""
    osu = parse_osu_file(content)
    assert len(osu.hit_objects) == 2
    assert osu.hit_objects[0].is_slider
    assert osu.hit_objects[1].is_slider
    assert osu.hit_objects[0].slider.repeats == 1
    assert osu.hit_objects[1].slider.repeats == 2
    assert osu.hit_objects[1].slider.pixel_length == 200.0


def test_parse_metadata_fallback_to_general():
    content = """[General]
Title:General Title
Artist:General Artist
Creator:General Creator
Version:Easy

[HitObjects]
256,192,1000,5,0
"""
    osu = parse_osu_file(content)
    assert osu.metadata.title == "General Title"
    assert osu.metadata.artist == "General Artist"
    assert osu.metadata.creator == "General Creator"
    assert osu.metadata.version == "Easy"


def test_parse_metadata_metadata_overrides_general():
    content = """[General]
Title:General Title
Artist:General Artist

[Metadata]
Title:Metadata Title
Artist:Metadata Artist

[HitObjects]
256,192,1000,5,0
"""
    osu = parse_osu_file(content)
    assert osu.metadata.title == "Metadata Title"
    assert osu.metadata.artist == "Metadata Artist"


def test_parse_colours_no_colours_section():
    content = """[General]

[HitObjects]
256,192,1000,5,0
"""
    osu = parse_osu_file(content)
    assert osu.combo_colors == []


def test_parse_colours_with_hash_prefix():
    content = """[Colours]
Combo1Colour:#FF0000

[HitObjects]
256,192,1000,5,0
"""
    osu = parse_osu_file(content)
    assert len(osu.combo_colors) == 1
    assert osu.combo_colors[0] == 0xFF0000


def test_parse_colours_invalid_hex_skipped():
    content = """[Colours]
Combo1Colour:ZZZZZZ
Combo2Colour:AABBCC

[HitObjects]
256,192,1000,5,0
"""
    osu = parse_osu_file(content)
    assert len(osu.combo_colors) == 1
    assert osu.combo_colors[0] == 0xAABBCC


def test_parse_hit_sample():
    content = """[General]

[HitObjects]
256,192,1000,5,0,Normal:Clap:0::
"""
    osu = parse_osu_file(content)
    obj = osu.hit_objects[0]
    assert obj.hit_sample == "Normal:Clap:0::"


def test_parse_combo_colour_derived():
    content = """[General]

[Colours]
Combo1Colour:255,0,0
Combo2Colour:0,255,0

[HitObjects]
256,192,1000,5,0
384,256,1500,5,0
512,192,2000,1,0
"""
    osu = parse_osu_file(content)
    assert len(osu.hit_objects) == 3
    # First object: combo index 0, colour 0 % 2 = 0
    assert osu.hit_objects[0].combo_colour == 0
    # Second object: combo index 1 (after first NEW_COMBO), colour 1 % 2 = 1
    assert osu.hit_objects[1].combo_colour == 1
    # Third object: combo index 2 (after second NEW_COMBO), colour 2 % 2 = 0
    assert osu.hit_objects[2].combo_colour == 0


def test_parse_combo_colour_with_skip():
    content = """[General]

[Colours]
Combo1Colour:255,0,0
Combo2Colour:0,255,0
Combo3Colour:0,0,255

[HitObjects]
256,192,1000,5,0
384,256,1500,21,0
512,192,2000,5,0
"""
    osu = parse_osu_file(content)
    assert len(osu.hit_objects) == 3
    # First object: combo index 0, colour 0 % 3 = 0
    assert osu.hit_objects[0].combo_colour == 0
    # Second object: combo index 1 (after first NEW_COMBO), colour 1 % 3 = 1
    assert osu.hit_objects[1].combo_colour == 1
    # Third object: combo index 3 (after second NEW_COMBO + COLOUR_SKIP_1), colour 3 % 3 = 0
    assert osu.hit_objects[2].combo_colour == 0


def test_hit_object_type_flags():
    """Verify the renamed HitObjectType flags."""
    assert HitObjectType.COLOUR_SKIP_1 == 16
    assert HitObjectType.COLOUR_SKIP_2 == 32
    assert HitObjectType.COLOUR_SKIP_4 == 64
    assert HitObjectType.MANIA_HOLD == 128


def test_count_circles_and_sliders():
    """Verify circle and slider counts for a pattern with mixed object types."""
    content = """[General]

[HitObjects]
256,192,1000,5,0
256,192,1500,6,0,L|100:100,1,100
384,256,2000,5,0
384,256,2500,6,0,L|500:300,1,100
512,320,3000,5,0
"""
    osu = parse_osu_file(content)
    assert osu.circle_count == 3
    assert osu.slider_count == 2


def test_count_only_circles():
    """Verify count when only circles are present."""
    content = """[General]

[HitObjects]
256,192,1000,5,0
384,256,1500,5,0
512,320,2000,5,0
"""
    osu = parse_osu_file(content)
    assert osu.circle_count == 3
    assert osu.slider_count == 0


def test_count_only_sliders():
    """Verify count when only sliders are present."""
    content = """[General]

[HitObjects]
256,192,1000,6,0,L|100:100,1,100
384,256,1500,6,0,L|500:300,2,200
"""
    osu = parse_osu_file(content)
    assert osu.circle_count == 0
    assert osu.slider_count == 2


def test_count_with_spinners_excluded():
    """Verify spinners are not counted in circle or slider counts."""
    content = """[General]

[HitObjects]
256,192,1000,5,0
256,192,1500,12,0,2000
384,256,2000,5,0
512,320,2500,12,0,3000
"""
    osu = parse_osu_file(content)
    assert osu.circle_count == 2
    assert osu.slider_count == 0
    assert len(osu.hit_objects) == 4
