"""Import dialog for adding new beatmap patterns to the gallery.

Provides a QTextEdit-based interface for pasting .osu file content,
parsing it, and saving the resulting pattern with auto-extracted tags.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from osu_gallery._constants import MAPPING_TAG_OPTIONS
from osu_gallery.db.database import DatabaseError, GalleryDatabase
from osu_gallery.db.models import Pattern
from osu_gallery.parser.models import OsuFile
from osu_gallery.parser.osu_file import ParseError, parse_osu_file
from osu_gallery.preview.image_resizer import resize_image_for_preview, resize_image_for_thumbnail
from osu_gallery.tags import TAG_CATEGORY_MAPPING, TAG_CATEGORY_METADATA
from osu_gallery.tags.mapping_tags import detect_object_tags
from osu_gallery.ui._image_drop_target import ImageDropTarget
from osu_gallery.ui._osu_text_normalizer import normalize_osu_text

logger = logging.getLogger(__name__)


class ImportDialog(QDialog):
    """Dialog for importing beatmap patterns from .osu file content.

    Accepts raw .osu file text via a QTextEdit, parses it using the
    osu_file parser, saves the resulting pattern to the database, and
    auto-extracts tags from the parsed metadata.
    """

    def __init__(self, db: GalleryDatabase, parent: QDialog | None = None) -> None:
        """Initialize the import dialog with a database and optional parent.

        Args:
            db: The gallery database instance for saving patterns and tags.
            parent: Optional parent widget for the dialog.
        """
        super().__init__(parent)
        self.db = db
        self._selected_image_path: str = ""
        self._setup_ui()
        self._setup_connections()

    # -- UI construction --

    def _setup_ui(self) -> None:
        """Initialize the dialog layout and all widgets."""
        self.setWindowTitle("Import Pattern")
        self.setMinimumSize(600, 500)

        layout = QGridLayout(self)
        layout.setSpacing(12)

        title_label = QLabel("Import Pattern")
        title_label.setFont(QFont(title_label.font().family(), 14, 75))
        layout.addWidget(title_label, 0, 0, 1, 2)

        self._text_edit = QTextEdit()
        self._text_edit.setPlaceholderText(
            "Paste .osu file content here...\n\n"
            "You can paste the raw code block from an .osu file.\n"
            "The parser will extract hit objects, metadata, and tags."
        )
        self._text_edit.setMinimumHeight(200)
        self._text_edit.setTabChangesFocus(True)
        layout.addWidget(self._text_edit, 1, 0, 1, 2)

        self._tags_scroll = QScrollArea()
        self._tags_scroll.setWidgetResizable(True)
        self._tags_scroll.setMaximumHeight(250)
        self._tags_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        tags_widget = QWidget()
        self._tags_layout = QVBoxLayout(tags_widget)
        self._tags_layout.setContentsMargins(0, 0, 0, 0)
        self._tags_layout.setSpacing(4)

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

        custom_tags = self.db.get_all_custom_tags()
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
        layout.addWidget(self._tags_scroll, 2, 0, 1, 2)

        self._error_label = QLabel()
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet("color: #cc0000; font-weight: bold;")
        self._error_label.hide()
        layout.addWidget(self._error_label, 3, 0, 1, 2)

        self._success_label = QLabel()
        self._success_label.setWordWrap(True)
        self._success_label.setStyleSheet("color: #006600; font-weight: bold;")
        self._success_label.hide()
        layout.addWidget(self._success_label, 4, 0, 1, 2)

        self._parse_button = QPushButton("Save the Pattern")
        self._parse_button.setMinimumHeight(36)
        layout.addWidget(self._parse_button, 5, 0, 1, 1)

        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.setMinimumHeight(36)
        layout.addWidget(self._cancel_button, 5, 1, 1, 1)

        self._image_drop_target = ImageDropTarget()
        self._image_drop_target.image_selected.connect(self._on_image_dropped)
        layout.addWidget(self._image_drop_target, 6, 0, 1, 2)

        self._image_filename_label = QLabel("")
        self._image_filename_label.setWordWrap(True)
        self._image_filename_label.setStyleSheet("color: rgb(160, 160, 160);")
        layout.addWidget(self._image_filename_label, 7, 0, 1, 2)

    def _setup_connections(self) -> None:
        """Wire up signal-slot connections for button clicks."""
        self._parse_button.clicked.connect(self._on_parse_and_save)
        self._cancel_button.clicked.connect(self.reject)
        self._image_drop_target.image_selected.connect(self._on_image_dropped)

    # -- Actions --

    def _on_parse_and_save(self) -> None:
        """Handle the Save the Pattern button click.

        Normalizes pasted .osu text (restoring Discord-collapsed line
        breaks), parses it, saves the pattern to the database, extracts
        and links tags, and updates the UI with success or error feedback.
        """
        self._clear_feedback()

        raw_content = self._text_edit.toPlainText()

        if not raw_content.strip():
            self._show_error("Please paste .osu file content before saving.")
            return

        content = normalize_osu_text(raw_content)

        has_hitobjects = self._has_hitobjects_section(content)
        parse_content = content if has_hitobjects else self._wrap_in_hitobjects(content)

        try:
            osu_file = parse_osu_file(parse_content)
        except ParseError as err:
            logger.warning("Parse failed: %s", err)
            self._show_error(f"Parse error: {err}")
            return
        except Exception as err:
            logger.exception("Unexpected error during parse: %s", err)
            self._show_error(f"Unexpected error: {err}")
            return

        try:
            objects_only = self._extract_objects_only(content)
            raw_code = parse_content if not has_hitobjects else content
            selected_tags = self._get_selected_mapping_tags()
            pattern = self.db.create_pattern(
                raw_code=raw_code,
                objects_only=objects_only,
                object_count=len(osu_file.hit_objects),
                circle_count=osu_file.circle_count,
                slider_count=osu_file.slider_count,
                timing_bpm=osu_file.timing_bpm,
                timing_bpm_min=osu_file.bpm_min,
                timing_bpm_max=osu_file.bpm_max,
                artist=osu_file.metadata.artist,
                title=osu_file.metadata.title,
                mapper=osu_file.metadata.creator,
                mapping_tags=json.dumps(selected_tags),
            )
        except DatabaseError as err:
            logger.error("Database error saving pattern: %s", err)
            self._show_error(f"Database error: {err}")
            return

        metadata_tags, mapping_tags = self._extract_tag_names(osu_file)
        manual_tags = self._get_selected_mapping_tags()
        mapping_tags = self._merge_tags(mapping_tags, manual_tags)

        linked_tag_names: list[str] = []
        try:
            for tag_name in metadata_tags:
                tag = self.db.get_tag_by_name(tag_name)
                if tag is None:
                    tag = self.db.create_tag(tag_name, category=TAG_CATEGORY_METADATA)
                self.db.add_tag_to_pattern(pattern.id, tag.id)
                linked_tag_names.append(tag_name)

            for tag_name in mapping_tags:
                tag = self.db.get_tag_by_name(tag_name)
                if tag is None:
                    tag = self.db.create_tag(tag_name, category=TAG_CATEGORY_MAPPING)
                self.db.add_tag_to_pattern(pattern.id, tag.id)
                linked_tag_names.append(tag_name)
        except DatabaseError as err:
            logger.error("Database error linking tags: %s", err)
            self._show_error(f"Database error linking tags: {err}")
            return

        # Persist any new custom tags that were selected but don't exist in DB
        try:
            for cb, tag_name in self._checkboxes:
                if cb.isChecked() and cb.property("is_custom"):
                    clean_name = tag_name.replace(" (custom)", "")
                    existing = self.db.get_tag_by_name(clean_name)
                    if existing is None:
                        self.db.add_custom_tag(clean_name)
                        logger.info("Added new custom tag: %s", clean_name)
        except Exception as persist_err:
            logger.warning("Failed to persist custom tag: %s", persist_err)

        # Handle user image (thumbnail + preview)
        try:
            thumbnail_bytes, preview_bytes = self._get_selected_image_bytes()
            user_image_filename = self._selected_image_path or ""
            if thumbnail_bytes:
                self.db.update_pattern_user_image(
                    pattern.id, thumbnail_bytes, user_image_filename, preview_bytes,
                )
        except Exception as img_err:
            logger.warning("Failed to attach user image: %s", img_err)
            self._show_error(f"Pattern saved, but image attachment failed: {img_err}")

        self._show_success(pattern, len(osu_file.hit_objects), linked_tag_names)
        logger.info(
            "Pattern %d saved with %d objects (%d circles, %d sliders) and tags: %s",
            pattern.id,
            len(osu_file.hit_objects),
            osu_file.circle_count,
            osu_file.slider_count,
            linked_tag_names,
        )

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

    def _extract_tag_names(self, osu_file: OsuFile) -> tuple[list[str], list[str]]:
        """Extract unique tag names from the parsed OsuFile metadata.

        Splits tags into two categories:
        - Metadata tags: from .osu file metadata (artist tags, creator, etc.)
        - Mapping tags: auto-detected from hit object patterns

        Args:
            osu_file: The parsed OsuFile object.

        Returns:
            A tuple of (metadata_tag_names, mapping_tag_names), each a list
            of unique, non-empty tag name strings.
        """
        mapping_tags = detect_object_tags(osu_file)

        return [], mapping_tags

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

    def _merge_tags(self, auto_tags: list[str], manual_tags: list[str]) -> list[str]:
        """Merge auto-extracted and manually entered tags, deduplicating.

        Args:
            auto_tags: Tags extracted from the parsed osu file.
            manual_tags: Tags entered manually by the user.

        Returns:
            A deduplicated list of tag names with manual tags appended
            after auto tags.
        """
        seen: set[str] = set()
        merged: list[str] = []

        for tag in auto_tags:
            if tag not in seen:
                seen.add(tag)
                merged.append(tag)

        for tag in manual_tags:
            if tag not in seen:
                seen.add(tag)
                merged.append(tag)

        return merged

    # -- Feedback --

    def _show_error(self, message: str) -> None:
        """Display an error message in the error label.

        Hides the success label and shows the error label with the
        provided message.

        Args:
            message: The error message to display.
        """
        self._success_label.hide()
        self._error_label.setText(message)
        self._error_label.show()

    def _show_success(
        self,
        pattern: Pattern,
        object_count: int,
        tag_names: list[str],
    ) -> None:
        """Display a success message and accept the dialog.

        Shows a confirmation message with the pattern ID, object count,
        and linked tag names. Then closes the dialog via accept().

        Args:
            pattern: The saved Pattern object.
            object_count: The number of hit objects in the pattern.
            tag_names: The list of tag names that were linked.
        """
        tag_display = ", ".join(tag_names) if tag_names else "none"
        selected_tags = self._get_selected_mapping_tags()
        tag_display += f"\nMapping tags: {', '.join(selected_tags) if selected_tags else 'none'}"
        message = f"Pattern saved! {object_count} objects, tagged with: {tag_display}"
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

    def _extract_objects_only(self, content: str) -> str:
        """Extract hit object lines from raw .osu content.

        Finds the [HitObjects] section and returns only the object lines
        (without the section header). If no [HitObjects] section is found,
        treats the entire content as raw object lines (filtering out
        comments and blank lines).

        Args:
            content: The raw .osu file content.

        Returns:
            The hit object lines as a string. If no [HitObjects] section
            is found, returns the non-comment, non-blank lines from the
            entire content.
        """
        section_pattern = re.compile(r"^\[HitObjects\]\s*$", re.MULTILINE | re.IGNORECASE)
        next_section_pattern = re.compile(r"^\[[^\]]+\]\s*$", re.MULTILINE)

        section_match = section_pattern.search(content)
        if not section_match:
            lines = []
            for line in content.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("//") and not stripped.startswith("#"):
                    lines.append(stripped)
            return "\n".join(lines)

        start = section_match.end()
        remaining = content[start:]

        next_match = next_section_pattern.search(remaining)
        objects_content = remaining[: next_match.start()] if next_match else remaining

        lines = []
        for line in objects_content.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("//") and not stripped.startswith("#"):
                lines.append(stripped)

        return "\n".join(lines)

    def _has_hitobjects_section(self, content: str) -> bool:
        """Check if the content contains a [HitObjects] section.

        Args:
            content: The raw .osu file content.

        Returns:
            True if a [HitObjects] section header is found.
        """
        section_pattern = re.compile(r"^\[HitObjects\]\s*$", re.MULTILINE | re.IGNORECASE)
        return bool(section_pattern.search(content))

    def _wrap_in_hitobjects(self, content: str) -> str:
        """Wrap content with a [HitObjects] header if not already present.

        Creates a minimal valid .osu wrapper so the parser can render
        patterns that were pasted without section headers.

        Args:
            content: The raw .osu file content (or object lines).

        Returns:
            Content wrapped with [HitObjects] header if needed.
        """
        if self._has_hitobjects_section(content):
            return content
        return f"[HitObjects]\n{content}"
