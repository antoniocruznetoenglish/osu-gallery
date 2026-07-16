# Technical Architecture: osu gallery

> Only here do we name actual technologies. Everything in this doc is a **frozen decision** an AI coding agent should treat as fixed â€” not a suggestion it's free to substitute. If you want to change something here, change it here first, deliberately, then implement.

**Last updated:** 2026-07-16
**Version:** 0.1
**Edit cadence:** Should be stable. This is the "constitution" your coding agent reads before every session.
**Design Phase (this doc's Status field):** Exploring / **Frozen** / Deprecated *(while Exploring, anything below is a hypothesis, not law. Once you flip this to Frozen, an agent should treat every row as fixed â€” and any proposed change gets logged in `06_Decision_Log.md` first, not silently made mid-session.)*

**Leave any section below blank until the project actually needs it.** A tiny desktop app doesn't need a CI row or a migration strategy on day one â€” filling them in prematurely just invents information you'll have to un-invent later. Blank is a valid, honest state; a guessed answer isn't.

---

## 1. Stack

| Layer | Choice | Why | Alternatives considered |
|---|---|---|---|
| Language | | | |
| UI/GUI framework | | | |
| Backend framework | | | |
| AI/LLM backend library | e.g. Ollama HTTP API, llama.cpp server (OpenAI-compatible) | | |
| Vector store | | | |
| Structured storage | | | |
| Config format | | | |
| Testing framework | | | |
| Linting/formatting | | | |
| Packaging/build tool | | | |
| CI | | | |

**Dependency philosophy:** minimize surface area (prefer stdlib/fewer deps) vs. accept heavier deps for speed of development â€” state which, so an agent doesn't decide inconsistently across sessions.

Keep each "Why" cell to one line. If the reasoning is longer than that, or alternatives were seriously weighed, it belongs in `06_Decision_Log.md` â€” link the decision number here instead of re-explaining it (e.g., "See ADR-003").


## 2. LLM Backend Configuration

| Question | Answer |
|---|---|
| Backend priority order | e.g., local-gguf > Ollama > OpenAI-compatible > cloud API |
| Local model constraints | VRAM/RAM ceiling, quantization, context window |
| Target hardware tier(s) | e.g., i5-12400f + RTX 3060 12GB (primary); i7-4770 + RX 5700 (homelab) |

## 3. Component Interfaces & Contracts

The strict boundaries between parts of the app â€” internal API routes, IPC channels, public functions each module exposes.

**Example:**
- `POST /api/generate` â†’ Input: `{ prompt: string, temperature: float }` â†’ Output: streamed tokens
- File system access: which directories can the app read/write?

### 3a. Cross-Boundary IPC Contract (if desktop GUI)

If the UI runs in a separate process or context from the backend (Electron, Tauri, PyQt with a QML/web frontend, etc.), spell this out explicitly â€” local models routinely hallucinate the frontend calling the database or filesystem directly, skipping the boundary entirely.

| Field | Detail |
|---|---|
| IPC mechanism | e.g., Electron contextBridge, Tauri `invoke`, PyQt signals/slots |
| Serialization law | Frontend and backend communicate only via [JSON / typed DTOs] â€” never shared memory or direct object references |
| Firewall rule | The frontend cannot see the filesystem, database connections, or LLM orchestration layer directly. It requests via a named channel and awaits a serialized response. |

## 4. Data Models

Concrete schemas â€” this is where 02's "conceptual store" entries get an actual shape.

```
Example:
Entity {
  id: uuid
  field: type
  ...
}
```

**Migration strategy:** how do you handle schema changes across versions?

## 5. External APIs / Integrations

| Service | Auth method | Rate limits | Fallback / offline mode |
|---|---|---|---|
| | | | |

## 6. Deployment & Packaging

| Question | Answer |
|---|---|
| Where does this run? | Local machine only / client-server / self-hosted / cloud |
| Target OS(es) | |
| Packaging | Raw script / installer / Docker / standalone executable |
| Update mechanism | |
| Supported OS/runtime versions | |

## 7. Testing Strategy

Summary only â€” the concrete coverage targets and framework choices live in `10_Testing_Strategy.md`. This row set exists so a reader of this doc alone still sees the shape.

| Layer | Coverage target |
|---|---|
| Unit tests | Which core logic must be rock solid? |
| Integration tests | DB access, API routes, IPC |
| End-to-end tests | Critical user journeys from 01_Product's Core Loop |

## 8. Operability (Health & Status)

*How do you know, at a glance, whether this is actually working?* Required in some form even for a solo local tool â€” "check the log file" is a valid answer, but it should be a stated one, not an assumption.

| Question | Answer |
|---|---|
| Health check mechanism | e.g., `/health` HTTP endpoint returning 200 + component status / CLI `--status` flag / log line on startup confirming each dependency (DB, LLM backend, vector store) connected |
| What counts as "healthy" | e.g., LLM backend reachable, DB writable, disk space above threshold |
| Logging | Where logs go, what's logged at minimum (startup, errors, and â€” per `09_Security.md` â€” never secrets or full user data payloads) |
| Monitoring (if any) | N/A for solo local tool is a valid answer â€” state it explicitly rather than leaving blank |
| Failure visibility | If a background/long-running component (e.g., an indexing job, a local server) dies silently, how would you find out? |

**Minimum viable version for a solo local tool:** a single startup log line per dependency ("âœ“ LLM backend reachable at :8080", "âœ— ChromaDB not found") is enough to satisfy this section â€” the point is that it exists and is deliberate, not that it's elaborate.
