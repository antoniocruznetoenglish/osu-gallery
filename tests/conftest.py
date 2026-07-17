"""Pytest configuration for osu gallery tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Create a QApplication instance for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.quit()


@pytest.fixture(scope="session")
def real_osu_content() -> str:
    """Load the real .osu file (Dream Walk by Hashiba Gin) for test reference.

    Returns:
        The raw text content of the .osu file.
    """
    test_data_dir = Path(__file__).parent / "test_data"
    osu_file_path = test_data_dir / "dream_walk.osu"
    if not osu_file_path.exists():
        pytest.skip(f"Real .osu test file not found at {osu_file_path}")
    return osu_file_path.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def real_parsed_file(real_osu_content):
    """Parse the real .osu file into an OsuFile object."""
    from osu_gallery.parser.osu_file import parse_osu_file
    return parse_osu_file(real_osu_content)
