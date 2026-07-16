# Technical Architecture: osu gallery

> Only here do we name actual technologies. Everything in this doc is a **frozen decision** an AI coding agent should treat as fixed — not a suggestion it's free to substitute. If you want to change something here, change it here first, deliberately, then implement.

**Last updated:** 2026-07-16
**Version:** 0.1
**Edit cadence:** Should be stable. This is the "constitution" your coding agent reads before every session.
**Design Phase (this doc's Status field):** Exploring / **Frozen** / Deprecated *(while Exploring, anything below is a hypothesis, not law. Once you flip this to Frozen, an agent should treat every row as fixed — and any proposed change gets logged in `06_Decision_Log.md` first, not silently made mid-session.)*

**Leave any section below blank until the project actually needs it.** A tiny desktop app doesn't need a CI row or a migration strategy on day one — filling them in prematurely just invents information you'll have to un-invent later. Blank is a valid, honest state; a guessed answer isn't.

---

## 1. Stack

| Layer | Choice | Why | Alternatives considered |
|---|---|---|---|
| Language | Python 3.10+ | Most trained on, large ecosystem, fast to develop | C# (native Windows), Rust (performant but steep) |
| UI/GUI framework | PySide6 (Qt for Python) | Feature-rich, native desktop, excellent for search/filter UIs with thumbnails | Tkinter (limited), Tauri (more complex) |
| Backend framework | None (stdlib + PySide6) | Desktop app, no web server needed | FastAPI, Flask |
| AI/LLM backend library | N/A (MVP) | Not used in MVP | Ollama, llama.cpp |
| Vector store | N/A (MVP) | Not used in MVP | ChromaDB, FAISS |
| Structured storage | SQLite + FTS5 | Offline, single-file, excellent for tag-based full-text search | PostgreSQL, MongoDB |
| Config format | JSON | Simple, human-readable, Python-native | YAML, TOML |
| Testing framework | pytest | Industry standard, good plugin ecosystem | unittest, nose |
| Linting/formatting | ruff | Fast, modern, replaces multiple tools | black + flake8 + isort |
| Packaging/build tool | PyInstaller | Standalone executable for Windows | cx_Freeze, Nuitka |
| CI | N/A (MVP) | Solo local tool, no CI needed | GitHub Actions, GitLab CI |

**Dependency philosophy:** minimize surface area (prefer stdlib/fewer deps) vs. accept heavier deps for speed of development — accept heavier deps for PySide6 (essential for UI) and SQLite (built-in), minimize elsewhere.

Keep each "Why" cell to one line. If the reasoning is longer than that, or alternatives were seriously weighed, it belongs in `06_Decision_Log.md` — link the decision number here instead of re-explaining it (e.g., "See ADR-003").


## 2. LLM Backend Configuration

| Question | Answer |
|---|---|
| Backend priority order | N/A (MVP) |
| Local model constraints | N/A (MVP) |
| Target hardware tier(s) | N/A (MVP) |

## 3. Component Interfaces & Contracts

The strict boundaries between parts of the app — internal API routes, IPC channels, public functions each module exposes.

**Example:**
- `POST /api/generate` → Input: `{ prompt: string, temperature: float }` → Output: streamed tokens
- File system access: which directories can the app read/write?

### 3a. Cross-Boundary IPC Contract (if desktop GUI)

If the UI runs in a separate process or context from the backend (Electron, Tauri, PyQt with a QML/web frontend, etc.), spell this out explicitly — local models routinely hallucinate the frontend calling the database or filesystem directly, skipping the boundary entirely.

| Field | Detail |
|---|---|
| IPC mechanism | PySide6 signals/slots (single-process, no IPC needed) |
| Serialization law | N/A — single-process Python app |
| Firewall rule | N/A — single-process Python app |

## 4. Data Models

Concrete schemas — this is where 02's "conceptual store" entries get an actual shape.

```
Pattern {
  id: integer (primary key)
  created_at: datetime
  updated_at: datetime
  raw_code: text (the original .osu code block)
  object_count: integer
  timing_bpm: float
  tag_ids: integer[] (many-to-many via PatternTag junction)
}

Tag {
  id: integer (primary key)
  name: text (unique)
  category: text (e.g., "slider", "circle_pattern", "timing")
}

PatternTag {
  pattern_id: integer (foreign key → Pattern)
  tag_id: integer (foreign key → Tag)
}

UserPreferences {
  key: text (primary key)
  value: text (JSON)
}
```

**Migration strategy:** SQLite has no built-in migration system. For MVP, use `CREATE TABLE IF NOT EXISTS` and add columns with `ALTER TABLE` as needed. Document schema changes in CHANGELOG.md. For v2+, consider a migration library like `sqlite-migrate` or `alembic`.

## 5. External APIs / Integrations

| Service | Auth method | Rate limits | Fallback / offline mode |
|---|---|---|---|
| N/A (MVP) | | | |

## 6. Deployment & Packaging

| Question | Answer |
|---|---|
| Where does this run? | Local machine only |
| Target OS(es) | Windows 10/11 (primary), Linux (future) |
| Packaging | Standalone executable via PyInstaller |
| Update mechanism | Manual download (v1), auto-update (future) |
| Supported OS/runtime versions | Python 3.10+, Windows 10+ |

## 7. Testing Strategy

Summary only — the concrete coverage targets and framework choices live in `10_Testing_Strategy.md`. This row set exists so a reader of this doc alone still sees the shape.

| Layer | Coverage target |
|---|---|
| Unit tests | Pattern parser (core logic must be rock solid), database queries, tag filtering logic |
| Integration tests | Database access, import flow (paste → parse → save) |
| End-to-end tests | Critical user journeys from 01_Product's Core Loop (import → search → copy) |

## 8. Operability (Health & Status)

*How do you know, at a glance, whether this is actually working?* Required in some form even for a solo local tool — "check the log file" is a valid answer, but it should be a stated one, not an assumption.

| Question | Answer |
|---|---|
| Health check mechanism | Startup log line confirming SQLite database accessible |
| What counts as "healthy" | Database writable, no corrupt pattern data |
| Logging | `logging` module to file (`osu_gallery.log`) and console. Minimum: startup, errors, import/save actions. Never log raw .osu code (may contain usernames). |
| Monitoring (if any) | N/A for solo local tool |
| Failure visibility | Toast notification for import errors, log file for debugging |

**Minimum viable version for a solo local tool:** a single startup log line per dependency ("✓ SQLite database ready") is enough to satisfy this section — the point is that it exists and is deliberate, not that it's elaborate.
