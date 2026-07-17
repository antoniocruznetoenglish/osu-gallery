# Implementation Roadmap 3: Size Overhaul, Tag Rework, Search Autocomplete & Combo Order

> This roadmap covers the next round of structural changes: larger previews, tag system rework (metadata fields replaced by structured artist/title/mapper, mapping tags become manual), search autocomplete, and combo order numbering on previews. Sequenced in dependency order.

**Created:** 2026-07-17
**Status:** Completed

---

## Task Summary

| # | Task | Priority | Depends On |
|---|---|---|---|
| 1 | Increase thumbnail size to match current preview; double preview size | P1 | — |
| 2 | Rework tags: structured metadata fields (artist, title, mapper) replace metadata tag category; mapping tags become manual user input | P1 | — |
| 3 | Auto-detection prioritizes object count/types; mapping tag detection removed (user adds manually) | P1 | Task 2 |
| 4 | Search bar autocomplete — suggest matching terms as user types | P1 | — |
| 5 | Display numerical combo order on thumbnails and preview | P2 | — |

---

## Task 1: Increase Thumbnail & Preview Sizes

**Problem:** Thumbnails are rendered at 200x150 — too small to see object details. Preview is 512x384 (osu! native) but displayed at 380px wide, making it look cramped. Both need to be larger for reference use.

**Goal:**
- Thumbnails: same size as current preview (512x384), displayed in the grid at a reasonable scaled size
- Preview pane: at least double the current size (1024x768), displayed proportionally in the pane

**Files to change:**
- `osu_gallery/_constants.py` — update `THUMBNAIL_WIDTH`, `THUMBNAIL_HEIGHT`, `PREVIEW_HEIGHT`, `PREVIEW_PANE_WIDTH`
- `osu_gallery/preview/thumbnail_renderer.py` — update default render dimensions
- `osu_gallery/ui/thumbnail_widget.py` — update `_load_and_render()` call, `paintEvent()` scaling
- `osu_gallery/ui/_preview_pane.py` — update `_PANE_WIDTH`, `_PREVIEW_HEIGHT`, scaled rendering
- `osu_gallery/ui/main_window.py` — update splitter default sizes

**Implementation plan:**

1. Update `_constants.py`:
   ```python
   THUMBNAIL_WIDTH = 512        # was 200
   THUMBNAIL_HEIGHT = 384       # was 150
   PREVIEW_HEIGHT = 768         # was 384 (doubled)
   PREVIEW_PANE_WIDTH = 500     # was 380 (wider for larger preview)
   PREVIEW_PANE_MAX_WIDTH = 620 # was 480
   ```

2. Update `thumbnail_renderer.py`:
   - `render_thumbnail()` default `width=512, height=384` (already matches new constants)
   - `render_pattern_preview()` default `width=1024, height=768` (doubled from 512x384)

3. Update `thumbnail_widget.py`:
   - `_load_and_render()` calls `render_thumbnail(osu_file, width=200, height=150)` → change to `width=512, height=384`
   - `paintEvent()` scales pixmap to widget size with `KeepAspectRatio` — no change needed (already correct)
   - Update `setMinimumSize(160, 120)` → `setMinimumSize(200, 150)` to accommodate scaled display

4. Update `_preview_pane.py`:
   - `_PANE_WIDTH = 500` (was 380)
   - `_PREVIEW_HEIGHT = 768` (was 384)
   - `load_pattern()` renders at `width=1024, height=768` (was 512x384)
   - Scaled display: `available_width = self._PANE_WIDTH`, `scaled_height = int(available_width * _PREVIEW_HEIGHT / 1024)` — update the divisor from 512 to 1024

5. Update `main_window.py`:
   - `_on_pattern_clicked()` default width: `380` → `500`
   - Splitter initial sizes: `[800, 0]` stays the same (preview still starts collapsed)

**Tests to add:**
- `test_thumbnail_rendered_at_new_size` — verify thumbnail rendered at 512x384
- `test_preview_rendered_at_doubled_size` — verify preview rendered at 1024x768
- `test_preview_pane_dimensions` — verify pane width/height constants updated

