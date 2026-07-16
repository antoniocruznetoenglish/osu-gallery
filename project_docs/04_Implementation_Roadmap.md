# Implementation Roadmap: osu gallery

> This doc is meant to change constantly â€” that's the point. It tracks *when*, not *what* or *how*. If a milestone requires a new module or a new dependency, that decision still belongs in 02 or 03 first; this just sequences the work.

**Last updated:** 2026-07-16
**Version:** 0.1 Â· **Status:** Draft / Review / Frozen / Deprecated *(this doc is rarely "Frozen" â€” it's meant to move)*

---

## 0. Feasibility Check (before a milestone or feature is approved)

Run this any time a new milestone or a non-trivial feature is added â€” not just at project start. It's the check against "the idea is bigger than what's actually buildable given what we already committed to." Five minutes here is cheaper than discovering the mismatch mid-implementation.

| Check | Answer |
|---|---|
| Does this fit inside `03_Technical_Architecture.md`'s existing stack, or does it require a new dependency/framework? | If new: that's a `03` decision first, not an assumption baked into this roadmap. |
| Does this fit the hardware ceiling in `03_Technical_Architecture.md` Â§2? | e.g., a feature requiring a bigger model than your VRAM allows isn't "figure it out later" â€” name the constraint now. |
| Does this fit the offline/privacy constraints in `01_Product.md` Â§7? | A feature that quietly needs a cloud call violates a constraint you already set â€” flag it, don't silently build around it. |
| How many new dependencies does this actually pull in (including transitive ones for anything non-trivial)? | If it's more than a couple, that's a signal the feature is doing too much â€” consider splitting it. |
| Is there anything in the request that was never specified anywhere in 01-03? | If yes: that's an assumption an AI agent would otherwise have to invent. Resolve it here â€” either add it to the right doc, or log it in Â§3 Open Questions â€” before it becomes an Open Question discovered mid-code. |

**If more than one of these raises a flag:** the feature is likely oversized for a single milestone. Split it, or push the uncertain part to an explicit Open Question (Â§3) and build the certain part first.

## 1. Milestones

| Phase | Goal | Depends on | Status |
|---|---|---|---|
| 1 | Basic [core loop] working end-to-end | | Not started / In progress / Done |
| 2 | | | |
| 3 | | | |

Keep phases scoped to something demoable â€” "basic UI," "database layer," "first AI integration" â€” not vague ("polish").

## 2. Extensibility Roadmap

Known-likely future additions, even if not building them now. Cross-reference the seams named in `02_System_Design.md` Â§6 â€” if something here doesn't have a seam yet, that's a signal to update 02 before building toward it.

| Planned addition | Impacts which module(s) | Design implication now |
|---|---|---|
| | | |

## 3. Open Questions

Things you genuinely don't know yet. Name them here instead of letting an AI agent silently guess â€” and guess differently next session.

- [ ]
- [ ]

## 4. Feature Specifications (for P0/P1 features only)

Small features just need a line in the Feature Log below. But before implementing anything sizable â€” anything touching multiple modules, adding a dependency, or changing a data model â€” turn its `01_Product.md` user story into a full spec **as its own file** under `project_docs/features/`, not inline here. Run the Feasibility Check (Â§0) before writing the spec, not after.

**Why a separate file, not a section of this doc:** this file accumulates milestones and log entries for the life of the project â€” over a few months it can grow into hundreds of lines. Loading all of that into a local model's context just to work on one feature wastes the budget you need for the actual code. A standalone `features/F001_name.md` lets you feed an agent exactly one feature's contract and nothing else.

Copy `project_docs/features/TEMPLATE.md` for each new P0/P1 feature, name it `F[n]_short-name.md`, and link it from the Feature Log row below.

## 5. Feature Log (append-only)

One line per feature added or changed, with which docs it touched. This becomes your change history and keeps 01-03 from silently drifting out of sync with what actually got built. For P0/P1 features, link the standalone spec file instead of re-describing it here. When a feature ships in a released version, also log it in the project's `CHANGELOG.md` (root, not `project_docs/`) â€” this log is the design-side history, the changelog is the release-side history.

| Date | Feature | Docs / spec touched | Notes |
|---|---|---|---|
| | | | |
