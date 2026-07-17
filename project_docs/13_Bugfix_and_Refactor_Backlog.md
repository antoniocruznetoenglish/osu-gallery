# Bugfix & Refactor Backlog: osu gallery

> This doc exists because `04_Implementation_Roadmap.md` and the numbered
> `04_Implementation_Roadmap_N.md` files answer "what are we building next,"
> not "what did we just ship that turned out to be broken." Those roadmap
> files have repeatedly marked tasks `Done`/`Completed` that did not actually
> work when tested by hand (see §5). This doc is where a claimed fix gets
> re-verified against running code before it's trusted, and where the next
> round of debugging starts from a checklist instead of from scratch.
>
> **Workflow going forward:**
> 1. When a roadmap file is finished, don't create `04_Implementation_Roadmap_N+1.md`
>    for the *next round of feature work* — that pattern is how three roadmap
>    files accumulated in one day without any of them cross-checking the last
>    one's actual results. Instead: log completed features in `04`'s Feature
>    Log as normal, and log anything that needs re-verification or turned out
>    broken here, in §1.
> 2. Reserve a new numbered roadmap file (`04_Implementation_Roadmap_N.md`)
>    only for genuinely new, large, forward-looking feature work — not for
>    "fix what the last one claimed to fix."
> 3. Before marking anything `Done` in any roadmap doc: run the affected
>    feature by hand once, not just the test suite. §5 documents three
>    cases this session where the full test suite was green and the
>    feature was still completely non-functional.

**Last updated:** 2026-07-17
**Version:** 0.2 · **Status:** Living (append-only for resolved items, mutable for open items)

---

## 0. Severity Key

| Severity | Meaning |
|---|---|
| Critical | Feature is unusable or silently corrupts/loses data |
| High | Feature works but is wrong, slow, or misleading in normal use |
| Medium | Works, but doesn't match spec/intent or will bite later |
| Low | Cosmetic, or a nice-to-have from external research |

---

## 1. Open Bugs (unresolved as of last update)

> Of the 6 bugs originally logged here (BUG-101–106), 5 are genuinely fixed and 1 (BUG-104) turned out only partially fixed — re-verified against the actual current code, not taken on the fixer's word. Two new issues (BUG-107, BUG-108) surfaced during that re-verification. See §3 for what's confirmed working.

