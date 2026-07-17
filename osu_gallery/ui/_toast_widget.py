"""Toast notification widget for brief on-screen messages."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QVBoxLayout, QWidget

logger = logging.getLogger(__name__)


class _ToastWidget(QWidget):
    """A transient notification that fades in, holds briefly, then fades out."""

    _DEFAULT_MESSAGE = "Copied!"
    _DEFAULT_DURATION_MS = 1800
    _FADE_DURATION_MS = 250
    _BG_COLOR = QColor(40, 40, 40)
    _TEXT_COLOR = QColor(220, 220, 220)
    _BORDER_COLOR = QColor(90, 150, 220)
    _PADDING = 14

    def __init__(
        self,
        message: str = _DEFAULT_MESSAGE,
        parent: QWidget | None = None,
        duration_ms: int = _DEFAULT_DURATION_MS,
    ) -> None:
        """Create the toast widget.

        Parameters
        ----------
        message:
            The text to display.
        parent:
            The parent widget.
        duration_ms:
            How long the toast stays visible (including fade).
        """
        super().__init__(parent)
        self._duration_ms = duration_ms

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        self._label = QLabel(message, self)
        self._label.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
        self._label.setStyleSheet(
            "color: rgb(220, 220, 220); background: transparent;"
        )
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(self._PADDING, self._PADDING, self._PADDING, self._PADDING)
        layout.addWidget(self._label, alignment=Qt.AlignmentFlag.AlignCenter)

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._fade_in = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._fade_in.setDuration(self._FADE_DURATION_MS)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)

        self._fade_out = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._fade_out.setDuration(self._FADE_DURATION_MS)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.finished.connect(self.close)

        self._stay_timer = QTimer(self)
        self._stay_timer.setSingleShot(True)
        self._stay_timer.timeout.connect(self._start_fade_out)

    def _start_fade_out(self) -> None:
        """Begin the fade-out animation."""
        self._fade_out.start()

    def show_at(self, parent: QWidget | None) -> None:
        """Position and show the toast near the center of the parent widget."""
        if parent is None:
            return

        parent_rect = parent.rect()
        self._label.adjustSize()
        content_size = self.sizeHint()
        x = parent_rect.center().x() - content_size.width() // 2
        y = parent_rect.center().y() - content_size.height() // 2
        self.setGeometry(x, y, content_size.width(), content_size.height())

        self._fade_in.start()
        stay_duration = max(100, self._duration_ms - 2 * self._FADE_DURATION_MS)
        self._stay_timer.start(stay_duration)


_toast_instance: _ToastWidget | None = None


def show_toast(
    message: str = "Copied!",
    parent: QObject | None = None,
    duration_ms: int = _ToastWidget._DEFAULT_DURATION_MS,
) -> None:
    """Show a toast notification.

    If a toast is already visible, close it first and show the new one.

    Parameters
    ----------
    message:
        The message to display.
    parent:
        The parent widget to center the toast on.
    duration_ms:
        How long the toast stays visible (including fade).
    """
    global _toast_instance

    if _toast_instance is not None and _toast_instance.isVisible():
        _toast_instance.close()

    widget = _ToastWidget(message=message, duration_ms=duration_ms)
    _toast_instance = widget
    widget.show_at(parent)
