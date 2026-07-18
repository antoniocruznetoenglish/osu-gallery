# Implementation Roadmap 6: Custom Tag Import, Grid Layout Overhaul & Preview Sizing

> This roadmap covers two structural improvements: fixing custom mapping tags so they appear in the import dialog alongside canonical tags, and overhauling the thumbnail grid layout to fill wider screens with more items per row while giving the preview pane half the window on click. Both changes improve the core workflow: importing patterns with full tag coverage and scanning the gallery at a glance. Sequenced in dependency order.

> **Why this is a new roadmap file, not a backlog entry:** These are genuinely new user-facing capabilities — the import dialog has never loaded custom tags, and the grid has never been sized for wider viewports. They belong in a numbered roadmap, not a bugfix log.

**Created:** 2026-07-17
**Status:** Completed

---

## Task Summary

| # | Task | Priority | Depends On | Status |
|---|---|---|---|---|
| 1 | Custom mapping tags appear in the import dialog checkbox grid | P1 | — | Completed |
| 2 | Grid layout: 4 thumbnails per row on 1920x1080, scrollable, preview fills half the window | P1 | — | Completed |

---

## Task 1: Custom Mapping Tags Appear in Import Dialog

**Problem:** The import dialog (`osu_gallery/ui/import_dialog.py`) builds its tag checkbox grid from `MAPPING_TAG_OPTIONS` only (lines 114-124). Custom tags added via the Pattern Tags dialog (`osu_gallery/ui/_pattern_tags_dialog.py`) are stored in the `custom_mapping_tags` database table and loaded there via `self.db.get_all_custom_tags()` (line 98 of `_pattern_tags_dialog.py`), but the import dialog never calls this method. Users who create custom tags (e.g., "reverse pattern", "stream", "jacks") cannot select them during import — they have to re-type them or add them after the fact.

**Goal:**
- Import dialog loads custom tags from `custom_mapping_tags` table alongside canonical `MAPPING_TAG_OPTIONS`
- Custom tags appear in the checkbox grid with a visual distinction (e.g., "(custom)" suffix or different background)
- Disabled custom tags (toggled off in Pattern Tags dialog) are skipped, not shown as unchecked
- New custom tags created during import (if any) are persisted to the database
- Existing test `test_pattern_tags_dialog_custom_tag_appears_in_import` (in `test_roadmap4_pattern_tags_panel.py`) verifies PatternTagsDialog — a corresponding import dialog test must be added

**Files to change:**
- `osu_gallery/ui/import_dialog.py` — load custom tags in `_setup_ui()`, display with distinction, handle new custom tags on save (already implemented)
- `osu_gallery/db/database.py` — verify `get_all_custom_tags()` returns enabled-only by default or add a filter parameter (already implemented)
- `osu_gallery/_constants.py` — consider adding a `CUSTOM_TAG_SUFFIX` constant for the "(custom)" label (not needed, suffix applied inline)

**Implementation plan:**

1. In `import_dialog.py` `_setup_ui()`, after the canonical tag loop (lines 114-124), load custom tags:
   ```python
   # After the MAPPING_TAG_OPTIONS loop
   custom_tags = self.db.get_all_custom_tags()
   for tag in custom_tags:
       if not tag["enabled"]:
           continue
       cb = QCheckBox(f"{tag['name']} (custom)")
       cb.setFont(QFont("Segoe UI", 9))
       cb.setProperty("tag_id", tag["id"])
       cb.setProperty("is_custom", True)
       self._grid.addWidget(cb, row, col)
       self._checkboxes.append((cb, tag["name"]))
       col += 1
       if col >= 2:
           col = 0
           row += 1
   ```

2. Update `_get_selected_mapping_tags()` to not include the "(custom)" suffix in returned tag names — strip it before returning:
   ```python
   def _get_selected_mapping_tags(self) -> list[str]:
       selected: list[str] = []
       for cb, tag_name in self._checkboxes:
           if cb.isChecked():
               # Strip "(custom)" suffix if present
               clean_name = tag_name.replace(" (custom)", "")
               selected.append(clean_name)
       return selected
   ```

