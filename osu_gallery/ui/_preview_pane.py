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
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from osu_gallery._constants import PREVIEW_HEIGHT
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

    _MIN_PANE_WIDTH = 300
    _MAX_PANE_WIDTH = 1200
    _PREVIEW_HEIGHT = PREVIEW_HEIGHT
    _LABEL_BG_ALPHA = 180

    def __init__(
        self,
        db: GalleryDatabase,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._current_pattern_id: int | None = None
        self._current_preview_pattern_id: int | None = None
        self._pixmap: QPixmap | None = None
        self._osu_file = None
        self._tags: list[Tag] = []
        self._combo_colors: list[int] = []

        self.setMinimumWidth(self._MIN_PANE_WIDTH)
        self.setMaximumWidth(self._MAX_PANE_WIDTH)
        self._apply_style()
        self._setup_ui()
        self._show_empty_state()

    # -- UI construction --

    def _setup_ui(self) -> None:
        """Build the preview pane layout with header, close button, and scroll area."""
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

    # -- Event overrides --

    def resizeEvent(self, event) -> None:  # noqa: ANN001
        """Re-scale the loaded pixmap whenever the pane's width changes."""
        super().resizeEvent(event)
        if self._pixmap is not None and self._current_pattern_id is not None:
            self._re_scale_pixmap()

    def _re_scale_pixmap(self) -> None:
        """Re-scale the current pixmap to fit the pane's current width."""
        if self._pixmap is None:
            return

        available_width = self.width()
        if available_width <= 0:
            available_width = self._MIN_PANE_WIDTH
        scaled_height = int(available_width * self._PREVIEW_HEIGHT / 1536)
        scaled = self._pixmap.scaled(
            available_width,
            scaled_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        for i in range(self._content_layout.count() - 1, -1, -1):
            item = self._content_layout.itemAt(i)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None and isinstance(widget, QLabel) and widget.pixmap() is not None:
                widget.setPixmap(scaled)
                break

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
        self._current_preview_pattern_id = None

    def load_pattern(self, pattern_id: int, force: bool = False) -> None:
        """Load and display a pattern's preview and metadata.

        Parameters
        ----------
        pattern_id:
            The pattern id to load.
        force:
            If True, reload even if this pattern is already displayed,
            bypassing the cache guard.
        """
        if pattern_id == self._current_pattern_id and not force:
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
        self._current_preview_pattern_id = pattern_id

        # Check for user image: prefer preview-resolution copy, fall back to thumbnail
        preview_bytes = pattern.user_image_preview or pattern.user_image
        if preview_bytes:
            pixmap = QPixmap()
            if pixmap.loadFromData(preview_bytes):
                self._pixmap = pixmap
            else:
                logger.warning("Failed to load user image for pattern %d", pattern_id)
                self._pixmap = render_pattern_preview(osu_file, width=1536, height=1152)
        else:
            try:
                self._pixmap = render_pattern_preview(osu_file, width=1536, height=1152)
            except (OSError, ValueError) as exc:
                logger.exception(
                    "Failed to render preview for pattern %d: %s", pattern_id, exc
                )
                self._show_error_state("Failed to render preview")
                return

        self._render_content(pattern)

    def _render_content(self, pattern: Pattern) -> None:
        """Render the preview image and metadata into the content layout."""
        # Preview image — rendered at 1536×1152 (4:3, 3x osu! native),
        # scaled proportionally to fit within the pane width while preserving aspect ratio.
        preview_label = QLabel()
        preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        available_width = self.width()
        if available_width <= 0:
            available_width = self._MIN_PANE_WIDTH
        scaled_height = int(available_width * self._PREVIEW_HEIGHT / 1536)
        scaled = self._pixmap.scaled(
            available_width,
            scaled_height,
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

        if pattern.circle_count > 0 and pattern.slider_count > 0:
            count_text = f"{pattern.circle_count} circles, {pattern.slider_count} sliders"
        elif pattern.circle_count > 0:
            count_text = f"{pattern.circle_count} circles"
        elif pattern.slider_count > 0:
            count_text = f"{pattern.slider_count} sliders"
        else:
            count_text = f"{pattern.object_count} objects"

        count_label = QLabel(f"Objects: {count_text}")
        count_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        count_label.setStyleSheet("color: rgb(200, 200, 200);")
        info_row.addWidget(count_label)

        info_row.addStretch()

        if pattern.timing_bpm > 0:
            if (
                pattern.timing_bpm_min
                and pattern.timing_bpm_max
                and pattern.timing_bpm_min != pattern.timing_bpm_max
            ):
                bpm_text = f"BPM: {pattern.timing_bpm_min:.0f}–{pattern.timing_bpm_max:.0f}"
            else:
                bpm_text = f"BPM: {pattern.timing_bpm:.0f}"
            bpm_label = QLabel(bpm_text)
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

        # Artist/Title/Mapper rows
        if pattern.artist:
            self._add_meta_row(meta_layout, "Artist:", pattern.artist)
        if pattern.title:
            self._add_meta_row(meta_layout, "Title:", pattern.title)
        if pattern.mapper:
            self._add_meta_row(meta_layout, "Mapper:", pattern.mapper)

        # User mapping tags
        if pattern.mapping_tags:
            self._render_mapping_tags(meta_layout, pattern.mapping_tags)

        # Tags grouped by category
        if self._tags:
            self._render_tags(meta_layout)

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
        self._copy_button.clicked.connect(self._on_copy_code_clicked)
        self._content_layout.addWidget(self._copy_button)

        self._content_layout.addStretch()

    def _add_meta_row(self, layout: QVBoxLayout, label: str, value: str) -> None:
        """Add a metadata row with a bold label and regular value text.

        Args:
            layout: The layout to add the row to.
            label: The label text (e.g., "Artist:").
            value: The value text to display.
        """
        row = QHBoxLayout()
        label_widget = QLabel(label)
        label_widget.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        label_widget.setStyleSheet("color: rgb(180, 180, 180);")
        row.addWidget(label_widget)

        value_widget = QLabel(value)
        value_widget.setFont(QFont("Segoe UI", 10))
        value_widget.setStyleSheet("color: rgb(200, 200, 200);")
        value_widget.setWordWrap(True)
        row.addWidget(value_widget)

        layout.addLayout(row)

    def _render_mapping_tags(self, parent_layout: QVBoxLayout, tags: list[str]) -> None:
        """Render user mapping tags as styled badges.

        Displays user-selected mapping tags as dark badges with rounded corners.
        Auto-detected tags (from parser) are shown separately with a lighter style.

        Args:
            parent_layout: The layout to add tag widgets to.
            tags: The list of user mapping tag names.
        """
        header = QLabel("Mapping Tags:")
        header.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        header.setStyleSheet("color: rgb(180, 180, 180);")
        parent_layout.addWidget(header)

        tags_layout = QHBoxLayout()
        tags_layout.setSpacing(4)

        for tag in tags:
            badge = QLabel(tag)
            badge.setStyleSheet("""
                background-color: #2a2a4a;
                color: #e0e0e0;
                border: 1px solid #4a4a6a;
                border-radius: 10px;
                padding: 2px 8px;
                margin: 2px;
            """)
            badge.setFont(QFont("Segoe UI", 9))
            tags_layout.addWidget(badge)

        parent_layout.addLayout(tags_layout)

    def _render_tags(self, parent_layout: QVBoxLayout) -> None:
        """Render tags grouped by category (metadata vs mapping).

        Groups tags into metadata tags (.osu file tags like artist, genre)
        and mapping tags (auto-detected from hit objects like circle count,
        slider type). Tags with other categories are displayed under a
        general "Tags" section. Each group gets its own section header.

        Args:
            parent_layout: The layout to add tag widgets to.
        """
        mapping_tags = [t for t in self._tags if t.category == "mapping"]
        other_tags = [t for t in self._tags if t.category not in ("metadata", "mapping")]

        if mapping_tags:
            map_label = QLabel("Mapping:")
            map_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
            map_label.setStyleSheet("color: rgb(180, 180, 180);")
            parent_layout.addWidget(map_label)

            for tag in mapping_tags:
                tag_widget = _TagChip(tag=tag)
                parent_layout.addWidget(tag_widget)

        if other_tags:
            other_label = QLabel("Tags:")
            other_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
            other_label.setStyleSheet("color: rgb(180, 180, 180);")
            parent_layout.addWidget(other_label)

            for tag in other_tags:
                tag_widget = _TagChip(tag=tag)
                parent_layout.addWidget(tag_widget)

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
        """Apply the dark theme stylesheet to the preview pane and its child widgets."""
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
        """Copy the pattern's object lines to clipboard.

        Uses objects_only if available, falling back to raw_code for
        patterns imported before this field was added.
        """
        text = pattern.objects_only if pattern.objects_only else pattern.raw_code
        copy_to_clipboard(text, self)

    def _on_copy_code_by_id(self, pattern_id: int) -> None:
        """Copy a pattern's object lines to clipboard by its id.

        Looks up the pattern from the database, then delegates to
        _on_copy_code.
        """
        pattern = self._db.get_pattern(pattern_id)
        if pattern is None:
            logger.warning("Cannot copy: pattern %d not found", pattern_id)
            return
        self._on_copy_code(pattern)

    def _on_copy_code_clicked(self) -> None:
        """Handle copy button click using the currently displayed pattern."""
        if self._current_preview_pattern_id is None:
            return
        self._on_copy_code_by_id(self._current_preview_pattern_id)


class _TagChip(QWidget):
    """A small chip-style widget displaying a tag name."""

    def __init__(self, tag: Tag, parent: QWidget | None = None) -> None:
        """Create a tag chip displaying the given tag's name."""
        super().__init__(parent)
        self._tag = tag
        self.setMinimumHeight(24)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the chip layout: tag name label on the left, stretch on the right."""
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
