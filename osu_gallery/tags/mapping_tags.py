"""Auto-detection of object type tags from parsed .osu file data.

Only counts circles, sliders, and spinners. All other mapping tags
(e.g., kicksliders, angled patterns, screen coverage) are added manually
by the user via the import dialog.
"""

from __future__ import annotations

from osu_gallery.parser.models import OsuFile
from osu_gallery.tags._format_helpers import format_object_count


def detect_object_tags(osu_file: OsuFile) -> list[str]:
    """Auto-detect object type tags (circles, sliders, spinners).

    Only counts the number of circles, sliders, and spinners in the
    parsed OsuFile. Does not detect slider patterns, angles, or coverage.

    Args:
        osu_file: The parsed OsuFile object to analyze.

    Returns:
        A list of object count tag strings (e.g., ['3 circles', '2 sliders']).
    """
    tags: list[str] = []
    if osu_file.circle_count > 0:
        tags.append(format_object_count(osu_file.circle_count, "circle"))
    if osu_file.slider_count > 0:
        tags.append(format_object_count(osu_file.slider_count, "slider"))
    spinners = sum(1 for obj in osu_file.hit_objects if obj.is_spinner)
    if spinners > 0:
        tags.append(format_object_count(spinners, "spinner"))
    return tags
