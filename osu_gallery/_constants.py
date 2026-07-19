"""Application-wide constants for osu gallery."""

from __future__ import annotations

import sys

APP_NAME = "osu gallery"
APP_VERSION = "0.1.0"
DB_FILENAME = "gallery.db"

# UI dimensions
MIN_WINDOW_WIDTH = 1400
MIN_WINDOW_HEIGHT = 700
SEARCH_EDIT_MIN_WIDTH = 240
SEARCH_DEBOUNCE_MS = 250
PREVIEW_PANE_WIDTH = 900
PREVIEW_PANE_MAX_WIDTH = 1000
PREVIEW_HEIGHT = 1152
THUMBNAIL_WIDTH = 512
THUMBNAIL_HEIGHT = 384
THUMBNAIL_WIDGET_MIN_WIDTH = 220
THUMBNAIL_WIDGET_MIN_HEIGHT = 165
IMPORT_DIALOG_MIN_WIDTH = 600
IMPORT_DIALOG_MIN_HEIGHT = 500

# Visual constants
LABEL_BG_ALPHA = 180
NORMAL_BORDER_COLOR = (180, 180, 180)
HOVER_BORDER_COLOR = (90, 150, 220)
if sys.platform == "win32":
    FONT_FAMILY = "Segoe UI"
elif sys.platform == "darwin":
    FONT_FAMILY = "Helvetica"
else:
    FONT_FAMILY = "Noto Sans"

# Toast
TOAST_DEFAULT_MESSAGE = "Copied!"
TOAST_DEFAULT_DURATION_MS = 1800
TOAST_FADE_DURATION_MS = 250

# Font sizes
FONT_SIZE_TITLE = 16
FONT_SIZE_HEADER = 13
FONT_SIZE_BODY = 12
FONT_SIZE_META = 10
FONT_SIZE_LABEL = 9
FONT_SIZE_ERROR = 11

# Splitter
SPLITTER_PREVIEW_DEFAULT_WIDTH = 900

# Tag categories
TAG_CATEGORY_METADATA = "metadata"
TAG_CATEGORY_MAPPING = "mapping"

# Mapping tag options (manual user input)
MAPPING_TAG_OPTIONS: list[str] = [
    "Circle", "Slider", "Circles", "Sliders",
    "Slider art", "Kickslider", "Kicksliders",
    "vertical slider", "horizontal slider",
    "15\u00b0 angled pattern", "0\u00b0 angled pattern",
    "full screen pattern", "compact pattern",
    "3/4 slider", "3/4sliders",
    "1/2 slider", "1/2 sliders",
    "1/1 slider", "1/1 sliders",
    "2 circles", "3 circles", "4 circles",
    "circle triangle", "circle square", "circle pentagon", "circle hexagon",
    "slider triangle", "slider square", "slider pentagon", "slider hexagon",
]
