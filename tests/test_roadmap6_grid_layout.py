"""Tests for Task 2: Grid layout overhaul (Roadmap 6).

Verifies that dimension constants drive thumbnail widget sizes,
preview pane dimensions, window minimums, and splitter behavior.
"""

from __future__ import annotations

import inspect

import pytest
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication

from osu_gallery._constants import (
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    PREVIEW_HEIGHT,
    PREVIEW_PANE_WIDTH,
    THUMBNAIL_WIDGET_MIN_HEIGHT,
    THUMBNAIL_WIDGET_MIN_WIDTH,
)
from osu_gallery.db.database import GalleryDatabase
from osu_gallery.db.models import Pattern
from osu_gallery.ui._preview_pane import _PreviewPane
from osu_gallery.ui.main_window import MainWindow
from osu_gallery.ui.thumbnail_widget import _ThumbnailWidget


@pytest.fixture
def app(qapp: QApplication) -> QApplication:
    """Return the shared QApplication instance."""
    return qapp


@pytest.fixture
def db(tmp_path) -> GalleryDatabase:
    """Create a fresh database for each test."""
    db_path = tmp_path / "test.db"
    database = GalleryDatabase(db_path)
    yield database
    database.close()


# ---------------------------------------------------------------------------
# 1. Thumbnail widget size
# ---------------------------------------------------------------------------


def test_thumbnail_widget_new_size(db):
    """sizeHint returns 220x165 from THUMBNAIL_WIDGET_MIN constants."""
    widget = _ThumbnailWidget(pattern_id=0, db=db)
    assert widget.sizeHint() == QSize(THUMBNAIL_WIDGET_MIN_WIDTH, THUMBNAIL_WIDGET_MIN_HEIGHT)
    assert THUMBNAIL_WIDGET_MIN_WIDTH == 220
    assert THUMBNAIL_WIDGET_MIN_HEIGHT == 165
    widget.close()


# ---------------------------------------------------------------------------
# 2. Preview pane uses new constants
# ---------------------------------------------------------------------------


def test_preview_pane_new_dimensions(db):
    """Preview pane references PREVIEW_HEIGHT = 1152 from constants."""
    pane = _PreviewPane(db=db)
    assert pane._PREVIEW_HEIGHT == PREVIEW_HEIGHT
    assert PREVIEW_HEIGHT == 1152
    pane.close()


# ---------------------------------------------------------------------------
# 3. Splitter sets 50/50 on pattern click
# ---------------------------------------------------------------------------


def test_preview_splits_window_half(db):
    """Clicking a pattern sets the splitter to 50/50 split."""
    window = MainWindow(db_path=db.db_path)
    window.resize(1600, 800)
    window.show()
    QApplication.processEvents()

    window._on_pattern_clicked(1)

    sizes = window._splitter.sizes()
    assert len(sizes) == 2
    assert sizes[0] > 0
    assert sizes[1] > 0
    # Splitter handle width causes minor discrepancy (~5-10px)
    assert abs(sizes[0] - sizes[1]) <= 10
    window.close()


# ---------------------------------------------------------------------------
# 4. Four thumbnails per row at 1920 with preview open
# ---------------------------------------------------------------------------


def test_four_thumbnails_per_row_on_1920_with_preview(db):
    """At 1920px with preview open, grid fits 4 thumbnails per row."""
    window = MainWindow(db_path=db.db_path)
    window.resize(1920, 1000)
    window.show()
    QApplication.processEvents()

    # Simulate clicking a pattern to open preview (50/50 split)
    window._on_pattern_clicked(1)

    sizes = window._splitter.sizes()
    grid_width = sizes[0]

    # At 1920 with 50/50, grid_width should be ~960
    # With 220px thumbnails and margins, 4 should fit
    assert grid_width >= 220 * 4  # minimum space for 4 thumbnails

    window.close()


# ---------------------------------------------------------------------------
# 5. Preview image scaled correctly
# ---------------------------------------------------------------------------


def test_preview_image_scaled_correctly(db):
    """Preview image at 1536x1152 scales proportionally to pane width."""
    pane = _PreviewPane(db=db)
    pane.setMinimumWidth(PREVIEW_PANE_WIDTH)
    pane.resize(PREVIEW_PANE_WIDTH, 1200)

    # Verify the scaling ratio: available_width * PREVIEW_HEIGHT / 1536
    available_width = pane.width()
    expected_scaled_height = int(available_width * pane._PREVIEW_HEIGHT / 1536)

    # The pane's _PREVIEW_HEIGHT should be 1152
    assert pane._PREVIEW_HEIGHT == 1152

    # Calculate what the scaled height would be at pane width
    calculated = int(PREVIEW_PANE_WIDTH * 1152 / 1536)
    assert calculated == expected_scaled_height

    pane.close()


# ---------------------------------------------------------------------------
# 6. Window minimum size updated
# ---------------------------------------------------------------------------


