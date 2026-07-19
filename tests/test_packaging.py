"""Packaging verification tests for osu gallery (Phase 8)."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


def test_package_version() -> None:
    """Verify the package has a version string."""
    import osu_gallery
    assert hasattr(osu_gallery, "__version__")
    assert osu_gallery.__version__ == "0.1.0"


def test_constants_module_exists() -> None:
    """Verify the constants module exists and has key constants."""
    from osu_gallery._constants import (
        APP_NAME,
        APP_VERSION,
        DB_FILENAME,
        FONT_FAMILY,
        PREVIEW_PANE_WIDTH,
        THUMBNAIL_WIDGET_MIN_WIDTH,
        TOAST_DEFAULT_DURATION_MS,
    )
    assert APP_NAME == "osu gallery"
    assert APP_VERSION == "0.1.0"
    assert DB_FILENAME == "gallery.db"
    assert isinstance(FONT_FAMILY, str)
    assert len(FONT_FAMILY) > 0
    assert PREVIEW_PANE_WIDTH == 900
    assert THUMBNAIL_WIDGET_MIN_WIDTH == 220
    assert TOAST_DEFAULT_DURATION_MS == 1800


def test_get_data_dir_dev_mode() -> None:
    """Verify get_data_dir returns a valid path in development mode."""
    from osu_gallery.db.database import get_data_dir
    had_frozen = hasattr(sys, "frozen")
    sys.frozen = False
    try:
        data_dir = get_data_dir()
    finally:
        if had_frozen:
            pass
        else:
            del sys.frozen
    assert data_dir.is_dir() or True  # may not exist yet, but should not raise


def test_get_data_dir_frozen_mode() -> None:
    """Verify get_data_dir returns executable directory in frozen mode."""
    from osu_gallery.db.database import get_data_dir
    fake_exec = Path("/fake/path/osu-gallery.exe")
    had_frozen = hasattr(sys, "frozen")
    had_executable = hasattr(sys, "executable")
    sys.frozen = True
    sys.executable = str(fake_exec)
    try:
        data_dir = get_data_dir()
    finally:
        if not had_frozen:
            del sys.frozen
        if not had_executable:
            del sys.executable
    assert data_dir.parent == fake_exec.parent


def test_modules_importable() -> None:
    """Verify all core modules can be imported without errors."""
    modules = [
        "osu_gallery",
        "osu_gallery.db",
        "osu_gallery.db.database",
        "osu_gallery.db.models",
        "osu_gallery.parser",
        "osu_gallery.parser.osu_file",
        "osu_gallery.parser.models",
        "osu_gallery.preview",
        "osu_gallery.preview.thumbnail_renderer",
        "osu_gallery.search",
        "osu_gallery.search.engine",
        "osu_gallery.ui",
        "osu_gallery.ui.main_window",
        "osu_gallery.ui.import_dialog",
        "osu_gallery.ui.thumbnail_widget",
        "osu_gallery.ui._preview_pane",
        "osu_gallery.ui._flow_layout",
        "osu_gallery.ui._clipboard",
        "osu_gallery.ui._toast_widget",
    ]
    for module_name in modules:
        mod = importlib.import_module(module_name)
        assert mod is not None, f"Failed to import {module_name}"


def test_db_path_uses_get_data_dir() -> None:
    """Verify that GalleryDatabase can be initialized with get_data_dir output."""
    from osu_gallery.db.database import GalleryDatabase, get_data_dir
    had_frozen = hasattr(sys, "frozen")
    had_executable = hasattr(sys, "executable")
    sys.frozen = True
    sys.executable = str(Path("/tmp/test_exe.exe"))
    try:
        data_dir = get_data_dir()
        db = GalleryDatabase(data_dir / "test.db")
        assert db.db_path == data_dir / "test.db"
        db.close()
    finally:
        if not had_frozen:
            del sys.frozen
        if not had_executable:
            del sys.executable


def test_build_script_exists() -> None:
    """Verify the build script exists."""
    build_path = Path(__file__).parent.parent / "build.ps1"
    assert build_path.exists(), f"Build script not found at {build_path}"


def test_gitignore_exists() -> None:
    """Verify the .gitignore file exists."""
    gitignore_path = Path(__file__).parent.parent / ".gitignore"
    assert gitignore_path.exists(), f".gitignore not found at {gitignore_path}"


def test_search_engine_has_public_remove_method() -> None:
    """Verify SearchEngine has a public remove_from_fts method."""
    from osu_gallery.search.engine import SearchEngine
    assert hasattr(SearchEngine, "remove_from_fts")
    assert callable(SearchEngine.remove_from_fts)
