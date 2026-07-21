"""Thumbnail widget for displaying rendered beatmap pattern previews."""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QPoint, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeySequence, QPainter, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QMenu,
    QMessageBox,
    QWidget,
)

from osu_gallery._constants import (
    FONT_FAMILY,
    THUMBNAIL_WIDGET_MIN_HEIGHT,
    THUMBNAIL_WIDGET_MIN_WIDTH,
)
from osu_gallery.db.database import GalleryDatabase
from osu_gallery.parser.models import OsuFile
from osu_gallery.parser.osu_file import ParseError, parse_osu_file
from osu_gallery.preview.thumbnail_renderer import render_thumbnail
from osu_gallery.tags._format_helpers import format_object_count
from osu_gallery.ui._clipboard import copy_to_clipboard
from osu_gallery.ui._toast_widget import show_toast

logger = logging.getLogger(__name__)


class _ThumbnailWidget(QWidget):
    """A widget that renders a thumbnail of a beatmap pattern.

    Loads the pattern's raw_code from the database, parses it, and renders
    a thumbnail using the preview renderer. Displays the thumbnail along
    with an object count label and combo color indicator.

    Supports right-click context menu with "Copy Code" action and a keyboard
    shortcut (Ctrl+C) for the same action.
    """

    pattern_clicked = Signal(int)
    pattern_copied = Signal(int)
    pattern_deleted = Signal(int)
    pattern_edited = Signal(int)

    _HOVER_BORDER_COLOR = (90, 150, 220)
    _NORMAL_BORDER_COLOR = (180, 180, 180)
    _LABEL_BG_ALPHA = 180

    def __init__(
        self,
        pattern_id: int,
        db: GalleryDatabase,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._pattern_id = pattern_id
        self._db = db
        self._pixmap: QPixmap | None = None
        self._osu_file: OsuFile | None = None
        self._object_count: int = 0
        self._circle_count: int = 0
        self._slider_count: int = 0
        self._combo_color: int | None = None
        self._is_rendered = False
        self._is_hovered = False

        self.setMinimumSize(THUMBNAIL_WIDGET_MIN_WIDTH, THUMBNAIL_WIDGET_MIN_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style()
        self._load_and_render()
        self._setup_context_menu()
        self._setup_shortcut()

    def sizeHint(self) -> QSize:
        """Return the fixed size hint for the flow layout."""
        return QSize(THUMBNAIL_WIDGET_MIN_WIDTH, THUMBNAIL_WIDGET_MIN_HEIGHT)

    # -- Loading & rendering --

    def _load_and_render(self) -> None:
        """Load the pattern from the database and render its thumbnail."""
        pattern = self._db.get_pattern(self._pattern_id)
        if pattern is None:
            logger.warning("Pattern %d not found in database", self._pattern_id)
            self._show_error_state()
            return

        self._object_count = pattern.object_count
        self._circle_count = pattern.circle_count
        self._slider_count = pattern.slider_count
        self._render(pattern.raw_code)

    def _render(self, raw_code: str) -> None:
        """Parse the raw code and render a thumbnail."""
        pattern = self._db.get_pattern(self._pattern_id)
        if pattern is None:
            self._show_error_state()
            return

        # Check for user image first
        if pattern.user_image:
            pixmap = QPixmap()
            if pixmap.loadFromData(pattern.user_image):
                self._pixmap = pixmap
                self._is_rendered = True
                self._apply_style()
                self.update()
                return

        try:
            osu_file = parse_osu_file(raw_code)
        except ParseError as exc:
            logger.warning(
                "Failed to parse pattern %d: %s", self._pattern_id, exc
            )
            self._show_error_state()
            return

        self._osu_file = osu_file
        self._combo_color = osu_file.combo_colors[0] if osu_file.combo_colors else None

        try:
            self._pixmap = render_thumbnail(osu_file, width=512, height=384)
        except (OSError, ValueError) as exc:
            logger.exception(
                "Failed to render thumbnail for pattern %d: %s",
                self._pattern_id,
                exc,
            )
            self._show_error_state()
            return

        self._is_rendered = True
        self._apply_style()
        self.update()

    def _show_error_state(self) -> None:
        """Show a fallback state when rendering fails."""
        self._pixmap = None
        self._is_rendered = True
        self._apply_style()
        self.update()

    # -- Styling --

    def _apply_style(self) -> None:
        """Apply the widget's border and hover styles."""
        r, g, b = self._NORMAL_BORDER_COLOR
        hover_r, hover_g, hover_b = self._HOVER_BORDER_COLOR
        self.setStyleSheet(
            f"""
            QWidget#thumbnailWidget {{
                background-color: rgb(30, 30, 30);
                border: 2px solid rgb({r}, {g}, {b});
                border-radius: 6px;
            }}
            QWidget#thumbnailWidget:hover {{
                border: 2px solid rgb({hover_r}, {hover_g}, {hover_b});
            }}
            """
        )

    # -- Painting --

    def paintEvent(self, event: Any) -> None:  # noqa: ANN401
        """Paint the thumbnail pixmap and overlay info."""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._pixmap is not None:
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            pixmap_rect = scaled.rect()
            pixmap_rect.moveCenter(self.rect().center())
            painter.drawPixmap(pixmap_rect.topLeft(), scaled)
        else:
            self._draw_error_indicator(painter)

        self._draw_object_count_label(painter)
        self._draw_combo_color_indicator(painter)

        painter.end()

    def _draw_error_indicator(self, painter: QPainter) -> None:
        """Draw a simple error indicator when no thumbnail is available."""
        painter.setPen(QColor(160, 160, 160))
        painter.setFont(QFont(FONT_FAMILY, 10))
        label = "No preview"
        text_rect = painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignCenter,
            label,
        )
        _ = text_rect

    def _draw_object_count_label(self, painter: QPainter) -> None:
        """Draw the object count label at the bottom of the widget."""
        if self._circle_count > 0 and self._slider_count > 0:
            circle_text = format_object_count(self._circle_count, "circle")
            slider_text = format_object_count(self._slider_count, "slider")
            text = f"{circle_text}, {slider_text}"
        elif self._circle_count > 0:
            text = format_object_count(self._circle_count, "circle")
        elif self._slider_count > 0:
            text = format_object_count(self._slider_count, "slider")
        else:
            text = f"{self._object_count} objects"
        font = QFont(FONT_FAMILY, 9, QFont.Weight.Medium)
        painter.setFont(font)

        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(text)
        padding = 6
        label_height = metrics.height() + padding * 2

        label_rect = self.rect().adjusted(0, -label_height - 4, 0, -4)
        label_rect.setWidth(text_width + padding * 2)
        label_rect.moveBottomRight(self.rect().bottomRight())

        painter.fillRect(label_rect, QColor(0, 0, 0, self._LABEL_BG_ALPHA))

        painter.setPen(QColor(220, 220, 220))
        painter.drawText(
            label_rect,
            Qt.AlignmentFlag.AlignCenter,
            text,
        )

    def _draw_combo_color_indicator(self, painter: QPainter) -> None:
        """Draw a small colored circle indicating the first combo color."""
        if self._combo_color is None:
            return

        color = QColor(self._combo_color)
        radius = 5
        x = 10 + radius
        y = self.height() - 10 - radius

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(QPoint(x, y), radius, radius)

    # -- Interaction --

    def enterEvent(self, event: Any) -> None:  # noqa: ANN401
        """Handle mouse entering the widget — enable hover styling."""
        self._is_hovered = True
        self._apply_style()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: Any) -> None:  # noqa: ANN401
        """Handle mouse leaving the widget — disable hover styling."""
        self._is_hovered = False
        self._apply_style()
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: Any) -> None:  # noqa: ANN401
        """Handle left-click — emit pattern_clicked signal."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.pattern_clicked.emit(self._pattern_id)
        super().mousePressEvent(event)

    # -- Context menu & shortcut --

    def _setup_context_menu(self) -> None:
        """Enable custom context menu and connect it to _show_context_menu."""
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _setup_shortcut(self) -> None:
        """Install a Ctrl+C keyboard shortcut that triggers _on_copy_code."""
        self._copy_shortcut = QShortcut(QKeySequence("Ctrl+C"), self)
        self._copy_shortcut.activated.connect(self._on_copy_code)

    def _build_menu(self) -> QMenu:
        """Build and return the context menu without showing it."""
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background-color: rgb(45, 45, 45); color: rgb(220, 220, 220); "
            "border: 1px solid rgb(80, 80, 80); border-radius: 4px; padding: 4px; }"
            "QMenu::item:selected { background-color: rgb(60, 60, 60); }"
            "QMenu::item:checked { background-color: rgb(70, 70, 70); }"
        )

        copy_action = menu.addAction("Copy Code\tCtrl+C")
        copy_action.triggered.connect(self._on_copy_code)

        edit_action = menu.addAction("Edit Pattern")
        edit_action.triggered.connect(self._on_edit_requested)

        menu.addSeparator()

        delete_action = menu.addAction("Delete Pattern")
        delete_action.triggered.connect(self._on_delete_requested)

        return menu

    def _show_context_menu(self, pos: Any) -> None:  # noqa: ANN401
        """Show the context menu at the given widget-local position."""
        menu = self._build_menu()
        menu.exec(self.mapToGlobal(pos))

    def _on_delete_requested(self) -> None:
        """Show confirmation dialog and emit delete signal if confirmed."""
        reply = QMessageBox.question(
            self,
            "Delete Pattern",
            "Are you sure you want to delete this pattern?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.pattern_deleted.emit(self._pattern_id)

    def _on_edit_requested(self) -> None:
        """Emit the pattern_edited signal to request editing the pattern."""
        self.pattern_edited.emit(self._pattern_id)

    def _on_copy_code(self) -> None:
        """Copy the pattern's raw code (or objects-only code) to the clipboard."""
        pattern = self._db.get_pattern(self._pattern_id)
        if pattern is None:
            logger.warning("Cannot copy: pattern %d not found", self._pattern_id)
            return

        text = pattern.objects_only if pattern.objects_only else pattern.raw_code
        copy_to_clipboard(text, self)
        self.pattern_copied.emit(self._pattern_id)
        show_toast("Copied!", self)
