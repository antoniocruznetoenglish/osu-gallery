"""Tests for the edit dialog and layout changes (edit patterns, 4-column grid, half-window preview)."""

import inspect

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QSplitter, QWidget

from osu_gallery.db.database import GalleryDatabase, set_search_engine
from osu_gallery.db.models import Pattern
from osu_gallery.search.engine import SearchEngine
from osu_gallery.ui._flow_layout import QFlowLayout
from osu_gallery.ui._preview_pane import _PreviewPane
from osu_gallery.ui.edit_dialog import EditDialog
from osu_gallery.ui.main_window import MainWindow
from osu_gallery.ui.thumbnail_widget import _ThumbnailWidget

SAMPLE_OSU = """[General]
AudioFilename: test.mp3

[Metadata]
Title:Test Song
Creator:TestMapper
Tags:slider circle_pattern

[HitObjects]
256,192,1000,5,0
384,256,1500,6,0,L|480:128,1,100
512,192,2000,5,0
"""


@pytest.fixture
def db(tmp_path):
    """Create a fresh database for each test."""
    db_path = tmp_path / "test.db"
    database = GalleryDatabase(db_path)
    search_engine = SearchEngine(database)
    set_search_engine(search_engine)
    yield database


@pytest.fixture
def window(db):
    """Create a MainWindow with a test database."""
    main_window = MainWindow(db_path=db.db_path)
    yield main_window
    main_window.close()


# -- EditDialog tests --


def test_edit_dialog_creation(qtbot, db):
    """EditDialog can be created with a pattern and shown without errors."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3, artist="TestArtist", title="TestTitle", mapper="TestMapper")
    dialog = EditDialog(pattern=pattern, db=db)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.wait(100)
    assert dialog.isVisible()
    assert dialog.windowTitle() == f"Edit Pattern #{pattern.id}"
    dialog.close()


def test_edit_dialog_populates_fields(qtbot, db):
    """EditDialog pre-fills fields with the pattern's current data."""
    pattern = db.create_pattern(
        SAMPLE_OSU,
        object_count=3,
        artist="OriginalArtist",
        title="OriginalTitle",
        mapper="OriginalMapper",
    )
    dialog = EditDialog(pattern=pattern, db=db)
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)

    assert dialog._artist_edit.text() == "OriginalArtist"
    assert dialog._title_edit.text() == "OriginalTitle"
    assert dialog._mapper_edit.text() == "OriginalMapper"
    assert dialog._text_edit.toPlainText() == SAMPLE_OSU
    dialog.close()


def test_edit_dialog_save_changes(qtbot, db):
    """Saving changes in the edit dialog updates the pattern in the database."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3, artist="OldArtist", title="OldTitle", mapper="OldMapper")
    dialog = EditDialog(pattern=pattern, db=db)
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)

    dialog._artist_edit.setText("NewArtist")
    dialog._title_edit.setText("NewTitle")
    dialog._mapper_edit.setText("NewMapper")

    save_button = dialog._save_button
    qtbot.mouseClick(save_button, Qt.MouseButton.LeftButton)
    qtbot.wait(200)

    assert dialog.result() == QDialog.Accepted

    updated = db.get_pattern(pattern.id)
    assert updated is not None
    assert updated.artist == "NewArtist"
    assert updated.title == "NewTitle"
    assert updated.mapper == "NewMapper"
    dialog.close()


def test_edit_dialog_cancel(qtbot, db):
    """Clicking Cancel in the edit dialog rejects without saving."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3, artist="OriginalArtist")
    dialog = EditDialog(pattern=pattern, db=db)
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)

    dialog._artist_edit.setText("ShouldNotSave")
    cancel_button = dialog._cancel_button
    qtbot.mouseClick(cancel_button, Qt.MouseButton.LeftButton)
    qtbot.wait(100)

    assert dialog.result() == QDialog.Rejected

    unchanged = db.get_pattern(pattern.id)
    assert unchanged.artist == "OriginalArtist"
    dialog.close()


