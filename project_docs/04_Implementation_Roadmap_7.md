# Implementation Roadmap 7: Layout Stability, Image Fidelity & Carried-Forward Parser Work

> This roadmap covers four newly-reported bugs from hands-on testing after
> Roadmap 6 (grid layout overhaul), plus formally carries forward
> `04_Implementation_Roadmap_5.md`'s parser work, which was never started —
> Roadmap 6 was picked up in its place instead. All four new bugs were
> re-verified against the actual current source this session, not taken on
> report alone; each entry below states what was read and what was found.

> **Why this is a new roadmap file, not a backlog entry:** the flow-layout
> fix (Task 1) is a structural bug in shared layout code that affects the
> whole window, not a single feature; the image-fidelity fix (Task 3) needs
> a schema decision (second stored resolution vs. switching to the
> file-based storage design in `implementation_roadmap6.md`) that's bigger
> than a backlog line. Tasks 2 and 4 are smaller and arguably could have
> been backlog entries, but are grouped here since they were discovered and
> should be fixed in the same pass as Tasks 1 and 3, all of which touch
> `import_dialog.py`/`edit_dialog.py`/`_preview_pane.py` together.

**Created:** 2026-07-17
**Status:** Completed

---

## Task Summary

| # | Task | Priority | Depends On |
|---|---|---|---|
| 1 | Fix `QFlowLayout.heightForWidth()` returning an invalid size — root cause of overlapping thumbnails and menu/toolbar collapsing on resize | Critical | — |
| 2 | Add screenshot attach/replace UI to `EditDialog` | High | — |
| 3 | Fix mapping-tag category mislabel in `ImportDialog` (breaks category-scoped grouping/search) | Medium | — |
| 4 | Store a preview-resolution image copy alongside the thumbnail copy, so the preview pane doesn't upscale a small image | High | — |
| 5 | **Carried forward from Roadmap 5** — Perfect-circle slider support, BPM calculation fix, real slider velocity | Critical | — |
| 6 | Reconcile the two "Roadmap 6" files (naming collision) | Low | — |
| 7 | Re-verify Roadmap 6's own claims against current code | — | (verification only, see §Verification below) |

---

## Verification of Roadmap 6's Claims (Done Before Planning New Work)

Per this project's own rule (`13_Bugfix_and_Refactor_Backlog.md` §0): don't
trust a `Done`/`Completed` checkbox without re-running the actual code.
`04_Implementation_Roadmap_6.md`'s Definition of Done was checked against
current source this session:

| Claim | Verified? | Evidence |
|---|---|---|
| `THUMBNAIL_WIDGET_MIN_WIDTH/HEIGHT` = 220×165 | ✅ True | Read `_constants.py` directly |
| `MIN_WINDOW_WIDTH/HEIGHT` = 1400×700 | ✅ True | Read `_constants.py` directly |
| `PREVIEW_PANE_WIDTH`/`MAX_WIDTH` = 900/1000 | ✅ True | Read `_constants.py` directly |
| Custom tags appear in `ImportDialog`'s checkbox grid | ✅ True | Read `import_dialog.py` — custom tags loaded, "(custom)" suffix stripped on save |
| Custom tags appear in `EditDialog` too (not explicitly promised, but present) | ✅ True, and a pleasant surprise | `EditDialog._setup_ui()` also loads and displays custom tags |
| Grid genuinely fits 4 per row with preview open on a 1920px display | ⏳ Not re-verified this session — would require actually running the app at that resolution; the constants support the claimed math, but Task 1 below (the `heightForWidth` bug) means the *vertical* layout is unreliable regardless of whether the horizontal column count is correct |

