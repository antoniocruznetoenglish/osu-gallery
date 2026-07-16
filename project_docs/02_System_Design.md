# System Design: osu gallery

> Describes the software like Lego blocks — modules, responsibilities, and how data moves between them. **No specific frameworks or libraries here** — that's 03_Technical_Architecture.md. If a sentence names a technology, it belongs in that doc instead. This separation is what stops an AI coding agent from treating a tech-stack swap as equivalent to a refactor.

**Last updated:** 2026-07-16
**Version:** 0.1 · **Status:** Draft / Review / Frozen / Deprecated
**Edit cadence:** Should be stable. Editing this often = you're mid-refactor; do it deliberately, not accidentally via prompting.

---

## 0. Architectural Principles

A handful of short, durable rules — not architecture itself, the philosophy the architecture implements. Keep this to 3-6 one-liners; if a principle needs a paragraph to explain, it's not a principle, it belongs in a module's responsibilities below.

- Offline-first: nothing in the core loop requires network access.
- Modular design: core gallery logic separated from any future osu! client integration.
- Manual input only in MVP: no automatic client communication until v2.
- Search-first: database and indexing designed from day one to support fast, multi-criteria queries.

## 1. Module Map

List every major module/component. Each gets a one-line responsibility — think directory listing, not implementation.

```
osu gallery
├── UI                    → display gallery, search bar, thumbnails, preview pane
├── Pattern Storage       → save/load patterns, manage tags/categories, local database with search indexing
├── Pattern Parser (.osu) → parse .osu code blocks into structured object data, translate to visual coordinates
├── Preview Renderer      → render visual previews of patterns (read-only, uses parsed coordinates)
├── Search/Filter Engine  → query the database, apply multiple filter criteria, rank results
└── Import/Export         → handle manual paste input, copy to clipboard, future osu! client integration
```

### Module Detail

Copy this block per module.

**Module: UI**
| Field | Value |
|---|---|
| Responsibilities | Display main gallery view, search bar, thumbnail grid, preview pane, import dialog |
| Explicitly NOT responsible for | Data persistence, pattern parsing, business logic |
| Inputs | User clicks, search queries, import data |
| Outputs | Rendered views, user actions forwarded to other modules |
| Depends on (other modules) | Pattern Storage (load patterns), Search/Filter Engine (query results), Preview Renderer (display) |

**Module: Pattern Storage**
| Field | Value |
|---|---|
| Responsibilities | Save/load patterns, manage tags/categories, maintain local database with search indexing |
| Explicitly NOT responsible for | Parsing .osu format, rendering visuals |
| Inputs | Parsed pattern data from Parser, user tag edits |
| Outputs | Pattern objects, filtered result sets |
| Depends on (other modules) | None (foundation layer) |

**Module: Pattern Parser (.osu)**
| Field | Value |
|---|---|
| Responsibilities | Parse .osu code blocks into structured object data, translate hit objects to visual coordinates |
| Explicitly NOT responsible for | Storing patterns, rendering visuals |
| Inputs | Raw .osu code strings (from paste or file import) |
| Outputs | Structured pattern objects with timing, position, type metadata |
| Depends on (other modules) | None (stateless utility) |

**Module: Preview Renderer**
| Field | Value |
|---|---|
| Responsibilities | Render visual previews of patterns (read-only), display timing and object count |
| Explicitly NOT responsible for | Editing patterns, parsing .osu format |
| Inputs | Structured pattern objects from Parser |
| Outputs | Rendered visual preview image |
| Depends on (other modules) | Pattern Parser (structured data) |

**Module: Search/Filter Engine**
| Field | Value |
|---|---|
| Responsibilities | Query the database, apply multiple filter criteria (slider type, circle count, timing, tags), rank results |
| Explicitly NOT responsible for | Displaying results, storing patterns |
| Inputs | Search query string, filter criteria, tag list |
| Outputs | Ranked list of matching pattern objects |
| Depends on (other modules) | Pattern Storage (database queries) |

