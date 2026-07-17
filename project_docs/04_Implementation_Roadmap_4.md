# Implementation Roadmap 4: Preview Fixes, Tag UI Overhaul & User Image Inputs

> This roadmap covers the next round of fixes and improvements: correcting thumbnail/preview sizes, improving object visibility, displaying user input mapping tags on previews, overhauling the tag selection UI in the import dialog, adding a Pattern Tags management panel, fixing the last-saved pattern miniature mismatch, and adding user-provided image inputs as a fallback for auto-generated previews.

**Created:** 2026-07-17
**Status:** Completed

---

## Task Summary

| # | Task | Priority | Depends On |
|---|---|---|---|
| 1 | Fix thumbnail and preview sizes (they did not change in roadmap 3) | P1 | — |
| 2 | Improve object visibility — add numeric labels since objects are too small to see order in miniature/preview | P1 | — |
| 3 | Display user input mapping tags on the pattern preview box | P1 | Task 2 |
| 4 | Replace import dialog tag typing box with a checkmark-based multi-select tag picker | P1 | — |
| 5 | Add "Pattern Tags" panel button next to import — displays all tag options with ability to add more | P1 | Task 4 |
| 6 | Fix last-saved pattern miniature not matching its preview | P1 | Task 1 |
| 7 | Add user image input saved alongside pattern code; user image takes priority over auto-generated preview | P1 | — |

---

## Task 1: Fix Thumbnail & Preview Sizes

**Problem:** The thumbnail and preview sizes did not actually change from roadmap 3. Despite the constants being updated in code, the rendered sizes remain at the old dimensions (200x150 for thumbnails, 512x384 for previews). This means all the rendering logic needs to be verified and corrected to actually produce the intended sizes.

**Goal:**
- Thumbnails: rendered at 512x384 (doubled from 200x150)
- Preview: rendered at 1024x768 (doubled from 512x384)
- Display sizes: thumbnails displayed at a reasonable scaled size in the grid, preview displayed proportionally in the pane

**Files to change:**
- `osu_gallery/_constants.py` — verify `THUMBNAIL_WIDTH`, `THUMBNAIL_HEIGHT`, `PREVIEW_HEIGHT`, `PREVIEW_PANE_WIDTH`
- `osu_gallery/preview/thumbnail_renderer.py` — verify default render dimensions
- `osu_gallery/ui/thumbnail_widget.py` — verify `_load_and_render()` call and `paintEvent()` scaling
- `osu_gallery/ui/_preview_pane.py` — verify `_PANE_WIDTH`, `_PREVIEW_HEIGHT`, scaled rendering
- `osu_gallery/ui/main_window.py` — verify splitter default sizes

**Implementation plan:**

1. Audit `thumbnail_renderer.py`:
   - Verify `render_thumbnail()` defaults to `width=512, height=384`
   - Verify `render_pattern_preview()` defaults to `width=1024, height=768`
   - If defaults are still at old values, update them

2. Audit `thumbnail_widget.py`:
   - Check `_load_and_render()` — ensure it calls `render_thumbnail(osu_file, width=512, height=384)`
   - Check `paintEvent()` — ensure scaling uses `KeepAspectRatio` and renders at widget size
   - Update `setMinimumSize()` if needed to accommodate 512x384 rendered size

3. Audit `_preview_pane.py`:
   - Check `_PANE_WIDTH` and `_PREVIEW_HEIGHT` constants
   - Check `load_pattern()` — ensure it renders at `width=1024, height=768`
   - Check scaled display math — divisor should be 1024 (not 512)

4. Audit `main_window.py`:
   - Check `_on_pattern_clicked()` default width
   - Check splitter initial sizes

**Tests to add:**
- `test_thumbnail_rendered_at_512x384` — verify thumbnail rendered at correct size
- `test_preview_rendered_at_1024x768` — verify preview rendered at correct size
- `test_thumbnail_widget_paints_at_rendered_size` — verify widget displays full resolution
- `test_preview_pane_scales_correctly` — verify pane scales 1024x768 to fit available width