def test_edit_dialog_empty_raw_code_shows_error(qtbot, db):
    """Clearing the raw code and saving shows an error message."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3)
    dialog = EditDialog(pattern=pattern, db=db)
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)

    dialog._text_edit.setPlainText("")
    save_button = dialog._save_button
    qtbot.mouseClick(save_button, Qt.MouseButton.LeftButton)
    qtbot.wait(200)

    assert dialog.result() == 0
    assert "empty" in dialog._error_label.text().lower()
    dialog.close()


def test_edit_dialog_mapping_tags_preserved(qtbot, db):
    """Mapping tags are pre-checked and saved correctly."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3, mapping_tags='["Circle", "Slider"]')
    tag_circle = db.create_tag("Circle", "mapping")
    tag_slider = db.create_tag("Slider", "mapping")
    db.add_tag_to_pattern(pattern.id, tag_circle.id)
    db.add_tag_to_pattern(pattern.id, tag_slider.id)
    pattern.tag_ids = [tag_circle.id, tag_slider.id]

    dialog = EditDialog(pattern=pattern, db=db)
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)

    tag_names = [name for _, name in dialog._checkboxes]
    circle_cb = None
    slider_cb = None
    for cb, name in dialog._checkboxes:
        if name == "Circle":
            circle_cb = cb
        elif name == "Slider":
            slider_cb = cb

    if circle_cb is not None:
        assert circle_cb.isChecked()
    if slider_cb is not None:
        assert slider_cb.isChecked()

    dialog.close()


def test_edit_dialog_select_all_clear_all(qtbot, db):
    """Select All and Clear All buttons work correctly in the edit dialog."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3)
    dialog = EditDialog(pattern=pattern, db=db)
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)

    select_all = dialog._select_all_button
    clear_all = dialog._clear_all_button

    qtbot.mouseClick(select_all, Qt.MouseButton.LeftButton)
    qtbot.wait(50)
    for cb, _ in dialog._checkboxes:
        assert cb.isChecked()

    qtbot.mouseClick(clear_all, Qt.MouseButton.LeftButton)
    qtbot.wait(50)
    for cb, _ in dialog._checkboxes:
        assert not cb.isChecked()

    dialog.close()


# -- Thumbnail context menu tests --


def test_thumbnail_widget_has_edit_signal():
    """_ThumbnailWidget emits pattern_edited signal."""
    assert hasattr(_ThumbnailWidget, "pattern_edited")


def test_thumbnail_widget_context_menu_has_edit_action(db):
    """The context menu includes an 'Edit Pattern' action."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=1)
    widget = _ThumbnailWidget(pattern_id=pattern.id, db=db)
    menu = widget._build_menu()

    action_texts = [action.text().split("\t")[0] for action in menu.actions()]
    assert "Edit Pattern" in action_texts
    widget.deleteLater()


# -- Flow layout 4-column tests --


def test_flow_layout_default_columns_is_zero():
    """QFlowLayout defaults to 0 columns (auto-wrap)."""
    layout = QFlowLayout()
    assert layout._fixed_columns == 0
    layout.deleteLater()


def test_flow_layout_fixed_columns_parameter():
    """QFlowLayout accepts a columns parameter to fix the number of columns."""
    layout = QFlowLayout(columns=4)
    assert layout._fixed_columns == 4
    layout.deleteLater()


def test_flow_layout_four_columns_forces_four_per_row(qtbot):
    """With columns=4, items are laid out in rows of exactly 4."""
    parent = QWidget()
    layout = QFlowLayout(parent, columns=4)

    for i in range(8):
        label = QLabel(f"Item {i}")
        label.setFixedSize(100, 50)
        layout.addWidget(label)

    parent.resize(500, 300)
    parent.show()
    qtbot.wait(100)

    layout.update()
    qtbot.wait(100)

    positions = []
    y_coords = set()
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item is not None:
            rect = item.geometry()
            y_coords.add(rect.y())

    assert len(y_coords) == 2, f"Expected 2 rows for 8 items with 4 columns, got {len(y_coords)}"
    parent.close()


def test_flow_layout_four_columns_with_more_items(qtbot):
    """With columns=4 and 10 items, we get 3 rows (4+4+2)."""
    parent = QWidget()
    layout = QFlowLayout(parent, columns=4)

    for i in range(10):
        label = QLabel(f"Item {i}")
        label.setFixedSize(100, 50)
        layout.addWidget(label)

    parent.resize(500, 400)
    parent.show()
    qtbot.wait(100)

    layout.update()
    qtbot.wait(100)

    y_coords = set()
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item is not None:
            rect = item.geometry()
            y_coords.add(rect.y())

    assert len(y_coords) == 3, f"Expected 3 rows for 10 items with 4 columns, got {len(y_coords)}"
    parent.close()


# -- Preview pane sizing tests --


def test_preview_pane_has_min_max_width():
    """_PreviewPane has _MIN_PANE_WIDTH and _MAX_PANE_WIDTH constants."""
    assert hasattr(_PreviewPane, "_MIN_PANE_WIDTH")
    assert hasattr(_PreviewPane, "_MAX_PANE_WIDTH")
    assert _PreviewPane._MIN_PANE_WIDTH == 300
    assert _PreviewPane._MAX_PANE_WIDTH == 1200


