"""Logging configuration for osu gallery.

Sets up console and file handlers on first call to ``setup_logging``.
The file handler writes to ``osu_gallery.log`` in the data directory
(resolved via :func:`osu_gallery.db.database.get_data_dir`).

The root osu_gallery logger is set to INFO; individual modules can
obtain their own logger via ``logging.getLogger(__name__)``.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_SETUP = False


def setup_logging(
    level: int = logging.INFO,
    log_file: str | Path | None = None,
) -> logging.Logger:
    """Configure and return the root ``osu_gallery`` logger.

    Safe to call multiple times — only the first call installs handlers.
    """
    global _LOG_SETUP

    logger = logging.getLogger("osu_gallery")

    if _LOG_SETUP:
        logger.setLevel(level)
        return logger

    _LOG_SETUP = True

    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler — always present.
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler — placed in the data directory so it survives
    # reinstallation and is easy to find. Skipped if the data dir is
    # unwritable (e.g. tests running in a read-only tmp).
    if log_file is None:
        try:
            from osu_gallery.db.database import get_data_dir

            log_file = get_data_dir() / "osu_gallery.log"
        except Exception:
            log_file = Path("osu_gallery.log")

    try:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=2,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except (OSError, PermissionError):
        logger.debug(
            "Could not open log file at %s; file logging disabled.", log_path
        )

    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the ``osu_gallery`` namespace."""
    return logging.getLogger(f"osu_gallery.{name}")
