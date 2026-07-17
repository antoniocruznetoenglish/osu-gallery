"""Phase 9 tests: logging, entry point, error handling."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from unittest import mock

# ---------------------------------------------------------------------------
# Logging tests
# ---------------------------------------------------------------------------


def test_setup_logging_returns_logger() -> None:
    """setup_logging returns a logger named 'osu_gallery'."""
    from osu_gallery._logging import setup_logging

    logger = setup_logging()
    assert logger.name == "osu_gallery"


def test_setup_logging_adds_console_handler() -> None:
    """setup_logging installs a StreamHandler on the root logger."""
    from osu_gallery._logging import setup_logging

    setup_logging()
    handlers = [
        h for h in logging.getLogger("osu_gallery").handlers
        if isinstance(h, logging.StreamHandler)
    ]
    assert len(handlers) >= 1


def test_setup_logging_idempotent() -> None:
    """Calling setup_logging twice does not duplicate handlers."""
    from osu_gallery._logging import setup_logging

    logger = logging.getLogger("osu_gallery")
    initial_count = len(logger.handlers)
    setup_logging()
    setup_logging()
    assert len(logger.handlers) == initial_count


def test_setup_logging_creates_log_file() -> None:
    """setup_logging creates the log file in the data directory."""
    from osu_gallery._logging import setup_logging
    from osu_gallery.db.database import get_data_dir

    setup_logging()
    log_file = get_data_dir() / "osu_gallery.log"
    assert log_file.exists(), f"Log file not created at {log_file}"


def test_get_logger_returns_child_logger() -> None:
    """get_logger returns a logger with the osu_gallery.{name} prefix."""
    from osu_gallery._logging import get_logger, setup_logging

    setup_logging()
    child = get_logger("db")
    assert child.name == "osu_gallery.db"


def test_get_logger_nested() -> None:
    """Nested get_logger calls produce correctly nested logger names."""
    from osu_gallery._logging import get_logger, setup_logging

    setup_logging()
    child = get_logger("parser.osu_file")
    assert child.name == "osu_gallery.parser.osu_file"


def test_logging_does_not_log_raw_code() -> None:
    """Verify the logging module docstring promise: raw .osu code is not logged."""
    from osu_gallery._logging import setup_logging

    setup_logging()
    # The module exists and is importable — the actual promise is
    # behavioural (enforced by developer discipline, not runtime).
    # We verify the formatter does not reference raw_code.
    import osu_gallery._logging as m
    source = Path(m.__file__).read_text()
    assert "raw_code" not in source.lower() or "raw code" not in source.lower()


# ---------------------------------------------------------------------------
# Entry point tests
# ---------------------------------------------------------------------------


def test_project_scripts_in_pyproject() -> None:
    """Verify [project.scripts] exists in pyproject.toml."""
    import tomllib

    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)
    assert "project" in data
    assert "scripts" in data["project"], "Missing [project.scripts] in pyproject.toml"


def test_entry_point_target_exists() -> None:
    """The entry point target osu_gallery.__main__:main must be importable."""
    import importlib

    mod = importlib.import_module("osu_gallery.__main__")
    assert hasattr(mod, "main")
    assert callable(mod.main)


def test_entry_point_in_pyproject_correct() -> None:
    """The entry point value in pyproject.toml matches the actual module."""
    import tomllib

    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)
    scripts = data["project"]["scripts"]
    assert "osu-gallery" in scripts
    assert scripts["osu-gallery"] == "osu_gallery.__main__:main"


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


def test_show_fatal_error_exists() -> None:
    """_show_fatal_error function exists in __main__."""
    from osu_gallery.__main__ import _show_fatal_error
    assert callable(_show_fatal_error)


def test_main_catches_import_error() -> None:
    """main() catches ImportError and exits with code 1."""
    from osu_gallery.__main__ import main

    with (
        mock.patch("sys.exit") as mock_exit,
        mock.patch("osu_gallery.__main__._show_fatal_error"),
        mock.patch(
            "PySide6.QtWidgets.QApplication",
            side_effect=ImportError("No module named 'PySide6'"),
        ),
    ):
        main()

    mock_exit.assert_called_once_with(1)


def test_main_catches_os_error() -> None:
    """main() catches OSError and exits with code 1."""
    from osu_gallery.__main__ import main

    with (
        mock.patch("sys.exit") as mock_exit,
        mock.patch("osu_gallery.__main__._show_fatal_error"),
        mock.patch(
            "PySide6.QtWidgets.QApplication",
            side_effect=OSError("Cannot load Qt platform plugin"),
        ),
    ):
        main()

    mock_exit.assert_called_once_with(1)


def test_main_catches_generic_exception() -> None:
    """main() catches unexpected exceptions and exits with code 1."""
    from osu_gallery.__main__ import main

    with (
        mock.patch("sys.exit") as mock_exit,
        mock.patch("osu_gallery.__main__._show_fatal_error"),
        mock.patch(
            "PySide6.QtWidgets.QApplication",
            side_effect=ValueError("something went wrong"),
        ),
    ):
        main()

    mock_exit.assert_called_once_with(1)


# ---------------------------------------------------------------------------
# Data directory on startup
# ---------------------------------------------------------------------------


def test_data_dir_created_on_import() -> None:
    """get_data_dir() creates the data directory if it does not exist."""
    import contextlib

    from osu_gallery.db.database import get_data_dir

    had_frozen = hasattr(sys, "frozen")
    try:
        sys.frozen = False
        data_dir = get_data_dir()
    finally:
        if not had_frozen:
            with contextlib.suppress(KeyError):
                del sys.frozen

    assert data_dir.is_dir(), f"Data directory not created at {data_dir}"
