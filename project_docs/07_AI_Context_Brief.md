# AI Context Brief: osu gallery

**Version:** 0.1 · **Status:** Draft / Review / Frozen / Deprecated *(regenerate whenever this drifts from 01-03, 09, 10)*

> This is the whole seed context in under a page. Regenerate it by hand whenever 01-03 (or 09/10) change meaningfully — it should never drift far from the source docs. Paste this at the top of a fresh session, especially on a smaller local model where full docs won't fit the context window.

```
PROJECT: osu gallery
PURPOSE: A visual reference library for osu! beatmap objects (patterns, sliders, shapes, object groups) with search, categorization, and quick alt+tab access for mappers.

CORE LOOP: User edits in osu! editor → alt+tab to gallery app → types search term → clicks thumbnail → views large preview → copies code or references → alt+tab back to editor

INTERFACE: Desktop GUI (PySide6) — Main Gallery View (search bar + thumbnail grid), Pattern Preview Pane (large static preview + copy button), Import Dialog (paste .osu code block)

STACK (frozen — do not deviate without asking):
  Language: Python 3.10+
  UI/GUI framework: PySide6 (Qt for Python)
  Backend: None (stdlib + PySide6)
  AI/LLM backend: N/A (MVP)
  Storage: SQLite + FTS5

MODULE BOUNDARIES (see 02_System_Design.md §1 for full detail):
  UI:        Display gallery, search bar, thumbnails, preview pane — NEVER store data or parse .osu
  Storage:   Save/load patterns, manage tags/categories, local database with search indexing — NEVER render visuals
  Parser:    Parse .osu code blocks into structured object data, translate to hit objects — NEVER store or render
  Preview:   Render visual previews of patterns (read-only, uses parsed coordinates) — NEVER edit patterns or parse .osu
  Search:    Query database, apply multiple filter criteria, rank results — NEVER display results or store patterns

DATA: Patterns (objects, timing, tags) stored in SQLite, must survive reinstall. Thumbnails cached locally, rebuildable from patterns.

HARDWARE CEILING: Existing hardware only, no special GPU requirements beyond basic rendering (static thumbnails).

SECURITY POSTURE (see 09_Security.md for full detail):
  Network exposure: None (fully offline, no listener)
  Secrets storage: None (no API keys, no authentication)

NON-NEGOTIABLE CONSTRAINTS:
  - Fully offline: nothing in the core loop requires network access
  - Single-user only: no multi-user or cloud sync
  - Manual input only in MVP: no osu! client communication until v2

EXPLICIT NON-GOALS (do not build these):
  - Not a fully online website application
  - Not a beatmap editor (visual preview only, no interactive editing)
  - Not a map discovery tool (no osu! API scraping)
  - Not a real-time collaboration feature

AI RULES:
  - No new dependencies without asking (see 03_Technical_Architecture.md §1)
  - No new modules/screens without asking (see 02_System_Design.md)
  - Architectural changes get a Decision Log entry first (06_Decision_Log.md)
  - Never hardcode secrets; treat untrusted/LLM output as untrusted before executing it (09_Security.md)
  - New logic ships with a test in the same change (10_Testing_Strategy.md)
  - Full rules: 05_AI_Collaboration_Rules.md

CURRENT TASK: Phase 8 complete (polish + PyInstaller packaging with 140 passing tests) — MVP feature complete
```

## Mandatory pre-flight check

This travels with the brief so it applies even on tasks that don't load `05_AI_Collaboration_Rules.md`. Before generating any code, answer these in a short checklist — don't skip straight to code:

1. **Target module:** which boundary from `02_System_Design.md` §1 am I operating inside, and what is it explicitly forbidden from doing?
2. **Dependency audit:** does this introduce any import/library not already listed in `03_Technical_Architecture.md` §1?
3. **State footprint:** does this touch existing data structures, or is it isolated to this feature's view/logic?
4. **Trust boundary:** does this touch untrusted input (network, file, user, LLM output) — and if so, is it validated before use, per `09_Security.md`?
5. **Test coverage:** does this land in a layer `10_Testing_Strategy.md` §2 requires coverage for — and if so, is a test included?

If any answer is uncertain, say so and wait — don't guess and proceed.
