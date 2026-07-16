# Product Definition: osu gallery

> Answers "what are we building and why." No frameworks, no libraries, no architecture — those belong in 02 and 03. If you find yourself naming a technology here, move it.

**Last updated:** 2026-07-16
**Version:** 0.1 · **Status:** Draft / Review / Frozen / Deprecated

---

## 1. Problem & Purpose

**Problem statement** (2-3 sentences max — if it takes longer, the scope isn't clear yet):

There's no easy way to organize osu! patterns, sliders, shapes, and object groups into categories or a visual gallery. Mappers currently have to leave the editor to search other maps, open multiple osu! clients simultaneously, or rely on memory — all of which break flow and slow down the mapping process.

**Why does this deserve to exist?** (What's broken or missing without it?)

No categorization or tag system exists for saving patterns and ideas for quick reference. Creative block is common, and finding the right pattern in the moment requires context-switching away from the editor or running parallel instances.

## 2. Core Loop

The minimum sequence of actions a user takes to get value. Strip away every feature that isn't part of this loop — those become P1/P2 below, not part of the definition of "done."

```
User edits in osu! editor → alt+tab to gallery app → types search term → clicks thumbnail → views large preview → copies code or references → alt+tab back to editor
```

## 3. Target Users

| User type | Goals | Skill level | Notes |
|---|---|---|---|
| osu! mappers (beginners) | Learn patterns, find reference quickly | Varies | Use gallery to study and replicate techniques |
| osu! mappers (experienced) | Speed up workflow, beat creative block | Advanced | Use gallery as quick alt+tab reference library |

## 4. Success Criteria

How will you know this worked? Concrete and measurable if possible (e.g., "cuts alt-tabbing between editor and reference material by 80%"), not "it should be cool."

- Adding patterns is easy and intuitive (one-click or paste-from-clipboard import)
- Application loads fast (under 2 seconds)
- Visual thumbnails clearly display pattern details at a glance
- Search feature supports multiple filter criteria (slider type, circle count, timing combos, tags) to narrow results quickly
- Copy-to-clipboard works reliably for direct paste into .osu files

## 5. User Stories & Features

Priority: **P0** = core loop, ships without it = pointless. **P1** = should have. **P2** = nice-to-have / future.

| ID | Priority | Feature | User Story (As a... I want... So that...) |
|---|---|---|---|
| F1 | P0 | Manual import of .osu code blocks | As a mapper, I want to paste or manually input object code so that I can save patterns to my gallery without client integration |
| F2 | P0 | Search bar with live results | As a mapper, I want to type search terms and see thumbnails instantly so that I can find patterns without leaving my workflow |
| F3 | P0 | Thumbnail grid with click-to-expand | As a mapper, I want to click a thumbnail and see a larger view so that I can study the pattern details |
| F4 | P0 | Copy object code to clipboard | As a mapper, I want to copy the raw object code with one click so that I can paste it into my .osu file |
| F5 | P1 | Categorization/tags system | As a mapper, I want to tag patterns with categories (1 slider, 3 circle, etc.) so that search can filter by them |
| F6 | P1 | Visual preview of objects | As a mapper, I want to see a rendered preview of the pattern, not just raw code, so that I can quickly judge if it's what I need |
| F7 | P2 | Bulk import from existing maps | As a mapper, I want to scan my existing maps and import all unique patterns so that I don't have to save them one by one |

## 6. Explicit Non-Goals

What this deliberately will **not** do, even if it sounds related. This is the single biggest lever against scope creep — and against an AI agent "helpfully" adding something you didn't ask for.

- Not a fully online website application
- Not a beatmap editor (visual preview only, no interactive editing)
- Not a map discovery tool (no osu! API scraping or map finding)
- Not a real-time collaboration feature

## 7. Constraints

Hard limits that shape everything downstream (these get elaborated with specifics in 02/03, but name them here first):

- Must work fully offline? Yes
- Must run on existing hardware only? Yes (no special GPU requirements beyond basic rendering)
- Single-user or shared/multi-user? Single-user
- Any privacy/data-ownership requirement (e.g., scraped/personal content never leaves the machine)? All data stored locally, no cloud sync