---

## Task 2: Rework Tags — Structured Metadata Fields

**Problem:** The current system stores artist, title, and mapper as "metadata tags" in the tag system alongside mapping tags. These are fundamentally different: artist/title/mapper are structured metadata fields, not free-form tags. They should be first-class fields on the Pattern, not tags.

**Goal:**
- Add `artist`, `title`, `mapper` fields to the `Pattern` dataclass and database
- Remove auto-extraction of .osu metadata into tags
- Display artist/title/mapper as structured metadata in the preview pane (above tags)
- The "Metadata:" tag section in the preview pane is removed

**Files to change:**
- `osu_gallery/db/models.py` — add `artist`, `title`, `mapper` fields to `Pattern`
- `osu_gallery/db/database.py` — add columns to schema, update all CRUD methods
- `osu_gallery/ui/import_dialog.py` — extract artist/title/mapper during import, stop auto-creating metadata tags
- `osu_gallery/ui/_preview_pane.py` — display artist/title/mapper as structured info, remove metadata tag section
- `osu_gallery/search/engine.py` — index artist/title/mapper in FTS5 for searchability
- `osu_gallery/parser/models.py` — `OsuFile` already has `metadata.artist`, `metadata.title`, `metadata.creator` — no change needed

**Implementation plan:**

1. Update `db/models.py` — add to `Pattern` dataclass:
   ```python
   artist: str = ""
   title: str = ""
   mapper: str = ""
   ```

2. Update `db/database.py`:
   - Add columns to schema: `artist TEXT NOT NULL DEFAULT ''`, `title TEXT NOT NULL DEFAULT ''`, `mapper TEXT NOT NULL DEFAULT ''`
   - Add migration in `_migrate_existing_schema()`:
     ```python
     if not self._column_exists("pattern", "artist"):
         self.conn.execute("ALTER TABLE pattern ADD COLUMN artist TEXT NOT NULL DEFAULT ''")
     if not self._column_exists("pattern", "title"):
         self.conn.execute("ALTER TABLE pattern ADD COLUMN title TEXT NOT NULL DEFAULT ''")
     if not self._column_exists("pattern", "mapper"):
         self.conn.execute("ALTER TABLE pattern ADD COLUMN mapper TEXT NOT NULL DEFAULT ''")
     ```
   - Update `create_pattern()` to accept and store `artist`, `title`, `mapper`
   - Update `get_pattern()` to read and return these fields
   - Update `get_all_patterns()` similarly
   - Update `update_pattern()` to include these fields

3. Update `import_dialog.py`:
   - In `_on_parse_and_save()`, extract from parsed `osu_file`:
     ```python
     pattern = self.db.create_pattern(
         raw_code=raw_code,
         objects_only=objects_only,
         object_count=len(osu_file.hit_objects),
         circle_count=osu_file.circle_count,
         slider_count=osu_file.slider_count,
         timing_bpm=osu_file.timing_bpm,
         artist=osu_file.metadata.artist,
         title=osu_file.metadata.title,
         mapper=osu_file.metadata.creator,
     )
     ```
   - In `_extract_tag_names()`: remove the metadata tag extraction block (the part that pulls `metadata.tags` and `creator` into metadata_tags list). The function should only return mapping tags (which will become manual in Task 3).

4. Update `_preview_pane.py`:
   - In `_render_content()`, add structured metadata display above tags:
     ```python
     # Artist/Title/Mapper rows
     if pattern.artist:
         self._add_meta_row(meta_layout, "Artist:", pattern.artist)
     if pattern.title:
         self._add_meta_row(meta_layout, "Title:", pattern.title)
     if pattern.mapper:
         self._add_meta_row(meta_layout, "Mapper:", pattern.mapper)
     ```
   - Add helper `_add_meta_row(layout, label, value)` that creates a label+value row
   - Remove `_render_tags()` metadata section — tags are now purely mapping tags (or manual)

5. Update `search/engine.py`:
   - In `sync_fts()`, include artist, title, mapper in searchable text:
     ```python
     searchable = f"{pattern.artist} {pattern.title} {pattern.mapper} {pattern.raw_code} {tag_text}"
     ```

