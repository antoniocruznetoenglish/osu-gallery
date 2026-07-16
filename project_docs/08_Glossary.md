# Glossary: osu gallery

**Version:** 0.1 · **Status:** Living (append-only)

> The cheapest fix for the most common AI-assisted-dev failure: an agent quietly redefines a domain term and everything built on top of that session inherits the wrong meaning. This file exists so "what do we mean by X" has one answer, not a different guess per session.

**Add a term here the first time it's ambiguous** — you don't need to front-load this before writing any code; populate it as terms come up.

| Term | Definition | Is NOT |
|---|---|---|
| Beatmap | An osu! difficulty/chart definition (the .osu file) | A score, a replay, a pattern |
| Pattern | A named, reusable arrangement of notes (circles, sliders, spinners) that mappers save for reference | A difficulty rating, a beatmap |
| Hit object | A single note, circle, slider, or spinner in an .osu file | A beatmap, a pattern (a pattern contains multiple hit objects) |
| Object group | A set of hit objects that move together (e.g., a 4-note circle pattern) | A single hit object, a beatmap |
| Slider | A hit object where the cursor must follow a path from start to end | A circle, a spinner |
| Approach circle | The expanding circle around a hit object that indicates timing | A slider, a pattern |
| Combo color | The color assigned to a sequence of hit objects (changes per combo) | A hit object, a beatmap |
| .osu code block | The raw hit object section of an .osu file (numbers after `[HitObjects]`) | The full .osu file, a beatmap |
| Thumbnail | A small static preview image of a pattern (200x200 or 300x300) | An animated preview, a full beatmap |
| Tag | A category label for filtering patterns (e.g., "1slider", "3circle", "1/1kick") | A pattern, a beatmap |

**Format note:** the "Is NOT" column matters as much as the definition — most real ambiguity is an AI conflating two adjacent-but-different concepts (e.g., mistaking a leaderboard for a ranking algorithm), not misunderstanding the term outright.
