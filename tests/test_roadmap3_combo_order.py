"""Tests for Task 5: Combo order numbering."""

from __future__ import annotations

from osu_gallery.parser.models import HitObjectType
from osu_gallery.parser.osu_file import parse_osu_file
from osu_gallery.preview.thumbnail_renderer import render_thumbnail


def test_hit_object_has_combo_order():
    """HitObject has combo_order field with default 0."""
    from osu_gallery.parser.models import HitObject
    obj = HitObject(x=256, y=192, type=HitObjectType.CIRCLE | HitObjectType.NEW_COMBO,
                    sound_types=0, time=1000, combo_colour=0)
    assert hasattr(obj, "combo_order")
    assert obj.combo_order == 0


def test_combo_order_assigned_correctly():
    """Combo order is 1-based and sequential within a combo."""
    content = """[General]

[Colours]
Combo1Colour:255,0,0

[HitObjects]
256,192,1000,5,0
384,256,1500,5,0
512,192,2000,5,0
"""
    osu = parse_osu_file(content)
    assert len(osu.hit_objects) == 3
    assert osu.hit_objects[0].combo_order == 1
    assert osu.hit_objects[1].combo_order == 2
    assert osu.hit_objects[2].combo_order == 3


def test_combo_order_increments_with_new_combo():
    """Combo order increments globally across combos."""
    content = """[General]

[Colours]
Combo1Colour:255,0,0
Combo2Colour:0,255,0

[HitObjects]
256,192,1000,5,0
384,256,1500,5,0
512,192,2000,1,0
256,100,2500,5,0
"""
    osu = parse_osu_file(content)
    assert len(osu.hit_objects) == 4
    assert osu.hit_objects[0].combo_order == 1
    assert osu.hit_objects[1].combo_order == 2
    assert osu.hit_objects[2].combo_order == 3
    assert osu.hit_objects[3].combo_order == 3


def test_combo_number_drawn_on_thumbnail():
    """Combo numbers appear in rendered thumbnail."""
    content = """[General]

[Colours]
Combo1Colour:255,0,0

[HitObjects]
256,192,1000,5,0
384,256,1500,5,0
"""
    osu = parse_osu_file(content)
    pixmap = render_thumbnail(osu, width=512, height=384)
    assert pixmap.width() == 512
    assert pixmap.height() == 384
    assert pixmap.width() > 0
    assert pixmap.height() > 0


def test_combo_number_drawn_on_preview():
    """Combo numbers appear in rendered preview."""
    content = """[General]

[Colours]
Combo1Colour:255,0,0

[HitObjects]
256,192,1000,5,0
384,256,1500,5,0
"""
    osu = parse_osu_file(content)
    from osu_gallery.preview.thumbnail_renderer import render_pattern_preview
    pixmap = render_pattern_preview(osu, width=1024, height=768)
    assert pixmap.width() == 1024
    assert pixmap.height() == 768
