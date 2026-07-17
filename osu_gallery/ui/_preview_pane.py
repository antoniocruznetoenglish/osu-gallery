"""Preview pane widget for displaying a large pattern preview with metadata."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from osu_gallery.db.database import GalleryDatabase
from osu_gallery.db.models import Pattern, Tag
from osu_gallery.parser.osu_file import ParseError, parse_osu_file
from osu_gallery.preview.thumbnail_renderer import render_pattern_preview
from osu_gallery.ui._clipboard import copy_to_clipboard

logger = logging.getLogger(__name__)


class _PreviewPane(QWidget):
    """A side panel showing a large rendered preview of a selected pattern.

    Displays the full-resolution preview image, metadata (object count, BPM,
    tags, combo colors), a copy code button, and a close button. Shows an
    empty state when no pattern is selected.
    """

    closed = Signal()

    _PANE_WIDTH = 380
    _PREVIEW_HEIGHT = 384
    _LABEL_BG_ALPHA = 180

    def __init__(
        self,
        db: GalleryDatabase,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._current_pattern_id: int | None = None
        self._pixmap: QPixmap | None = None
        self._osu_file = None
        self._tags: list[Tag] = []
        self._combo_colors: list[int] = []

        self.setMinimumWidth(self._PANE_WIDTH)
        self.setMaximumWidth(self._PANE_WIDTH + 100)
        self._apply_style()
        self._setup_ui()
        self._show_empty_state()

    # -- UI construction --

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header row: title + close button
        header = QHBoxLayout()

        title_label = QLabel("Pattern Preview")
        title_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title_label.setStyleSheet("color: rgb(220, 220, 220);")
        header.addWidget(title_label)

        header.addStretch()

        self._close_button = QPushButton("Close")
        self._close_button.setMinimumHeight(30)
        self._close_button.setMaximumWidth(80)
        self._close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_button.clicked.connect(self._on_close)
        header.addWidget(self._close_button)

        layout.addLayout(header)

        # Scroll area for content
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(10)
        self._scroll.setWidget(self._content_widget)

        layout.addWidget(self._scroll, stretch=1)

    # -- Display states --

    def _clear_layout(self) -> None:
        """Remove all items from a layout."""
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()

    def _show_empty_state(self) -> None:
        """Show the empty state when no pattern is selected."""
        self._clear_layout()

        empty_label = QLabel("Click a pattern to preview")
        empty_label.setFont(QFont("Segoe UI", 12))
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setStyleSheet("color: rgb(140, 140, 140);")
        empty_label.setWordWrap(True)
        self._content_layout.addWidget(empty_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self._content_layout.addStretch()

        self._pixmap = None
        self._osu_file = None
        self._tags = []
        self._combo_colors = []
        self._current_pattern_id = None

    def load_pattern(self, pattern_id: int) -> None:
        """Load and display a pattern's preview and metadata."""
        if pattern_id == self._current_pattern_id:
            return

        self._current_pattern_id = pattern_id
        self._clear_layout()

        pattern = self._db.get_pattern(pattern_id)
        if pattern is None:
            logger.warning("Pattern %d not found for preview", pattern_id)
            self._show_error_state("Pattern not found")
            return

        # Load tags
        self._tags = self._db.get_pattern_tags(pattern_id)

        # Parse and render
        try:
            osu_file = parse_osu_file(pattern.raw_code)
        except ParseError as exc:
            logger.warning("Failed to parse pattern %d for preview: %s", pattern_id, exc)
            self._show_error_state("Failed to parse pattern")
            return

        self._osu_file = osu_file
        self._combo_colors = osu_file.combo_colors

        try:
            self._pixmap = render_pattern_preview(osu_file, width=512, height=384)
        except (OSError, ValueError) as exc:
            logger.exception(
                "Failed to render preview for pattern %d: %s", pattern_id, exc
            )
            self._show_error_state("Failed to render preview")
            return

        self._render_content(pattern)

    def _render_content(self, pattern: Pattern) -> None:
        """Render the preview image and metadata into the content layout."""
        # Preview image
        preview_label = QLabel()
        preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_label.setMinimumHeight(self._PREVIEW_HEIGHT)

        scaled = self._pixmap.scaled(
            512,
            self._PREVIEW_HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        preview_label.setPixmap(scaled)
        preview_label.setStyleSheet(
            "QLabel { background-color: rgb(25, 25, 25); border-radius: 6px; }"
        )
        self._content_layout.addWidget(preview_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Metadata section
        meta_widget = QWidget()
        meta_layout = QVBoxLayout(meta_widget)
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(6)

        # Object count and BPM
        info_row = QHBoxLayout()

        count_label = QLabel(f"Objects: {pattern.object_count}")
        count_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        count_label.setStyleSheet("color: rgb(200, 200, 200);")
        info_row.addWidget(count_label)

        info_row.addStretch()

        if pattern.timing_bpm > 0:
            bpm_label = QLabel(f"BPM: {pattern.timing_bpm:.0f}")
            bpm_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
            bpm_label.setStyleSheet("color: rgb(200, 200, 200);")
            info_row.addWidget(bpm_label)

        meta_layout.addLayout(info_row)

        # Combo color indicators
        if self._combo_colors:
            color_row = QHBoxLayout()
            color_label = QLabel("Combo:")
            color_label.setFont(QFont("Segoe UI", 10))
            color_label.setStyleSheet("color: rgb(160, 160, 160);")
            color_row.addWidget(color_label)

            for color_hex in self._combo_colors[:8]:
                color = QColor(f"#{color_hex:06x}")
                dot = QWidget()
                dot.setFixedSize(14, 14)
                dot.setStyleSheet(
                    f"background-color: {color.name()}; border-radius: 7px;"
                )
                dot.setToolTip(color.name())
                color_row.addWidget(dot)

            color_row.addStretch()
            meta_layout.addLayout(color_row)

        # Tags
        if self._tags:
            tags_label = QLabel("Tags:")
            tags_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
            tags_label.setStyleSheet("color: rgb(200, 200, 200);")
            meta_layout.addWidget(tags_label)

            for tag in self._tags:
                tag_widget = _TagChip(tag=tag)
                meta_layout.addWidget(tag_widget)

        meta_layout.addStretch()
        self._content_layout.addWidget(meta_widget)

        # Divider
        divider = QLabel()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: rgb(60, 60, 60);")
        self._content_layout.addWidget(divider)

        # Copy button
        self._copy_button = QPushButton("Copy Code")
        self._copy_button.setMinimumHeight(36)
        self._copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_button.clicked.connect(lambda: self._on_copy_code(pattern))
        self._content_layout.addWidget(self._copy_button)

        self._content_layout.addStretch()

    def _show_error_state(self, message: str) -> None:
        """Show an error message in the preview pane."""
        self._clear_layout()

        error_label = QLabel(message)
        error_label.setFont(QFont("Segoe UI", 11))
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_label.setStyleSheet("color: rgb(200, 100, 100);")
        error_label.setWordWrap(True)
        self._content_layout.addWidget(error_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self._content_layout.addStretch()

        self._pixmap = None
        self._osu_file = None

    # -- Styling --

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QWidget#previewPane {
                background-color: rgb(35, 35, 35);
                border-left: 1px solid rgb(60, 60, 60);
            }
            QPushButton {
                background-color: rgb(50, 50, 50);
                color: rgb(220, 220, 220);
                border: 1px solid rgb(70, 70, 70);
                border-radius: 4px;
                padding: 4px 12px;
                font-family: "Segoe UI";
            }
            QPushButton:hover {
                background-color: rgb(65, 65, 65);
                border: 1px solid rgb(90, 90, 90);
            }
            QPushButton:pressed {
                background-color: rgb(45, 45, 45);
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            """
        )

    # -- Signal handlers --

    def _on_close(self) -> None:
        """Handle close button click."""
        self._show_empty_state()
        self.closed.emit()

    def _on_copy_code(self, pattern: Pattern) -> None:
        """Copy the pattern's raw code to clipboard."""
        copy_to_clipboard(pattern.raw_code, self)


class _TagChip(QWidget):
    """A small chip-style widget displaying a tag name."""

    def __init__(self, tag: Tag, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tag = tag
        self.setMinimumHeight(24)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(4)

        label = QLabel(self._tag.name)
        label.setFont(QFont("Segoe UI", 9))
        label.setStyleSheet("color: rgb(180, 200, 220);")
        layout.addWidget(label)

        layout.addStretch()

        self.setStyleSheet(
            """
            QWidget {
                background-color: rgb(40, 55, 75);
                border-radius: 10px;
            }
            QWidget:hover {
                background-color: rgb(50, 70, 95);
            }
            """
        )