**Database migration:** The `ALTER TABLE ADD COLUMN ... DEFAULT ''` approach is safe for existing data. All existing patterns get empty strings for the new fields.

**Tests to add:**
- `test_pattern_has_artist_title_mapper_fields` — verify dataclass fields exist
- `test_database_stores_artist_title_mapper` — verify CRUD round-trip
- `test_import_extracts_artist_title_mapper` — verify import dialog populates fields
- `test_preview_displays_artist_title_mapper` — verify preview pane shows structured fields
- `test_search_indexes_artist_title_mapper` — verify FTS5 includes new fields
- `test_schema_migration_adds_new_columns` — verify migration works on existing DB

---

## Task 3: Auto-Detection Prioritizes Object Count/Types; Mapping Tags Manual

**Problem:** The current auto-detection in `mapping_tags.py` generates tags like "2 circles", "kickslider", "15º angled pattern" automatically. The user wants auto-detection to only cover object counts/types (circles, sliders, spinners) and have all mapping tags (circle patterns, slider types, angles, coverage, shapes) be manually added by the user.

**Goal:**
- Auto-detection: only count circles, sliders, spinners → these become the "object type" tags
- Manual: all mapping tags from the priority list are added by the user via the import dialog
- The import dialog's manual tag field becomes the primary place for mapping tags

**Mapping tag priority list (manual input):**
```
Circle, Slider, Circles, Sliders,
Slider art, Kickslider, Kicksliders,
vertical slider, horizontal slider,
15º angled pattern, 0° angled pattern,
full screen pattern, compact pattern,
3/4 slider, 3/4sliders,
1/2 slider, 1/2 sliders,
1/1 slider, 1/1 sliders,
2 circles, 3 circles, 4 circles,
circle triangle, circle square, circle pentagon, circle hexagon,
slider triangle, slider square, slider pentagon, slider hexagon
```

**Files to change:**
- `osu_gallery/tags/mapping_tags.py` — strip to only count circles/sliders/spinners
- `osu_gallery/ui/import_dialog.py` — update tag extraction, make mapping tags manual
- `osu_gallery/_constants.py` — define the canonical mapping tag list
- `osu_gallery/ui/_preview_pane.py` — display mapping tags section (user-added only)

**Implementation plan:**

1. Create `osu_gallery/_constants.py` constant for the canonical mapping tag list:
   ```python
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
   ```

2. Simplify `mapping_tags.py`:
   - Remove `_detect_slider_patterns()`, `_detect_coverage_patterns()`, `_calculate_slider_angle()`
   - Keep only a simple function that counts objects:
     ```python
     def detect_object_tags(osu_file: OsuFile) -> list[str]:
         """Auto-detect object type tags (circles, sliders, spinners)."""
         tags: list[str] = []
         if osu_file.circle_count > 0:
             tags.append(f"{osu_file.circle_count} circles")
         if osu_file.slider_count > 0:
             tags.append(f"{osu_file.slider_count} sliders")
         spinners = sum(1 for obj in osu_file.hit_objects if obj.is_spinner)
         if spinners > 0:
             tags.append(f"{spinners} spinners")
         return tags
     ```

3. Update `import_dialog.py`:
   - Replace `detect_mapping_tags(osu_file)` call with `detect_object_tags(osu_file)`
   - The manual tag input field now accepts mapping tags from the priority list
   - Add a helper to validate/suggest mapping tags from the priority list as the user types
   - Metadata tags (from .osu file `Tags:` field) are no longer auto-created — those values go into the `title` field instead (already handled in Task 2)

4. Update `_preview_pane.py`:
   - Tags section now shows only user-added mapping tags (no auto-detected ones besides object counts)
   - Display object count tags (auto-detected) separately from mapping tags (manual)

**Tests to add:**
- `test_detect_object_tags_only_counts` — verify only circle/slider/spinner counts are auto-detected
- `test_no_slider_pattern_auto_detection` — verify "kickslider", "angled", etc. are NOT auto-detected
- `test_mapping_tag_options_constant` — verify the canonical list is defined
- `test_import_dialog_manual_mapping_tags` — verify user can add mapping tags manually

