# Implementation Roadmap 8: Refactor User Images from BLOBs to File References

> Replaces inline BLOB storage of user screenshots with on-disk PNG files referenced by path. This eliminates the single biggest source of database bloat, fixes the long-standing image attachment bugs (BUG-101/102) at the architectural level, and makes the gallery portable — the database no longer grows unboundedly with binary data. The change touches every layer: DB schema, data model, import flow, thumbnail rendering, preview pane, and migration.

> **Why this is a new roadmap file, not a backlog entry:** This is a structural refactor that changes the data persistence model for a core feature. It affects every module that reads or writes `user_image`. It deserves its own roadmap with explicit migration, backward compatibility, and rollback plans — not a bugfix backlog item.

**Created:** 2026-07-17
**Status:** Planned (not started)

---

## Task Summary

| # | Task | Priority | Depends On |
|---|---|---|---|
| 1 | Add `screenshots/` directory and file-path column to `pattern` table | P0 | — |
| 2 | Migrate existing BLOB data to on-disk files | P0 | Task 1 |
| 3 | Update `Pattern` model and `GalleryDatabase` to use file paths | P0 | Task 1 |
| 4 | Update `ImportDialog` to save images to disk instead of BLOBs | P0 | Task 3 |
| 5 | Update `ThumbnailWidget` and `_PreviewPane` to load from disk | P0 | Task 3 |
| 6 | Update `EditDialog` to support replacing images | P1 | Task 3 |
| 7 | Update tests for new file-based image storage | P0 | Task 4-6 |
| 8 | Delete images when patterns are deleted (cleanup) | P1 | Task 3 |

---

## Task 1: Add `screenshots/` Directory and File-Path Column

**Problem:** The `pattern` table stores screenshots as `BLOB` data in the `user_image` column. This makes the SQLite database grow with every imported screenshot, prevents external tools from accessing the images, and is the root cause of BUG-101/102 (the resize pipeline writes bytes into a `bytearray` that `QPixmap.save()` cannot handle).

**Goal:**
- Add a `screenshot_path` TEXT column to the `pattern` table storing the relative path to the on-disk PNG
- Create a `screenshots/` directory under the data directory (`data/screenshots/`)
- Each pattern gets its own file: `screenshots/{pattern_id}.png`
- The original `user_image_filename` column is repurposed to store the original filename (for display/reference only)

**Files to change:**
- `osu_gallery/db/database.py` — schema creation, migration, column existence check
- `osu_gallery/_constants.py` — add `SCREENSHOTS_DIR` constant
- `osu_gallery/db/models.py` — add `screenshot_path` field to `Pattern` dataclass

**Implementation plan:**

1. Add constants to `_constants.py`:
   ```python
   SCREENSHOTS_DIR = "screenshots"
   SCREENSHOT_FILENAME_TEMPLATE = "{pattern_id}.png"
   ```

2. Add column to schema in `database.py`:
   ```sql
   screenshot_path TEXT NOT NULL DEFAULT ''
   ```
   Add to the `CREATE TABLE IF NOT EXISTS pattern (...)` block (line 106).

3. Add migration in `_migrate_existing_schema()`:
   ```python
   if not self._column_exists("pattern", "screenshot_path"):
       self.conn.execute(
           "ALTER TABLE pattern ADD COLUMN screenshot_path TEXT NOT NULL DEFAULT ''"
       )
   ```

4. Add helper method to `GalleryDatabase`:
   ```python
   def get_screenshot_path(self, pattern_id: int) -> Path | None:
       """Return the absolute path to a pattern's screenshot file, or None."""
       row = self.conn.execute(
           "SELECT screenshot_path FROM pattern WHERE id = ?", (pattern_id,)
       ).fetchone()
       if row is None or not row["screenshot_path"]:
           return None
       return self._data_dir / row["screenshot_path"]
   ```
   Where `_data_dir` is stored as `self._data_dir = get_data_dir()` in `__init__`.

5. Update `Pattern` model in `models.py`:
   ```python
   @dataclass
   class Pattern:
       # ... existing fields ...
       screenshot_path: str = ""  # relative path like "screenshots/26.png"
   ```