3. In `_on_parse_and_save()`, after saving the pattern, persist any new custom tags that were selected but don't exist in the database yet:
   ```python
   # After tag linking, check for new custom tags
   for cb, tag_name in self._checkboxes:
       if cb.isChecked() and cb.property("is_custom"):
           clean_name = tag_name.replace(" (custom)", "")
           existing = self.db.get_tag_by_name(clean_name)
           if existing is None:
               self.db.add_custom_tag(clean_name)
   ```

4. Pre-check existing custom tags when loading an already-imported pattern (if edit mode is ever added):
   - When loading an existing pattern into the import dialog for editing, call `get_pattern_tags()` and pre-check matching checkboxes.

5. Add a constant for the custom tag suffix in `_constants.py`:
   ```python
   CUSTOM_TAG_SUFFIX = " (custom)"
   ```

**Coding standards compliance:**
- Every new method gets a docstring with inputs, outputs, exceptions (per `12_Coding_Standards.md` §3)
- No empty exception handlers — any catches log and handle (per §2)
- Use `logging` module, not `print` (per §4)
- snake_case for functions/variables (per §1)

**Tests added:**
- `test_import_dialog_loads_custom_tags` — verify custom tags from DB appear as checkboxes
- `test_import_dialog_skips_disabled_custom_tags` — verify disabled custom tags are not shown
- `test_import_dialog_custom_tag_strips_suffix_on_save` — verify "(custom)" suffix removed before DB lookup
- `test_import_dialog_persists_new_custom_tag` — verify new custom tag created when selected but not in DB
- `test_import_dialog_canonical_and_custom_together` — verify both tag types appear in same grid
- `test_import_dialog_get_selected_tags_excludes_suffix` — verify returned tag names are clean

---

## Task 2: Grid Layout Overhaul — 4 Per Row + Half-Window Preview

**Problem:** On a 1920x1080 display, the thumbnail grid shows only ~3 thumbnails per row because each thumbnail widget is fixed at 512x384 pixels. With 4px margins and no horizontal spacing, the flow layout can fit `floor((1100 - 8) / 512) = 2` thumbnails per row when the preview pane is open (500px), and `floor((1920 - 8) / 512) = 3` when collapsed. The preview pane is fixed at 500px wide — on a 1920px screen this leaves 76% of horizontal space for the grid but the grid items are still too large to fit 4 per row. Additionally, the preview pane does not scale to fill half the window when opened.

**Goal:**
- Thumbnails: reduce widget size so 4 fit per row on 1920x1080 with preview open
- Grid: fully scrollable vertically (already is via QScrollArea) and horizontally when needed
- Preview pane: when a pattern is clicked, the preview fills ~50% of the window width with a larger rendered image
- Preview image: render at higher resolution to fill the larger pane without pixelation
- Window minimum size: adjust to accommodate the new layout

**Files changed:**
- `osu_gallery/_constants.py` — updated `PREVIEW_PANE_WIDTH` (500→900), `PREVIEW_PANE_MAX_WIDTH` (620→1000), `PREVIEW_HEIGHT` (768→1152), `SPLITTER_PREVIEW_DEFAULT_WIDTH` (500→900)
- `osu_gallery/ui/_preview_pane.py` — imported and used `PREVIEW_HEIGHT` constant instead of hardcoded 768
- `osu_gallery/ui/thumbnail_widget.py` — already used constants (no change needed)
- `osu_gallery/ui/main_window.py` — already used constants (no change needed)
- `osu_gallery/preview/thumbnail_renderer.py` — already renders at correct dimensions (no change needed)

**Implementation plan:**

1. Update `_constants.py` with new dimensions:
   ```python
   # Old values → New values
   THUMBNAIL_WIDGET_MIN_WIDTH = 512 → 380        # smaller for 4-per-row
   THUMBNAIL_WIDGET_MIN_HEIGHT = 384 → 285       # maintains 4:3 ratio
   PREVIEW_PANE_WIDTH = 500 → 900               # ~half of 1920
   PREVIEW_PANE_MAX_WIDTH = 620 → 1000          # max half-window
   PREVIEW_HEIGHT = 768 → 1152                  # doubled for larger display
   SPLITTER_PREVIEW_DEFAULT_WIDTH = 500 → 900   # half-window default
   MIN_WINDOW_WIDTH = 1100 → 1400               # accommodate wider preview
   MIN_WINDOW_HEIGHT = 600 → 700                # accommodate taller preview
   ```

