# Contributing: osu gallery

> This doc exists for the day this project outgrows "just me." Even solo, filling it in as you go costs almost nothing and saves a scramble later. If a section is genuinely not applicable yet (e.g., no CI), say so explicitly rather than leaving it blank.

**Last updated:** 2026-07-16
**Version:** 0.1 · **Status:** Draft / Review / Frozen / Deprecated

---

## 1. Getting Started

Steps to go from a fresh clone to a running dev environment. Keep this literal enough that someone (or an AI agent) with zero prior context can follow it.

1. Clone the repo: `git clone [url]`
2. Install dependencies: `pip install -r requirements.txt` (PySide6, pytest, pytest-qt, ruff)
3. Required local services/backends: None (fully offline)
4. Environment/config setup: None required for MVP
5. Run it: `python -m osu_gallery` (or run `main.py` from project root)
6. Run the test suite: `pytest` (see `10_Testing_Strategy.md`)

## 2. Project Orientation

Read in this order before touching code:

1. `project_docs/07_AI_Context_Brief.md` — the whole project in under a page
2. `project_docs/02_System_Design.md` — module map and boundaries
3. `project_docs/05_AI_Collaboration_Rules.md` — the rules any contributor (human or AI) follows
4. The specific feature file in `project_docs/features/` for whatever you're working on

## 3. Branch & Commit Conventions

| Question | Answer |
|---|---|
| Branch naming | `feature/F00X-short-name`, `fix/short-desc` |
| Commit message format | One-line summary, imperative mood ("Fix parser bug", not "Fixed") |
| PR requirements (if/when this has more than one contributor) | Links the feature file, passes tests, updated relevant docs |

## 4. Code Style

| Question | Answer |
|---|---|
| Formatter/linter | ruff (run `ruff check --fix` before every commit) |
| Naming conventions | snake_case for functions/variables, PascalCase for classes, no abbreviations without a Glossary entry |
| Max function/file length guidance | Soft target, not a hard gate — "if a function needs a comment to explain sections, it needs splitting" |
| Comment philosophy | Comment *why*, not *what* — the code should say what, the comment says why it's not the obvious alternative |

## 5. Where Things Live

Quick-reference so a new contributor doesn't have to reverse-engineer the module map:

| I want to... | Look in... |
|---|---|
| Add a feature | Start with `01_Product.md` §5, then `04_Implementation_Roadmap.md` §4 |
| Understand a module's job | `02_System_Design.md` §1 |
| Check if a dependency is approved | `03_Technical_Architecture.md` §1 |
| Understand a domain term | `08_Glossary.md` |
| See why a past decision was made | `06_Decision_Log.md` |

## 6. Who to Ask / How Decisions Get Made

| Question | Answer |
|---|---|
| Solo project — who approves architecture changes? | You. But it still goes through `06_Decision_Log.md` first — writing it down is the review. |
| If this grows beyond solo | [fill in when it happens — don't pre-invent a governance structure for a team that doesn't exist yet] |
