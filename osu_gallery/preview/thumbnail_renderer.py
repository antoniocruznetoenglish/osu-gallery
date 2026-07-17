"""Thumbnail and pattern preview renderer using PySide6."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QPixmap

if TYPE_CHECKING:
    from osu_gallery.parser.models import OsuFile

logger = logging.getLogger(__name__)

_OSU_WIDTH = 512.0
_OSU_HEIGHT = 384.0
_PADDING = 0.10

_DEFAULT_COMBO_COLORS: list[tuple[int, int, int]] = [
    (255, 100, 100),
    (100, 255, 100),
    (100, 100, 255),
    (255, 255, 100),
    (255, 100, 255),
    (100, 255, 255),
    (255, 165, 0),
]


def _get_combo_color(combo_colour: int, combo_colors: list[int]) -> QColor:
    """Resolve a combo colour index to a QColor."""
    if combo_colors:
        hex_val = combo_colors[combo_colour % len(combo_colors)]
    else:
        r, g, b = _DEFAULT_COMBO_COLORS[combo_colour % len(_DEFAULT_COMBO_COLORS)]
        hex_val = (r << 16) | (g << 8) | b
    return QColor(f"#{hex_val:06x}")


def _circle_radius(circle_size: float) -> float:
    """Map osu! circle_size (0-10) to pixel radius (roughly 30-6 range)."""
    clamped = max(0.0, min(10.0, circle_size))
    return 30.0 - (clamped * 2.4)


def _map_coords(
    x: float, y: float, scale_x: float, scale_y: float, offset_x: float, offset_y: float
) -> tuple[float, float]:
    """Map osu! coordinates to thumbnail pixel coordinates."""
    return x * scale_x + offset_x, y * scale_y + offset_y


def _draw_circle(
    painter: QPainter,
    x: float,
    y: float,
    radius: float,
    color: QColor,
) -> None:
    """Draw a filled circle at (x, y) with the given radius and color."""
    painter.setPen(QPen(color.darker(130), max(1.0, radius * 0.08)))
    painter.setBrush(QBrush(color))
    painter.drawEllipse(QRectF(x - radius, y - radius, radius * 2, radius * 2))


def _draw_slider_path(
    painter: QPainter,
    slider_data,
    start_x: float,
    start_y: float,
    scale_x: float,
    scale_y: float,
    offset_x: float,
    offset_y: float,
    color: QColor,
) -> None:
    """Draw slider path as line segments."""
    if not slider_data.path:
        return

    pen = QPen(color, max(2.0, 4.0 * scale_x))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)

    prev_px: tuple[float, float] = (
        start_x * scale_x + offset_x,
        start_y * scale_y + offset_y,
    )

    for path_segment in slider_data.path:
        points = path_segment.points
        if not points:
            continue

        for px, py in points:
            curr_px, curr_py = _map_coords(px, py, scale_x, scale_y, offset_x, offset_y)

            if path_segment.path_type == "B" and len(points) > 2:
                for i in range(len(points) - 2):
                    x0, y0 = _map_coords(
                        points[i][0], points[i][1], scale_x, scale_y, offset_x, offset_y
                    )
                    x1, y1 = _map_coords(
                        points[i + 1][0], points[i + 1][1], scale_x, scale_y, offset_x, offset_y
                    )
                    x2, y2 = _map_coords(
                        points[i + 2][0], points[i + 2][1], scale_x, scale_y, offset_x, offset_y
                    )
                    cpx = x1
                    cpy = y1
                    steps = 10
                    for s in range(1, steps + 1):
                        t = s / steps
                        inv_t = 1.0 - t
                        interp_x = (
                            inv_t * inv_t * x0 + 2 * inv_t * t * cpx + t * t * x2
                        )
                        interp_y = (
                            inv_t * inv_t * y0 + 2 * inv_t * t * cpy + t * t * y2
                        )
                        painter.drawLine(prev_px[0], prev_px[1], interp_x, interp_y)
                        prev_px = (interp_x, interp_y)
                break
            else:
                painter.drawLine(prev_px[0], prev_px[1], curr_px, curr_py)
                prev_px = (curr_px, curr_py)


def _render_objects(
    painter: QPainter,
    osu_file: OsuFile,
    width: float,
    height: float,
    scale_x: float,
    scale_y: float,
    offset_x: float,
    offset_y: float,
) -> None:
    """Draw all hit objects onto the painter."""
    circle_size = _circle_radius(osu_file.difficulty.circle_size)

    for obj in osu_file.hit_objects:
        color = _get_combo_color(obj.combo_colour, osu_file.combo_colors)

        if obj.is_circle:
            px, py = _map_coords(obj.x, obj.y, scale_x, scale_y, offset_x, offset_y)
            _draw_circle(painter, px, py, circle_size, color)

        elif obj.is_slider:
            px, py = _map_coords(obj.x, obj.y, scale_x, scale_y, offset_x, offset_y)
            _draw_circle(painter, px, py, circle_size, color)
            if obj.slider is not None:
                _draw_slider_path(
                    painter,
                    obj.slider,
                    obj.x,
                    obj.y,
                    scale_x,
                    scale_y,
                    offset_x,
                    offset_y,
                    color,
                )

        elif obj.is_spinner:
            px, py = _map_coords(obj.x, obj.y, scale_x, scale_y, offset_x, offset_y)
            spinner_radius = circle_size * 4.0
            spinner_color = QColor(color)
            spinner_color.setAlpha(80)
            painter.setPen(QPen(color.darker(130), 2.0))
            painter.setBrush(QBrush(spinner_color))
            diameter = spinner_radius * 2
            painter.drawEllipse(
                QRectF(px - spinner_radius, py - spinner_radius, diameter, diameter)
            )


def render_thumbnail(
    osu_file: OsuFile,
    width: int = 200,
    height: int = 150,
) -> QPixmap:
    """Render a scaled thumbnail of the osu! beatmap.

    Args:
        osu_file: Parsed OsuFile to render.
        width: Thumbnail width in pixels.
        height: Thumbnail height in pixels.

    Returns:
        QPixmap with the rendered thumbnail.
    """
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    padding_px_x = width * _PADDING
    padding_px_y = height * _PADDING
    available_w = width - 2 * padding_px_x
    available_h = height - 2 * padding_px_y

    scale_x = available_w / _OSU_WIDTH
    scale_y = available_h / _OSU_HEIGHT
    offset_x = padding_px_x
    offset_y = padding_px_y

    _render_objects(painter, osu_file, width, height, scale_x, scale_y, offset_x, offset_y)

    painter.end()
    return pixmap


def render_pattern_preview(
    osu_file: OsuFile,
    width: int = 512,
    height: int = 384,
) -> QPixmap:
    """Render a full-resolution pattern preview of the osu! beatmap.

    Args:
        osu_file: Parsed OsuFile to render.
        width: Preview width in pixels (default 512).
        height: Preview height in pixels (default 384).

    Returns:
        QPixmap with the rendered preview at native osu! resolution.
    """
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    padding_px_x = width * _PADDING
    padding_px_y = height * _PADDING
    available_w = width - 2 * padding_px_x
    available_h = height - 2 * padding_px_y

    scale_x = available_w / _OSU_WIDTH
    scale_y = available_h / _OSU_HEIGHT
    offset_x = padding_px_x
    offset_y = padding_px_y

    _render_objects(painter, osu_file, width, height, scale_x, scale_y, offset_x, offset_y)

    painter.end()
    return pixmap
