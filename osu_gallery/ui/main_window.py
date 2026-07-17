"""Main application window for the osu gallery."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import QStringListModel, Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCompleter,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from osu_gallery._constants import DB_FILENAME, MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT
from osu_gallery.db.database import GalleryDatabase, get_data_dir, set_search_engine
from osu_gallery.db.models import Pattern
from osu_gallery.search.engine import SearchEngine, SearchQuery
from osu_gallery.ui._preview_pane import _PreviewPane
from osu_gallery.ui._toast_widget import show_toast
from osu_gallery.ui.import_dialog import ImportDialog
from osu_gallery.ui.thumbnail_widget import _ThumbnailWidget

from ._flow_layout import QFlowLayout

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Empty-state widget shown when no patterns exist.
# ---------------------------------------------------------------------------


class _EmptyStateWidget(QWidget):
    """Centered message and import button for when the gallery is empty."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the empty-state widget.

        Parameters
        ----------
        parent:
            Optional parent widget.
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the centered message label and import button."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel("No patterns yet — import some!")
        label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        self._import_button = QPushButton("Import Pattern")
        self._import_button.setMinimumHeight(44)
        self._import_button.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self._import_button, alignment=Qt.AlignmentFlag.AlignCenter)

    @property
    def import_button(self) -> QPushButton:
        """Return the import button so the parent can connect a signal."""
        return self._import_button


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------