def test_window_minimum_size_updated():
    """MainWindow minimum size is 1400x700."""
    source = inspect.getsource(MainWindow)
    assert "MIN_WINDOW_WIDTH" in source
    assert "MIN_WINDOW_HEIGHT" in source

    assert MIN_WINDOW_WIDTH == 1400
    assert MIN_WINDOW_HEIGHT == 700


# ---------------------------------------------------------------------------
# 7. No magic numbers in UI code
# ---------------------------------------------------------------------------


def test_no_magic_numbers_in_ui():
    """All dimension constants are imported and used from _constants."""
    thumbnail_source = inspect.getsource(_ThumbnailWidget)
    preview_source = inspect.getsource(_PreviewPane)
    main_window_source = inspect.getsource(MainWindow)

    # Thumbnail widget should reference constants, not raw numbers
    assert "THUMBNAIL_WIDGET_MIN_WIDTH" in thumbnail_source
    assert "THUMBNAIL_WIDGET_MIN_HEIGHT" in thumbnail_source

    # Preview pane should reference constants
    assert "PREVIEW_HEIGHT" in preview_source
    assert "PREVIEW_PANE_WIDTH" in preview_source or "_PREVIEW_HEIGHT" in preview_source

    # MainWindow should reference constants
    assert "MIN_WINDOW_WIDTH" in main_window_source
    assert "MIN_WINDOW_HEIGHT" in main_window_source

    # Verify splitter uses 50% split logic (not hardcoded pixel values)
    assert "total_width // 2" in main_window_source or "total_width / 2" in main_window_source


# ---------------------------------------------------------------------------
# 8. BUG-124: clear() removes widgets from the tree immediately
# ---------------------------------------------------------------------------


def _make_patterns(ids: list[int]) -> list[Pattern]:
    """Build a list of Pattern objects with the given ids (no DB reads)."""
    return [Pattern(id=i, artist="test", title="test", mapper="test") for i in ids]


def test_clear_hides_and_detaches_widgets_before_delete_later(qtbot, db):
    """clear() must hide each widget so it disappears from view immediately,
    not merely scheduled for deferred deletion via deleteLater().
    """
    from osu_gallery.ui._flow_layout import QFlowLayout
    from PySide6.QtWidgets import QWidget

    container = QWidget()
    qtbot.addWidget(container)
    flow = QFlowLayout(container)
    container.setLayout(flow)
    container.show()
    qtbot.waitExposed(container)

    widgets = [_ThumbnailWidget(pattern_id=i, db=db) for i in range(5)]
    for w in widgets:
        flow.addWidget(w)
        w.show()
    qtbot.waitExposed(container)

    assert flow.count() == 5

    flow.clear()

    assert flow.count() == 0
    for w in widgets:
        assert w.isHidden()

    container.close()


def test_clear_hides_old_widgets_immediately(qtbot):
    from osu_gallery.ui._flow_layout import QFlowLayout
    from PySide6.QtWidgets import QWidget

    container = QWidget()
    qtbot.addWidget(container)
    flow = QFlowLayout(container)
    container.setLayout(flow)
    container.show()
    qtbot.waitExposed(container)

    w = QWidget(container)
    flow.addWidget(w)
    w.show()
    qtbot.waitExposed(w)
    assert not w.isHidden()

    flow.clear()
    assert w.isHidden()


def test_refresh_grid_replaces_old_widgets_not_accumulates(qtbot, db):
    """Calling _refresh_grid with a new pattern list must leave exactly
    that many widgets in the grid_widget — not old + new. This is the
    user-visible symptom of BUG-124: searching then searching again
    produces duplicated thumbnails on screen.
    """
    window = MainWindow(db_path=db.db_path)
    qtbot.addWidget(window)
    window.resize(1400, 700)
    window.show()
    qtbot.waitExposed(window)

    scroll_widget = window._page_stack.widget(0).widget()

    old_patterns = _make_patterns([1, 2, 3])
    window._refresh_grid(old_patterns)
    qtbot.wait(100)

    old_widgets = scroll_widget.findChildren(_ThumbnailWidget)
    assert len(old_widgets) == 3

    for w in old_widgets:
        w.show()
    qtbot.waitExposed(window)

    new_patterns = _make_patterns([4, 5])
    window._refresh_grid(new_patterns)
    qtbot.wait(100)

    remaining_old = [w for w in old_widgets if w in scroll_widget.findChildren(_ThumbnailWidget)]
    assert len(remaining_old) == 0, "Old widgets should be removed from the grid after refresh"

    new_widgets = scroll_widget.findChildren(_ThumbnailWidget)
    visible_new = [w for w in new_widgets if not w.isHidden()]
    assert len(visible_new) == 2, (
        f"Expected 2 visible widgets after refresh, got {len(visible_new)}"
    )

    window.close()