---

## Task 2: Improve Object Visibility with Numeric Labels

**Problem:** The miniature and preview sizes are small enough that object numbers (combo order) are not visible. The previous roadmap attempted to add combo order numbers, but at the current rendered sizes the numbers are too small to read on the miniature thumbnails and still cramped on the preview.

**Goal:**
- Display clear, readable numeric labels on each hit object showing its combo order
- Numbers must be visible on both thumbnails (512x384) and previews (1024x768)
- Labels should use high-contrast styling (dark background circle + white text) for readability at small sizes
- Numbers should be proportionally sized to the rendered object size

**Files to change:**
- `osu_gallery/parser/models.py` — verify `combo_order` field exists on `HitObject`
- `osu_gallery/parser/osu_file.py` — verify combo order assignment during parsing
- `osu_gallery/preview/thumbnail_renderer.py` — update `_draw_combo_number()` for visibility at small sizes

**Implementation plan:**

1. Verify `parser/models.py` has `combo_order: int = 0` on `HitObject`
2. Verify `parser/osu_file.py` assigns `combo_order = combo_index + 1` during the second pass
3. Update `_draw_combo_number()` in `thumbnail_renderer.py`:
   - Increase font size for readability (e.g., 10-12px instead of 8px)
   - Use a solid dark circle background (QColor(0, 0, 0, 220)) for contrast
   - Use white bold text (QColor(255, 255, 255))
   - Position number at the center-top of each hit circle
   - Scale number size relative to the rendered object radius (min 7px font, max 14px font)
   - For thumbnails: ensure minimum visible size (skip if rendered circle < 10px radius)
   - For previews: always draw (preview is large enough)