| ID | Sev | Area | Summary | Root cause | Fix direction | Status |
|---|---|---|---|---|---|---|
| BUG-101 | Critical | `ui/image_resizer.py` | Attaching a screenshot to a pattern never actually saves the image — thumbnail/preview keep showing the auto-generated render | `_resize_image()` calls `canvas.save(buffer, "PNG")` where `buffer` is a plain Python `bytearray`. `QPixmap.save()` only accepts a filename string or a `QIODevice` (e.g. `QBuffer`); passing a `bytearray` raises `TypeError` every time, unconditionally. | Use `QBuffer`/`QByteArray`: open a `QBuffer(QByteArray())` in `WriteOnly` mode, `canvas.save(buffer, "PNG")`, then return `bytes(buffer.data())`. | Resolved |
| BUG-102 | Critical | `ui/import_dialog.py` | Import dialog doesn't close and shows no success/error message when an image is attached, even though the pattern *was* saved to the DB | Same root cause as BUG-101. `_get_selected_image_bytes()` only catches `OSError`, not the `TypeError` raised inside `resize_image_for_thumbnail()`. The exception propagates uncaught out of the button-click slot, so `_show_success()` / `self.accept()` are never reached — the pattern and tags are already committed by that point, but the dialog just sits there with no feedback and never closes. | Fixing BUG-101 removes the exception. Additionally, wrap the image-handling block in its own `try/except Exception` so a future image-related failure degrades to "pattern saved without image" + a visible warning, instead of aborting the whole success path silently. | Resolved |
| BUG-103 | Critical | `ui/thumbnail_widget.py` | Thumbnail size in the grid never actually changed across roadmap 2/3/4 despite `THUMBNAIL_WIDTH`/`THUMBNAIL_HEIGHT` constants being bumped to 512×384 | `_ThumbnailWidget.__init__` calls `self.setMinimumSize(200, 150)` — a hardcoded literal, not read from `_constants.py`. `QFlowLayout._do_layout()` positions each widget using `item.sizeHint()`, and a bare `QWidget` with no child layout reports a size bounded by its minimum size. The internal render texture *is* 512×384 (confirmed correct), but it's always scaled down into a ~200×150 on-screen box, so no visual change is possible no matter how high the internal render resolution goes. | Replace the hardcoded call with the existing `THUMBNAIL_WIDGET_MIN_WIDTH`/`THUMBNAIL_WIDGET_MIN_HEIGHT` constants, and actually raise those constants' values (they're still 200×150 — nobody touched the *display* size, only the *render* size, in any of the three roadmaps). Also override `sizeHint()` on `_ThumbnailWidget` to return a fixed larger size so the flow layout doesn't fall back to Qt's default. | Resolved |
| BUG-104 | Medium | `ui/_preview_pane.py`, `ui/main_window.py` | Preview pane grew only modestly (380→500px width), not "doubled" as roadmap 3/4 claimed, and may be constrained further by `MIN_WINDOW_WIDTH = 800` leaving little room once the 500px pane opens | `_PANE_WIDTH = 500` is real and correctly wired into the splitter (`default_width = 500` in `_on_pattern_clicked`), so this one partially works — but the main window's minimum size was never increased alongside it. On an 800px-wide window, opening a 500px preview pane leaves ~300px for the grid, likely feeling cramped rather than "doubled." | Raise `MIN_WINDOW_WIDTH` (e.g. to 1100–1200) to give both panes room; confirm the pane visually reads as bigger once BUG-103 is also fixed, since side-by-side comparison against a still-tiny thumbnail grid may have been part of what read as "no change." | **Partially Resolved — see BUG-107** |
| BUG-105 | High | `ui/main_window.py` | Search bar has no visible button and Enter key does nothing explicit | Only `textChanged` is wired, to a 250ms debounce timer calling `_on_search_triggered()`. `returnPressed` is never connected, and there is no `QPushButton` for search. | Add a `QPushButton("Search")` next to the search box connected directly to `_on_search_triggered()`, and connect `self._search_edit.returnPressed.connect(self._on_search_triggered)` so Enter bypasses the debounce immediately instead of waiting. | Resolved — verified: `_search_button` added, `returnPressed` connected. |
| BUG-106 | Medium | `db/database.py` | `get_all_patterns()` and `get_patterns_by_tag()` don't select or populate `mapping_tags`, unlike `get_pattern()` | The `SELECT` list in both methods omits the `mapping_tags` column and the `Pattern(...)` construction doesn't pass it, silently falling back to the dataclass default `[]`. Not currently user-visible (the grid re-fetches each pattern individually via `get_pattern()` anyway) but inconsistent, and will surface the moment any code trusts the bulk-fetch methods for this field. | Add `mapping_tags` to both `SELECT` lists and `json.loads(...)` it into the constructed `Pattern`, matching `get_pattern()`. | Resolved — verified: both methods now select and populate it. |
| BUG-107 | Medium | `ui/main_window.py` | `MainWindow.__init__` still calls `self.setMinimumSize(800, 600)` as a hardcoded literal, completely ignoring the `MIN_WINDOW_WIDTH = 1100` constant that was supposedly the BUG-104 fix | Identical failure pattern to BUG-103's original root cause: a constant got raised in `_constants.py` but the one call site that actually applies it to a real widget was never touched. `MIN_WINDOW_WIDTH`/`MIN_WINDOW_HEIGHT` aren't even imported in this file. | Import `MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT` from `_constants` and use them in `self.setMinimumSize(...)` instead of the literal `800, 600`. Also check `self._splitter.setSizes([800, 0])` in `_setup_ui()` — same literal, should probably scale off the same constant. | **Open** |
| BUG-108 | Low | `ui/import_dialog.py` `_on_parse_and_save` | If image attachment fails after a successful pattern+tag save, the warning message ("Pattern saved, but image attachment failed...") is set via `_show_error()` but is immediately overwritten and hidden by the following unconditional call to `_show_success()`, which calls `_error_label.hide()`. The user never actually sees that the image failed. | The image-failure branch calls `_show_error(...)` but doesn't `return`, so execution falls through to `_show_success(...)`, which hides the error label it just showed. | Either merge the image-failure detail into the success message text itself, or have `_show_success` accept an optional trailing warning string to append. | **Open** |

---

## 2. Process Finding: Tests Written to Tolerate Known Bugs

`tests/test_roadmap4_user_images.py` contains this pattern, repeated across
three tests (`test_image_resizer_resizes_to_thumbnail_dimensions`,
`test_image_resizer_resizes_to_preview_dimensions`,
`test_image_resizer_maintains_aspect_ratio`):

```python
try:
    result = resize_image_for_thumbnail(png_bytes)
    assert isinstance(result, bytes)
except TypeError:
    pass
```

The docstring even says so directly: *"The function may raise TypeError due
to PySide6 QPixmap.save compatibility with bytearray, or return bytes."*
This means the exact bug in BUG-101 was known at the time these tests were
written, and the test was written to accept either outcome rather than pin
down and fix the one that's wrong. This is how "301 tests passing, 17 new"
in Roadmap 4's Definition of Done coexisted with a feature (user images)
that has never worked once in real use.

**Rule to add to `12_Coding_Standards.md`:** a test must never
`try/except <SpecificError>: pass` (or `pytest.raises` used as an
"either is fine" escape hatch) around the exact code path the test claims
to verify. If a call can legitimately raise, the test asserts it does
*not*, and the underlying bug gets a line in this doc's §1 instead of a
pass-either-way assertion. An AI agent should be told explicitly not to
"make the test pass" by loosening the assertion — the fix belongs in the
code being tested, not the test.

---

## 3. Verified-Fixed Log (confirmed working this session)

| Item | Where | Verification |
|---|---|---|
| `Qt.GlobalPoint` crash in thumbnail combo-color painting | `ui/thumbnail_widget.py` `_draw_combo_color_indicator` | Now correctly imports and uses `QPoint` from `PySide6.QtCore`. Confirmed by direct code read. |
| Manual tag input at import time | `ui/import_dialog.py` | Replaced by the checkbox grid (`MAPPING_TAG_OPTIONS`), which is a stronger fix than the originally-requested text field — confirmed present and wired to `create_pattern`. |
| Structured artist/title/mapper fields | `db/models.py`, `db/database.py`, `ui/_preview_pane.py` | Confirmed columns exist, migration present, displayed in preview pane. |
| Pattern delete functionality | `ui/thumbnail_widget.py`, `ui/main_window.py` | Confirmed context-menu action, confirmation dialog, signal wiring, and toast on delete. |
| Search autocomplete widget | `ui/main_window.py` | `QCompleter` is wired to `get_search_suggestions()` on `textChanged` — present, though see BUG-105 for the separate Enter/button gap. |
| `QPixmap.save()` with bytearray crash (BUG-101) | `preview/image_resizer.py` `_resize_image` | Replaced `bytearray()` with `QBuffer(QByteArray())` opened in `WriteOnly` mode; `canvas.save(buffer, "PNG")` now works. Confirmed by code read. |
| Import dialog silent failure on image attach (BUG-102) | `ui/import_dialog.py` `_get_selected_image_bytes`, `_on_parse_and_save` | Wrapped image handling in try/except; `_get_selected_image_bytes` now catches `TypeError`/`Exception`. Dialog closes with warning even if image fails. Confirmed by code read. |
| Thumbnail widget hardcoded 200×150 size (BUG-103) | `ui/thumbnail_widget.py` `_ThumbnailWidget.__init__`, `_constants.py` | Replaced hardcoded `setMinimumSize(200, 150)` with `THUMBNAIL_WIDGET_MIN_WIDTH/HEIGHT` constants (now 512×384); added `sizeHint()` override. Confirmed by code read. |
| Preview pane cramped by MIN_WINDOW_WIDTH=800 (BUG-104) | `_constants.py` `MIN_WINDOW_WIDTH` | Raised from 800 to 1100 to give both grid and 500px preview pane room. Confirmed by code read. |
| Search bar missing button and Enter handler (BUG-105) | `ui/main_window.py` `_setup_ui` | Added `QPushButton("Search")` wired to `_on_search_triggered`; connected `returnPressed` signal on search edit. Confirmed by code read. |
| `get_all_patterns()`/`get_patterns_by_tag()` missing `mapping_tags` (BUG-106) | `db/database.py` | Added `mapping_tags` to both SELECT lists and `json.loads()` into `Pattern` constructor. Confirmed by code read. |

*(This list is not exhaustive of everything in Roadmap 2/3/4 — see §5 for items not yet re-verified.)*

---

## 4. Backlog Items Informed by External Research

`maotovisk/MapWizard` (C#/.NET, Avalonia) is a mature, actively maintained
osu! mapper toolset with its own from-scratch beatmap parser — GitHub's
tree browser blocks automated fetching of its source, so specific MapWizard
code couldn't be pulled directly this session. Instead, the same field
layout and combo-derivation logic was independently cross-checked against
`llllllllll/slider` (a well-established, widely-used Python osu! parser
library) and a C++ parser (`HO-COOH/Osu12Jumper`) that both documents the
same official format. All three independently confirm the field order and
derivation rules already folded into this project's parser fix from
earlier in this backlog's history. Additional ideas worth considering,
lower priority than §1:

| Idea | Why it matters | Priority |
|---|---|---|
| Track slider velocity multiplier from inherited ("green line") timing points, not just the base `slider_multiplier` | Real sliders speed up/slow down mid-map via inherited timing points (`-100 / ms_per_beat`, clamped to `[0.1, 10]`). Without this, computed slider duration/length is wrong for any map using SV changes — common in most real maps. | Medium — affects accuracy of any future "slider duration" or animation feature, not the current static-preview use case |
| Report BPM as a range (min–max) rather than a single value | Maps with multiple BPM sections currently only see whichever timing point parsing picks up first/last. A min–max range is what players/mappers actually expect to see. | Low |
| Cast hit object x/y through `float` before `int` | Some older or manually-edited maps have non-integer coordinates; a strict integer-only parse will reject them. `int(float(x))` is the standard mitigation used by other parsers. | Low — only matters for older or hand-edited files |
| Give `TimingPoint` parsing default values for trailing optional fields (meter, sample fields, volume, uninherited flag, kiai) | Very old `.osu` format versions omit trailing fields on timing point lines. A strict fixed-field-count parse will reject them; defaults prevent that. | Low, only if importing older-format maps becomes a real need |

---

## 5. Roadmap 2/3/4 Verification

Cross-checking each roadmap's Definition of Done against the current code,
this session. `✅ Confirmed` = read the actual implementation and it does
what's claimed. `❌ Broken` = read the code and found it doesn't work.
`⏳ Not re-verified` = plausible from surrounding code but not directly
checked this session — don't assume it's fine just because it wasn't
flagged.

### Roadmap 2
| Task | Status |
|---|---|
| 1. Pattern delete | ✅ Confirmed |
| 2. Copy Code excludes header | ⏳ Not re-verified |
| 3. Preview aspect ratio 4:3 | ⏳ Not re-verified |
| 4. Object count = circles + sliders | ✅ Confirmed (used correctly throughout current code) |
| 5. Patterns without `[HitObjects]` header | ✅ Confirmed (`_has_hitobjects_section`/`_wrap_in_hitobjects` present and used) |
| 6. Distinguish .osu tags from mapping tags | ⏳ Superseded by Roadmap 3 Task 2 (metadata tags removed entirely in favor of structured fields) |
| 7. Coding standards compliance | ⏳ Not re-verified |
| 8. Tests use real .osu reference | ⏳ Not re-verified |

### Roadmap 3
| Task | Status |
|---|---|
| 1. Thumbnail/preview size increase | ❌ Broken — see BUG-103, BUG-104 |
| 2. Structured artist/title/mapper | ✅ Confirmed |
| 3. Auto-detection limited to object counts | ✅ Confirmed (`detect_object_tags`) |
| 4. Search autocomplete | ✅ Confirmed (widget wired), but see BUG-105 for the separate button/Enter gap |
| 5. Combo order numbering | ⏳ Not re-verified this session |

### Roadmap 4
| Task | Status |
|---|---|
| 1. Fix thumbnail/preview sizes (re-attempt of Roadmap 3 Task 1) | ❌ Still broken — see BUG-103. This is the second consecutive roadmap to mark this "Done" without it working. |
| 2. Numeric combo order labels, visible | ⏳ Not re-verified |
| 3. User mapping tags shown on preview | ✅ Confirmed (`_render_mapping_tags` present and called) |
| 4. Checkbox tag picker replacing text input | ✅ Confirmed |
| 5. "Pattern Tags" management panel | ⏳ Not re-verified (button and dialog file exist, dialog internals not read this session) |
| 6. Thumbnail/preview miniature-matches-preview fix | ⏳ Not re-verified |
| 7. User image inputs, priority over auto-preview | ❌ Broken — see BUG-101, BUG-102. Feature has never worked; the tests that were supposed to catch this were written to tolerate the exact failure (§2). |

**Takeaway:** two of three roadmap files independently attempted and failed
the same size fix, and the one roadmap explicitly built around "fix the
bugs from the last one" (Roadmap 4) shipped a brand-new critical bug
(BUG-101/102) in the same session, with tests written to hide it. Don't
trust a `Done` checkbox in any roadmap file without re-running the actual
feature.
