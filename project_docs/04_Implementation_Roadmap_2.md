# Implementation Roadmap 2: Bug Fixes, Feature Additions & Code Quality

> This roadmap covers all changes requested after Phase 9 (MVP complete). It sequences the 8 tasks in dependency order so each step builds cleanly on the previous one.

**Created:** 2026-07-17
**Status:** In Progress (Tasks 1-8 complete)

---

## Task Summary

| # | Task | Priority | Depends On |
|---|---|---|---|
| 1 | Add pattern delete functionality to UI | P1 | — | ✅ Done |
| 2 | Copy Code copies only objects (no `[HitObjects]` header) | P1 | — | ✅ Done |
| 3 | Fix preview aspect ratio to 4:3 | P1 | — | ✅ Done |
| 4 | Fix object count (count circles + sliders, not raw hit objects) | P1 | — | ✅ Done |
| 5 | Support patterns without `[HitObjects]` header | P1 | Task 2 | ✅ Done |
| 6 | Distinguish .osu file tags from software mapping tags | P1 | — | ✅ Done |
| 7 | Enforce Coding Standards compliance + documentation | P1 | — | ✅ Done |
| 8 | Update tests to use the real .osu file as reference | P1 | Task 4, 5 | ✅ Done |

---

## Task 1: Add Pattern Delete Functionality

**Problem:** The current UI has no way to delete patterns from the gallery.

**Files to change:**
- `osu_gallery/ui/thumbnail_widget.py` — add delete action to context menu
- `osu_gallery/ui/main_window.py` — handle delete signal, confirm before deleting
- `osu_gallery/db/database.py` — `delete_pattern()` already exists, just needs UI wiring

**Implementation plan:**
1. Add a "Delete" action to the context menu in `_ThumbnailWidget._show_context_menu()`
2. Add a confirmation dialog (QMessageBox) before deleting — patterns are not easily recoverable
3. Connect delete action to a `_on_delete_pattern()` handler in `_ThumbnailWidget`
4. Emit a `pattern_deleted` signal from `_ThumbnailWidget`
5. In `MainWindow._refresh_grid()`, connect the signal to call `self._db.delete_pattern(pattern_id)` then `self.refresh()`
6. Show a toast confirmation after successful deletion

**Tests to add:**
- `test_delete_pattern_from_context_menu` — verify delete appears in context menu
- `test_delete_pattern_confirms_dialog` — verify confirmation dialog shows
- `test_delete_pattern_removes_from_db_and_grid` — verify pattern is removed after confirmation
- `test_delete_pattern_cancel` — verify cancel aborts deletion

---

## Task 2: Copy Code Copies Only Objects (No `[HitObjects]` Header)

**Problem:** Currently, "Copy Code" copies the full `raw_code` which includes headers like `[HitObjects]`, `[General]`, etc. For pasting into an .osu file, only the object lines should be copied.

**Files to change:**
- `osu_gallery/db/models.py` — add `objects_only` field to `Pattern` dataclass
- `osu_gallery/db/database.py` — store/retrieve `objects_only` alongside `raw_code`
- `osu_gallery/ui/_preview_pane.py` — use `objects_only` for copy
- `osu_gallery/ui/thumbnail_widget.py` — use `objects_only` for copy
- `osu_gallery/ui/import_dialog.py` — extract objects-only lines during import

**Implementation plan:**
1. Add `objects_only: str = ""` field to `Pattern` dataclass
2. Add `objects_only` column to the `pattern` table in `_init_schema()`
3. Update `create_pattern()` and `get_pattern()` to read/write `objects_only`
4. Update `update_pattern()` to include `objects_only`
5. In `ImportDialog._on_parse_and_save()`, extract just the hit object lines from the parsed content and pass as `objects_only`
6. In `_PreviewPane._on_copy_code()` and `_ThumbnailWidget._on_copy_code()`, use `objects_only` instead of `raw_code` when copying
7. Fallback: if `objects_only` is empty, strip `[HitObjects]` header from `raw_code` as a safety net

