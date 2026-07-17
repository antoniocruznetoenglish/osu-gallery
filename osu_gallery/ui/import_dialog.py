"""Import dialog for adding new beatmap patterns to the gallery.

Provides a QTextEdit-based interface for pasting .osu file content,
parsing it, and saving the resulting pattern with auto-extracted tags.
"""

from __future__ import annotations

import logging

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QLabel,
    QPushButton,
    QTextEdit,
)

from osu_gallery.db.database import DatabaseError, GalleryDatabase
from osu_gallery.db.models import Pattern
from osu_gallery.parser.models import OsuFile
from osu_gallery.parser.osu_file import ParseError, parse_osu_file

logger = logging.getLogger(__name__)


class ImportDialog(QDialog):
    """Dialog for importing beatmap patterns from .osu file content.

    Accepts raw .osu file text via a QTextEdit, parses it using the
    osu_file parser, saves the resulting pattern to the database, and
    auto-extracts tags from the parsed metadata.
    """

    def __init__(self, db: GalleryDatabase, parent: QDialog | None = None) -> None:
        super().__init__(parent)
        self.db = db
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

        self._error_label = QLabel()
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet("color: #cc0000; font-weight: bold;")
        self._error_label.hide()
        layout.addWidget(self._error_label, 2, 0, 1, 2)

        self._success_label = QLabel()
        self._success_label.setWordWrap(True)
        self._success_label.setStyleSheet("color: #006600; font-weight: bold;")
        self._success_label.hide()
        layout.addWidget(self._success_label, 3, 0, 1, 2)

        self._parse_button = QPushButton("Parse & Save")
        self._parse_button.setMinimumHeight(36)
        layout.addWidget(self._parse_button, 4, 0, 1, 1)

        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.setMinimumHeight(36)
        layout.addWidget(self._cancel_button, 4, 1, 1, 1)

    def _setup_connections(self) -> None:
        """Wire up signal-slot connections for button clicks."""
        self._parse_button.clicked.connect(self._on_parse_and_save)
        self._cancel_button.clicked.connect(self.reject)

    # -- Actions --

    def _on_parse_and_save(self) -> None:
        """Handle the Parse & Save button click.

        Reads the text edit content, parses it, saves the pattern to
        the database, extracts and links tags, and updates the UI
        with success or error feedback.
        """
        self._clear_feedback()

        content = self._text_edit.toPlainText()

        if not content.strip():
            self._show_error("Please paste .osu file content before saving.")
            return

        try:
            osu_file = parse_osu_file(content)
        except ParseError as err:
            logger.warning("Parse failed: %s", err)
            self._show_error(f"Parse error: {err}")
            return
        except Exception as err:
            logger.exception("Unexpected error during parse: %s", err)
            self._show_error(f"Unexpected error: {err}")
            return

        try:
            pattern = self.db.create_pattern(
                raw_code=content,
                object_count=len(osu_file.hit_objects),
                timing_bpm=0.0,
            )
        except DatabaseError as err:
            logger.error("Database error saving pattern: %s", err)
            self._show_error(f"Database error: {err}")
            return

        tag_names = self._extract_tag_names(osu_file)

        linked_tag_names: list[str] = []
        try:
            for tag_name in tag_names:
                tag = self.db.get_tag_by_name(tag_name)
                if tag is None:
                    tag = self.db.create_tag(tag_name, category="auto")
                self.db.add_tag_to_pattern(pattern.id, tag.id)
                linked_tag_names.append(tag_name)
        except DatabaseError as err:
            logger.error("Database error linking tags: %s", err)
            self._show_error(f"Database error linking tags: {err}")
            return

        self._show_success(pattern, len(osu_file.hit_objects), linked_tag_names)
        logger.info(
            "Pattern %d saved with %d objects and tags: %s",
            pattern.id,
            len(osu_file.hit_objects),
            linked_tag_names,
        )

    def _extract_tag_names(self, osu_file: OsuFile) -> list[str]:
        """Extract unique tag names from the parsed OsuFile metadata.

        Collects tags from OsuFile.metadata.tags (space-separated) and
        OsuFile.metadata.creator, deduplicated and filtered for empty
        strings.

        Args:
            osu_file: The parsed OsuFile object.

        Returns:
            A list of unique, non-empty tag name strings.
        """
        tags: list[str] = []
        metadata = getattr(osu_file, "metadata", None)

        if metadata is not None:
            raw_tags = getattr(metadata, "tags", "")
            if raw_tags:
                for tag in raw_tags.split():
                    stripped = tag.strip()
                    if stripped:
                        tags.append(stripped)

            creator_name = getattr(metadata, "creator", "")
            if creator_name:
                tags.append(creator_name.strip())

        seen: set[str] = set()
        unique_tags: list[str] = []
        for name in tags:
            if name not in seen:
                seen.add(name)
                unique_tags.append(name)

        return unique_tags

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
        message = (
            f"Pattern saved! {object_count} objects, "
            f"tagged with: {tag_display}"
        )
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
