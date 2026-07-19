"""Clipboard utility for copying pattern code to the system clipboard."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QApplication

if TYPE_CHECKING:
    from PySide6.QtCore import QObject

logger = logging.getLogger(__name__)


def copy_to_clipboard(text: str, parent: QObject | None = None) -> None:
    """Copy text to the system clipboard.

    Parameters
    ----------
    text:
        The text to copy.
    parent:
        Optional parent QObject for the QApplication reference.
    """
    app = QApplication.instance()
    if app is None:
        logger.warning("No QApplication instance available; cannot copy to clipboard")
        return

    clipboard = app.clipboard()
    try:
        clipboard.setText(text)
    except Exception as exc:
        logger.warning(
            "QClipboard.setText() raised %s: %s — clipboard write failed",
            type(exc).__name__,
            exc,
        )
        return

    try:
        readback = clipboard.text()
    except Exception as exc:
        logger.warning(
            "QClipboard.text() readback raised %s: %s — cannot verify clipboard round-trip",
            type(exc).__name__,
            exc,
        )
        return

    if readback != text:
        logger.warning(
            "Clipboard readback mismatch: wrote %d bytes, read back %d bytes — "
            "the text may not be available to other applications on this system",
            len(text),
            len(readback),
        )
        return

    logger.debug("Copied %d bytes to clipboard", len(text))