---

## Task 4: Search Bar Autocomplete

**Problem:** The search bar has no autocomplete. As the user types, they should see matching suggestions (tag names, artist, title, mapper, and other searchable terms) in a dropdown.

**Goal:**
- As the user types in the search bar, show a dropdown with matching suggestions
- Suggestions come from: tag names, artist names, song titles, mapper names already in the database
- Selecting a suggestion fills the search bar and triggers the search
- Use Qt's `QCompleter` for the dropdown

**Files to change:**
- `osu_gallery/ui/main_window.py` — add `QCompleter` to the search edit
- `osu_gallery/search/engine.py` — add a method to collect all searchable suggestion terms
- `osu_gallery/db/database.py` — add a method to get distinct artist/title/mapper values

**Implementation plan:**

1. Add `get_search_suggestions()` to `SearchEngine`:
   ```python
   def get_search_suggestions(self, partial: str) -> list[str]:
       """Return all searchable terms matching the partial prefix.

       Combines tag names, artist names, song titles, and mapper names
       from the database. Results are deduplicated and limited to 15.
       """
       if not partial.strip():
           return []

       terms: set[str] = set()

       # Tag names (prefix match via FTS-compatible LIKE)
       for row in self._db.conn.execute(
           "SELECT name FROM tag WHERE name LIKE ? ORDER BY name LIMIT 15",
           (partial + "%",),
       ):
           terms.add(row["name"])

       # Artist names
       for row in self._db.conn.execute(
           "SELECT DISTINCT artist FROM pattern WHERE artist != '' AND artist LIKE ? ORDER BY artist",
           (partial + "%",),
       ):
           terms.add(row["artist"])

       # Title names
       for row in self._db.conn.execute(
           "SELECT DISTINCT title FROM pattern WHERE title != '' AND title LIKE ? ORDER BY title",
           (partial + "%",),
       ):
           terms.add(row["title"])

       # Mapper names
       for row in self._db.conn.execute(
           "SELECT DISTINCT mapper FROM pattern WHERE mapper != '' AND mapper LIKE ? ORDER BY mapper",
           (partial + "%",),
       ):
           terms.add(row["mapper"])

       return sorted(terms)[:15]
   ```

2. Update `main_window.py`:
   - Import `QCompleter` from `PySide6.QtWidgets`
   - In `_setup_ui()`, after creating `self._search_edit`:
     ```python
     from PySide6.QtWidgets import QCompleter
     self._completer = QCompleter([], self)
     self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
     self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
     self._search_edit.setCompleter(self._completer)
     ```
   - Connect `textChanged` to update completer model:
     ```python
     def _on_search_text_changed(self, text: str) -> None:
         self._search_timer.start()
         # Update autocomplete suggestions
         suggestions = self._search_engine.get_search_suggestions(text)
         self._completer.setModel(QStringListModel(suggestions, self))
         self._completer.complete()
     ```
   - Import `QStringListModel` from `PySide6.QtCore`

3. The existing `_on_search_triggered()` already handles executing the search — no change needed. Autocomplete just provides suggestions; the user still presses Enter or clicks to search.

**Tests to add:**
- `test_search_suggestions_returns_tags` — verify tag names appear in suggestions
- `test_search_suggestions_returns_artists` — verify artist names appear
- `test_search_suggestions_returns_titles` — verify title names appear
- `test_search_suggestions_returns_mappers` — verify mapper names appear
- `test_search_suggestions_prefix_match` — verify only prefix matches returned
- `test_search_suggestions_limited_to_15` — verify result cap
- `test_search_suggestions_deduplicated` — verify no duplicate terms
- `test_search_completer_populated` — verify QCompleter gets suggestions on text change (Qt test)

---

## Task 5: Display Combo Order on Previews

**Problem:** The osu! gameplay highlights objects in combo order (numbered circles). The current previews don't show this numbering, making it hard to reference the sequence.

**Goal:**
- Display a small number label on each hit object showing its combo order (1st, 2nd, 3rd, etc.)
- Combo order = the sequential index within a combo color group (resets on new combo)
- Visible on both thumbnails and full previews