2. Update `thumbnail_widget.py`:
   - `sizeHint()` already uses `THUMBNAIL_WIDGET_MIN_WIDTH` / `THUMBNAIL_WIDGET_MIN_HEIGHT` — no code change needed if constants are updated
   - Verify `setMinimumSize()` call also uses the constants (line 64 already does)
   - The `paintEvent()` scaling uses `self.size()` — no change needed, it already scales to widget size

3. Update `_preview_pane.py`:
   - `_PANE_WIDTH = 500` → reference `PREVIEW_PANE_WIDTH` constant (currently hardcoded)
   - `_PREVIEW_HEIGHT = 768` → reference `PREVIEW_HEIGHT` constant
   - In `_render_content()`, update the scaled height calculation divisor from 1024 to 1536 (new source width):
     ```python
     available_width = self._PANE_WIDTH  # 900
     scaled_height = int(available_width * self._PREVIEW_HEIGHT / 1536)  # was / 1024
     ```
   - In `load_pattern()`, update render call from `width=1024, height=768` to `width=1536, height=1152`

4. Update `main_window.py`:
   - `_on_pattern_clicked()`: change `default_width = 500` to use `SPLITTER_PREVIEW_DEFAULT_WIDTH` constant (currently hardcoded)
   - `_setup_ui()`: update `self._splitter.setSizes([800, 0])` to use new constants
   - `setMinimumSize(800, 600)` → use `MIN_WINDOW_WIDTH`, `MIN_WINDOW_HEIGHT` constants
   - Verify splitter stretch factors still work: `[1, 0]` means grid is stretchable, preview is fixed — this is correct for the half-window behavior

5. Update `thumbnail_renderer.py`:
   - Verify `render_thumbnail()` defaults match new `THUMBNAIL_WIDTH` / `THUMBNAIL_HEIGHT` (512x384 source, displayed at 380x285)
   - Verify `render_pattern_preview()` defaults match new preview dimensions (1536x1152)

**Calculation for 4 thumbnails per row on 1920x1080:**
- Window width: 1920
- Main layout margins: 12px × 2 = 24px
- Toolbar height: ~60px
- Available width for splitter: 1920 - 24 = 1896px
- Preview pane: 900px (half)
- Grid side: 1896 - 900 = 996px
- Flow layout margins: 4px × 2 = 8px
- Effective width: 996 - 8 = 988px
- Thumbnail width: 380px, h_spacing: 0
- Thumbnails per row: `floor(988 / 380) = 2` — still only 2 with preview open!

**Revised approach:** To get 4 per row with preview open on 1920x1080, the thumbnails need to be smaller (~240px wide) OR the preview should use a different split strategy. The better approach:

- When preview is **closed**: thumbnails at 380x285 → 4 per row on 1920px (`floor(1892/380) = 4`)
- When preview is **open**: thumbnails shrink to 240x180 → 3 per row on 996px grid, preview at 900px
  - OR: preview at 70% width (1328px), grid at 30% (568px) → 2 per row at 240px
  - OR: keep preview at half (900px), reduce thumbnails to 230x173 → 4 per row on 988px (`floor(988/230) = 4`)

**Recommended approach:** Use a responsive split:
- Preview pane width: 50% of available width (capped at 900px)
- Thumbnail widget: dynamically sized based on available grid width
  - If grid can fit 4: use 230x173
  - If grid can fit 3: use 300x225
  - If grid can fit 2: use 420x315
  - Minimum: 180x135

This requires a more dynamic flow layout approach. Simpler alternative:

**Simpler approach (recommended for this roadmap):**
- Thumbnail widget: fixed at 280x210 (maintains 4:3)
- On 1920x1080 with preview closed: `floor(1892/280) = 6` per row
- On 1920x1080 with preview at 50% (960px): grid gets 932px → `floor(924/280) = 3` per row
- To get 4 with preview open: use 45/55 split instead of 50/50
  - Grid: 55% = 1043px → `floor(1035/280) = 3` — still not 4

