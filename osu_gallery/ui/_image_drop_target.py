"""Reusable image drag-and-drop target widget for PySide6."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".bmp"})


class ImageDropTarget(QFrame):
    """A drop target widget that accepts a single local image file.

    Accepts one local image file dropped as a URL. Supported extensions:
    png, jpg, jpeg, bmp. Rejects directories, multiple files, remote URLs,
    and unsupported files with visible feedback and warning log.

    Signals:
        image_selected: emitted when a valid image is dropped.
            Payload: (file_path: str) - the local file path.
    """

    image_selected = Signal(str)

    def __init__(self, parent: QFrame | None = None) -> None:
        """Initialize the drop target with styled border and placeholder text.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)

        self._label = QLabel("Drop screenshot here")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet(
            "color: #888888; font-size: 14px; padding: 20px;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self._label)

        self.setStyleSheet(
            "QFrame {"
            "    border: 2px dashed #aaaaaa;"
            "    border-radius: 6px;"
            "    background-color: #f5f5f5;"
            "}"
            "QFrame:hover {"
            "    border-color: #4488cc;"
            "    background-color: #eef4ff;"
            "}"
        )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter -- accept if a single image file is being dragged.

        Args:
            event: The drag enter event.
        """
        if self._is_valid_drop_event(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        """Handle drag move -- accept if the drop is still valid.

        Args:
            event: The drag move event.
        """
        if self._is_valid_drop_event(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        """Handle drag leave -- reset visual feedback.

        Args:
            event: The drag leave event.
        """
        self._reset_display()
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop -- validate and emit signal or show error.

        Args:
            event: The drop event.
        """
        mime_data = event.mimeData()
        result = self._validate_mime_data(mime_data)

        if result["valid"]:
            self._label.setText(result["path"].name)
            self._label.setStyleSheet(
                "color: #222222; font-size: 14px; padding: 20px;"
            )
            self.image_selected.emit(result["file_path"])
            event.acceptProposedAction()
        else:
            self._show_error(result["error"])
            logger.warning("Drop rejected: %s", result["error"])
            event.ignore()

    def _is_valid_drop_event(
        self, event: QDragEnterEvent | QDragMoveEvent
    ) -> bool:
        """Check whether the drag event contains a single valid image URL.

        Args:
            event: The drag enter or move event.

        Returns:
            True if the event contains exactly one local file URL with a
            supported image extension.
        """
        mime_data = event.mimeData()
        if mime_data is None:
            return False
        result = self._validate_mime_data(mime_data)
        return result["valid"]

    def _validate_mime_data(self, mime_data: QMimeData) -> dict:
        """Validate a QMimeData object for image drop acceptance.

        Checks that exactly one local file URL with a supported image
        extension is present. Returns a dict with 'valid' (bool),
        'file_path' (str), 'path' (Path), and 'error' (str) keys.

        Args:
            mime_data: The QMimeData to validate.

        Returns:
            A dict with validation results.
        """
        urls = mime_data.urls()

        if len(urls) != 1:
            return {
                "valid": False,
                "file_path": "",
                "path": Path(),
                "error": "Please drop exactly one file.",
            }

        url = urls[0]

        if not url.isLocalFile():
            return {
                "valid": False,
                "file_path": "",
                "path": Path(),
                "error": "Only local files can be dropped.",
            }

        file_path = url.toLocalFile()
        path = Path(file_path)

        if not path.is_file():
            return {
                "valid": False,
                "file_path": "",
                "path": path,
                "error": "The dropped item is not a valid file.",
            }

        if path.is_dir():
            return {
                "valid": False,
                "file_path": "",
                "path": path,
                "error": "Please drop a file, not a directory.",
            }

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return {
                "valid": False,
                "file_path": "",
                "path": path,
                "error": (
                    f"Unsupported file type '{path.suffix}'. "
                    f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
                ),
            }

        return {
            "valid": True,
            "file_path": file_path,
            "path": path,
            "error": "",
        }

    def _reset_display(self) -> None:
        """Reset the label text and styling to the placeholder state."""
        self._label.setText("Drop screenshot here")
        self._label.setStyleSheet(
            "color: #888888; font-size: 14px; padding: 20px;"
        )

    def _show_error(self, message: str) -> None:
        """Display an error message on the drop target label.

        Args:
            message: The error message to display.
        """
        self._label.setText(message)
        self._label.setStyleSheet(
            "color: #cc0000; font-size: 14px; padding: 20px;"
        )