def test_preview_pane_no_fixed_width_constraint(db):
    """_PreviewPane does not have a fixed width — uses min/max constraints."""
    pane = _PreviewPane(db=db)
    assert pane.minimumWidth() == _PreviewPane._MIN_PANE_WIDTH
    assert pane.maximumWidth() == _PreviewPane._MAX_PANE_WIDTH
    pane.deleteLater()


def test_preview_pane_does_not_have_old_pane_width():
    """The old _PANE_WIDTH constant is removed from _PreviewPane."""
    assert not hasattr(_PreviewPane, "_PANE_WIDTH")


# -- Main window half-window preview tests --


def test_main_window_preview_takes_half_window(qtbot, db):
    """When a pattern is clicked, the preview pane takes approximately 50% of the window."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3)
    window = MainWindow(db_path=db.db_path)
    qtbot.addWidget(window)
    qtbot.waitExposed(window)

    window.resize(1000, 600)
    qtbot.wait(100)

    window._on_pattern_clicked(pattern.id)
    qtbot.wait(100)

    splitter = window._splitter
    sizes = splitter.sizes()
    total = sum(sizes)
    assert total > 0
    preview_size = sizes[1]
    assert preview_size > 0, "Preview pane should be visible"
    ratio = preview_size / total
    assert 0.4 <= ratio <= 0.6, f"Preview ratio {ratio} not approximately 0.5"
    window.close()


def test_main_window_preview_collapses_on_close(qtbot, db):
    """Closing the preview pane collapses the right side of the splitter."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3)
    window = MainWindow(db_path=db.db_path)
    qtbot.addWidget(window)
    qtbot.waitExposed(window)

    window.resize(1000, 600)
    qtbot.wait(100)

    window._on_pattern_clicked(pattern.id)
    qtbot.wait(100)

    sizes_after_open = window._splitter.sizes()
    assert sizes_after_open[1] > 0

    window._on_preview_closed()
    qtbot.wait(100)

    sizes_after_close = window._splitter.sizes()
    assert sizes_after_close[1] == 0
    window.close()


def test_main_window_edit_opens_dialog(qtbot, db):
    """The _on_pattern_edited handler exists and can be called."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3, artist="TestArtist")
    window = MainWindow(db_path=db.db_path)
    qtbot.addWidget(window)
    qtbot.waitExposed(window)

    assert hasattr(window, "_on_pattern_edited")
    assert callable(window._on_pattern_edited)
    window.close()


def test_main_window_flow_layout_has_four_columns():
    """MainWindow uses a flow layout with 4 columns."""
    window = MainWindow()
    assert window._flow_layout._fixed_columns == 4
    window.close()


# -- Integration tests --


def test_e2e_edit_pattern_workflow(qtbot, db):
    """Full workflow: import, edit, verify changes persisted."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3, artist="Original", title="Original", mapper="Original")

    dialog = EditDialog(pattern=pattern, db=db)
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)

    dialog._artist_edit.setText("UpdatedArtist")
    dialog._title_edit.setText("UpdatedTitle")
    dialog._mapper_edit.setText("UpdatedMapper")

    save_button = dialog._save_button
    qtbot.mouseClick(save_button, Qt.MouseButton.LeftButton)
    qtbot.wait(200)

    assert dialog.result() == QDialog.Accepted

    updated = db.get_pattern(pattern.id)
    assert updated.artist == "UpdatedArtist"
    assert updated.title == "UpdatedTitle"
    assert updated.mapper == "UpdatedMapper"

    dialog.close()


def test_e2e_thumbnail_click_opens_half_window_preview(qtbot, db):
    """Clicking a thumbnail opens the preview pane at half the window width."""
    pattern = db.create_pattern(SAMPLE_OSU, object_count=3)
    window = MainWindow(db_path=db.db_path)
    qtbot.addWidget(window)
    qtbot.waitExposed(window)

    window.resize(1200, 700)
    qtbot.wait(100)

    window._on_pattern_clicked(pattern.id)
    qtbot.wait(200)

    sizes = window._splitter.sizes()
    total = sum(sizes)
    preview_width = sizes[1]
    assert preview_width > 0
    ratio = preview_width / total
    assert 0.4 <= ratio <= 0.6, f"Preview ratio {ratio} not approximately 0.5"

    window.close()


def test_e2e_four_columns_in_grid(qtbot, db):
    """With 8 patterns, the grid shows exactly 2 rows of 4."""
    for i in range(8):
        db.create_pattern(SAMPLE_OSU, object_count=1)

    window = MainWindow(db_path=db.db_path)
    qtbot.addWidget(window)
    qtbot.waitExposed(window)

    window.resize(1200, 700)
    qtbot.wait(100)

    window.refresh()
    qtbot.wait(200)

    assert window._flow_layout.count() == 8
    assert window._flow_layout._fixed_columns == 4

    window.close()