**Files to change:**
- `osu_gallery/parser/osu_file.py` — assign combo order to each `HitObject` during parsing
- `osu_gallery/parser/models.py` — add `combo_order` field to `HitObject`
- `osu_gallery/preview/thumbnail_renderer.py` — draw combo order number on each object

**Implementation plan:**

1. Add `combo_order` to `HitObject` in `parser/models.py`:
   ```python
   @dataclass
   class HitObject:
       # ... existing fields ...
       combo_order: int = 0  # 1-based position within its combo color group
   ```

2. Update `_parse_hit_objects_section()` in `parser/osu_file.py`:
   - The existing second pass already tracks `combo_index` (0-based, increments on NEW_COMBO)
   - Assign `combo_order = combo_index + 1` (1-based) to each object during that pass
   ```python
   for obj in raw_objects:
       obj._raw_combo_index = combo_index
       obj.combo_order = combo_index + 1  # 1-based
       # ... existing flag processing ...
   ```

3. Update `thumbnail_renderer.py` — draw combo order number:
   - In `_render_objects()`, after drawing each circle/slider start, draw a small number:
     ```python
     def _draw_combo_number(
         painter: QPainter, x: float, y: float, order: int, color: QColor
     ) -> None:
         """Draw a small white number label on a hit object."""
         painter.setPen(QPen(QColor(0, 0, 0, 180), 1.5))
         painter.setBrush(QBrush(QColor(255, 255, 255)))
         painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
         text_rect = QRectF(x - 6, y - 8, 12, 10)
         painter.drawEllipse(text_rect)
         painter.setPen(QColor(0, 0, 0))
         painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, str(order))
     ```
   - Call this for circles and slider start positions (not spinners, not slider body)
   - Only draw if the combo order is visible at the rendered scale (skip if too small)

4. The slider rendering already draws the start circle — add the number there. Slider body paths don't get numbers (only the start circle represents the combo position).

**Tests to add:**
- `test_hit_object_has_combo_order` — verify field exists on parsed objects
- `test_combo_order_assigned_correctly` — verify order matches combo sequence
- `test_combo_order_resets_on_new_combo` — verify new combo starts at 1
- `test_combo_number_drawn_on_thumbnail` — verify number appears in rendered thumbnail
- `test_combo_number_drawn_on_preview` — verify number appears in rendered preview

---

## Execution Order

```
Step 1: Task 1 (Size overhaul) — no dependencies, foundational change to constants
Step 2: Task 2 (Tag rework) — schema change, affects import + preview + search
Step 3: Task 3 (Auto-detection simplification) — depends on Task 2 (metadata fields removed from tags)
Step 4: Task 4 (Search autocomplete) — depends on Task 2 (artist/title/mapper now searchable)
Step 5: Task 5 (Combo order numbering) — independent, parser + renderer changes
```

**Parallelization opportunities:**
- Task 1 and Task 5 can be done in parallel (different modules: constants/renderer vs parser/renderer)
- Task 4 can start after Task 2's schema is in place

---

## Database Schema Changes

The `pattern` table needs new columns:

```sql
ALTER TABLE pattern ADD COLUMN artist TEXT NOT NULL DEFAULT '';
ALTER TABLE pattern ADD COLUMN title TEXT NOT NULL DEFAULT '';
ALTER TABLE pattern ADD COLUMN mapper TEXT NOT NULL DEFAULT '';
```

No changes to `tag` or `pattern_tag` tables — the tag system is simplified, not restructured.

---

## New Files

| File | Purpose |
|---|---|
| (none) | All changes fit within existing modules |

---

## Risk Assessment

| Risk | Mitigation |
|---|---|
| Larger thumbnails may slow grid rendering | Thumbnails are rendered lazily (only when visible); Qt's scroll area handles this |
| Schema migration on existing databases | `ALTER TABLE ADD COLUMN DEFAULT ''` is safe; all existing rows get empty strings |
| Combo order numbering may clutter small thumbnails | Skip drawing numbers on objects where the rendered circle is too small (< 8px radius) |
| Autocomplete suggestions may be slow with many patterns | Query is simple LIKE on indexed columns; limit to 15 results |
| Removing auto-detection may surprise users | Existing mapping tags remain in DB; only new imports use manual input |