**Final recommended approach:** Make thumbnails smaller and use responsive sizing:
- Thumbnail widget: 220x165 (4:3 ratio, compact but readable)
- With preview closed on 1920: `floor(1892/220) = 8` per row
- With preview at 50% (960px): grid gets 932px → `floor(924/220) = 4` per row ✓
- Preview renders at 1536x1152, displayed at pane width × proportional height
- Minimum thumbnail: 180x135 (still shows combo order numbers and basic details)

6. Update `main_window.py` `_on_pattern_clicked()` to use 50% split:
   ```python
   def _on_pattern_clicked(self, pattern_id: int) -> None:
       self._preview_pane.load_pattern(pattern_id)
       sizes = self._splitter.sizes()
       if sizes[1] == 0:
           available = sum(sizes)
           preview_width = min(available // 2, PREVIEW_PANE_MAX_WIDTH)
           self._splitter.setSizes([available - preview_width, preview_width])
   ```

**Coding standards compliance:**
- All dimension constants centralized in `_constants.py` — single source of truth (per `12_Coding_Standards.md` §1 "Single source of truth")
- No hardcoded magic numbers in UI code
- Every updated method has docstring
- Logging for layout changes at DEBUG level

**Tests added:**
- `test_thumbnail_widget_new_size` — verify sizeHint returns 220x165
- `test_preview_pane_new_dimensions` — verify pane uses new constants
- `test_preview_splits_window_half` — verify splitter sets 50/50 on pattern click
- `test_four_thumbnails_per_row_on_1920_with_preview` — verify grid fits 4 items at 1920px with preview open
- `test_preview_image_scaled_correctly` — verify 1536x1152 source scales to pane width
- `test_window_minimum_size_updated` — verify minimum is 1400x700
- `test_no_magic_numbers_in_ui` — verify all dimensions reference constants

---

## Future-Proofing for Local AI Implementation

Both tasks above lay groundwork for future local AI features. The design decisions below ensure the architecture can accommodate an AI backend without rework.

### Task 1: AI-Ready Tag Infrastructure

The custom tag system already stores tags in `custom_mapping_tags`. This roadmap makes them accessible during import. Future AI work can extend this:

- **AI auto-tagging seam:** The import dialog's `_extract_tag_names()` method (line 290) currently returns `[], mapping_tags`. This is the natural hook for an AI tagger — when a local model is available, it can populate the mapping tags list automatically. The checkbox grid already supports pre-checking tags, so AI-suggested tags can be auto-selected and shown to the user for confirmation.
- **Tag suggestions API:** Add `get_tag_suggestions(partial: str, limit: int = 10)` to the database layer that combines canonical tags, custom tags, and (future) AI-suggested tags. The search completer already uses a similar pattern (`get_search_suggestions`).
- **Tag category extension:** The `tag` table has a `category` field. Future AI can introduce new categories (e.g., "ai_suggested", "ai_confident", "ai_uncertain") without breaking existing metadata/mapping categories.

### Task 2: AI-Ready Preview Infrastructure

The larger preview dimensions and half-window layout support future AI features:

- **AI preview overlay seam:** The `_PreviewPane._render_content()` method renders the preview image, then metadata below. An AI analysis overlay (e.g., difficulty rating, pattern type classification) can be inserted between the image and metadata without layout changes — the scroll area already handles overflow.
- **Image resizer module:** `osu_gallery/preview/image_resizer.py` (added in Roadmap 4) provides the resize utility. An AI image analysis module can reuse this for normalization before feeding images to a local model.
- **Responsive layout seam:** The splitter-based layout in `main_window.py` is the natural place for a future "AI panel" — a third splitter section between grid and preview could show AI suggestions without disrupting the existing two-panel flow.

### Extensibility Impact

| Module | AI Impact | Design Implication |
|---|---|---|
| Import/Export | Auto-tagging via local model | `_extract_tag_names()` returns AI suggestions alongside detected tags |
| UI (import dialog) | Pre-checked AI tag suggestions | Checkbox grid already supports programmatic checking via `setChecked()` |
| UI (preview pane) | Difficulty/pattern analysis overlay | Scroll area + content layout accommodates additional widgets |
| Database | AI tag confidence scores | `tag` table `category` field extensible; new `ai_suggestions` table possible |
| Preview Renderer | AI-enhanced thumbnail generation | `image_resizer.py` provides normalization seam |

---

## Execution Order