**Coding standards compliance:**
- `screenshot_path` is a relative path, never absolute — stored in DB, resolved to absolute at read time (per `_constants.py` convention)
- Single source of truth for screenshot directory: `SCREENSHOTS_DIR` constant
- New method gets docstring with inputs, outputs, exceptions

---

## Task 2: Migrate Existing BLOB Data to On-Disk Files

**Problem:** Existing patterns in the database have their screenshots stored as BLOBs. A migration script is needed to extract them to disk before the schema change takes effect, otherwise those images become inaccessible.

**Goal:**
- Extract all existing `user_image` BLOBs to `screenshots/{id}.png`
- Update `screenshot_path` column with the relative path
- Preserve the original `user_image_filename` for reference
- Migration is idempotent — safe to re-run

**Files to change:**
- New file: `osu_gallery/db/migrate_images.py` — one-time migration script
- `osu_gallery/db/database.py` — add `export_user_image_blobs()` method for the migration

**Implementation plan:**

1. Add a migration method to `GalleryDatabase`:
   ```python
   def export_user_image_blobs(self) -> int:
       """Export all BLOB images to disk. Returns count of exported files."""
       rows = self.conn.execute(
           "SELECT id, user_image, user_image_filename "
           "FROM pattern WHERE user_image IS NOT NULL AND user_image != X''"
       ).fetchall()
       screenshots_dir = self._data_dir / "screenshots"
       screenshots_dir.mkdir(parents=True, exist_ok=True)
       count = 0
       for row in rows:
           path = screenshots_dir / f"{row['id']}.png"
           if path.exists():
               continue  # idempotent: skip already-migrated
           path.write_bytes(row["user_image"])
           self.conn.execute(
               "UPDATE pattern SET screenshot_path = ? WHERE id = ?",
               (f"screenshots/{row['id']}.png", row["id"]),
           )
           count += 1
       self.conn.commit()
       return count
   ```

2. Add a CLI entry point or a manual trigger in `__main__.py`:
   ```python
   # In __main__.py or a new migrate.py
   if __name__ == "__main__":
       db = GalleryDatabase(get_data_dir() / DB_FILENAME)
       count = db.export_user_image_blobs()
       print(f"Migrated {count} images to disk.")
       db.close()
   ```

3. After migration, the old `user_image BLOB` column can be kept for one release as a fallback, then removed.

**Risk assessment:**
- If a BLOB is corrupted, `path.write_bytes()` will still write garbage — wrap in a try/except and log failures
- Migration should be logged: `logger.info("Migrated %d images to disk", count)`

---

## Task 3: Update `Pattern` Model and `GalleryDatabase` to Use File Paths

**Problem:** All database methods that currently read/write `user_image` BLOBs need to be updated to work with file paths instead.

**Goal:**
- Remove `user_image` BLOB column reads from all query methods
- Add `screenshot_path` to all Pattern constructions
- Replace `update_pattern_user_image()` with `set_pattern_screenshot()`
- Update `update_pattern()` to no longer include `user_image` in the UPDATE
- Update `delete_pattern()` to remove the associated screenshot file

**Files to change:**
- `osu_gallery/db/database.py` — all methods touching `user_image`
- `osu_gallery/db/models.py` — `Pattern` dataclass field rename

**Implementation plan:**

1. Remove `user_image` from `Pattern` dataclass, add `screenshot_path`:
   ```python
   # Remove:
   # user_image: bytes = b""
   # user_image_filename: str = ""
   # Add:
   screenshot_path: str = ""  # relative path, e.g. "screenshots/26.png"
   ```

2. Update `create_pattern()`:
   - Remove `user_image` and `user_image_filename` parameters
   - Add `screenshot_path: str = ""` parameter
   - Include in INSERT statement and Pattern construction

3. Update `get_pattern()`:
   - Remove `user_image, user_image_filename` from SELECT
   - Add `screenshot_path` to SELECT
   - Pass `screenshot_path=row["screenshot_path"] or ""` to Pattern constructor

4. Update `get_all_patterns()`:
   - Same changes as `get_pattern()`

5. Update `update_pattern()`:
   - Remove `user_image, user_image_filename` from UPDATE
   - Add `screenshot_path` to UPDATE

