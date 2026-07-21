"""Edit dialog for modifying existing beatmap patterns in the gallery."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from osu_gallery._constants import MAPPING_TAG_OPTIONS
from osu_gallery.db.database import GalleryDatabase
from osu_gallery.db.models import Pattern
from osu_gallery.preview.image_resizer import resize_image_for_preview, resize_image_for_thumbnail
from osu_gallery.ui._image_drop_target import ImageDropTarget

logger = logging.getLogger(__name__)


class EditDialog(QDialog):
    """Dialog for editing an existing beatmap pattern.

    Pre-populated with the pattern's current data. Allows modifying raw code,
    artist, title, mapper, and mapping tags. Commits changes back to the
    database on accept.
    """

    def __init__(
        self,
        pattern: Pattern,
        db: GalleryDatabase,
        parent: QDialog | None = None,
    ) -> None:
        """Initialize the edit dialog with the pattern to edit.

        Args:
            pattern: The Pattern object to edit.
            db: The gallery database instance.
            parent: Optional parent widget for the dialog.
        """
        super().__init__(parent)
        self._pattern = pattern
        self._db = db
        self._original_raw_code = pattern.raw_code
        self._selected_image_path: str = ""
        self._setup_ui()
        self._populate_fields()
        self._setup_connections()

    # -- UI construction --

    def _setup_ui(self) -> None:
        """Initialize the dialog layout and all widgets."""
        self.setWindowTitle(f"Edit Pattern #{self._pattern.id}")
        self.setMinimumSize(600, 500)

        layout = QGridLayout(self)
        layout.setSpacing(12)

        title_label = QLabel(f"Edit Pattern #{self._pattern.id}")
        title_label.setFont(QFont(title_label.font().family(), 14, 75))
        layout.addWidget(title_label, 0, 0, 1, 2)

        self._text_edit = QTextEdit()
        self._text_edit.setPlaceholderText("Edit the .osu file content here...")
        self._text_edit.setMinimumHeight(200)
        self._text_edit.setTabChangesFocus(True)
        layout.addWidget(self._text_edit, 1, 0, 1, 2)

        # Metadata fields
        meta_layout = QHBoxLayout()

        artist_group = QVBoxLayout()
        artist_label = QLabel("Artist:")
        artist_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        artist_group.addWidget(artist_label)
        self._artist_edit = QLineEdit()
        self._artist_edit.setMinimumHeight(30)
        artist_group.addWidget(self._artist_edit)
        meta_layout.addLayout(artist_group)

        title_group = QVBoxLayout()
        title_label = QLabel("Title:")
        title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        title_group.addWidget(title_label)
        self._title_edit = QLineEdit()
        self._title_edit.setMinimumHeight(30)
        title_group.addWidget(self._title_edit)
        meta_layout.addLayout(title_group)

        mapper_group = QVBoxLayout()
        mapper_label = QLabel("Mapper:")
        mapper_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        mapper_group.addWidget(mapper_label)
        self._mapper_edit = QLineEdit()
        self._mapper_edit.setMinimumHeight(30)
        mapper_group.addWidget(self._mapper_edit)
        meta_layout.addLayout(mapper_group)

        layout.addLayout(meta_layout, 2, 0, 1, 2)

        # Tags section
        self._tags_scroll = QScrollArea()
        self._tags_scroll.setWidgetResizable(True)
        self._tags_scroll.setMaximumHeight(250)
        self._tags_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        tags_widget = QWidget()
        self._tags_layout = QVBoxLayout(tags_widget)
        self._tags_layout.setContentsMargins(0, 0, 0, 0)
        self._tags_layout.setSpacing(4)

        tags_header = QLabel("Mapping Tags:")
        tags_header.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self._tags_layout.addWidget(tags_header)

        buttons_row = QHBoxLayout()
        self._select_all_button = QPushButton("Select All")
        self._select_all_button.setMinimumHeight(28)
        self._select_all_button.clicked.connect(self._on_select_all)
        buttons_row.addWidget(self._select_all_button)

        self._clear_all_button = QPushButton("Clear All")
        self._clear_all_button.setMinimumHeight(28)
        self._clear_all_button.clicked.connect(self._on_clear_all)
        buttons_row.addWidget(self._clear_all_button)

        buttons_row.addStretch()
        self._tags_layout.addLayout(buttons_row)

        self._grid = QGridLayout()
        self._grid.setSpacing(4)
        self._tags_layout.addLayout(self._grid)

        self._checkboxes: list[tuple[QCheckBox, str]] = []
        row, col = 0, 0
        for tag in MAPPING_TAG_OPTIONS:
            cb = QCheckBox(tag)
            cb.setFont(QFont("Segoe UI", 9))
            self._grid.addWidget(cb, row, col)
            self._checkboxes.append((cb, tag))
            col += 1
            if col >= 2:
                col = 0
                row += 1

        custom_tags = self._db.get_all_custom_tags()
        if custom_tags:
            custom_header = QLabel("Custom Tags:")
            custom_header.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self._grid.addWidget(custom_header, row, 0, 1, 2)
            row += 1

            for tag in custom_tags:
                if not tag.get("enabled", True):
                    continue
                cb = QCheckBox(f"{tag['name']} (custom)")
                cb.setFont(QFont("Segoe UI", 9))
                cb.setProperty("tag_id", tag["id"])
                cb.setProperty("is_custom", True)
                self._grid.addWidget(cb, row, col)
                self._checkboxes.append((cb, tag["name"]))
                col += 1
                if col >= 2:
                    col = 0
                    row += 1

        self._tags_scroll.setWidget(tags_widget)
        layout.addWidget(self._tags_scroll, 3, 0, 1, 2)

        self._error_label = QLabel()
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet("color: #cc0000; font-weight: bold;")
        self._error_label.hide()
        layout.addWidget(self._error_label, 4, 0, 1, 2)

        self._success_label = QLabel()
        self._success_label.setWordWrap(True)
        self._success_label.setStyleSheet("color: #006600; font-weight: bold;")
        self._success_label.hide()
        layout.addWidget(self._success_label, 5, 0, 1, 2)

        self._save_button = QPushButton("Save Changes")
        self._save_button.setMinimumHeight(36)
        layout.addWidget(self._save_button, 6, 0, 1, 1)

        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.setMinimumHeight(36)
        layout.addWidget(self._cancel_button, 6, 1, 1, 1)

        self._image_drop_target = ImageDropTarget()
        self._image_drop_target.image_selected.connect(self._on_image_dropped)
        layout.addWidget(self._image_drop_target, 7, 0, 1, 2)

        self._image_filename_label = QLabel("")
        self._image_filename_label.setWordWrap(True)
        self._image_filename_label.setStyleSheet("color: rgb(160, 160, 160);")
        layout.addWidget(self._image_filename_label, 8, 0, 1, 2)

    def _populate_fields(self) -> None:
        """Fill all form fields with the current pattern data."""
        self._text_edit.setPlainText(self._pattern.raw_code)
        self._artist_edit.setText(self._pattern.artist)
        self._title_edit.setText(self._pattern.title)
        self._mapper_edit.setText(self._pattern.mapper)

        existing_tags = set(self._pattern.mapping_tags) if self._pattern.mapping_tags else set()
        for cb, tag_name in self._checkboxes:
            cb.setChecked(tag_name in existing_tags)

        if self._pattern.user_image:
            filename = self._pattern.user_image_filename or "screenshot"
            self._image_filename_label.setText(f"Screenshot attached: {filename}")
        else:
            self._image_filename_label.setText("No screenshot attached")

    def _setup_connections(self) -> None:
        """Wire up signal-slot connections for button clicks."""
        self._save_button.clicked.connect(self._on_save)
        self._cancel_button.clicked.connect(self.reject)
        self._image_drop_target.image_selected.connect(self._on_image_dropped)

    # -- Actions --

    def _on_save(self) -> None:
        """Handle the Save Changes button click."""
        self._clear_feedback()

        new_raw_code = self._text_edit.toPlainText()
        new_artist = self._artist_edit.text().strip()
        new_title = self._title_edit.text().strip()
        new_mapper = self._mapper_edit.text().strip()
        new_mapping_tags = self._get_selected_mapping_tags()

        if not new_raw_code.strip():
            self._show_error("Raw code cannot be empty.")
            return

        self._pattern.raw_code = new_raw_code
        self._pattern.artist = new_artist
        self._pattern.title = new_title
        self._pattern.mapper = new_mapper
        self._pattern.mapping_tags = new_mapping_tags

        try:
            self._db.update_pattern(self._pattern)
        except Exception as err:
            logger.error("Database error updating pattern: %s", err)
            self._show_error(f"Database error: {err}")
            return

        # Handle image attachment/replacement
        try:
            thumbnail_bytes, preview_bytes = self._get_selected_image_bytes()
            if thumbnail_bytes:
                image_filename = self._selected_image_path or ""
                self._db.update_pattern_user_image(
                    self._pattern.id, thumbnail_bytes, image_filename, preview_bytes,
                )
        except Exception as img_err:
            logger.warning("Failed to attach user image: %s", img_err)
            self._show_error(f"Pattern saved, but image attachment failed: {img_err}")

        self._sync_tags(new_mapping_tags)

        self._show_success(new_mapping_tags)
        logger.info(
            "Pattern %d updated: artist=%r, title=%r, mapper=%r, tags=%s",
            self._pattern.id,
            new_artist,
            new_title,
            new_mapper,
            new_mapping_tags,
        )

    def _sync_tags(self, mapping_tag_names: list[str]) -> None:
        """Synchronize tag associations for the pattern.

        Removes old tags and creates/links new ones based on the updated
        mapping tag selection.

        Args:
            mapping_tag_names: The list of mapping tag names to associate.
        """
        from osu_gallery.tags import TAG_CATEGORY_MAPPING

        old_tag_ids = set(self._pattern.tag_ids) if self._pattern.tag_ids else set()
        new_tag_ids: set[int] = set()

        for tag_name in mapping_tag_names:
            tag = self._db.get_tag_by_name(tag_name)
            if tag is None:
                tag = self._db.create_tag(tag_name, category=TAG_CATEGORY_MAPPING)
            new_tag_ids.add(tag.id)

        tags_to_remove = old_tag_ids - new_tag_ids
        tags_to_add = new_tag_ids - old_tag_ids

        for tag_id in tags_to_remove:
            try:
                self._db.remove_tag_from_pattern(self._pattern.id, tag_id)
            except Exception:
                logger.debug("Failed to remove tag %d from pattern %d", tag_id, self._pattern.id)

        for tag_id in tags_to_add:
            try:
                self._db.add_tag_to_pattern(self._pattern.id, tag_id)
            except Exception:
                logger.debug("Failed to add tag %d to pattern %d", tag_id, self._pattern.id)

        self._pattern.tag_ids = list(new_tag_ids)

    def _on_image_dropped(self, file_path: str) -> None:
        """Handle a successfully dropped image file.

        Sets the selected image path and updates the filename label
        to show the basename of the dropped file.

        Args:
            file_path: The local file path of the dropped image.
        """
        self._selected_image_path = file_path
        self._image_filename_label.setText(Path(file_path).name)

    def _get_selected_image_bytes(self) -> tuple[bytes, bytes]:
        """Read and resize the selected image for both thumbnail and preview storage.

        Reads the selected image file and resizes it to thumbnail
        dimensions (512x384) and preview dimensions (1536x1152) for storage.

        Returns:
            A tuple of (thumbnail_bytes, preview_bytes), each in PNG format.
            Empty bytes are returned for either if no image was selected
            or reading/resizing failed.
        """
        if not self._selected_image_path:
            return b"", b""
        try:
            with open(self._selected_image_path, "rb") as f:
                raw_bytes = f.read()
            thumbnail_bytes = resize_image_for_thumbnail(raw_bytes, 512, 384)
            preview_bytes = resize_image_for_preview(raw_bytes, 1536, 1152)
            return thumbnail_bytes, preview_bytes
        except (OSError, TypeError, Exception) as exc:
            logger.warning("Failed to read or resize image: %s", exc)
            return b"", b""

    # -- Helpers --

    def _get_selected_mapping_tags(self) -> list[str]:
        """Get the list of selected mapping tags from the checkbox grid.

        Returns:
            A list of tag name strings corresponding to checked checkboxes.
            Custom tag checkboxes have the " (custom)" suffix stripped.
        """
        selected: list[str] = []
        for cb, tag_name in self._checkboxes:
            if cb.isChecked():
                clean_name = tag_name.replace(" (custom)", "")
                selected.append(clean_name)
        return selected

    def _on_select_all(self) -> None:
        """Check all checkboxes in the mapping tag grid."""
        for cb, _ in self._checkboxes:
            cb.setChecked(True)

    def _on_clear_all(self) -> None:
        """Uncheck all checkboxes in the mapping tag grid."""
        for cb, _ in self._checkboxes:
            cb.setChecked(False)

    # -- Feedback --

    def _show_error(self, message: str) -> None:
        """Display an error message in the error label.

        Args:
            message: The error message to display.
        """
        self._success_label.hide()
        self._error_label.setText(message)
        self._error_label.show()

    def _show_success(self, mapping_tags: list[str]) -> None:
        """Display a success message and accept the dialog.

        Args:
            mapping_tags: The list of mapping tags that were saved.
        """
        tag_display = ", ".join(mapping_tags) if mapping_tags else "none"
        message = f"Pattern #{self._pattern.id} updated successfully.\nMapping tags: {tag_display}"
        self._error_label.hide()
        self._success_label.setText(message)
        self._success_label.show()
        self.accept()

    def _clear_feedback(self) -> None:
        """Hide both the error and success labels."""
        self._error_label.hide()
        self._error_label.clear()
        self._success_label.hide()
        self._success_label.clear()