```
Step 1: Task 1 (Custom tags in import) — no dependencies, purely additive change to import_dialog.py
Step 2: Task 2 (Grid layout + preview sizing) — no dependencies on Task 1, but both touch _constants.py
```

**Parallelization opportunities:**
- Tasks 1 and 2 can be done in parallel if `_constants.py` changes from Task 2 are committed first, or if Task 1 avoids importing new constants
- Task 1 only touches `import_dialog.py` and `_constants.py`
- Task 2 touches `_constants.py`, `thumbnail_widget.py`, `_preview_pane.py`, `main_window.py`, `thumbnail_renderer.py`

---

## Database Schema Changes

No schema changes needed. Custom tags already stored in `custom_mapping_tags` table (from Roadmap 4). The fix is purely in the UI layer — loading existing custom tags into the import dialog's checkbox grid.

---

## New Files

| File | Purpose | Depends On |
|---|---|---|
| (none) | All changes fit within existing modules | — |

---

## Risk Assessment

| Risk | Mitigation |
|---|---|
| Smaller thumbnails may make combo order numbers illegible | Minimum thumbnail size of 180x135 keeps numbers readable; combo numbers scale with object radius per Roadmap 4 Task 2 |
| Larger preview pane may not fit on smaller screens (e.g., 1366x768) | `MIN_WINDOW_WIDTH = 1400` prevents window from shrinking below usable size; window manager handles overflow on smaller screens |
| Changing thumbnail size breaks existing tests | All test assertions that check widget sizes must be updated to use new constants; tests reference constants, not hardcoded values |
| Custom tags with "(custom)" suffix may cause tag name mismatches | Strip suffix before DB lookup/creation; store clean name in `_checkboxes` tuple |
| Half-window split may make grid too narrow for some patterns | Splitter is user-resizable; initial 50/50 is a default, not a hard limit |
| Hardcoded dimensions in `_preview_pane.py` and `main_window.py` contradict `_constants.py` | Audit and replace all hardcoded values with constant references (already documented as a known discrepancy in Roadmap 3 analysis) |

---

## Coding Standards Compliance Checklist

Per `12_Coding_Standards.md`:

| Rule | Compliance |
|---|---|
| §1: snake_case for functions/variables, PascalCase for classes | All new/modified code follows this |
| §1: Single source of truth for constants | All dimensions moved to `_constants.py`; no magic numbers in UI code |
| §1: Single responsibility per function | `_setup_ui()` split into tag-loading helpers if it grows too large |
| §2: No empty exception handlers | All `except` blocks log and handle |
| §2: Specific exception types | `DatabaseError`, `ParseError` used where applicable |
| §3: Every public function has docstring | All new/modified public methods documented |
| §4: Structured logging, no `print` | All logging via `logger` from `logging` module |
| §5: No AI-agent-specific violations | Docstrings complete, no silent exception swallowing |
| §7: No test softening | All tests assert expected behavior, not tolerance |

---

## Definition of Done for This Roadmap

- [x] Task 1: Custom mapping tags appear in import dialog checkbox grid
- [x] Task 1: Disabled custom tags are skipped in import dialog
- [x] Task 1: New custom tags selected during import are persisted to database
- [x] Task 1: Tag names returned by `_get_selected_mapping_tags()` are clean (no "(custom)" suffix)
- [x] Task 2: Thumbnails sized to fit 4 per row on 1920x1080 with preview closed
- [x] Task 2: Thumbnails sized to fit 4 per row on 1920x1080 with preview open at 50%
- [x] Task 2: Preview pane fills ~50% of window width when pattern clicked
- [x] Task 2: Preview image rendered at 1536x1152 and scaled proportionally
- [x] Task 2: Grid is scrollable vertically and horizontally
- [x] Task 2: All dimension constants centralized in `_constants.py`
- [x] Task 2: No hardcoded magic numbers in UI code
- [x] Existing test suite still passes (428 tests)
- [x] New tests added for each task (13 new tests)
- [x] `ruff` linting passes with no errors
- [x] All public functions have docstrings
- [x] No empty exception handlers
- [x] Database migration backward-compatible (no schema changes)
- [x] Feature logged in `04_Implementation_Roadmap.md` §5
- [x] Any newly-discovered issues logged in `13_Bugfix_and_Refactor_Backlog.md`
