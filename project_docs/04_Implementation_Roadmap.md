# Implementation Roadmap: osu gallery

> This doc is meant to change constantly — that's the point. It tracks *when*, not *what* or *how*. If a milestone requires a new module or a new dependency, that decision still belongs in 02 or 03 first; this just sequences the work.

**Last updated:** 2026-07-16
**Version:** 0.1 · **Status:** Draft / Review / Frozen / Deprecated *(this doc is rarely "Frozen" — it's meant to move)*

---

## 0. Feasibility Check (before a milestone or feature is approved)

Run this any time a new milestone or a non-trivial feature is added — not just at project start. It's the check against "the idea is bigger than what's actually buildable given what we already committed to." Five minutes here is cheaper than discovering the mismatch mid-implementation.

| Check | Answer |
|---|---|
| Does this fit inside `03_Technical_Architecture.md`'s existing stack, or does it require a new dependency/framework? | Yes — Python + PySide6 + SQLite, all already chosen |
| Does this fit the hardware ceiling in `03_Technical_Architecture.md` §2? | Yes — static thumbnails don't need GPU, SQLite is lightweight |
| Does this fit the offline/privacy constraints in `01_Product.md` §7? | Yes — fully offline, no network calls |
| How many new dependencies does this actually pull in (including transitive ones for anything non-trivial)? | PySide6 (heavy but essential), SQLite (built-in), ruff (dev only) |
| Is there anything in the request that was never specified anywhere in 01-03? | No — all covered |

**If more than one of these raises a flag:** the feature is likely oversized for a single milestone. Split it, or push the uncertain part to an explicit Open Question (§3) and build the certain part first.

## 1. Milestones

| Phase | Goal | Depends on | Tests | Status |
|---|---|---|---|---|
| 1 | Project setup + .osu parser | None | Unit tests for parser (parse valid/invalid code, extract hit objects, timing) | Done |
| 2 | SQLite database layer | Phase 1 | Unit tests for CRUD operations, tag many-to-many relationships | Done |
| 3 | Basic UI shell | Phase 2 | UI tests for main window, import dialog, empty state rendering | Done |
| 4 | Static thumbnail renderer | Phase 3 | Integration tests: parse → store → render thumbnail → display in grid | Done |
| 5 | Search bar + FTS5 | Phase 4 | Integration tests: tag indexing, multi-tag queries, real-time filter | Done |
| 6 | Copy-to-clipboard + toast | Phase 5 | End-to-end test: import → search → copy → verify clipboard | Done |
| 7 | Click-to-expand preview pane | Phase 6 | User testing: static preview displays correctly, metadata shown | Done |
| 8 | Polish + PyInstaller packaging | Phase 7 | Final regression test, packaging verification | Done |
| 9 | First run: logging, entry point, error handling | Phase 8 | Logging config test, graceful ImportError handling test, console + file handler verification | Done |

Keep phases scoped to something demoable — "basic UI," "database layer," "first AI integration" — not vague ("polish").

## 2. Extensibility Roadmap

Known-likely future additions, even if not building them now. Cross-reference the seams named in `02_System_Design.md` §6 — if something here doesn't have a seam yet, that's a signal to update 02 before building toward it.

| Planned addition | Impacts which module(s) | Design implication now |
|---|---|---|
| Animated pattern preview (P1) | Preview Renderer | Use QTimer for timing-based playback, QPropertyAnimation for smooth movement |
| osu! client integration (v2) | Import/Export adapter | Research Mapping Tools for integration patterns, build adapter module |
| Bulk import from existing maps | Import/Export, Pattern Parser | Add file dialog, scan .osu files in directory, deduplicate patterns |
| Custom tag categories | Pattern Storage, UI | Allow user-defined categories, extend Tag table with category field |
| Auto-tagging with LLM (future) | Search/Filter Engine | Add LLM backend, train classifier on pattern features |

## 3. Open Questions

Things you genuinely don't know yet. Name them here instead of letting an AI agent silently guess — and guess differently next session.

- [ ] Exact .osu file format spec for hit objects (timing, position, type) — need to reverse-engineer from existing maps or find official docs
- [ ] Best approach for static thumbnail rendering (QGraphicsScene vs. QPixmap vs. external renderer)
- [ ] How to handle slider curves in static previews (bezier approximation vs. point sampling)
- [ ] Optimal thumbnail size for performance (200x200? 300x300?)
- [ ] How to handle combo colors in previews (fixed colors per pattern? user-defined?)

## 4. Feature Specifications (for P0/P1 features only)

Small features just need a line in the Feature Log below. But before implementing anything sizable — anything touching multiple modules, adding a dependency, or changing a data model — turn its `01_Product.md` user story into a full spec **as its own file** under `project_docs/features/`, not inline here. Run the Feasibility Check (§0) before writing the spec, not after.

**Why a separate file, not a section of this doc:** this file accumulates milestones and log entries for the life of the project — over a few months it can grow into hundreds of lines. Loading all of that into a local model's context just to work on one feature wastes the budget you need for the actual code. A standalone `features/F001_name.md` lets you feed an agent exactly one feature's contract and nothing else.

Copy `project_docs/features/TEMPLATE.md` for each new P0/P1 feature, name it `F[n]_short-name.md`, and link it from the Feature Log row below.

## 5. Feature Log (append-only)

One line per feature added or changed, with which docs it touched. This becomes your change history and keeps 01-03 from silently drifting out of sync with what actually got built. For P0/P1 features, link the standalone spec file instead of re-describing it here. When a feature ships in a released version, also log it in the project's `CHANGELOG.md` (root, not `project_docs/`) — this log is the design-side history, the changelog is the release-side history.

| Date | Feature | Docs / spec touched | Notes |
|---|---|---|---|
| 2026-07-16 | Project initialized | 00-12 | All design docs filled, roadmap defined |
| 2026-07-16 | Phase 1: Project setup + .osu parser | 03, 04 | Parser handles circles/sliders/spinners, INI sections, colours; 26 tests passing |
| 2026-07-16 | Phase 2: SQLite database layer | 03, 04 | GalleryDatabase with CRUD for patterns/tags, PatternTag junction, CASCADE deletes; 26 tests passing |
| 2026-07-16 | Phase 3: Basic UI shell | 03, 04 | MainWindow with search/grid/empty state, ImportDialog with parse/save/tags, QFlowLayout; 11 UI tests passing |
| 2026-07-16 | Phase 4: Static thumbnail renderer | 03, 04 | Preview Renderer module with QPixmap rendering, _ThumbnailWidget with hover/click, database commit fixes, 10 integration tests passing |
| 2026-07-16 | Phase 5: Search bar + FTS5 | 02, 03, 04 | SearchEngine module with SQLite FTS5 full-text search, real-time debounced search bar, tag-based filtering, 17 search tests + 3 UI integration tests passing |
| 2026-07-16 | Phase 6: Copy-to-clipboard + toast | 02, 03, 04 | _clipboard.py utility, _toast_widget.py with fade animation, right-click context menu + Ctrl+C shortcut on thumbnails, pattern_copied signal, 18 tests passing |
| 2026-07-16 | Phase 7: Click-to-expand preview pane | 02, 03, 04 | _preview_pane.py with large rendered preview, metadata display (tags, BPM, combo colors), copy code button, QSplitter layout in MainWindow, 19 tests passing |
| 2026-07-16 | Phase 8: Polish + PyInstaller packaging | 03, 04 | Centralized constants module, PyInstaller spec file, build script, frozen-mode data directory, fixed slider regex, toast timer guard, specific exception handlers, packaging tests |
| 2026-07-16 | Phase 9: First run — logging, entry point, graceful errors | 03, 04, 08 | Configure logging (console + file handlers per architecture doc §8), add `[project.scripts]` console entry point, wrap app launch in try/except for friendly ImportError/Qt plugin error display, verify database directory creation on startup |
| 2026-07-16 | Phase 9: First run — logging, entry point, graceful errors | 03, 04, 08 | Configure logging (console + file handlers per architecture doc §8), add `[project.scripts]` console entry point, wrap app launch in try/except for friendly ImportError/Qt plugin error display, verify database directory creation on startup |
| 2026-07-17 | Roadmap 2: Bug fixes & feature additions (Tasks 1–8) | 04_Implementation_Roadmap_2 | Task 1: pattern delete from context menu (P1); Task 2: copy code copies only hit object lines, no `[HitObjects]` header (P1); Task 3: preview aspect ratio fixed to 4:3 (P1); Task 4: object count counts circles + sliders not raw hit objects (P1); Task 5: support patterns without `[HitObjects]` header via `objects_only` field (P1); Task 6: distinguish .osu metadata tags from software mapping tags with auto-detection (P1); Task 7: coding standards compliance audit + docstrings (P1); Task 8: tests updated to use real .osu file (P1); DB schema: `objects_only`, `circle_count`, `slider_count` columns added; new module `osu_gallery/tags/mapping_tags.py`; new test data `tests/test_data/dream_walk.osu` |
| 2026-07-17 | Roadmap 6: Custom tag import + grid layout overhaul | 04_Implementation_Roadmap_6 | Task 1: custom mapping tags appear in import dialog checkbox grid; Task 2: thumbnails sized for 4-per-row on 1920x1080, preview fills half window, all dimensions centralized in `_constants.py` |
| 2026-07-17 | Roadmap 6: Completed — 13 new tests, 428 total passing, ruff clean | 04_Implementation_Roadmap_6, _constants.py, ui/_preview_pane.py, tests/test_roadmap6_*.py | Updated PREVIEW_PANE_WIDTH (500→900), PREVIEW_PANE_MAX_WIDTH (620→1000), PREVIEW_HEIGHT (768→1152), SPLITTER_PREVIEW_DEFAULT_WIDTH (500→900); _preview_pane.py now imports PREVIEW_HEIGHT from constants; Task 1 was already implemented, added 6 tests; Task 2 code changes + 7 tests; fixed 8 stale test assertions for old constant values |
| 2026-07-18 | Bugfix round: BUG-116/119 (flow layout reflow), BUG-117 (preview load ordering + resize), BUG-118 (force-reload edited pattern), BUG-120 (FTS5 slash quoting), BUG-113 (Resolved) | 13_Bugfix_and_Refactor_Backlog.md, ui/main_window.py, ui/_preview_pane.py, ui/_flow_layout.py, search/engine.py, tests/test_search.py, tests/test_edit_and_layout.py | Dropped `columns=4` from QFlowLayout (natural wrap); reordered splitter setSizes before load_pattern; added resizeEvent override to _PreviewPane; added `force` param to load_pattern + force-reload in _on_pattern_edited; quoted FTS5 terms with escaped double-quotes; added 5 new tests (452 total passing) |
