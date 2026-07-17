# Decision Log: osu gallery

**Version:** 0.1 · **Status:** Living (append-only, never Frozen)

> Append-only. Never edit or delete a past entry — if a decision gets reversed, add a new entry that supersedes it and say so. This is what answers "why did we choose X" six months from now, for you and for any AI session that asks.

**When to add an entry:** any time `03_Technical_Architecture.md` changes, a significant architectural call in `02_System_Design.md` is made (module boundaries, data ownership, etc.), a new network-facing surface is added (`09_Security.md`), or an unresolved item from a Feasibility Check (`04_Implementation_Roadmap.md` §0) gets resolved. Small implementation details don't need one — this is for choices that would be annoying to silently re-litigate.

---

### ADR-001: Use Python as the primary language

| Field | Detail |
|---|---|
| Date | 2026-07-16 |
| Status | Accepted |
| Context | Need a language that's fast to develop in, has good GUI and database libraries, and aligns with the developer's expertise. |
| Why now | Stack decision blocks all downstream work (UI, parser, database). |
| Decision | Python 3.10+ |
| Alternatives considered | C# (native Windows, but steeper for this use case), Rust (performant but steep learning curve), JavaScript/TypeScript (Tauri adds complexity) |
| Tradeoffs | Python is slower than Rust/C# at runtime, but development speed and ecosystem outweigh this for a solo desktop tool. |
| **Future revisit trigger** | If performance becomes a bottleneck (e.g., rendering 1000+ thumbnails lagging), reconsider. |

---

### ADR-002: Use PySide6 (Qt) for the UI framework

| Field | Detail |
|---|---|
| Date | 2026-07-16 |
| Status | Accepted |
| Context | Need a desktop GUI framework that supports search/filter UIs, thumbnail grids, and alt+tab workflow. |
| Why now | UI framework choice determines all frontend code. |
| Decision | PySide6 (Qt for Python) |
| Alternatives considered | Tkinter (limited for modern UIs), Kivy (mobile-focused), Tauri + Svelte (more complex setup) |
| Tradeoffs | PySide6 is a heavier dependency than Tkinter, but essential for the search/filter UI we need. |
| **Future revisit trigger** | If we need web deployment or cross-platform mobile support. |

---

### ADR-006: Copy-to-clipboard via right-click context menu + Ctrl+C shortcut

| Field | Detail |
|---|---|
| Date | 2026-07-16 |
| Status | Accepted |
| Context | Need a way for users to copy pattern raw_code to the system clipboard for pasting into .osu files. Core loop requires this (F4, P0). |
| Why now | Phase 6 of the implementation roadmap. |
| Decision | Right-click context menu on thumbnails with "Copy Code" action, plus Ctrl+C keyboard shortcut. Toast notification confirms the copy. `QApplication.clipboard().setText()` for clipboard access. |
| Alternatives considered | Dedicated "Copy" button on each thumbnail (takes space), drag-to-copy ( unintuitive), toolbar copy button (requires selection state) |
| Tradeoffs | Context menu is slightly less discoverable than a button, but preserves thumbnail real estate and matches common desktop app patterns. Ctrl+C shortcut mirrors user expectations. |
| **Future revisit trigger** | If user testing shows context menu is confusing, add a visible copy button as an alternative. |

---

### ADR-003: Use SQLite with FTS5 for the database

| Field | Detail |
|---|---|
| Date | 2026-07-16 |
| Status | Accepted |
| Context | Need offline, single-file storage with fast tag-based search (Booru-style). |
| Why now | Database choice affects data model and search implementation. |
| Decision | SQLite + FTS5 (Full-Text Search) |
| Alternatives considered | PostgreSQL (overkill for single-user), MongoDB (needs server), plain JSON files (slow for search) |
| Tradeoffs | SQLite has no built-in migration system; we'll use `CREATE TABLE IF NOT EXISTS` and document schema changes. |
| **Future revisit trigger** | If concurrent multi-writer access becomes necessary (unlikely for single-user). |

---

### ADR-004: Build our own .osu parser (don't use OsuParsers C# library)

| Field | Detail |
|---|---|
| Date | 2026-07-16 |
| Status | Accepted |
| Context | Need to parse .osu hit objects into structured data for storage and preview. OsuParsers is C# and too comprehensive for our needs. |
| Why now | Parser is core to the import flow. |
| Decision | Build a minimal Python parser that extracts hit objects, timing, and basic metadata from .osu code blocks. |
| Alternatives considered | Use mrflashstudio/OsuParsers (C#, too heavy), use Awlexus/python-osu-parser (13 stars, may not cover all cases) |
| Tradeoffs | More initial development work, but we control the output format and can keep it minimal. |
| **Future revisit trigger** | If we need to parse storyboards, replays, or osu! database files. |

---

### ADR-005: Static thumbnails for MVP, animated preview as P1

| Field | Detail |
|---|---|
| Date | 2026-07-16 |
| Status | Accepted |
| Context | Need to decide whether to implement animated pattern previews from day one or defer. |
| Why now | Affects Phase 4-7 scope and testing strategy. |
| Decision | Static thumbnails for MVP (Phase 4-7), animated preview as P1 (future). |
| Alternatives considered | Animated from day one (more complex, slower to MVP) |
| Tradeoffs | Static thumbnails lose timing info, but get the core search/gallery working faster. Animation can be added later. |
| **Future revisit trigger** | If user testing shows static previews aren't useful for mappers. |
