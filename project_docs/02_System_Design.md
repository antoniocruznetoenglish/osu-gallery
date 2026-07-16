# System Design: osu gallery

> Describes the software like Lego blocks â€” modules, responsibilities, and how data moves between them. **No specific frameworks or libraries here** â€” that's 03_Technical_Architecture.md. If a sentence names a technology, it belongs in that doc instead. This separation is what stops an AI coding agent from treating a tech-stack swap as equivalent to a refactor.

**Last updated:** 2026-07-16
**Version:** 0.1 Â· **Status:** Draft / Review / Frozen / Deprecated
**Edit cadence:** Should be stable. Editing this often = you're mid-refactor; do it deliberately, not accidentally via prompting.

---

## 0. Architectural Principles

A handful of short, durable rules â€” not architecture itself, the philosophy the architecture implements. Keep this to 3-6 one-liners; if a principle needs a paragraph to explain, it's not a principle, it belongs in a module's responsibilities below.

- e.g. "Business logic never knows the UI exists."
- e.g. "Every external dependency is isolated behind an adapter."
- e.g. "Offline-first: nothing in the core loop requires network access."
-
-

## 1. Module Map

List every major module/component. Each gets a one-line responsibility â€” think directory listing, not implementation.

```
System
â”œâ”€â”€ UI               â†’ display info, collect input, show status
â”œâ”€â”€ Backend/Logic     â†’ business rules, validation, orchestration
â”œâ”€â”€ Storage           â†’ persistence, cache, config
â”œâ”€â”€ AI/LLM Layer       â†’ prompt construction, backend routing, evidence packaging
â”œâ”€â”€ External Services  â†’ adapters to APIs/services outside this system
â””â”€â”€ [Plugin/Extension] â†’ seam for future modules
```

### Module Detail

Copy this block per module.

**Module: [name]**
| Field | Value |
|---|---|
| Responsibilities | |
| Explicitly NOT responsible for | (e.g., UI "Never: store permanent data, business logic") |
| Inputs | |
| Outputs | |
| Depends on (other modules) | |

---

## 2. Users & Interaction Plan

| Question | Answer |
|---|---|
| Interface type | CLI / Desktop GUI / Web app / API-only / Mobile / Mix |
| Primary interaction pattern | One-shot command / Long-running session / Background service / Request-response |
| Who else besides you touches this? | |

**Screens / views** (if GUI or web) â€” one line each, purpose only, no layout design yet:

1.
2.

**UI state coverage** â€” for each key view, what does the user see when: loading / empty / error / success?

---

## 3. Data Flow (Happy Path)

Numbered steps from entry point to result. This should stay true even as internals get rewritten underneath it.

1.
2.
3.

## 4. Data Design

| Data type | Conceptual store (not the specific DB yet) | Owner module | Rebuild or preserve? |
|---|---|---|---|
| e.g. scraped documents | flat files | Storage | Rebuildable from source |
| e.g. vector embeddings | vector store | AI/LLM Layer | Rebuildable from source |
| e.g. user config | structured store | Storage | Must survive reinstall |

**Source of truth:** which store is authoritative if others disagree?


## 5. AI / LLM Role (conceptual)

*Specific backends (Ollama, llama.cpp, OpenAI-compatible) go in 03. This is about the role, not the tool.*

| Question | Answer |
|---|---|
| Is an LLM core to the core loop, or an enhancement? | Core / Optional enhancement / Not used |
| Minimum viable experience with zero LLM available | |
| What's it actually used for | Generation / Retrieval reasoning / Classification / Embedding / Orchestration |

## 6. Extensibility Seams

Where are the plug-in points you already know you'll need? Naming these now stops an agent from hardcoding assumptions that block extension later (e.g., "new data source exporters," "new LLM backend," "new UI screen").

-
-

## 7. Non-Functional Requirements

| Concern | Target |
|---|---|
| Performance (latency/throughput) | |
| Concurrency | Single-user only / multi-session |
| Offline requirement | Fully offline / hybrid / requires internet |
| Error handling philosophy | Fail loud and fast / graceful degradation / silent fallback |
| Security / secrets handling | See `09_Security.md` for full detail â€” this row is a one-line pointer, not the spec |
| Observability / health checks | See `03_Technical_Architecture.md` Â§8 for full detail |
| Accessibility / localization | |
