"""Shared formatting helpers for object count display."""

from __future__ import annotations


def format_object_count(count: int, object_type: str) -> str:
    """Format an object count with correct singular/plural form.

    Args:
        count: The number of objects (non-negative integer).
        object_type: One of 'circle', 'slider', 'spinner'.

    Returns:
        A string like '1 circle' or '3 circles'.

    Raises:
        ValueError: If object_type is not one of the supported types.
    """
    if object_type == "circle":
        suffix = "circle" if count == 1 else "circles"
    elif object_type == "slider":
        suffix = "slider" if count == 1 else "sliders"
    elif object_type == "spinner":
        suffix = "spinner" if count == 1 else "spinners"
    else:
        raise ValueError(
            f"Unknown object_type: {object_type!r}. "
            f"Must be one of 'circle', 'slider', 'spinner'."
        )
    return f"{count} {suffix}"
