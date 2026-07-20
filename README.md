# osu gallery

A visual reference library for osu! beatmap objects. Browse, search, and organize osu! hit circles, sliders, and spinners with full metadata and combo color previews.

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.5+-green.svg)
![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)

## Features

- Parse `.osu` files (circles, sliders, spinners, INI sections, combo colours)
- SQLite-backed database with tag/pattern management and many-to-many relationships
- Full-text search powered by SQLite FTS5
- Thumbnail grid with real-time filtering
- Click-to-expand preview pane with large rendered images, BPM, object counts, and combo colors
- Copy code button for easy reference

## Quick Start

### Prerequisites

- Python 3.10 or higher
```
winget install Python.Python.3.10
```
- pip (Python package manager)

### Installation

1. Clone the repository:

```bash
git clone https://github.com/antoniocruznetoenglish/osu-gallery.git
cd osu-gallery
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

For development (includes testing and linting tools):

```bash
pip install -e ".[dev]"
```

### Running

Launch the application:

```bash
python -m osu_gallery
```

Or if installed in editable mode:

```bash
osu-gallery
```

### Running Tests

```bash
pytest
```

### Building a Standalone Executable (Windows)

Both build modes use `--onedir` to keep the `data/` folder next to the executable (not in temp).

#### Option A: PyInstaller (legacy)

```powershell
.\build.ps1
```

The compiled executable will be in `dist\osu-gallery\osu-gallery.exe` (~234 MB). Run `osu-gallery.exe` from the `dist\osu-gallery\` folder.

#### Option B: Nuitka (recommended, smaller)

```powershell
python -m nuitka --standalone --enable-plugin=pyside6 --nofollow-import-to=tkinter,pydoc,tests osu_gallery/__main__.py
```

The compiled executable will be in `dist\osu-gallery\osu-gallery.exe` (~78 MB). Requires Visual Studio Build Tools or MinGW for the C++ compiler.

### Release Executable

Pre-built release executables are available in the [releases](https://github.com/antoniocruznetoenglish/osu-gallery/releases) page. The Nuitka build (~78 MB) is the recommended version. No installation required — just run `osu-gallery.exe`.

## Project Structure

```
osu_gallery/
  __main__.py          - Application entry point
  _constants.py        - App name, version, UI dimensions
  _logging.py          - Logging configuration
  db/                  - SQLite database layer and models
  parser/              - .osu file parser
  preview/             - Thumbnail and image rendering
  search/              - Full-text search engine (FTS5)
  tags/                - Tag and mapping tag management
  ui/                  - Qt UI components (main window, dialogs, preview pane)
tests/                 - Test suite (pytest)
project_docs/          - Design and architecture documentation
```

## License

[Add your license here]

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
