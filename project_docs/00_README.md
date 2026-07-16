# Design Docs â€” How This Works

One giant spec document gets stale and gets skipped. Small, purpose-built documents don't â€” because each one only changes when the *kind* of decision it holds actually changes.

```
project_docs/
â”œâ”€â”€ 00_README.md                 â†’ you are here
â”œâ”€â”€ 01_Product.md                â†’ WHAT are we building, for whom, why
â”œâ”€â”€ 02_System_Design.md          â†’ HOW it's structured, framework-agnostic
â”œâ”€â”€ 03_Technical_Architecture.md â†’ WHICH tools/libraries/stack (frozen choices) + operability
â”œâ”€â”€ 04_Implementation_Roadmap.md â†’ WHEN â€” feasibility gate, milestones, feature log, open questions
â”œâ”€â”€ 05_AI_Collaboration_Rules.md â†’ rules for any AI agent (human or model) touching this repo
â”œâ”€â”€ 06_Decision_Log.md           â†’ WHY â€” append-only record of decisions and rejected alternatives
â”œâ”€â”€ 07_AI_Context_Brief.md       â†’ condensed single-page cheat sheet, paste this into every session
â”œâ”€â”€ 08_Glossary.md               â†’ shared vocabulary â€” the cheapest fix for an AI silently redefining terms
â”œâ”€â”€ 09_Security.md               â†’ network exposure, secrets, trust boundaries, attack surface
â”œâ”€â”€ 10_Testing_Strategy.md       â†’ concrete coverage targets and testing rules, promoted out of 03
â”œâ”€â”€ 11_Contributing.md           â†’ onboarding â€” setup, conventions, where things live
â”œâ”€â”€ 12_Coding_Standards.md       â†’ clean code, error handling, documentation, and logging conventions
â””â”€â”€ features/                    â†’ one lean file per P0/P1 feature (see 04 Â§4), so a session loads only what it needs
    â””â”€â”€ TEMPLATE.md

CHANGELOG.md (project root, not in project_docs/) â†’ release history, separate from design history
```

**Three phases, not two.** Every project moves through:

```
EXPLORATION   â†’   DESIGN FREEZE   â†’   IMPLEMENTATION
(anything's        (01-03 & 09 are     (coding begins;
 on the table)       set, changes now    03/09 become
                     go through 06       read-only law)
                     first)
```

Most AI-assisted projects go wrong by skipping straight from Exploration to Implementation. `03_Technical_Architecture.md` has a **Design Phase** field at the top â€” check it before letting an agent touch code. If it says "Exploring," finish exploring first; don't code against a moving target.

**The build order:**

```
Idea â†’ 01_Product â†’ 02_System_Design â†’ 03_Technical_Architecture + 09_Security (â†’ freeze) â†’ 04_Roadmap (Â§0 Feasibility Check) â†’ Coding
```

Not the reverse. If you catch yourself opening an editor and prompting an AI coding agent before these are filled in, stop â€” that's the exact pattern that produced the gaps you hit on the osu! project.

## A note for local models specifically

Since you're running local backends (Ollama / llama.cpp) with real VRAM ceilings, don't feed the whole `project_docs/` folder into every session â€” that's context budget better spent on the actual code. Two options:

- For a specific task, paste only the relevant section(s) â€” e.g., `02_System_Design.md` Â§1 plus the one feature spec from `04`.
- For a fresh session or a smaller local model, paste `07_AI_Context_Brief.md` alone â€” it's designed to be the entire seed context in under a page.

**Context budget by task type** â€” different work needs different docs loaded, not the whole folder:

| Task | Load |
|---|---|
| Scoping a new idea | `01_Product.md` + `04_Implementation_Roadmap.md` Â§0 |
| Designing a module layout | `01_Product.md` + `02_System_Design.md` |
| Writing frontend/UI code | `02_System_Design.md` Â§2 + the one feature file in `features/` |
| Writing backend/core logic or DB queries | `02_System_Design.md` + `03_Technical_Architecture.md` |
| Anything touching network input, auth, or secrets | `09_Security.md` |
| Writing or reviewing tests | `10_Testing_Strategy.md` Â§2 for the relevant layer |
| Cross-boundary/IPC work | `03_Technical_Architecture.md` Â§3a specifically |
| Debugging or optimization | `03_Technical_Architecture.md` + `05_AI_Collaboration_Rules.md` |
| Any code-level task â€” naming, error handling, docstrings, logging | `12_Coding_Standards.md` |
| Architecture change | `02` (full) + `06_Decision_Log.md` (recent entries) |
| Unfamiliar term in the code | `08_Glossary.md` |
| Onboarding a new contributor (or a fresh agent to the whole repo) | `11_Contributing.md` |
| Fresh session, no specific task yet | `07_AI_Context_Brief.md` alone |

**Why not split further into a full knowledge-graph or per-concept folder structure** (vision/, decisions/, features/F001/, etc.): that scales well for a team, but for a solo/homelab setup it's more files than you'll realistically keep in sync â€” and an unmaintained elaborate structure fails the same way an unmaintained single doc does, just with more places for the drift to hide. Twelve flat files is close to the ceiling worth maintaining alone; if a project outgrows this, that's the signal to split, not a reason to pre-build it now.

## Why split instead of one file

| If you mix... | You get... |
|---|---|
| Product goals + tech stack | Feature creep disguised as "just adding a library" |
| Architecture + specific frameworks | An AI agent "helpfully" swapping frameworks because the doc didn't say not to |
| Roadmap + architecture | A doc you stop updating because milestones change weekly and you don't want to re-edit the stable parts |
| Architecture + security posture | Security treated as an afterthought instead of a frozen decision an agent must respect |

Splitting means **02, 03, and 09 rarely change** once set (edit = you're mid-refactor, do it deliberately). **01 changes per feature idea. 04 changes constantly** and is meant to. Each doc's volatility matches how often you'll actually touch it.

## Workflow for adding a new feature

1. Add the idea to `01_Product.md` under User Stories, with a priority (P0/P1/P2).
2. Run the Feasibility Check in `04_Implementation_Roadmap.md` Â§0 â€” does it fit the existing stack, hardware ceiling, and constraints, or does something need to change first?
3. Check `02_System_Design.md` â€” does it fit an existing module's responsibility, or does it need a new module / new seam? Update the module table, don't invent structure ad hoc.
4. Check `03_Technical_Architecture.md` â€” does it need a new dependency? If yes, that's a deliberate decision, not something an AI agent should pick mid-implementation. Add it here first.
5. Check `09_Security.md` â€” does it touch untrusted input, secrets, or add network exposure? Note it there.
6. Log it in `04_Implementation_Roadmap.md`'s Feature Log.
7. *Then* prompt your coding agent â€” and reference these docs explicitly (see `05_AI_Collaboration_Rules.md`).

## Getting an AI to help you fill these out

Don't fill blank templates alone if you don't have to. Open a chat and say:

> "I want to build [one-liner]. Read `01_Product.md`'s structure and interview me â€” ask one question at a time until it's filled in."

Repeat for each doc, in order. Answering one question at a time produces much better answers than trying to fill a whole template in one pass.

## Documentation-first, even solo

Before implementing a feature: update the relevant doc â†’ re-read it â†’ *then* write code. Skipping straight to "just prompt the coding agent" is the habit that produced the gaps on the osu! project in the first place. This feels like overhead for a one-person team right up until an AI agent is writing most of the implementation â€” at that point it's the difference between the agent implementing a design you already approved versus inventing one on the fly.
