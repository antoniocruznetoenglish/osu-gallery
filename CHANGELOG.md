# Changelog: osu gallery

> Tracks releases of the actual software — distinct from `06_Decision_Log.md` (why architectural choices were made) and `04_Implementation_Roadmap.md` (when work happened). This is: what shipped, in what version, when.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/) — Added / Changed / Fixed / Removed / Security, newest on top.

**Versioning:** [state your scheme — e.g., semantic versioning MAJOR.MINOR.PATCH; for a solo/homelab tool, even a simple date-based version like `2026.07.12` is fine, just say which]

---

## [Unreleased]

### Added
- Logging module (`osu_gallery/_logging.py`) with console + rotating file handler (5 MB cap, 2 backups)
- `[project.scripts]` console entry point (`osu-gallery = "osu_gallery.__main__:main"`) in pyproject.toml
- Graceful error handling in `__main__.py`: `ImportError`, `OSError` (Qt plugin), and generic exception handlers with friendly user messages via QMessageBox / stderr
- Startup database directory creation verified on app launch via `get_data_dir()`
- 15 Phase 9 tests covering logging config, entry point, and error handling
- `.osu` file parser (`osu_gallery/parser/`) supporting circles, sliders, spinners, INI sections, combo colours
- 26 unit tests for the parser covering valid/invalid input, all object types, edge cases
- SQLite database layer (`osu_gallery/db/`) with CRUD for patterns/tags and many-to-many relationships
- 26 database tests covering tag/pattern CRUD and relationships
- Main window UI with search bar, import dialog, and thumbnail grid
- 11 UI tests for main window and import dialog
- Static thumbnail renderer (`osu_gallery/preview/`) with QPixmap rendering
- 10 integration tests for parse → store → render → display flow
- Search/Filter Engine (`osu_gallery/search/`) with SQLite FTS5 full-text search
- Real-time debounced search bar with tag-based filtering
- 17 search engine tests + 3 UI integration tests for search
- Click-to-expand preview pane (`osu_gallery/ui/_preview_pane.py`) with large rendered preview, metadata display (object count, BPM, tags, combo colors), copy code button, and close button
- QSplitter-based layout in MainWindow for grid + preview side-by-side
- 19 tests for preview pane functionality
- PyInstaller packaging spec file (`osu_gallery.spec`) and build script (`build.ps1`)
- Centralized constants module (`osu_gallery/_constants.py`) with app name, version, UI dimensions, and visual constants
- `get_data_dir()` helper for resolving the database path in both development and PyInstaller-frozen modes
- `__version__` export from the package root
- Packaging verification tests (`tests/test_packaging.py`) covering constants, imports, data directory resolution, and spec file existence

### Changed
- Replaced blanket `except Exception` handlers with specific `except (OSError, ValueError)` in thumbnail and preview renderers
- Replaced private `_search_engine._remove_from_fts()` access with public `remove_from_fts()` method on `SearchEngine`
- Fixed slider path regex in parser to handle comma-containing coordinate data (greedy matching)
- Added guard against negative stay timer duration in toast widget
- Fixed type annotations in `ImportDialog._extract_tag_names` and `_show_success` (no longer using `object` type)
- Resolved relative `gallery.db` path to use `get_data_dir()` for correct behavior in frozen apps

### Fixed
- `QPixmap.save()` crashing with `TypeError` when saving to `bytearray` — now uses `QBuffer`/`QByteArray` (`preview/image_resizer.py`)
- Import dialog hanging silently when image attachment fails — now catches `TypeError`/`Exception` and shows warning (`ui/import_dialog.py`)
- Thumbnail widget always rendering at 200×150 despite 512×384 internal render — now uses `THUMBNAIL_WIDGET_MIN_WIDTH/HEIGHT` constants (512×384) with `sizeHint()` override (`ui/thumbnail_widget.py`, `_constants.py`)
- Preview pane cramped on small windows — raised `MIN_WINDOW_WIDTH` from 800 to 1100 (`_constants.py`)
- Search bar with no visible button and non-functional Enter key — added `QPushButton("Search")` and `returnPressed` connection (`ui/main_window.py`)
- `get_all_patterns()` and `get_patterns_by_tag()` not populating `mapping_tags` — added column to SELECT and `json.loads()` into `Pattern` (`db/database.py`)
- Slider path regex that failed for standard osu! format with comma-separated coordinates in path data

---

## [0.1.0] - 2026-07-16

### Added
- Initial scaffold from project template

<!--
Copy the [Unreleased] block pattern for each new version when you cut one.
A "Security" subsection is worth adding explicitly (not folding into "Fixed")
whenever a change closes a real vulnerability — it's the kind of line future-you
or an auditor will specifically grep for.
-->