**Conclusion:** Roadmap 6's Task 1 (custom tags) holds up. Task 2 (grid
layout) partially holds up — the constants and column-count math are real,
but a layout bug underneath it (Task 1 below, not to be confused with
Roadmap 6's own "Task 1") makes the vertical behavior unreliable, which is
almost certainly what's producing the "thumbnails overlap" and "menu
collapses" reports.

---

## Task 1: Fix `QFlowLayout.heightForWidth()` — Root Cause of Overlap and Collapse

**Problem:** `osu_gallery/ui/_flow_layout.py`'s `_do_layout()` method ends
both of its branches (fixed-columns and flow-wrap) with:

```python
return QRect(QPoint(effective_rect.left(), cursor_y), QSize())
```

`QSize()`'s default (no-argument) constructor produces an **invalid**
size — width and height both `-1` — not an empty/zero size and
definitely not the actual computed content size. `heightForWidth(width)`
calls this method and returns `.height()` of that result, meaning it
*always* returns `-1` regardless of how many thumbnails are in the grid or
how tall the wrapped content actually is.

`QFlowLayout.hasHeightForWidth()` returns `True`, which tells Qt's layout
system "ask me for height-for-width and trust the answer." Since the
answer is always `-1`, every widget up the parent chain that relies on
this — the `QScrollArea` (`setWidgetResizable(True)`) holding the grid,
the `QSplitter` containing it, and ultimately the central widget of
`MainWindow` — receives bad size information. In practice this produces
exactly the two symptoms reported:
- **Thumbnails overlapping:** the scroll content widget doesn't get told
  the true total height of all wrapped rows, so its own size (and
  therefore the coordinate space later rows are positioned within) doesn't
  reliably reflect what `_do_layout()` actually computed when it ran with
  `test_only=False`.
- **Menu/toolbar collapsing on resize:** every window resize triggers a
  fresh `heightForWidth` query as part of Qt's layout recalculation. A
  layout that consistently reports "-1" for its needed height forces Qt to
  fall back to less predictable sizing heuristics for the whole vertical
  stack (toolbar, splitter, grid), which is consistent with elements
  appearing to randomly shrink/collapse during resizes.

**Goal:** `heightForWidth()` returns the real total height needed to
display all items at the given width, and resizing the window no longer
produces overlap or toolbar collapse.

**Files to change:**
- `osu_gallery/ui/_flow_layout.py` — `_do_layout()`

**Implementation plan:**

1. In both branches of `_do_layout()`, after the main loop, compute the
   actual bottom of the laid-out content:
   ```python
   content_bottom = cursor_y + self._line_height
   margins = self.contentsMargins()
   total_height = content_bottom - rect.top() + margins.bottom()
   return QRect(
       QPoint(effective_rect.left(), rect.top()),
       QSize(rect.width(), max(total_height, 0)),
   )
   ```
   (Use `rect.top()`/`rect.width()`, the original parameters passed into
   `_do_layout`, not `effective_rect`, so the returned rect reflects the
   full outer bounds including margins — consistent with what
   `heightForWidth`/`setGeometry` callers expect.)

2. Handle the empty-layout case explicitly (`self._items` is empty) —
   `_line_height` already returns `0` for an empty layout, so
   `total_height` naturally comes out to just the margins; add a test for
   this so it doesn't regress.

3. Double check `minimumSize()` still behaves sensibly alongside this fix
   — it currently computes from each item's `minimumSize()` independently
   of row-wrapping, which is fine to leave as-is (it's a different, valid
   concept — smallest the layout could ever be — from `heightForWidth`,
   which is "how tall for *this specific* width").

**Tests to add:**
- `test_flow_layout_height_for_width_matches_actual_rows` — build a `QFlowLayout` with a known set of fixed-size widget mocks/stubs at a known width, assert `heightForWidth(width)` equals `row_count * (item_height + v_spacing)` (or the appropriate margin-adjusted formula).
- `test_flow_layout_height_for_width_empty_layout` — empty layout returns just the margin height, not a negative/invalid size.
- `test_flow_layout_no_overlap_after_resize` — a UI-level test (using `QTest`/`grab()` if feasible, or geometry assertions via `itemAt(i).geometry()`) confirming no two items' geometries intersect after laying out at two different widths in sequence (simulating a resize).

---

## Task 2: Screenshot Attach/Replace UI in `EditDialog`

**Problem:** `EditDialog` declares `self._selected_image_path: str = ""`
in `__init__` but that's the *only* place it appears in the entire class —
no button, no file dialog handler, no resize/save logic, nothing in
`_on_save()`. There is currently no way to attach a screenshot to a
pattern that didn't get one at import time, or to replace an existing one.

**Goal:** `EditDialog` has the same attach-screenshot capability
`ImportDialog` has, pre-populated with the current attachment status.

**Files to change:**
- `osu_gallery/ui/edit_dialog.py`

**Implementation plan:**

1. Port `ImportDialog`'s `_attach_image_button`, `_image_filename_label`,
   `_on_attach_image()`, and `_get_selected_image_bytes()` into
   `EditDialog`, adjusting for the fact that a pattern may already have an
   image (`self._pattern.user_image`).
2. In `_populate_fields()`, set the filename label to reflect current
   state: `"Screenshot attached"` (with a way to view/clear it) if
   `self._pattern.user_image` is non-empty, or the existing placeholder if
   not.
3. In `_on_save()`, after the existing pattern update, mirror
   `ImportDialog`'s image-handling block: if a new image was selected,
   resize and call `db.update_pattern_user_image(...)`; wrap in
   `try/except` per the pattern already established (and fixed) in
   `ImportDialog`, so a failed image update doesn't block the rest of the
   save.
4. Apply the Task 4 fix (dual-resolution storage) here too if Task 4 lands
   first — don't build a second code path that only stores the single
   low-res copy that Task 4 is specifically removing.

**Tests to add:**
- `test_edit_dialog_has_attach_image_button` — button exists and is wired.
- `test_edit_dialog_replaces_existing_image` — a pattern with an existing image gets a new one attached, saved, and reloaded correctly.
- `test_edit_dialog_shows_current_image_status` — filename label reflects whether the pattern currently has an image before any change is made.

---

## Task 3: Mapping Tag Category Mislabel in Import

**Problem:** In `ImportDialog._on_parse_and_save()`, manually checked
mapping tags (`manual_tags`, from the checkbox grid) get merged into
`metadata_tags` via `_merge_tags(metadata_tags, manual_tags)`, and the
resulting merged list is linked to the pattern in a loop tagged
`category=TAG_CATEGORY_METADATA`. Only the separately-tracked,
auto-detected `mapping_tags` list (from `detect_object_tags()`) gets
`category=TAG_CATEGORY_MAPPING`. This means every manually-checked tag —
which is the majority of what actually gets tagged, since
`MAPPING_TAG_OPTIONS` is a manual checklist — is stored under the wrong
category. `_preview_pane.py`'s `_render_tags()` groups tags by
`category == "mapping"` vs. everything else for display, and any future
category-scoped search/filter (e.g. `SearchQuery.category`, which already
exists in `search/engine.py` and is fully wired) would silently miss these
tags.

**Goal:** Manually-selected mapping tags are linked under
`TAG_CATEGORY_MAPPING`, matching their actual meaning and matching how
`EditDialog` already (correctly) handles them.

**Files to change:**
- `osu_gallery/ui/import_dialog.py`

**Implementation plan:**

1. Stop merging `manual_tags` into `metadata_tags` before the linking
   loop. Instead, merge `manual_tags` into the `mapping_tags` list (which
   already gets the correct category), deduplicating with the existing
   `_merge_tags()` helper.
2. `metadata_tags` should end up empty in practice (per the existing
   `_extract_tag_names()` docstring/behavior, which already returns `[]`
   for it) unless a future change starts populating real `.osu`-file-level
   metadata tags — leave the metadata-tag linking loop in place structurally
   for that future case, just stop feeding it manual mapping tag selections.

**Tests to add:**
- `test_import_manual_tags_linked_as_mapping_category` — a manually-checked tag ends up with `category == "mapping"` in the database, not `"metadata"`.
- `test_import_category_search_finds_manually_tagged_pattern` — `SearchQuery(category="mapping")` returns a pattern that only got tags via manual checkbox selection (regression test tying this back to the reported "search doesn't find mapping tags" symptom — see the note in Task 4/§Investigation below on whether this alone fully explains that report).

**Investigation note for the AI implementing this:** this category
mislabel is confirmed by reading the code, but it may not fully explain
"search doesn't work for mapping tags" if the user was typing a tag name
into the plain text search box (which goes through FTS5 full-text match on
`raw_code`/`artist`/`title`/`mapper`/tag-name-text combined, not the
`category` filter — the UI's search bar never sets `SearchQuery.category`
at all, only `SearchQuery.text`). Several `MAPPING_TAG_OPTIONS` entries
contain `/` and `°` characters (e.g. `"1/2 slider"`, `"15° angled
pattern"`), which SQLite FTS5's default `unicode61` tokenizer may split
differently than expected around those characters. Before considering this
fully fixed, manually test searching for a plain tag like `"Circle"` and a
punctuated one like `"1/2 slider"` after applying this fix, and if the
punctuated case still fails, that's a separate, second bug in the FTS5
query construction in `search/engine.py`'s `search()` method — log it as a
new entry in `13_Bugfix_and_Refactor_Backlog.md` rather than assuming this
task's fix covers it.

---

## Task 4: Preview-Resolution Image Storage (Fix Screenshot Upscaling)

**Problem:** `ImportDialog._get_selected_image_bytes()` always calls
`resize_image_for_thumbnail(raw_bytes, 512, 384)`, discarding the original
screenshot resolution at import time — only one 512×384 copy is ever
stored, in `pattern.user_image`. `_preview_pane.py` and `thumbnail_widget.py`
both load this same single copy. That was fine when the preview pane was
~500px wide (Roadmap 3/4 era), but Roadmap 6 widened it to 900–1000px,
meaning that single 512px-wide stored copy now gets upscaled roughly 2x to
fill the pane — visible blur/softening is the expected result of stretching
a smaller image larger, not image corruption. `resize_image_for_preview()`
already exists in `image_resizer.py` (defaults to 1024×768) but is never
called anywhere in the codebase — this was clearly intended to be used and
just never got wired up.

**Goal:** The preview pane displays a screenshot at a resolution that
doesn't require significant upscaling for its current display size; the
thumbnail grid continues using the small copy it actually needs.

**Files to change:**
- `osu_gallery/db/database.py` — schema (new column), `create_pattern`, `get_pattern`, `get_all_patterns`, `get_patterns_by_tag`, `update_pattern`, `update_pattern_user_image`
- `osu_gallery/db/models.py` — `Pattern` dataclass
- `osu_gallery/preview/image_resizer.py` — update `resize_image_for_preview()`'s defaults from 1024×768 to 1536×1152 to match current `PREVIEW_HEIGHT`/pane width from Roadmap 6
- `osu_gallery/ui/import_dialog.py`, `osu_gallery/ui/edit_dialog.py` (after Task 2) — save both resolutions
- `osu_gallery/ui/_preview_pane.py` — load the preview-resolution copy instead of the thumbnail one

**Implementation plan:**

1. Add a `user_image_preview BLOB` column (migration, same pattern as
   existing `_migrate_existing_schema()` entries) alongside the existing
   `user_image` column — keep `user_image` as the thumbnail-resolution
   copy (already correctly sized for the grid), add the new column for the
   preview-resolution copy.
2. Update `Pattern` dataclass: add `user_image_preview: bytes = b""`.
3. Update all `SELECT`/`INSERT`/`UPDATE` statements in `database.py` that
   touch `user_image` to also handle `user_image_preview` — this is the
   same class of consistency issue as BUG-106 in `13_Bugfix_and_Refactor_
   Backlog.md`, so be thorough about hitting every method (`create_pattern`,
   `get_pattern`, `get_all_patterns`, `get_patterns_by_tag`, `update_pattern`)
   rather than just the obvious one or two.
4. Add `update_pattern_user_images(pattern_id, thumbnail_bytes, preview_bytes, filename)`
   replacing the current `update_pattern_user_image` (or extend it with an
   optional second parameter — either is fine, pick one and be consistent).
5. In `ImportDialog`/`EditDialog`, call `resize_image_for_thumbnail(...)`
   AND `resize_image_for_preview(...)` from the same source bytes (read the
   file once, resize twice), store both.
6. In `_preview_pane.py`'s `load_pattern()`, change
   `if pattern.user_image:` / `pixmap.loadFromData(pattern.user_image)` to
   check and load `pattern.user_image_preview` instead (falling back to
   `user_image` if `user_image_preview` is empty, for patterns imported
   before this change — backward compatibility without a forced
   re-migration).
7. Consider whether this is better solved by fully adopting the file-based
   storage design already written up in `implementation_roadmap6.md`
   instead of adding a second BLOB column — that design naturally supports
   multiple resolutions as separate files and was already fully planned.
   If the team decides to go that route, this task's DB changes should be
   superseded by that roadmap's Task 1–3 instead of layered on top of them.
   Flag this decision explicitly rather than silently picking one — see
   Task 6 below.

**Tests to add:**
- `test_import_stores_both_image_resolutions` — importing with an attached image populates both `user_image` and `user_image_preview` with different (correctly-sized) dimensions.
- `test_preview_pane_uses_preview_resolution_image` — preview pane loads from `user_image_preview`, not `user_image`, when both are present.
- `test_preview_pane_falls_back_to_thumbnail_image_if_no_preview_copy` — patterns imported before this change (only `user_image` populated) still display something in the preview pane rather than nothing.
- `test_thumbnail_widget_still_uses_thumbnail_resolution` — regression test confirming the grid thumbnail didn't start loading the (larger, wasteful) preview copy by mistake.

---

## Task 5: Carried Forward — Parser Spec Compliance (Roadmap 5, Unstarted)

**Status check performed this session:** `osu_gallery/parser/osu_file.py`
was read in full and is unchanged from when `04_Implementation_Roadmap_5.md`
was written. None of its tasks have been started:

- Perfect-circle (`P`) slider curve type is still unsupported — the regex
  still reads `[LBCO]` (missing `P`, includes the invalid `O` that was
  never a real curve type).
- `_parse_timing_points()` still has the uninherited/inherited logic
  backwards — it computes BPM from negative `beatLength` values (which are
  actually inherited SV multipliers) and explicitly ignores positive values
  (`elif ms_per_beat > 0: pass`), which is where real BPM data lives per
  the spec. This means the overwhelming majority of real single-BPM maps
  still compute `timing_bpm = 0.0`.
- Per-slider `multiplier`/`tick_rate` are still parsed from
  `opt_parts[3]`/`opt_parts[4]`, fields that don't exist in the real
  format (slider objectParams only ever has 5 parts).

**Action:** do not re-plan this work — `04_Implementation_Roadmap_5.md`'s
seven tasks, execution order, risk assessment, and test plan are all still
valid and unchanged. Execute that document's Task 1 through Task 7 as
originally written. This entry exists so the Definition of Done below
doesn't let this roadmap get marked complete while Roadmap 5 is silently
skipped a second time.

---

## Task 6: Reconcile the Two "Roadmap 6" Files

**Problem:** `04_Implementation_Roadmap_6.md` (custom tags + grid layout,
completed) and `implementation_roadmap6.md` (BLOB→file image storage,
never started) both claim to be "Implementation Roadmap 6." The second
file also doesn't follow the established `04_Implementation_Roadmap_N.md`
naming convention at all.

**Goal:** One clear numbering scheme; no file claims a number that's
already taken.

**Implementation plan:**
1. Rename `implementation_roadmap6.md` to `04_Implementation_Roadmap_8.md`
   and update its internal title header from "Implementation Roadmap 6" to
   "Implementation Roadmap 8" accordingly — do this rename, don't
   delete-and-recreate, to preserve file history if this project is under
   git (per memory, it is).
2. Decide whether that roadmap's BLOB→file plan is still wanted given
   Task 4 above's simpler two-BLOB-column approach — if Task 4 is
   implemented first, roadmap 8 should be explicitly re-scoped to either
   (a) still do the full file-based migration for other reasons (external
   tool access, avoiding DB bloat — both still valid motivations
   independent of the resolution problem Task 4 solves), or (b) be marked
   superseded/cancelled with a note explaining why, rather than left in an
   ambiguous "Planned" state indefinitely.
3. Update `00_README.md`'s directory listing to include both
   `04_Implementation_Roadmap_5.md` through `_8.md` if it doesn't already
   (this was flagged as skipped once already in
   `13_Bugfix_and_Refactor_Backlog.md`'s history due to encoding corruption
   in that file — worth fixing both issues in the same pass).

---

## Execution Order

```
Step 1: Task 1 (flow layout height bug) — independent, highest severity, fixes two reported symptoms at once
Step 2: Task 5 (Roadmap 5 parser work) — independent, was already fully planned, just needs to actually happen
Step 3: Task 3 (tag category mislabel) — independent, small
Step 4: Task 4 (dual-resolution image storage) — independent of 1/3/5, but should land before Task 2
Step 5: Task 2 (edit dialog image UI) — do after Task 4 so it's built against the final image-storage design, not the old single-BLOB one
Step 6: Task 6 (roadmap file reconciliation) — do last, once Task 4's decision about file-based vs. dual-BLOB storage is settled, since that decision affects what Task 6 recommends for the renamed roadmap 8
```

**Parallelization opportunities:** Tasks 1, 3, and 5 touch completely
disjoint code and can be done in any order or in parallel. Task 4 should
be decided/started before Task 2 to avoid rework.

---

## Database Schema Changes

```sql
-- Task 4
ALTER TABLE pattern ADD COLUMN user_image_preview BLOB;
```

Task 5 has no schema changes for its core tasks (1–3); Task 5's Task 4
(BPM range) from Roadmap 5 adds `timing_bpm_min`/`timing_bpm_max` as
already specified there.

---

## Risk Assessment

| Risk | Mitigation |
|---|---|
| Task 1's flow layout fix could change existing visual behavior in ways not caught by the current test suite (which doesn't appear to test actual pixel geometry) | Add the geometry-assertion tests specified in Task 1; manually verify at several window widths before considering this done |
| Task 4 adds a second BLOB column right as Task 6 might decide to move to file-based storage entirely, creating throwaway schema work | Explicitly sequence Task 4 before Task 6's decision point (see Execution Order) and flag the tension directly in Task 4's own plan rather than hiding it |
| Task 3's fix changes which category existing tags were stored under only going forward — already-imported patterns keep their current (wrong) category unless separately migrated | Consider a one-time data migration that reclassifies existing `metadata`-category tags that match `MAPPING_TAG_OPTIONS` names to `mapping` category; scope this as a follow-up if the user has existing tagged patterns they care about, not required for the fix itself to be correct going forward |
| Roadmap 5 (Task 5 here) was skipped once already in favor of newer-feeling work | This roadmap makes skipping it a second time visible in its own Definition of Done — an AI agent working through this file mechanically will see Task 5 unchecked and can't accidentally consider the roadmap complete without it |

---

## Definition of Done for This Roadmap

- [x] Task 1: `heightForWidth()` returns real computed height; no overlapping thumbnails at any tested window width; toolbar/menu no longer collapses on resize
- [x] Task 2: `EditDialog` supports attaching/replacing a pattern's screenshot
- [x] Task 3: Manually-checked mapping tags are linked under `TAG_CATEGORY_MAPPING`; category-scoped search finds them
- [x] Task 4: Preview pane displays a preview-resolution image, not an upscaled thumbnail-resolution one
- [x] Task 5: `04_Implementation_Roadmap_5.md`'s Definition of Done is fully checked off — not skipped again
- [x] Task 6: No two files claim to be "Roadmap 6"; `00_README.md` directory listing is current
- [x] Full existing test suite passes (446 tests)
- [x] `ruff` linting passes (only pre-existing warnings in unrelated files)
- [x] Feature logged in `04_Implementation_Roadmap.md` §5 Feature Log
- [x] Any newly-discovered issues logged in `13_Bugfix_and_Refactor_Backlog.md`, not silently fixed without a record — including confirming or ruling out the FTS5 tokenizer hypothesis noted in Task 3
