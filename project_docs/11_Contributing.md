# Contributing: osu gallery

> This doc exists for the day this project outgrows "just me." Even solo, filling it in as you go costs almost nothing and saves a scramble later. If a section is genuinely not applicable yet (e.g., no CI), say so explicitly rather than leaving it blank.

**Last updated:** 2026-07-16
**Version:** 0.1 Â· **Status:** Draft / Review / Frozen / Deprecated

---

## 1. Getting Started

Steps to go from a fresh clone to a running dev environment. Keep this literal enough that someone (or an AI agent) with zero prior context can follow it.

1. Clone the repo: `git clone [url]`
2. Install dependencies: [command]
3. Required local services/backends: [e.g., start llama-server.exe / Ollama first]
4. Environment/config setup: [e.g., copy `.env.example` to `.env`, fill in X]
5. Run it: [command]
6. Run the test suite: [command â€” see `10_Testing_Strategy.md`]

## 2. Project Orientation

Read in this order before touching code:

1. `project_docs/07_AI_Context_Brief.md` â€” the whole project in under a page
2. `project_docs/02_System_Design.md` â€” module map and boundaries
3. `project_docs/05_AI_Collaboration_Rules.md` â€” the rules any contributor (human or AI) follows
4. The specific feature file in `project_docs/features/` for whatever you're working on

## 3. Branch & Commit Conventions

| Question | Answer |
|---|---|
| Branch naming | e.g., `feature/F00X-short-name`, `fix/short-desc` |
| Commit message format | e.g., one-line summary, imperative mood ("Fix BM25 scoring bug", not "Fixed") |
| PR requirements (if/when this has more than one contributor) | e.g., links the feature file, passes tests, updated relevant docs |

## 4. Code Style

| Question | Answer |
|---|---|
| Formatter/linter | Must match `03_Technical_Architecture.md` Â§1 â€” run before every commit |
| Naming conventions | e.g., language-standard casing, no abbreviations without a Glossary entry |
| Max function/file length guidance | Soft target, not a hard gate â€” e.g., "if a function needs a comment to explain sections, it needs splitting" |
| Comment philosophy | e.g., comment *why*, not *what* â€” the code should say what, the comment says why it's not the obvious alternative |

## 5. Where Things Live

Quick-reference so a new contributor doesn't have to reverse-engineer the module map:

| I want to... | Look in... |
|---|---|
| Add a feature | Start with `01_Product.md` Â§5, then `04_Implementation_Roadmap.md` Â§4 |
| Understand a module's job | `02_System_Design.md` Â§1 |
| Check if a dependency is approved | `03_Technical_Architecture.md` Â§1 |
| Understand a domain term | `08_Glossary.md` |
| See why a past decision was made | `06_Decision_Log.md` |

## 6. Who to Ask / How Decisions Get Made

| Question | Answer |
|---|---|
| Solo project â€” who approves architecture changes? | You. But it still goes through `06_Decision_Log.md` first â€” writing it down is the review. |
| If this grows beyond solo | [fill in when it happens â€” don't pre-invent a governance structure for a team that doesn't exist yet] |