**How to extract objects-only lines:**
- After parsing, iterate `osu_file.hit_objects` and reconstruct the original line format: `x,y,time,type,hitSound,objectParams,hitSample`
- Or simpler: find the `[HitObjects]` section in the raw content and extract everything between `[HitObjects]` and the next section header

---

## Task 3: Fix Preview Aspect Ratio to 4:3

**Problem:** The preview pane uses a square box (384x384) but osu! beatmaps are 512x384 (4:3 ratio). The preview is being stretched or cropped.

**Files to change:**
- `osu_gallery/_constants.py` — update `PREVIEW_HEIGHT` to reflect 4:3 ratio
- `osu_gallery/ui/_preview_pane.py` — update `_PREVIEW_HEIGHT` constant and rendering dimensions
- `osu_gallery/preview/thumbnail_renderer.py` — verify rendering uses correct osu! resolution

**Implementation plan:**
1. osu! native resolution is 512x384 (4:3). The current code already uses `width=512, height=384` in `render_pattern_preview()` — this is correct.
2. The issue is in the UI: `_PreviewPane._PREVIEW_HEIGHT = 384` and the preview label has `setMinimumHeight(384)` but the label width is unconstrained, causing it to fill the pane width (380px) which makes it look stretched.
3. Fix: Set the preview label's maximum width to maintain 4:3 ratio. When height is 384, max width should be 512. But since the pane is 380px wide, scale proportionally: max_width = 380 * (512/384) = 506.67 → use 506.
4. Actually the simpler fix: ensure the preview pixmap is rendered at 512x384 and displayed with `KeepAspectRatio` so it scales proportionally within the available space. The current code does this, but the QLabel minimum height forces a square aspect. Remove the fixed minimum height and let the pixmap dictate dimensions.
5. Update `_constants.py`: set `PREVIEW_HEIGHT = 384` (already correct), ensure `PREVIEW_PANE_WIDTH` accommodates 512px at scale.

**Tests to add:**
- `test_preview_pane_aspect_ratio` — verify rendered pixmap dimensions are 4:3 (512x384 or proportional)
- `test_thumbnail_aspect_ratio` — verify thumbnail rendered at proportional 4:3

---

## Task 4: Fix Object Count (Circles + Sliders, Not Raw Hit Objects)

**Problem:** The "Objects" field shows 0 in both thumbnail and preview because `object_count` is being set to `len(osu_file.hit_objects)` which counts ALL hit object types (including spinners, mania hold), but the user expects it to count only circles and sliders. Additionally, the count may be 0 because the parser is encountering issues with the raw_code format.

**Files to change:**
- `osu_gallery/parser/models.py` — add `circle_count` and `slider_count` properties to `OsuFile`
- `osu_gallery/db/models.py` — add `circle_count` and `slider_count` fields to `Pattern`
- `osu_gallery/db/database.py` — store/retrieve the new counts
- `osu_gallery/ui/thumbnail_widget.py` — display circle + slider counts
- `osu_gallery/ui/_preview_pane.py` — display circle + slider counts
- `osu_gallery/ui/import_dialog.py` — compute and store the correct counts

**Implementation plan:**
1. Add a method to `OsuFile` that counts circles and sliders:
   ```python
   @property
   def circle_count(self) -> int:
       return sum(1 for obj in self.hit_objects if obj.is_circle)

   @property
   def slider_count(self) -> int:
       return sum(1 for obj in self.hit_objects if obj.is_slider)
   ```
2. Add `circle_count` and `slider_count` to the `Pattern` dataclass
3. Update database schema to include these columns
4. In `ImportDialog._on_parse_and_save()`, pass `circle_count` and `slider_count` to `create_pattern()`
5. In `_ThumbnailWidget`, display `f"{circles} circles, {sliders} sliders"` instead of just object count
6. In `_PreviewPane`, display the same format
7. Keep `object_count` as total for backward compatibility, but prioritize circle/slider counts in the UI