4. Draw numbers on:
   - Circle hit positions
   - Slider start positions (not slider body paths)
   - Not on spinner hit positions (spinners don't have combo order in the same way)

**Tests to add:**
- `test_combo_number_visible_on_thumbnail` — verify number rendered on thumbnail at 512x384
- `test_combo_number_visible_on_preview` — verify number rendered on preview at 1024x768
- `test_combo_number_high_contrast_styling` — verify dark bg + white text
- `test_combo_number_scaled_to_object_size` — verify font scales with circle radius
- `test_combo_number_skipped_on_tiny_objects` — verify objects < 10px radius are skipped on thumbnail

---

## Task 3: Display User Input Mapping Tags on Pattern Preview

**Problem:** When the user adds mapping tags via the import dialog (e.g., "Circle", "Kickslider", "3 circles"), these tags are saved to the database but are not visibly displayed on the pattern preview box below the rendered image. The preview box shows the rendered pattern but lacks the user's mapping tag annotations.

**Goal:**
- Display all user-added mapping tags below the rendered preview image in the preview pane
- Tags should be shown as styled label badges/chips
- Auto-detected object tags (e.g., "3 circles", "2 sliders") should be visually distinct from user-added mapping tags
- Tags should be scrollable if there are many

**Files to change:**
- `osu_gallery/ui/_preview_pane.py` — add mapping tags display section below the preview image
- `osu_gallery/db/models.py` — verify `mapping_tags` field exists on `Pattern`
- `osu_gallery/ui/import_dialog.py` — verify tags are saved correctly

**Implementation plan:**

1. Verify `Pattern` dataclass has a `mapping_tags` field (list of strings)
2. In `_preview_pane.py`, add a mapping tags section below the preview image:
   ```python
   def _render_mapping_tags(self, layout: QVBoxLayout) -> None:
       """Display user-added mapping tags below the preview."""
       if not self._pattern.mapping_tags:
           return
       # Section header
       header = QLabel("Mapping Tags:")
       header.setStyleSheet("font-weight: bold; margin-top: 8px;")
       layout.addWidget(header)
       # Tag badges
       tags_layout = QHBoxLayout()
       for tag in self._pattern.mapping_tags:
           badge = QLabel(f" {tag} ")
           badge.setStyleSheet("""
               background-color: #2a2a4a;
               color: #e0e0e0;
               border: 1px solid #4a4a6a;
               border-radius: 10px;
               padding: 2px 8px;
               margin: 2px;
           """)
           tags_layout.addWidget(badge)
       tags_layout.addStretch()
       layout.addLayout(tags_layout)
   ```
3. Call `_render_mapping_tags()` after the preview image widget in `_render_content()`
4. Auto-detected object tags (from `detect_object_tags()`) should be shown in a separate section or with a different style (e.g., lighter background) to distinguish from user-added tags

**Tests to add:**
- `test_preview_displays_user_mapping_tags` — verify tags rendered below preview
- `test_preview_tag_badge_styling` — verify tag badges have correct styling
- `test_preview_auto_detected_tags_distinct_from_user_tags` — verify visual distinction
- `test_preview_no_tags_section_when_empty` — verify section hidden when no tags
- `test_preview_scrollable_tags` — verify many tags are scrollable

---

## Task 4: Replace Tag Typing Box with Checkmark Multi-Select Picker

**Problem:** The import dialog currently uses a text input box for users to type mapping tags. This is error-prone (typos, inconsistent naming) and doesn't guide the user toward the canonical tag set. The user wants a visual checkmark-based picker where they can simply select from the available options.

**Goal:**
- Replace the free-text tag input in the import dialog with a scrollable grid of checkboxes
- Each checkbox corresponds to one option from the canonical mapping tag list
- User checks the boxes that apply to their pattern
- Selected tags are collected as a list and saved with the pattern
- The import dialog should still show auto-detected object tags (circles, sliders) as read-only indicators

**Canonical mapping tag options:**
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
- `osu_gallery/ui/import_dialog.py` — replace text input with checkbox grid
- `osu_gallery/_constants.py` — verify `MAPPING_TAG_OPTIONS` constant exists
- `osu_gallery/db/models.py` — verify `mapping_tags` field on `Pattern`
- `osu_gallery/db/database.py` — verify CRUD handles mapping_tags list

**Implementation plan:**

1. Verify `_constants.py` has `MAPPING_TAG_OPTIONS: list[str]` with all 32 options
2. Replace the tag input widget in `import_dialog.py`:
   - Remove the free-text QLineEdit/QTextEdit for tags
   - Add a `QScrollArea` containing a `QVBoxLayout` with checkboxes
   - Organize checkboxes in a 2-column or 3-column grid layout for compact display
   - Each checkbox: `QCheckBox(tag_name)` for each option in `MAPPING_TAG_OPTIONS`
   - Add a "Select All" / "Clear All" toggle at the top
   - Group checkboxes by category (shapes, angles, coverage, etc.) with section headers

3. Add helper to collect selected tags:
   ```python
   def _get_selected_mapping_tags(self) -> list[str]:
       """Return list of currently checked mapping tags."""
       return [
           cb.text() for cb in self._tag_checkboxes
           if cb.isChecked()
       ]
   ```

4. On import save, pass selected tags to pattern creation:
   ```python
   mapping_tags = self._get_selected_mapping_tags()
   pattern = self.db.create_pattern(
       ...
       mapping_tags=mapping_tags,
   )
   ```

5. On edit/load existing pattern, pre-check the saved tags

**Tests to add:**
- `test_import_dialog_shows_checkbox_grid` — verify checkboxes rendered for all options
- `test_import_dialog_collects_selected_tags` — verify selected tags returned correctly
- `test_import_dialog_select_all_clear_all` — verify bulk toggle works
- `test_import_dialog_pre_checks_existing_tags` — verify loaded pattern's tags are pre-checked
- `test_import_dialog_saves_mapping_tags_to_db` — verify round-trip through database

---

## Task 5: Add "Pattern Tags" Management Panel

**Problem:** There is no way for the user to manage, view, or add mapping tags outside of the import dialog. The user wants a dedicated "Pattern Tags" option/button (placed next to the import button in the top right) that opens a panel showing all available tag options with the ability to add new ones.

**Goal:**
- Add a "Pattern Tags" button next to the import button in the main window's top bar
- Clicking it opens a dialog/panel showing all mapping tag options as checkboxes
- User can check/uncheck tags to enable/disable them globally
- User can add new custom tags beyond the canonical list
- Added tags are saved to the database and persist across sessions
- New tags appear in the import dialog's checkbox picker

**Files to change:**
- `osu_gallery/ui/main_window.py` — add "Pattern Tags" button in top bar
- `osu_gallery/ui/_pattern_tags_dialog.py` — new dialog for tag management
- `osu_gallery/db/database.py` — add methods for custom tags CRUD
- `osu_gallery/db/models.py` — add `custom_tags` table or field
- `osu_gallery/_constants.py` — keep canonical list as default, allow extension
- `osu_gallery/ui/import_dialog.py` — load custom tags alongside canonical options

**Implementation plan:**

1. Add "Pattern Tags" button to `main_window.py`:
   ```python
   # In _setup_ui(), next to the import button:
   self._tags_button = QPushButton("Pattern Tags")
   self._tags_button.clicked.connect(self._open_pattern_tags_dialog)
   # Add to top bar layout
   ```

2. Create `osu_gallery/ui/_pattern_tags_dialog.py`:
   - Dialog with title "Pattern Tags"
   - Scrollable grid of checkboxes for all canonical + custom tags
   - "Add New Tag" field at the bottom:
     - QLineEdit for new tag name
     - "Add" button to save to database
     - Validation: no empty names, no duplicates
   - "Remove" button to deselect/remove custom tags
   - "Save" / "Cancel" buttons
   - Load existing tags from database on open

3. Add custom tags storage to database:
   - New table `custom_mapping_tags`:
     ```sql
     CREATE TABLE IF NOT EXISTS custom_mapping_tags (
         id INTEGER PRIMARY KEY AUTOINCREMENT,
         tag_name TEXT NOT NULL UNIQUE,
         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
     );
     ```
   - Add CRUD methods to `database.py`
   - Migration in `_migrate_existing_schema()`

4. Update `import_dialog.py`:
   - Load tags from: canonical `MAPPING_TAG_OPTIONS` + custom tags from database
   - Display all together in the checkbox grid
   - Custom tags appear at the bottom of the list with a "(custom)" indicator

5. Update `_constants.py`:
   - Keep `MAPPING_TAG_OPTIONS` as the base list
   - Add helper to merge canonical + custom tags

**Tests to add:**
- `test_pattern_tags_button_exists` — verify button in main window
- `test_pattern_tags_dialog_opens` — verify dialog opens on click
- `test_pattern_tags_dialog_loads_canonical_tags` — verify all canonical options shown
- `test_pattern_tags_dialog_adds_custom_tag` — verify new tag saved to DB
- `test_pattern_tags_dialog_removes_custom_tag` — verify removal works
- `test_pattern_tags_dialog_custom_tag_appears_in_import` — verify custom tag in import picker
- `test_pattern_tags_dialog_persists_across_sessions` — verify tags survive restart
- `test_pattern_tags_dialog_validation_no_empty` — verify empty tag names rejected
- `test_pattern_tags_dialog_validation_no_duplicates` — verify duplicate names rejected

---

## Task 6: Fix Last-Saved Pattern Miniature Mismatch

**Problem:** The miniature (thumbnail) of the last-saved pattern does not match what the pattern preview shows. The thumbnail renders one version of the pattern while the preview renders another, suggesting a discrepancy in rendering parameters, coordinate scaling, or timing between the two render paths.

**Goal:**
- Ensure the thumbnail and preview render the exact same visual representation of the pattern
- Both should use identical coordinate scaling, combo colors, object drawing, and timing
- The mismatch may be caused by: different render dimensions causing coordinate distortion, different combo color assignment, or different object drawing logic between thumbnail and preview renderers

**Files to change:**
- `osu_gallery/preview/thumbnail_renderer.py` — audit and align rendering logic between `render_thumbnail()` and `render_pattern_preview()`
- `osu_gallery/parser/osu_file.py` — verify coordinate normalization is consistent
- `osu_gallery/ui/thumbnail_widget.py` — verify thumbnail uses the same render path as preview
- `osu_gallery/ui/_preview_pane.py` — verify preview uses the same render path as thumbnail

**Implementation plan:**

1. Audit rendering pipeline:
   - Check if `render_thumbnail()` and `render_pattern_preview()` use the same coordinate normalization
   - Verify both use the same combo color assignment logic
   - Verify both use the same object drawing functions (circles, sliders, spinners)
   - Check if dimension differences (512x384 vs 1024x768) cause coordinate scaling issues

2. Identify the mismatch source:
   - If coordinates are normalized to 0-1 range: both renders should produce identical visuals regardless of output dimensions
   - If coordinates use absolute pixel values: scaling may differ between thumbnail and preview
   - If combo colors are assigned per-render: they may differ between the two paths

3. Fix the mismatch:
   - Standardize on coordinate normalization to a consistent coordinate space (e.g., 512x384 internal, then scale to output)
   - Ensure combo colors are assigned once during parsing and reused by both renderers
   - Ensure object drawing logic is shared (call same `_render_circle()`, `_render_slider()` functions from both paths)

4. Add visual regression test:
   - Render same pattern to both thumbnail and preview
   - Compare rendered images (or key features: circle positions, slider paths, combo colors)
   - Assert they are visually consistent

**Tests to add:**
- `test_thumbnail_matches_preview_coordinates` — verify same coordinates rendered
- `test_thumbnail_matches_preview_combo_colors` — verify same combo colors
- `test_thumbnail_matches_preview_slider_paths` — verify same slider rendering
- `test_thumbnail_matches_preview_circle_positions` — verify same circle positions
- `test_rendering_uses_shared_draw_functions` — verify both paths call same renderer helpers
- `test_last_saved_pattern_consistent_render` — verify last-saved pattern renders identically in both views

---

## Task 7: Add User Image Inputs as Preview Fallback

**Problem:** Auto-generated previews have bugs and inconsistencies. The user wants the ability to provide their own screenshot/image of the pattern as a fallback. When a user image is provided, it should be used instead of the auto-generated preview. The user image should be resized to match the preview dimensions.

**Priority:** User image (if saved) > Auto-generated preview (fallback)

**Goal:**
- Allow user to attach an image file (PNG, JPG) to a pattern during import or via an edit dialog
- User image is stored alongside the pattern in the database (BLOB or file path)
- When displaying a preview: check if user image exists → use it (resized to preview dimensions) → if not, generate auto-preview
- Thumbnail: same logic — user image resized to thumbnail dimensions if available
- Image resize targets:
  - Thumbnails: 200x150 → 512x384 (doubled for display)
  - Preview: 512x384 → 1024x768 (doubled for display)
- Images should be cropped/padded to maintain 4:3 aspect ratio

**Files to change:**
- `osu_gallery/db/models.py` — add `user_image` field (BLOB or file path) to `Pattern`
- `osu_gallery/db/database.py` — add column, update CRUD methods
- `osu_gallery/ui/import_dialog.py` — add image file picker button
- `osu_gallery/ui/_preview_pane.py` — load and display user image if available
- `osu_gallery/ui/thumbnail_widget.py` — load and display user image if available
- `osu_gallery/_constants.py` — define image resize dimensions

**Implementation plan:**

1. Update database schema:
   ```sql
   ALTER TABLE pattern ADD COLUMN user_image BLOB;
   ALTER TABLE pattern ADD COLUMN user_image_filename TEXT;
   ```
   - `user_image`: BLOB storing the resized image data (or file path to stored image)
   - `user_image_filename`: original filename for reference

2. Update `Pattern` dataclass:
   ```python
   user_image: bytes = b""  # resized image bytes, empty if not provided
   user_image_filename: str = ""
   ```

3. Add image picker to `import_dialog.py`:
   - Add a button "Attach Screenshot" next to the import button area
   - On click: open `QFileDialog.getOpenFileName()` filtering for `*.png;*.jpg;*.jpeg;*.bmp`
   - Show selected filename in a label
   - On save: read image bytes, resize to target dimensions, store in pattern

4. Add image resizing utility:
   ```python
   def resize_image_for_preview(image_bytes: bytes, target_width: int, target_height: int) -> bytes:
       """Resize image to target dimensions, maintaining 4:3 aspect ratio with padding."""
       # Use QPixmap for loading and scaling
       # If aspect ratio differs from 4:3, pad with transparent/background color
       # Return resized bytes
   ```
   - Thumbnail resize: target 512x384
   - Preview resize: target 1024x768
   - Both maintain 4:3 aspect ratio (pad if needed)

5. Update `_preview_pane.py`:
   ```python
   def _render_content(self):
       if self._pattern.user_image:
           # Display user image (resized)
           pixmap = self._load_user_image(self._pattern.user_image)
           self._preview_label.setPixmap(pixmap)
       else:
           # Fallback: generate auto-preview
           pixmap = render_pattern_preview(...)
           self._preview_label.setPixmap(pixmap)
   ```

6. Update `thumbnail_widget.py`:
   - Same logic: check `user_image` → display resized → else auto-render
   - Cache user image at thumbnail size for performance

7. Add edit capability:
   - Right-click context menu on preview → "Change Screenshot" / "Remove Screenshot"
   - Or add an edit mode in the preview pane

**Tests to add:**
- `test_pattern_has_user_image_field` — verify dataclass field exists
- `test_database_stores_user_image` — verify CRUD round-trip
- `test_import_dialog_image_picker_opens` — verify file dialog opens
- `test_import_dialog_accepts_image_files` — verify PNG/JPG accepted
- `test_image_resized_to_thumbnail_dimensions` — verify 512x384 output
- `test_image_resized_to_preview_dimensions` — verify 1024x768 output
- `test_image_maintains_4_3_aspect_ratio` — verify padding for non-4:3 images
- `test_preview_displays_user_image_when_available` — verify user image shown over auto-preview
- `test_preview_falls_back_to_auto_generated` — verify auto-preview when no user image
- `test_thumbnail_displays_user_image_when_available` — verify user image shown in thumbnail
- `test_user_image_removable` — verify user can remove attached image
- `test_user_image_changes_without_reimport` — verify image can be updated

---

## Execution Order

```
Step 1: Task 1 (Fix sizes) — foundational, everything else depends on correct rendering
Step 2: Task 6 (Fix miniature mismatch) — depends on Task 1 (correct sizes first)
Step 3: Task 2 (Object visibility) — depends on Task 1 (correct sizes for visibility)
Step 4: Task 3 (Display mapping tags on preview) — depends on Task 2 (preview working correctly)
Step 5: Task 4 (Tag checkmark picker) — independent, can be done in parallel with Task 3
Step 6: Task 5 (Pattern Tags panel) — depends on Task 4 (needs tag system in place)
Step 7: Task 7 (User image inputs) — independent, can be done in parallel with all above
```

**Parallelization opportunities:**
- Task 1, 6, 2, 3 are sequential (rendering pipeline fixes)
- Task 4 and Task 5 are sequential (tag UI) but independent of rendering tasks
- Task 7 (user images) is fully independent — can be done alongside any other task

---

## Database Schema Changes

```sql
-- Task 6: No schema changes needed (existing mapping_tags column)

-- Task 7: User image storage
ALTER TABLE pattern ADD COLUMN user_image BLOB;
ALTER TABLE pattern ADD COLUMN user_image_filename TEXT DEFAULT '';

-- Task 5: Custom mapping tags
CREATE TABLE IF NOT EXISTS custom_mapping_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## New Files

| File | Purpose | Depends On |
|---|---|---|
| `osu_gallery/ui/_pattern_tags_dialog.py` | Pattern Tags management dialog | Task 5 |
| `osu_gallery/preview/image_resizer.py` | Image resize utility for user images | Task 7 |

---

## Risk Assessment

| Risk | Mitigation |
|---|---|
| User images may be large (MBs) and slow to load | Resize on import, store resized version only, cache at both thumbnail and preview sizes |
| BLOB storage in SQLite may bloat the database | Set reasonable file size limit (e.g., 2MB max), compress if needed |
| Non-4:3 user images may look distorted | Pad with background color to maintain 4:3 ratio, never stretch |
| Adding custom tags may create duplicates or conflicts with canonical tags | Validate against canonical list, mark custom tags clearly, allow rename |
| User image may not match the pattern (wrong screenshot) | No validation possible without AI — trust user input, allow easy replacement |
| Image format compatibility | Support PNG, JPG, JPEG, BMP — most common formats, all handled by Qt's QPixmap |
| Last-saved miniature mismatch may have root cause in parser | Thorough audit of coordinate normalization between thumbnail and preview render paths |

---

## Changes Summary

All tasks to be completed in this roadmap.

### Files to Modify

| File | Tasks | Changes |
|------|-------|---------|
| `osu_gallery/_constants.py` | 1, 7 | Verify/update dimension constants; define image resize targets |
| `osu_gallery/parser/models.py` | 2 | Verify `combo_order` field on `HitObject` |
| `osu_gallery/parser/osu_file.py` | 2 | Verify combo order assignment |
| `osu_gallery/preview/thumbnail_renderer.py` | 1, 2, 6 | Fix render dimensions; update combo number visibility; align thumbnail/preview rendering |
| `osu_gallery/preview/image_resizer.py` | 7 | New: image resize utility with 4:3 aspect ratio padding |
| `osu_gallery/db/models.py` | 3, 5, 7 | Add `mapping_tags`, `user_image`, `user_image_filename` fields |
| `osu_gallery/db/database.py` | 5, 7 | Add `custom_mapping_tags` table; add user_image CRUD; migration |
| `osu_gallery/ui/import_dialog.py` | 3, 4, 7 | Replace tag input with checkbox grid; add image picker; save mapping_tags + user_image |
| `osu_gallery/ui/_preview_pane.py` | 1, 2, 3, 6, 7 | Fix preview dimensions; add mapping tags display; use user image when available |
| `osu_gallery/ui/thumbnail_widget.py` | 1, 2, 6, 7 | Fix thumbnail dimensions; improve combo number visibility; use user image when available |
| `osu_gallery/ui/main_window.py` | 5 | Add "Pattern Tags" button in top bar |
| `osu_gallery/ui/_pattern_tags_dialog.py` | 5 | New: Pattern Tags management dialog |

### New Test Files

| File | Tasks | Actual Tests |
|------|-------|-------------|
| `tests/test_roadmap4_sizes.py` | 1 | 8 |
| `tests/test_roadmap4_object_visibility.py` | 2 | 8 |
| `tests/test_roadmap4_mapping_tags_preview.py` | 3 | 9 |
| `tests/test_roadmap4_tag_picker.py` | 4 | 9 |
| `tests/test_roadmap4_pattern_tags_panel.py` | 5 | 11 |
| `tests/test_roadmap4_miniature_match.py` | 6 | 9 |
| `tests/test_roadmap4_user_images.py` | 7 | 17 |

---

## Definition of Done for This Roadmap

- [x] Task 1: Thumbnails rendered at 512x384, preview at 1024x768 (verified, not just constants updated)
- [x] Task 2: Numeric combo order labels visible and readable on both thumbnails and previews
- [x] Task 3: User input mapping tags displayed on pattern preview box below rendered image
- [x] Task 4: Import dialog uses checkmark-based multi-select tag picker instead of text input
- [x] Task 5: "Pattern Tags" button added next to import; panel shows all options with add/remove capability
- [x] Task 6: Last-saved pattern miniature matches its preview (no visual discrepancy)
- [x] Task 7: User image inputs saved alongside pattern; user image takes priority over auto-generated preview
- [x] Existing test suite still passes (301 tests)
- [x] New tests added for each task (73 tests)
- [x] `ruff` linting passes with no errors
- [x] Database migrations backward-compatible
- [x] Feature logged in `04_Implementation_Roadmap.md` §5
