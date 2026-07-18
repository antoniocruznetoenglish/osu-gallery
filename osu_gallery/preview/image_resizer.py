"""Image resizing utility for user-provided images.

Resizes user images to target dimensions while maintaining 4:3 aspect ratio
with padding for non-4:3 images.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QBuffer, QByteArray, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap

logger = logging.getLogger(__name__)


def resize_image_for_thumbnail(
    image_bytes: bytes, target_width: int = 512, target_height: int = 384
) -> bytes:
    """Resize a user image to thumbnail dimensions (512x384).

    Maintains 4:3 aspect ratio by padding with dark background if needed.

    Args:
        image_bytes: Raw image bytes (PNG, JPG, etc.).
        target_width: Target width in pixels (default 512).
        target_height: Target height in pixels (default 384).

    Returns:
        Resized image as bytes in PNG format.
    """
    return _resize_image(image_bytes, target_width, target_height)


def resize_image_for_preview(
    image_bytes: bytes, target_width: int = 1536, target_height: int = 1152
) -> bytes:
    """Resize a user image to preview dimensions (1536x1152).

    Maintains 4:3 aspect ratio by padding with dark background if needed.

    Args:
        image_bytes: Raw image bytes (PNG, JPG, etc.).
        target_width: Target width in pixels (default 1536).
        target_height: Target height in pixels (default 1152).

    Returns:
        Resized image as bytes in PNG format.
    """
    return _resize_image(image_bytes, target_width, target_height)


def _resize_image(image_bytes: bytes, target_width: int, target_height: int) -> bytes:
    """Internal resize implementation with 4:3 aspect ratio padding.

    Args:
        image_bytes: Raw image bytes.
        target_width: Target width in pixels.
        target_height: Target height in pixels.

    Returns:
        Resized image as bytes in PNG format.
    """
    if not image_bytes:
        return b""

    pixmap = QPixmap()
    if not pixmap.loadFromData(image_bytes):
        logger.warning("Failed to load image from bytes")
        return b""

    # Calculate scaled size maintaining 4:3 aspect ratio
    source_ratio = pixmap.width() / pixmap.height()
    target_ratio = target_width / target_height

    if source_ratio > target_ratio:
        # Image is wider than 4:3 - scale to height, pad sides
        scaled_height = target_height
        scaled_width = int(scaled_height * source_ratio)
        if scaled_width > target_width:
            scaled_width = target_width
            scaled_height = int(scaled_width / source_ratio)
    else:
        # Image is taller than 4:3 - scale to width, pad top/bottom
        scaled_width = target_width
        scaled_height = int(scaled_width / source_ratio)
        if scaled_height > target_height:
            scaled_height = target_height
            scaled_width = int(scaled_height * source_ratio)

    # Center the image in the target canvas
    x_offset = (target_width - scaled_width) // 2
    y_offset = (target_height - scaled_height) // 2

    # Create canvas with dark background
    canvas = QPixmap(target_width, target_height)
    canvas.fill(QColor(25, 25, 25))  # Dark background

    # Scale and draw
    scaled_pixmap = pixmap.scaled(
        scaled_width, scaled_height,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )

    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.drawPixmap(x_offset, y_offset, scaled_pixmap)
    painter.end()

    # Convert to bytes
    qba = QByteArray()
    buffer = QBuffer(qba)
    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
    canvas.save(buffer, "PNG")
    buffer.close()
    return bytes(qba)