**Tests to add:**
- `test_count_circles_and_sliders` — verify circle/slider counts are correct for mixed patterns
- `test_count_only_circles` — verify count when only circles present
- `test_count_only_sliders` — verify count when only sliders present
- `test_count_with_spinners_excluded` — verify spinners are not counted

---

## Task 5: Support Patterns Without `[HitObjects]` Header

**Answer before changing anything:**

The cleanest approach without major rework is to **store the object lines separately from the full raw code**. Here's the proposed design:

**Current state:** `raw_code` stores the entire pasted content (headers + objects). When copying, we currently copy `raw_code` which includes `[HitObjects]` and other section headers.

**Proposed change:**
- Keep `raw_code` as-is (full content for parsing/rendering)
- Add `objects_only: str` field to `Pattern` — stores just the hit object lines (no `[HitObjects]` header)
- During import, if the pasted content has a `[HitObjects]` section, extract lines from that section into `objects_only`
- If the pasted content has NO `[HitObjects]` section (just raw object lines), store those lines in `objects_only` and set `raw_code` to a minimal valid wrapper
- For copy-paste, always use `objects_only`

**Why this works without major rework:**
- The parser already handles content without `[HitObjects]` gracefully (returns empty list)
- We just need to preserve the raw object lines separately
- The thumbnail renderer and preview pane already parse `raw_code` — no change needed there
- Copy operations switch from `raw_code` to `objects_only` (Task 2 covers this)

**Files to change:**
- `osu_gallery/db/models.py` — add `objects_only` field
- `osu_gallery/db/database.py` — schema + CRUD updates
- `osu_gallery/ui/import_dialog.py` — extract objects during import
- `osu_gallery/ui/_preview_pane.py` — use `objects_only` for copy
- `osu_gallery/ui/thumbnail_widget.py` — use `objects_only` for copy

**Tests to add:**
- `test_import_pattern_without_hitobjects_header` — verify pattern with raw objects (no header) imports correctly
- `test_import_pattern_with_hitobjects_header` — verify normal import still works
- `test_copy_code_excludes_header` — verify copy produces only object lines
- `test_objects_only_stored_separately` — verify both fields are stored correctly

---

## Task 6: Distinguish .osu File Tags from Software Mapping Tags

**Problem:** The current system treats the `Tags:` field from .osu files (music metadata like "magical girl", "jpop") as the same as software mapping tags (like "Circle", "Slider", "Kickslider"). These are fundamentally different categories.

**Files to change:**
- `osu_gallery/db/models.py` — `Tag` already has `category` field, use it to distinguish
- `osu_gallery/ui/import_dialog.py` — separate auto-extraction into .osu metadata tags vs. mapping tags
- `osu_gallery/search/engine.py` — search should be able to filter by tag category
- `osu_gallery/ui/_preview_pane.py` — display tags grouped by category
- `osu_gallery/_constants.py` — define the software mapping tag categories

**Implementation plan:**
1. Define two tag categories in `_constants.py`:
   - `"metadata"` — .osu file tags (music-related: artist, genre, source, etc.)
   - `"mapping"` — software mapping tags (Circle, Slider, Kickslider, etc.)
2. In `ImportDialog._extract_tag_names()`, split into two lists:
   - Metadata tags: from `osu_file.metadata.tags` (space-separated string from .osu file)
   - Mapping tags: auto-detect from hit objects (count circles, sliders, detect patterns)
3. Create mapping tags automatically based on parsed data:
   - Count circles → tag "X circles" (e.g., "2 circles", "3 circles")
   - Count sliders → tag "X sliders" (e.g., "1 slider", "3 sliders")
   - Detect slider types → "Kickslider", "Slider art", etc.
   - Detect pattern angles → "15º angled pattern", "0° angled pattern"
   - Detect screen coverage → "full screen pattern", "compact pattern"