6. Replace `update_pattern_user_image()` with `set_pattern_screenshot()`:
   ```python
   def set_pattern_screenshot(self, pattern_id: int, relative_path: str) -> None:
       """Set the screenshot path for a pattern.
       
       Args:
           pattern_id: The id of the pattern.
           relative_path: Relative path to the screenshot file (e.g. "screenshots/26.png").
       """
       self.conn.execute(
           "UPDATE pattern SET screenshot_path = ? WHERE id = ?",
           (relative_path, pattern_id),
       )
       self.conn.commit()
   ```

7. Update `delete_pattern()` to clean up the file:
   ```python
   def delete_pattern(self, pattern_id: int) -> None:
       """Delete a pattern and its associated screenshot file."""
       # Get screenshot path before deleting
       row = self.conn.execute(
           "SELECT screenshot_path FROM pattern WHERE id = ?", (pattern_id,)
       ).fetchone()
       if row and row["screenshot_path"]:
           screenshot_file = self._data_dir / row["screenshot_path"]
           try:
               if screenshot_file.exists():
                   screenshot_file.unlink()
           except OSError as err:
               logger.warning("Failed to delete screenshot %s: %s", screenshot_file, err)
       self.conn.execute("DELETE FROM pattern WHERE id = ?", (pattern_id,))
       self.conn.commit()
       self._notify_search_sync_remove(pattern_id)
   ```

8. Remove the `user_image` and `user_image_filename` columns from the schema after migration is complete (can be a separate migration step).

