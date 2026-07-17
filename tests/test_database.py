"""Tests for the SQLite database layer (Phase 2)."""

import pytest

from osu_gallery.db.database import DatabaseError, GalleryDatabase


@pytest.fixture
def db(tmp_path):
    """Create a fresh in-memory database for each test."""
    db_path = tmp_path / "test.db"
    database = GalleryDatabase(db_path)
    yield database
    database.close()


# -- Tag CRUD --

def test_create_tag(db):
    tag = db.create_tag("slider", "slider_type")
    assert tag.id is not None
    assert tag.name == "slider"
    assert tag.category == "slider_type"


def test_get_tag(db):
    created = db.create_tag("circle_pattern", "circle")
    fetched = db.get_tag(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.name == "circle_pattern"
    assert fetched.category == "circle"


def test_get_tag_not_found(db):
    assert db.get_tag(9999) is None


def test_get_tag_by_name(db):
    db.create_tag("slider", "slider_type")
    tag = db.get_tag_by_name("slider")
    assert tag is not None
    assert tag.name == "slider"


def test_get_tag_by_name_not_found(db):
    assert db.get_tag_by_name("nonexistent") is None


def test_get_all_tags(db):
    db.create_tag("alpha")
    db.create_tag("beta")
    db.create_tag("gamma")
    tags = db.get_all_tags()
    assert len(tags) == 3
    names = [t.name for t in tags]
    assert names == ["alpha", "beta", "gamma"]


def test_update_tag(db):
    tag = db.create_tag("old_name", "old_cat")
    tag.name = "new_name"
    tag.category = "new_cat"
    db.update_tag(tag)
    fetched = db.get_tag(tag.id)
    assert fetched.name == "new_name"
    assert fetched.category == "new_cat"


def test_delete_tag(db):
    tag = db.create_tag("to_delete")
    db.delete_tag(tag.id)
    assert db.get_tag(tag.id) is None


def test_tag_name_unique(db):
    db.create_tag("unique_tag")
    with pytest.raises(DatabaseError):
        db.create_tag("unique_tag")


# -- Pattern CRUD --

def test_create_pattern(db):
    pattern = db.create_pattern(
        raw_code="[HitObjects]\n256,192,1000,1|2,0",
        object_count=1,
        timing_bpm=120.0,
    )
    assert pattern.id is not None
    assert pattern.object_count == 1
    assert pattern.timing_bpm == 120.0
    assert pattern.raw_code == "[HitObjects]\n256,192,1000,1|2,0"


def test_get_pattern(db):
    created = db.create_pattern(raw_code="test code", object_count=3, timing_bpm=90.0)
    fetched = db.get_pattern(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.object_count == 3
    assert fetched.timing_bpm == 90.0
    assert fetched.raw_code == "test code"
    assert fetched.tag_ids == []


def test_get_pattern_not_found(db):
    assert db.get_pattern(9999) is None


def test_get_all_patterns(db):
    db.create_pattern("pattern_a", object_count=1)
    db.create_pattern("pattern_b", object_count=2)
    patterns = db.get_all_patterns()
    assert len(patterns) == 2


def test_update_pattern(db):
    pattern = db.create_pattern(raw_code="old", object_count=1)
    pattern.raw_code = "new code"
    pattern.object_count = 5
    db.update_pattern(pattern)
    fetched = db.get_pattern(pattern.id)
    assert fetched.raw_code == "new code"
    assert fetched.object_count == 5


def test_delete_pattern(db):
    pattern = db.create_pattern(raw_code="to_delete")
    db.delete_pattern(pattern.id)
    assert db.get_pattern(pattern.id) is None


def test_pattern_default_values(db):
    pattern = db.create_pattern(raw_code="minimal")
    assert pattern.object_count == 0
    assert pattern.timing_bpm == 0.0


def test_create_pattern_with_circle_slider_counts(db):
    pattern = db.create_pattern(
        raw_code="test code",
        object_count=5,
        circle_count=3,
        slider_count=2,
        timing_bpm=120.0,
    )
    assert pattern.id is not None
    assert pattern.circle_count == 3
    assert pattern.slider_count == 2
    assert pattern.object_count == 5


def test_get_pattern_returns_circle_slider_counts(db):
    created = db.create_pattern(
        raw_code="test",
        object_count=4,
        circle_count=2,
        slider_count=2,
    )
    fetched = db.get_pattern(created.id)
    assert fetched is not None
    assert fetched.circle_count == 2
    assert fetched.slider_count == 2
    assert fetched.object_count == 4


def test_update_pattern_circle_slider_counts(db):
    pattern = db.create_pattern(raw_code="old", object_count=1)
    pattern.circle_count = 3
    pattern.slider_count = 1
    pattern.object_count = 4
    db.update_pattern(pattern)
    fetched = db.get_pattern(pattern.id)
    assert fetched.circle_count == 3
    assert fetched.slider_count == 1
    assert fetched.object_count == 4


def test_get_all_patterns_includes_circle_slider_counts(db):
    db.create_pattern("p1", object_count=1, circle_count=1, slider_count=0)
    db.create_pattern("p2", object_count=3, circle_count=1, slider_count=2)
    patterns = db.get_all_patterns()
    by_id = {p.id: p for p in patterns}
    assert by_id[patterns[0].id].circle_count in (1, 1)
    assert by_id[patterns[0].id].slider_count in (0, 2)


def test_get_patterns_by_tag_includes_circle_slider_counts(db):
    tag = db.create_tag("test_tag")
    p1 = db.create_pattern("p1", object_count=2, circle_count=1, slider_count=1)
    p2 = db.create_pattern("p2", object_count=1, circle_count=1, slider_count=0)
    db.add_tag_to_pattern(p1.id, tag.id)
    db.add_tag_to_pattern(p2.id, tag.id)
    patterns = db.get_patterns_by_tag(tag.id)
    assert len(patterns) == 2
    for p in patterns:
        assert hasattr(p, "circle_count")
        assert hasattr(p, "slider_count")


# -- Tag-Pattern relationships --

def test_add_tag_to_pattern(db):
    tag = db.create_tag("slider")
    pattern = db.create_pattern("test")
    db.add_tag_to_pattern(pattern.id, tag.id)
    tags = db.get_pattern_tags(pattern.id)
    assert len(tags) == 1
    assert tags[0].name == "slider"


def test_add_tag_to_pattern_duplicate_raises(db):
    tag = db.create_tag("slider")
    pattern = db.create_pattern("test")
    db.add_tag_to_pattern(pattern.id, tag.id)
    with pytest.raises(DatabaseError):
        db.add_tag_to_pattern(pattern.id, tag.id)


def test_remove_tag_from_pattern(db):
    tag = db.create_tag("slider")
    pattern = db.create_pattern("test")
    db.add_tag_to_pattern(pattern.id, tag.id)
    db.remove_tag_from_pattern(pattern.id, tag.id)
    tags = db.get_pattern_tags(pattern.id)
    assert len(tags) == 0


def test_get_pattern_tags_empty(db):
    pattern = db.create_pattern("test")
    tags = db.get_pattern_tags(pattern.id)
    assert tags == []


def test_get_patterns_by_tag(db):
    tag = db.create_tag("slider")
    p1 = db.create_pattern("pattern_1")
    p3 = db.create_pattern("pattern_3")
    db.add_tag_to_pattern(p1.id, tag.id)
    db.add_tag_to_pattern(p3.id, tag.id)
    patterns = db.get_patterns_by_tag(tag.id)
    assert len(patterns) == 2
    ids = {p.id for p in patterns}
    assert ids == {p1.id, p3.id}


def test_set_pattern_tags_replaces(db):
    tag_a = db.create_tag("tag_a")
    tag_b = db.create_tag("tag_b")
    tag_c = db.create_tag("tag_c")
    pattern = db.create_pattern("test")
    db.add_tag_to_pattern(pattern.id, tag_a.id)
    db.add_tag_to_pattern(pattern.id, tag_b.id)
    db.set_pattern_tags(pattern.id, [tag_c.id])
    tags = db.get_pattern_tags(pattern.id)
    assert len(tags) == 1
    assert tags[0].name == "tag_c"


def test_delete_tag_cascades_to_pattern_tags(db):
    tag = db.create_tag("cascading_tag")
    pattern = db.create_pattern("test")
    db.add_tag_to_pattern(pattern.id, tag.id)
    db.delete_tag(tag.id)
    tags = db.get_pattern_tags(pattern.id)
    assert tags == []


def test_delete_pattern_cascades_to_pattern_tags(db):
    tag = db.create_tag("slider")
    pattern = db.create_pattern("test")
    db.add_tag_to_pattern(pattern.id, tag.id)
    db.delete_pattern(pattern.id)
    tags = db.get_pattern_tags(pattern.id)
    assert tags == []


def test_get_tags_with_pattern_count(db):
    tag1 = db.create_tag("common")
    tag2 = db.create_tag("rare")
    p1 = db.create_pattern("p1")
    p2 = db.create_pattern("p2")
    p3 = db.create_pattern("p3")
    db.add_tag_to_pattern(p1.id, tag1.id)
    db.add_tag_to_pattern(p2.id, tag1.id)
    db.add_tag_to_pattern(p3.id, tag2.id)
    counts = db.get_tags_with_pattern_count()
    by_name = {c["name"]: c["pattern_count"] for c in counts}
    assert by_name["common"] == 2
    assert by_name["rare"] == 1


def test_pattern_get_includes_tag_ids(db):
    tag = db.create_tag("slider")
    pattern = db.create_pattern("test")
    db.add_tag_to_pattern(pattern.id, tag.id)
    fetched = db.get_pattern(pattern.id)
    assert tag.id in fetched.tag_ids