class MainWindow(QMainWindow):
    """The main application window for the osu gallery.

    Displays a toolbar with a search bar and import button, and a scrollable
    grid of pattern placeholders below.
    """

    # Emitted when a new pattern has been added and the grid should be refreshed.
    patterns_changed = Signal()

    def __init__(
        self,
        db_path: str | Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the main window, database, and search engine.

        Parameters
        ----------
        db_path:
            Optional path to the SQLite database file. Defaults to the
            application data directory.
        parent:
            Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("osu! Gallery")
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

        db_path = Path(db_path) if db_path else get_data_dir() / DB_FILENAME
        self._db = GalleryDatabase(db_path)
        self._search_engine = SearchEngine(self._db, self)
        set_search_engine(self._search_engine)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self._on_search_triggered)

        self._setup_ui()
        self._load_patterns()

        self._completer = QCompleter([], self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._search_edit.setCompleter(self._completer)

    # -- UI construction --

    def _setup_ui(self) -> None:
        """Construct the window layout: toolbar, splitter, grid, and preview pane."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # Toolbar row: search + import button
        toolbar = QHBoxLayout()

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Search patterns…")
        self._search_edit.setMinimumWidth(240)
        self._search_edit.textChanged.connect(self._on_search_text_changed)

        self._search_button = QPushButton("Search")
        self._search_button.setMinimumHeight(36)
        self._search_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._search_button.clicked.connect(self._on_search_triggered)
        toolbar.addWidget(self._search_button)

        toolbar.addWidget(self._search_edit, stretch=1)
        self._search_edit.returnPressed.connect(self._on_search_triggered)

        self._import_button = QPushButton("Import Pattern")
        self._import_button.setMinimumHeight(36)
        self._import_button.setCursor(Qt.CursorShape.PointingHandCursor)
        toolbar.addWidget(self._import_button)

        self._tags_button = QPushButton("Pattern Tags")
        self._tags_button.setMinimumHeight(36)
        self._tags_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._tags_button.clicked.connect(self._open_pattern_tags_dialog)
        toolbar.addWidget(self._tags_button)

        main_layout.addLayout(toolbar)

        # Main content: splitter with grid on left, preview pane on right
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # Stack widget: scroll area (with patterns) vs. empty state
        self._page_stack = QStackedWidget()

        # Scroll area holding the flow grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        grid_widget = QWidget()
        self._flow_layout = QFlowLayout(grid_widget)
        grid_widget.setLayout(self._flow_layout)
        scroll.setWidget(grid_widget)

        self._page_stack.addWidget(scroll)

        # Empty state
        self._empty_state = _EmptyStateWidget()
        self._empty_state.import_button.clicked.connect(self._on_import_clicked)
        self._page_stack.addWidget(self._empty_state)

        self._splitter.addWidget(self._page_stack)

        # Preview pane (initially hidden via splitter collapse)
        self._preview_pane = _PreviewPane(db=self._db)
        self._preview_pane.closed.connect(self._on_preview_closed)
        self._splitter.addWidget(self._preview_pane)

        # Set splitter sizes: left gets all space, right starts collapsed
        initial_width = max(800, self.minimumSize().width())
        self._splitter.setSizes([initial_width, 0])
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 0)

        main_layout.addWidget(self._splitter, stretch=1)

        # Wire toolbar import button
        self._import_button.clicked.connect(self._on_import_clicked)

    def _load_patterns(self) -> None:
        """Load patterns from the database and populate the grid."""
        patterns = self._db.get_all_patterns()
        self._refresh_grid(patterns)

    def _on_search_text_changed(self, text: str) -> None:
        """Handle search bar text changes with debouncing and autocomplete."""
        self._search_timer.start()
        # Update autocomplete suggestions
        suggestions = self._search_engine.get_search_suggestions(text)
        self._completer.setModel(QStringListModel(suggestions, self))
        self._completer.complete()

    def _on_search_triggered(self) -> None:
        """Execute the search query and update the grid."""
        query_text = self._search_edit.text().strip()
        query = SearchQuery(text=query_text)
        patterns = self._search_engine.search(query)
        self._refresh_grid(patterns)

    def _refresh_grid(self, patterns: list[Pattern]) -> None:
        """Clear the grid and add a thumbnail widget for each pattern.

        Parameters
        ----------
        patterns:
            The list of patterns to display.
        """
        self._flow_layout.clear()

        for pattern in patterns:
            widget = _ThumbnailWidget(
                pattern_id=pattern.id or 0,
                db=self._db,
            )
            widget.pattern_clicked.connect(self._on_pattern_clicked)
            widget.pattern_deleted.connect(self._on_pattern_deleted)
            self._flow_layout.addWidget(widget)

        if patterns:
            self._page_stack.setCurrentWidget(self._page_stack.widget(0))
        else:
            self._page_stack.setCurrentWidget(self._page_stack.widget(1))

    def _on_pattern_deleted(self, pattern_id: int) -> None:
        """Delete a pattern from the database and refresh the grid."""
        logger.info("Deleting pattern %d", pattern_id)
        self._db.delete_pattern(pattern_id)
        self.refresh()
        show_toast("Pattern deleted", self)

    # -- Signal handlers --

    def _on_import_clicked(self) -> None:
        """Open the import dialog, refreshing the grid on success."""
        dialog = ImportDialog(db=self._db, parent=self)
        dialog.finished.connect(self.refresh)
        dialog.exec()

    def _open_pattern_tags_dialog(self) -> None:
        """Open the Pattern Tags management dialog."""
        from osu_gallery.ui._pattern_tags_dialog import PatternTagsDialog
        dialog = PatternTagsDialog(db=self._db, parent=self)
        dialog.exec()

    def _on_pattern_clicked(self, pattern_id: int) -> None:
        """Show the preview pane for the clicked pattern."""
        self._preview_pane.load_pattern(pattern_id)

        # Make sure the preview pane is visible in the splitter — use 50% of available width
        sizes = self._splitter.sizes()
        if sizes[1] == 0:
            total_width = sizes[0]
            preview_width = total_width // 2
            self._splitter.setSizes([total_width - preview_width, preview_width])

    def _on_preview_closed(self) -> None:
        """Handle the preview pane being closed — collapse the right side."""
        sizes = self._splitter.sizes()
        if len(sizes) >= 2 and sizes[1] > 0:
            grid_width = sizes[0] + sizes[1]
            self._splitter.setSizes([grid_width, 0])

    # -- Public API for external callers (e.g. import dialog) --

    def refresh(self) -> None:
        """Reload patterns from the database and update the grid.

        Call this after a new pattern has been added to reflect the change.
        """
        self._load_patterns()
        self.patterns_changed.emit()

    # -- Cleanup --

    def closeEvent(self, event: Any) -> None:  # noqa: ANN401
        """Close the database connection when the window closes."""
        self._db.close()
        super().closeEvent(event)

    def search_by_tag(self, tag_id: int) -> None:
        """Search for patterns with a specific tag and update the grid."""
        patterns = self._search_engine.search_by_tag(tag_id)
        self._refresh_grid(patterns)
        self._search_edit.setText("")