**Backward compatibility:**
- Keep `user_image BLOB` column for one release with a deprecation note
- `get_pattern()` can fall back to `user_image` if `screenshot_path` is empty (for patterns that haven't been migrated yet)

---

## Task 4: Update `ImportDialog` to Save Images to Disk

**Problem:** `import_dialog.py` currently reads image bytes, resizes them, and passes them to `db.update_pattern_user_image()` which writes to a BLOB column. This needs to save the resized image to disk instead.

**Goal:**
- After selecting an image file, resize it and save to `screenshots/{pattern_id}.png`
- Store the relative path in the database
- Remove the resize-to-bytes pipeline (the `_get_selected_image_bytes()` method)
- Keep the file selection flow (`_on_attach_image`) unchanged

**Files to change:**
- `osu_gallery/ui/import_dialog.py` — image handling in `_on_parse_and_save`
- `osu_gallery/preview/image_resizer.py` — add a `save_resized_image_to_file()` function

**Implementation plan:**

1. Add a file-saving variant to `image_resizer.py`:
   ```python
   def resize_and_save_image(
       image_path: str,
       output_path: Path,
       target_width: int = 512,
       target_height: int = 384,
   ) -> Path:
       """Load, resize, and save an image to disk as PNG.
       
       Args:
           image_path: Path to the source image.
           output_path: Where to write the resized PNG.
           target_width: Target width in pixels.
           target_height: Target height in pixels.
           
       Returns:
           The output_path on success.
           
       Raises:
           OSError: If reading or writing fails.
       """
       # Reuse _resize_image to get bytes, then write to file
       with open(image_path, "rb") as f:
           raw_bytes = f.read()
       resized = _resize_image(raw_bytes, target_width, target_height)
       output_path.parent.mkdir(parents=True, exist_ok=True)
       output_path.write_bytes(resized)
       return output_path
   ```

2. Update `_on_parse_and_save()` in `import_dialog.py`:
   ```python
   # Replace the BLOB image handling block:
   # Handle user image — save to disk
   if self._selected_image_path:
       try:
           screenshot_filename = f"{pattern.id}.png"
           screenshot_path = self.db._data_dir / "screenshots" / screenshot_filename
           resize_and_save_image(
               self._selected_image_path, screenshot_path,
               target_width=512, target_height=384,
           )
           self.db.set_pattern_screenshot(
               pattern.id, f"screenshots/{screenshot_filename}"
           )
       except Exception as img_err:
           logger.warning("Failed to save screenshot: %s", img_err)
           self._show_error(f"Pattern saved, but screenshot failed: {img_err}")
   ```

3. Remove `_get_selected_image_bytes()` method entirely — no longer needed.

4. Update `_on_attach_image()` — keep as-is, it already stores the file path.

**Coding standards compliance:**
- New `resize_and_save_image()` has docstring with args, returns, raises
- No silent exception handlers
- Logging via `logger` module

---

## Task 5: Update `ThumbnailWidget` and `_PreviewPane` to Load from Disk

**Problem:** Both `thumbnail_widget.py` and `_preview_pane.py` load images via `pixmap.loadFromData(pattern.user_image)` which expects bytes. They need to load from file paths instead.

**Goal:**
- `ThumbnailWidget._render()`: check `pattern.screenshot_path`, load via `QPixmap(path)` if present
- `_PreviewPane.load_pattern()`: same change
- Both fall back to auto-rendered preview if no screenshot file exists

**Files to change:**
- `osu_gallery/ui/thumbnail_widget.py` — `_render()` method
- `osu_gallery/ui/_preview_pane.py` — `load_pattern()` method

**Implementation plan:**

1. Update `thumbnail_widget.py` `_render()`:
   ```python
   def _render(self, raw_code: str) -> None:
       pattern = self._db.get_pattern(self._pattern_id)
       if pattern is None:
           self._show_error_state()
           return

       # Check for user screenshot on disk
       if pattern.screenshot_path:
           screenshot_file = self._db._data_dir / pattern.screenshot_path
           if screenshot_file.exists():
               pixmap = QPixmap()
               if pixmap.load(str(screenshot_file)):
                   self._pixmap = pixmap
                   self._is_rendered = True
                   self._apply_style()
                   self.update()
                   return
               else:
                   logger.warning(
                       "Failed to load screenshot for pattern %d: %s",
                       self._pattern_id, screenshot_file,
                   )

       # Fall back to auto-rendered thumbnail
       try:
           osu_file = parse_osu_file(raw_code)
       except ParseError as exc:
           logger.warning("Failed to parse pattern %d: %s", self._pattern_id, exc)
           self._show_error_state()
           return

       self._osu_file = osu_file
       self._combo_color = osu_file.combo_colors[0] if osu_file.combo_colors else None

       try:
           self._pixmap = render_thumbnail(osu_file, width=512, height=384)
       except (OSError, ValueError) as exc:
           logger.exception(
               "Failed to render thumbnail for pattern %d: %s",
               self._pattern_id, exc,
           )
           self._show_error_state()
           return

       self._is_rendered = True
       self._apply_style()
       self.update()
   ```

2. Update `_preview_pane.py` `load_pattern()`:
   ```python
   # Replace the user_image block:
   # Check for user screenshot on disk first
   if pattern.screenshot_path:
       screenshot_file = self._db._data_dir / pattern.screenshot_path
       if screenshot_file.exists():
           pixmap = QPixmap()
           if pixmap.load(str(screenshot_file)):
               self._pixmap = pixmap
           else:
               logger.warning("Failed to load screenshot for pattern %d", pattern_id)
               self._pixmap = render_pattern_preview(osu_file, width=1536, height=1152)
       else:
           self._pixmap = render_pattern_preview(osu_file, width=1536, height=1152)
   else:
       try:
           self._pixmap = render_pattern_preview(osu_file, width=1536, height=1152)
       except (OSError, ValueError) as exc:
           logger.exception(
               "Failed to render preview for pattern %d: %s", pattern_id, exc
           )
           self._show_error_state("Failed to render preview")
           return
   ```

**Key change:** `QPixmap.loadFromData(bytes)` → `QPixmap.load(str_path)`. The file path is resolved from `self._db._data_dir / pattern.screenshot_path`.

---

## Task 6: Update `EditDialog` to Support Replacing Images

**Problem:** The `EditDialog` currently has a `_selected_image_path` attribute but no UI for selecting/replacing images. After the refactor, it should support attaching a new screenshot to an existing pattern.

**Goal:**
- Add an "Attach/Replace Screenshot" button to the edit dialog
- When a new image is selected, resize and save it, update the database path
- Show current screenshot status (has/hasn't)

**Files to change:**
- `osu_gallery/ui/edit_dialog.py` — add image selection UI and handler

**Implementation plan:**

1. Add UI elements to `_setup_ui()`:
   - `_attach_screenshot_button` — QPushButton
   - `_screenshot_status_label` — QLabel showing current state

2. Add handler `_on_attach_screenshot()`:
   - Opens file dialog (same as import dialog)
   - On selection, calls `resize_and_save_image()` with the pattern's ID
   - Calls `db.set_pattern_screenshot(pattern.id, relative_path)`

3. In `_populate_fields()`:
   - If `pattern.screenshot_path` is non-empty, show the filename
   - Enable/disable the attach button accordingly

4. In `_on_save()`:
   - If a new screenshot was attached, update the database before saving the pattern

---

## Task 7: Update Tests

**Problem:** The existing test suite (`tests/test_roadmap4_user_images.py`) has ~15 tests that verify BLOB-based image storage. All need to be rewritten for file-based storage.

**Goal:**
- Update existing tests to verify file-based image storage
- Add tests for migration, file cleanup on delete, missing file fallback
- Ensure `resize_and_save_image()` is tested
- Remove tests that only verify BLOB behavior

**Files to change:**
- `tests/test_roadmap4_user_images.py` — rewrite all image-related tests
- New tests for migration in a separate file or as part of database tests

**Tests to add/modify:**

| Test | What it verifies |
|---|---|
| `test_pattern_has_screenshot_path_field` | `Pattern` dataclass has `screenshot_path` instead of `user_image` |
| `test_database_stores_screenshot_path` | `create_pattern`/`get_pattern` round-trips `screenshot_path` |
| `test_set_pattern_screenshot_updates_path` | `set_pattern_screenshot()` updates the DB correctly |
| `test_resize_and_save_image_writes_png` | `resize_and_save_image()` produces a valid PNG file |
| `test_resize_and_save_image_maintains_aspect_ratio` | Resized output has correct dimensions |
| `test_thumbnail_widget_loads_from_disk` | Widget loads screenshot from file path |
| `test_thumbnail_widget_falls_back_to_render` | Widget falls back to auto-render when no screenshot file |
| `test_preview_pane_loads_from_disk` | Preview pane loads screenshot from file path |
| `test_preview_pane_falls_back_to_render` | Preview pane falls back to auto-render |
| `test_delete_pattern_removes_screenshot_file` | Deleting a pattern removes its screenshot file |
| `test_delete_pattern_no_file_does_not_crash` | Deleting a pattern without a screenshot doesn't error |
| `test_migration_exports_blobs_to_disk` | Migration extracts BLOBs to `screenshots/` directory |
| `test_migration_is_idempotent` | Re-running migration doesn't duplicate files |
| `test_screenshot_path_relative_not_absolute` | DB stores relative paths, never absolute |
| `test_missing_screenshot_file_falls_back` | Missing file on disk triggers auto-render fallback |
| `test_database_screenshot_path_helper` | `get_screenshot_path()` resolves to absolute path |

**Tests to remove:**
- `test_database_stores_user_image` — no longer applicable (BLOB)
- `test_database_stores_user_image_filename` — `user_image_filename` repurposed
- `test_database_update_pattern_user_image` — replaced by `set_pattern_screenshot`
- `test_preview_pane_uses_user_image_when_available` — check for `screenshot_path` instead
- `test_thumbnail_widget_uses_user_image_when_available` — check for `screenshot_path` instead
- `test_pattern_user_image_defaults_to_empty` — check `screenshot_path == ""` instead

---

## Task 8: Clean Up Old BLOB Column (Post-Migration)

**Problem:** After migration is verified, the old `user_image BLOB` and `user_image_filename TEXT` columns should be removed to prevent confusion and reduce schema clutter.

**Goal:**
- Remove `user_image` and `user_image_filename` from schema
- Remove all references from database methods
- Remove from `Pattern` model

**Implementation plan:**

1. After confirming migration is complete and tested:
   - Remove `user_image BLOB` and `user_image_filename TEXT NOT NULL DEFAULT ''` from the `CREATE TABLE` statement
   - Remove the `_column_exists` + `ALTER TABLE` migration blocks for these columns
   - Remove all `user_image` / `user_image_filename` references from `get_pattern()`, `get_all_patterns()`, `update_pattern()`, `create_pattern()`
   - Remove `user_image_filename` field from `Pattern` model (keep `screenshot_path` as the single source of truth)

2. Add a migration step for existing databases (one-time `ALTER TABLE pattern DROP COLUMN user_image`):
   ```python
   if self._column_exists("pattern", "user_image"):
       self.conn.execute("ALTER TABLE pattern DROP COLUMN user_image")
   if self._column_exists("pattern", "user_image_filename"):
       self.conn.execute("ALTER TABLE pattern DROP COLUMN user_image_filename")
   ```

---

## Execution Order

```
Step 1: Task 1 — Schema + constants + model changes (foundation, no behavior change yet)
Step 2: Task 2 — Migration script (extract existing BLOBs to disk)
Step 3: Task 3 — Update database layer (all CRUD methods)
Step 4: Task 4 — Update import dialog (new images saved to disk)
Step 5: Task 5 — Update thumbnail widget + preview pane (load from disk)
Step 6: Task 6 — Update edit dialog (replace images)
Step 7: Task 7 — Update all tests
Step 8: Task 8 — Remove old BLOB columns (cleanup, after verification)
```

**Parallelization opportunities:**
- Tasks 1 and 2 can be done together (schema + migration)
- Tasks 3 and 7 can partially overlap (model changes first, then tests)
- Tasks 4, 5, and 6 can be done in parallel once Task 3 is complete (they touch different UI files)
- Task 8 must be last — only after all code paths are verified

---

## Database Schema Changes

### New column
```sql
ALTER TABLE pattern ADD COLUMN screenshot_path TEXT NOT NULL DEFAULT '';
```

### Removed columns (post-migration)
```sql
ALTER TABLE pattern DROP COLUMN user_image;
ALTER TABLE pattern DROP COLUMN user_image_filename;
```

### New directory
```
data/
├── gallery.db
└── screenshots/
    ├── 1.png
    ├── 2.png
    └── ...
```

### Backward compatibility
- During transition: `screenshot_path` is empty for new patterns until an image is attached; populated for migrated patterns
- `get_pattern()` can fall back to `user_image` BLOB if `screenshot_path` is empty (one-release grace period)

---

## New Files

| File | Purpose | Depends On |
|---|---|---|
| `osu_gallery/db/migrate_images.py` | One-time migration script for BLOB → disk | Task 1 |
| `tests/test_screenshot_migration.py` | Migration tests | Task 2 |

## Modified Files

| File | Changes |
|---|---|
| `osu_gallery/db/database.py` | Schema, CRUD methods, new `set_pattern_screenshot()`, `get_screenshot_path()`, updated `delete_pattern()` |
| `osu_gallery/db/models.py` | `Pattern` dataclass: remove `user_image`/`user_image_filename`, add `screenshot_path` |
| `osu_gallery/_constants.py` | Add `SCREENSHOTS_DIR`, `SCREENSHOT_FILENAME_TEMPLATE` |
| `osu_gallery/ui/import_dialog.py` | Replace BLOB image handling with file save; remove `_get_selected_image_bytes()` |
| `osu_gallery/ui/thumbnail_widget.py` | Load screenshot from disk path instead of bytes |
| `osu_gallery/ui/_preview_pane.py` | Load screenshot from disk path instead of bytes |
| `osu_gallery/ui/edit_dialog.py` | Add screenshot attach/replace UI |
| `osu_gallery/preview/image_resizer.py` | Add `resize_and_save_image()` file-output variant |
| `tests/test_roadmap4_user_images.py` | Rewrite all tests for file-based storage |

---

## Risk Assessment

| Risk | Mitigation |
|---|---|
| Migration loses images if script crashes mid-way | Migration is idempotent — each file is checked for existence before writing; re-run is safe |
| File paths break if data directory moves | Always resolve via `get_data_dir()` + relative path; never store absolute paths in DB |
| Old BLOB column left in schema causes confusion | One-release deprecation with explicit migration step; removed in next release |
| Large existing database makes migration slow | Migration processes one row at a time with commit after each batch; not blocking |
| Screenshot file deleted externally while DB still references it | `delete_pattern()` removes the file; missing file triggers auto-render fallback (graceful degradation) |
| `QPixmap.load()` fails on corrupted PNG files | Try/except around `load()`, fall back to auto-render with warning log |
| PyInstaller bundling doesn't include `screenshots/` directory | `screenshots/` is under `data/` which is created at runtime — not bundled, not affected |
| Tests reference old `user_image` field | All tests rewritten in Task 7; no references to `user_image` remain in test code |

---

## Coding Standards Compliance Checklist

Per `12_Coding_Standards.md`:

| Rule | Compliance |
|---|---|
| §1: snake_case for functions/variables, PascalCase for classes | All new/modified code follows this |
| §1: Single source of truth for constants | `SCREENSHOTS_DIR` in `_constants.py`; screenshot path resolution via `get_data_dir()` |
| §1: Single responsibility per function | `resize_and_save_image()` separates resize logic from file I/O |
| §2: No empty exception handlers | All `except` blocks log and handle; missing file → fallback render |
| §2: Specific exception types | `OSError` for file I/O, `ParseError` for parse failures |
| §3: Every public function has docstring | All new/modified public methods documented |
| §4: Structured logging, no `print` | All logging via `logger` from `logging` module |
| §5: No AI-agent-specific violations | Docstrings complete, no silent exception swallowing |
| §7: No test softening | All tests assert expected behavior; no `try/except: pass` |

---

## Definition of Done for This Roadmap

- [ ] Task 1: `screenshot_path` column added to schema
- [ ] Task 1: `screenshots/` directory constant defined in `_constants.py`
- [ ] Task 1: `Pattern` model updated with `screenshot_path` field
- [ ] Task 2: Migration script extracts all existing BLOBs to disk
- [ ] Task 2: Migration is idempotent (safe to re-run)
- [ ] Task 3: All database CRUD methods use `screenshot_path` instead of `user_image` BLOB
- [ ] Task 3: `set_pattern_screenshot()` method exists and works
- [ ] Task 3: `delete_pattern()` removes associated screenshot file
- [ ] Task 4: Import dialog saves resized images to disk
- [ ] Task 4: `_get_selected_image_bytes()` removed
- [ ] Task 5: Thumbnail widget loads screenshots from disk
- [ ] Task 5: Preview pane loads screenshots from disk
- [ ] Task 5: Both fall back to auto-render when no screenshot file exists
- [ ] Task 6: Edit dialog supports attaching/replacing screenshots
- [ ] Task 7: All old BLOB tests removed or rewritten
- [ ] Task 7: 15+ new tests for file-based storage
- [ ] Task 7: Migration tests added
- [ ] Task 8: Old `user_image` BLOB column removed from schema
- [ ] Existing test suite passes (all green)
- [ ] `ruff` linting passes with no errors
- [ ] All public functions have docstrings
- [ ] No empty exception handlers
- [ ] Feature logged in `04_Implementation_Roadmap.md` Feature Log
- [ ] Any newly-discovered issues logged in `13_Bugfix_and_Refactor_Backlog.md`

---

## Future-Proofing

This refactor lays groundwork for several future features:

- **Batch export:** Users can now copy the `screenshots/` directory to back up their images independently of the database
- **External image editors:** Screenshots are standard PNG files that can be opened in any image editor
- **Image compression:** Since images are files, future work can add lossy compression (JPEG) to reduce disk usage without touching the database
- **Multi-resolution:** The file-based approach makes it trivial to store multiple resolutions (thumbnail + full-res) as separate files
- **AI preview enhancement:** Future AI analysis can read the PNG file directly without extracting from the database

### Extensibility Impact

| Module | Impact | Design Implication |
|---|---|---|
| Database | Schema change, new file I/O seam | `get_screenshot_path()` centralizes path resolution |
| Import/Export | Image pipeline: bytes → file | `resize_and_save_image()` is the new seam |
| UI (thumbnail) | Load from disk | `QPixmap.load(str)` replaces `loadFromData(bytes)` |
| UI (preview pane) | Load from disk | Same change as thumbnail |
| UI (edit dialog) | New: attach/replace image | Reuses same resize + save pipeline |
| Search/Filter | No impact | FTS5 index doesn't reference images |
| Migration | One-time data transfer | Isolated in `migrate_images.py` |