4. Store metadata tags with `category="metadata"` and mapping tags with `category="mapping"`
5. In the preview pane, display tags grouped by category with section headers
6. In search, allow filtering by tag category

**Mapping tag auto-detection rules (from the user's tag list):**
| Condition | Tag |
|---|---|
| Pattern has circles | "Circles" (count: X circles) |
| Pattern has sliders | "Sliders" (count: X sliders) |
| Slider with vertical movement | "vertical slider" |
| Slider with horizontal movement | "horizontal slider" |
| Slider art style | "Slider art" |
| Fast repeated sliders | "Kickslider", "Kicksliders" |
| 15-degree angle sliders | "15º angled pattern" |
| 0-degree angle sliders | "0° angled pattern" |
| Full screen coverage | "full screen pattern" |
| Compact pattern | "compact pattern" |
| 3/4 slider ratio | "3/4 slider", "3/4sliders" |
| 1/2 slider ratio | "1/2 slider", "1/2 sliders" |
| 1/1 slider ratio | "1/1 slider", "1/1 sliders" |
| Circle shapes (triangle, square, pentagon, hexagon) | "circle triangle", "circle square", etc. |
| Slider shapes | "slider triangle", "slider square", etc. |

**Tests to add:**
- `test_metadata_tags_separate_from_mapping_tags` — verify two categories stored
- `test_auto_detect_circle_count_tag` — verify circle count tag created
- `test_auto_detect_slider_count_tag` — verify slider count tag created
- `test_search_filters_by_tag_category` — verify category-based filtering

---

## Task 7: Coding Standards Compliance & Documentation

**Problem:** The code needs to be reviewed against `12_Coding_Standards.md` and documented for human readability.

**Files to audit:**
- All `osu_gallery/**/*.py` files — check for missing docstrings, empty exception handlers, raw print statements, naming conventions
- All `tests/**/*.py` files — check for test quality

**Audit checklist per file:**
1. Every public function/method has a docstring (inputs, outputs, exceptions)
2. No empty `except:` or `except Exception:` blocks
3. No `print()` statements (use logging)
4. snake_case for functions/variables, PascalCase for classes
5. No duplicated constants (use `_constants.py`)
6. Single responsibility per function
7. Inline comments explain *why*, not *what*
8. No dead code or commented-out blocks

**Known issues to fix:**
- `_extract_hit_sample()` in `osu_file.py` has complex logic that could be split
- `_do_layout()` in `_flow_layout.py` could use clearer variable names
- Some functions lack docstrings for return values
- `_on_copy_code` in `_preview_pane.py` uses lambda — could be a proper method
- `contextMenuEvent` in `thumbnail_widget.py` is empty (pass) — should be removed since custom context menu is handled via signal

**Documentation to add:**
- Module-level docstrings for any module missing them
- `__init__.py` files should export public API
- Add inline comments for non-obvious osu! format parsing logic (why certain regex patterns are used)

**Tests to add:**
- `test_all_public_functions_have_docstrings` — verify documentation compliance

---

## Task 8: Update Tests to Use Real .osu File

**Problem:** Current tests use synthetic/minimal .osu content. Tests should use the real .osu file provided ("Dream Walk" by Hashiba Gin) as reference to ensure the parser handles real-world beatmap data correctly.

**Files to change:**
- `tests/conftest.py` — add a fixture that loads the real .osu file
- `tests/test_parser.py` — add tests using the real file's structure
- `tests/test_database.py` — verify patterns stored from real file retain all data
- `tests/test_preview_integration.py` — verify rendering works with real data
- `tests/test_search.py` — verify search works with real tag data
- `tests/test_ui.py` — verify UI components work with real parsed data

**Implementation plan:**
1. Add a `real_osu_content` fixture in `conftest.py` that loads the real .osu file from a test data file
2. Create a `tests/test_data/` directory with the real .osu file (or embed as a string constant)
3. Add parser tests that verify:
   - All 14 timing points are parsed correctly
   - BPM is calculated correctly from timing points
   - Combo colors from [Colours] section are parsed
   - All metadata fields are extracted
   - Hit objects with various types (circles, sliders, spinners) are parsed
4. Add integration tests that verify:
   - Full import flow with real .osu content
   - Thumbnail rendering with real coordinate data
   - Search with real tag data
5. Add tests for edge cases found in real .osu files:
   - Sliders with complex bezier paths
   - Multiple timing points
   - Combo color skips
   - Edge sounds on sliders

**Note:** The real .osu file is very large (~240+ hit objects). For tests, we can use the full file or a truncated version. The fixture should load from a file path, not embed the entire content as a string constant (keeps test files readable).

---

## Execution Order

```
Step 1: Task 4 (Object count fix) — no dependencies, foundational ✅ Done
Step 2: Task 2 (Copy objects only) — needs database schema change from Task 4 ✅ Done
Step 3: Task 5 (Patterns without header) — depends on Task 2's objects_only field ✅ Done
Step 4: Task 3 (Preview aspect ratio) — UI-only change, no dependencies ✅ Done
Step 5: Task 1 (Delete patterns) — UI-only change, no dependencies ✅ Done
Step 6: Task 6 (Tag distinction) — needs mapping tag auto-detection logic ✅ Done
Step 7: Task 7 (Coding standards) — review and fix all files ✅ Done
Step 8: Task 8 (Real .osu tests) — depends on Tasks 2, 4, 5 being implemented ✅ Done
```

**Parallelization opportunities:**
- Tasks 3 and 5 can be done in parallel (different files)
- Task 1 can be done in parallel with any other task
- Task 7 should be done last (after all features are implemented)

---

## Database Schema Changes

The `pattern` table needs new columns:

```sql
ALTER TABLE pattern ADD COLUMN objects_only TEXT DEFAULT '';
ALTER TABLE pattern ADD COLUMN circle_count INTEGER DEFAULT 0;
ALTER TABLE pattern ADD COLUMN slider_count INTEGER DEFAULT 0;
```

The `tag` table already has `category` — no change needed.

---

## New Files

| File | Purpose |
|---|---|
| `tests/test_data/dream_walk.osu` | Real .osu file for test reference |
| `osu_gallery/tags/mapping_tags.py` | Mapping tag auto-detection logic |

---

## Risk Assessment

| Risk | Mitigation |
|---|---|
| Real .osu file is very large for tests | Use truncated version (first 50 objects) for fast tests, full file for integration tests |
| Object-only extraction may lose formatting | Store raw lines as-is, don't re-serialize |
| Mapping tag auto-detection may be imperfect | Start with simple rules (circle count, slider count), expand later |
| Database migration may fail on existing data | Use `ALTER TABLE ADD COLUMN ... DEFAULT ''` which is safe for existing rows |

---

## Definition of Done for This Roadmap

- [x] Task 4: Fix object count (count circles + sliders, not raw hit objects)
- [x] Task 1: Add pattern delete functionality
- [x] Task 2: Copy Code copies only objects (no `[HitObjects]` header)
- [x] Task 3: Fix preview aspect ratio to 4:3
- [x] Task 5: Support patterns without `[HitObjects]` header
- [x] Task 6: Distinguish .osu file tags from software mapping tags
- [x] Task 7: Enforce Coding Standards compliance + documentation
- [x] Task 8: Update tests to use the real .osu file as reference
- [x] Existing test suite (278+ tests) still passes
- [x] New tests added for each task (regression tests)
- [x] Tests use real .osu file as reference data
- [x] `ruff` linting passes with no errors
- [x] All public functions have docstrings
- [x] No empty exception handlers
- [x] No raw `print()` statements
- [x] Database migration is backward-compatible
- [ ] Feature logged in `04_Implementation_Roadmap.md` §5