---

## Changes Summary

All tasks completed in a single implementation session on 2026-07-17.

### Files Modified (15)

| File | Tasks | Changes |
|------|-------|---------|
| `osu_gallery/_constants.py` | 1, 3 | Updated dimensions (THUMBNAIL 200x150→512x384, PREVIEW 384→768, PANE 380→500); added `MAPPING_TAG_OPTIONS` |
| `osu_gallery/db/models.py` | 2 | Added `artist`, `title`, `mapper` fields to `Pattern` dataclass |
| `osu_gallery/db/database.py` | 2 | Added columns to schema + migration; updated all CRUD methods |
| `osu_gallery/parser/models.py` | 5 | Added `combo_order: int = 0` to `HitObject` |
| `osu_gallery/parser/osu_file.py` | 5 | Assign `combo_order = combo_index + 1` during parsing |
| `osu_gallery/preview/thumbnail_renderer.py` | 1, 5 | Updated default render sizes; added `_draw_combo_number()` and calls in `_render_objects()` |
| `osu_gallery/ui/thumbnail_widget.py` | 1 | Updated render call and minimum size |
| `osu_gallery/ui/_preview_pane.py` | 1, 2 | Updated pane dimensions; added artist/title/mapper rows; removed metadata tag section |
| `osu_gallery/ui/main_window.py` | 1, 4 | Updated splitter width; added `QCompleter` + `get_search_suggestions` integration |
| `osu_gallery/ui/import_dialog.py` | 2, 3 | Extract artist/title/mapper during import; use `detect_object_tags`; no auto metadata tags |
| `osu_gallery/search/engine.py` | 2, 4 | Restructured FTS5 to single `content` field; added `get_search_suggestions()` |
| `osu_gallery/tags/mapping_tags.py` | 3 | Replaced with `detect_object_tags()` — only counts circles/sliders/spinners |
| `tests/test_search.py` | 2 | Fixed FTS5 column references (`raw_code`/`tags` → `content`) |
| `tests/test_tag_categories.py` | 3 | Updated for `detect_object_tags` rename and simplified detection |

### New Test Files (5)

| File | Task | Tests |
|------|------|-------|
| `tests/test_roadmap3_sizes.py` | 1 | 8 |
| `tests/test_roadmap3_metadata.py` | 2 | 11 |
| `tests/test_roadmap3_object_tags.py` | 3 | 7 |
| `tests/test_roadmap3_search_suggestions.py` | 4 | 10 |
| `tests/test_roadmap3_combo_order.py` | 5 | 5 |

### Schema Change

```sql
ALTER TABLE pattern ADD COLUMN artist TEXT NOT NULL DEFAULT '';
ALTER TABLE pattern ADD COLUMN title TEXT NOT NULL DEFAULT '';
ALTER TABLE pattern ADD COLUMN mapper TEXT NOT NULL DEFAULT '';
```

### FTS5 Schema Change

```sql
-- Before:
CREATE VIRTUAL TABLE pattern_fts USING fts5(
    pattern_id UNINDEXED, raw_code, tags
);
-- After:
CREATE VIRTUAL TABLE pattern_fts USING fts5(
    pattern_id UNINDEXED, content
);
```

## Definition of Done for This Roadmap

- [x] Task 1: Thumbnails at 512x384, preview at 1024x768
- [x] Task 2: artist/title/mapper as structured Pattern fields, metadata tags removed
- [x] Task 3: Auto-detection limited to object counts; mapping tags manual
- [x] Task 4: Search bar shows autocomplete suggestions as user types
- [x] Task 5: Combo order numbers displayed on preview objects
- [x] Existing test suite still passes (70 tests, all green)
- [x] New tests added for each task (41 new tests across 5 test files)
- [x] `ruff` linting passes with no errors
- [x] Database migration backward-compatible
- [x] Feature logged in `04_Implementation_Roadmap.md` §5