**Module: Import/Export**
| Field | Value |
|---|---|
| Responsibilities | Handle manual paste input, copy to clipboard, validate .osu code blocks |
| Explicitly NOT responsible for | Parsing internals, rendering |
| Inputs | Raw text from user paste, clipboard data |
| Outputs | Validated code blocks forwarded to Parser, copied strings |
| Depends on (other modules) | Pattern Parser (validation), UI (clipboard feedback) |

## 2. Users & Interaction Plan

| Question | Answer |
|---|---|
| Interface type | Desktop GUI (alt+tab workflow) |
| Primary interaction pattern | Long-running session (keeps open while mapping) |
| Who else besides you touches this? | Just you (single-user) |

**Screens / views** (if GUI or web) — one line each, purpose only, no layout design yet:

1. **Main Gallery View** → search bar at top, thumbnail grid below, click to expand
2. **Pattern Preview Pane** → large visual preview, copy code button, tag/category info
3. **Import Dialog** → paste .osu code block or drag-drop file, parse and save

**UI state coverage** — for each key view, what does the user see when: loading / empty / error / success?

| State | Main Gallery | Preview Pane |
|---|---|---|
| Loading | Spinner or skeleton | Loading indicator |
| Empty | "No patterns yet — import some!" with prominent import button | N/A |
| Error | Toast notification, retry button | Error message |
| Success | Thumbnails populated | Full preview rendered |

## 3. Data Flow (Happy Path)

Numbered steps from entry point to result. This should stay true even as internals get rewritten underneath it.

1. User launches app → main gallery view loads, patterns loaded from local database
2. User types in search bar → search engine queries database with filters → thumbnail grid updates in real-time
3. User clicks a thumbnail → preview pane renders the pattern visually, displays metadata (tags, timing, object count)
4. User clicks "Copy Code" → object code copied to clipboard, toast notification confirms
5. User alt+tab back to osu! editor → pastes code into .osu file

**Alternative flow (no patterns yet):**
1. User launches app → empty gallery view shows "No patterns yet" with prominent "Import Pattern" button
2. User clicks import → paste dialog opens
3. User pastes .osu code block → parser validates and saves to database
4. App returns to gallery → thumbnail appears, ready for search

## 4. Data Design

| Data type | Conceptual store (not the specific DB yet) | Owner module | Rebuild or preserve? |
|---|---|---|---|
| Patterns (objects, timing, tags) | Local database (SQLite) | Pattern Storage | Must survive reinstall |
| User preferences (UI state, filter defaults) | Config file | Pattern Storage | Must survive reinstall |
| Thumbnail cache | Local cache | UI | Rebuildable from patterns |

**Source of truth:** which store is authoritative if others disagree?

The local database is authoritative for all pattern data.

## 5. AI / LLM Role (conceptual)

*Specific backends (Ollama, llama.cpp, OpenAI-compatible) go in 03. This is about the role, not the tool.*

| Question | Answer |
|---|---|
| Is an LLM core to the core loop, or an enhancement? | Not used in MVP |
| Minimum viable experience with zero LLM available | Full gallery search and reference workflow |
| What's it actually used for | N/A (future: could power smart suggestions or auto-tagging) |

## 6. Extensibility Seams

Where are the plug-in points you already know you'll need? Naming these now stops an agent from hardcoding assumptions that block extension later (e.g., "new data source exporters," "new LLM backend," "new UI screen").

- **osu! Client Integration Adapter** → future module to auto-import patterns from osu! editor (separated from manual import). Research existing solutions like Mapping Tools for integration patterns.
- **Tag/Category Plugin System** → allow users to define custom categories or import tag sets
- **Export Format Plugin** → support multiple output formats (not just raw .osu code)

## 7. Non-Functional Requirements

| Concern | Target |
|---|---|
| Performance (latency/throughput) | Search results under 100ms, app load under 2 seconds |
| Concurrency | Single-user only |
| Offline requirement | Fully offline |
| Error handling philosophy | Fail loud and fast with clear error messages |
| Security / secrets handling | N/A (no network, no secrets) |
| Observability / health checks | Basic logging for debugging |
| Accessibility / localization | N/A for MVP |
