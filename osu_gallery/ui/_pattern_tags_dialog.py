"""Pattern Tags management dialog."""
from __future__ import annotations

import logging

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from osu_gallery._constants import MAPPING_TAG_OPTIONS
from osu_gallery.db.database import GalleryDatabase

logger = logging.getLogger(__name__)


class PatternTagsDialog(QDialog):
    """Dialog for managing mapping tag options."""

    def __init__(self, db: GalleryDatabase, parent: QDialog | None = None) -> None:
        """Initialize the pattern tags dialog with database and optional parent.

        Args:
            db: The gallery database instance for managing custom tags.
            parent: Optional parent widget for the dialog.
        """
        super().__init__(parent)
        self.db = db
        self._checkboxes: list[QCheckBox] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the dialog layout with header, checkbox grid, and controls."""
        self.setWindowTitle("Pattern Tags")
        self.setMinimumSize(500, 500)
        layout = QVBoxLayout(self)

        header = QLabel("Manage mapping tag options")
        header.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        self._grid = QGridLayout(scroll_widget)
        self._grid.setSpacing(6)
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll, stretch=1)

        self._load_tags()

        add_layout = QHBoxLayout()
        add_layout.addWidget(QLabel("Add new tag:"))
        self._new_tag_edit = QLineEdit()
        self._new_tag_edit.setPlaceholderText("Tag name...")
        add_layout.addWidget(self._new_tag_edit)
        self._add_button = QPushButton("Add")
        self._add_button.clicked.connect(self._on_add_tag)
        add_layout.addWidget(self._add_button)
        layout.addLayout(add_layout)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_tags(self) -> None:
        """Load all tags (canonical + custom) and create checkboxes."""
        row, col = 0, 0

        section_header = QLabel("Canonical Tags:")
        section_header.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self._grid.addWidget(section_header, row, 0, 1, 2)
        row += 1

        for tag in MAPPING_TAG_OPTIONS:
            cb = QCheckBox(tag)
            cb.setChecked(True)
            self._checkboxes.append(cb)
            self._grid.addWidget(cb, row, col)
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
                cb = QCheckBox(f"{tag['name']} (custom)")
                cb.setChecked(tag.get("enabled", True))
                cb.setProperty("tag_id", tag["id"])
                cb.setProperty("is_custom", True)
                self._checkboxes.append(cb)
                self._grid.addWidget(cb, row, col)
                col += 1
                if col >= 2:
                    col = 0
                    row += 1

    def _on_add_tag(self) -> None:
        """Handle adding a new custom tag from the input field."""
        name = self._new_tag_edit.text().strip()
        if not name:
            return
        if not self.db.add_custom_tag(name):
            logger.warning("Failed to add custom tag '%s' (duplicate or error)", name)
            return
        self._new_tag_edit.clear()
        self._load_tags()

    def _on_save(self) -> None:
        """Handle save button - update tag enabled states in database."""
        for cb in self._checkboxes:
            if cb.property("is_custom"):
                tag_id = cb.property("tag_id")
                enabled = cb.isChecked()
                self.db.update_custom_tag_enabled(tag_id, enabled)
        self.accept()
