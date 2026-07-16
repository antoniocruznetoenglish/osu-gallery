# Glossary: osu gallery

**Version:** 0.1 Â· **Status:** Living (append-only)

> The cheapest fix for the most common AI-assisted-dev failure: an agent quietly redefines a domain term and everything built on top of that session inherits the wrong meaning. This file exists so "what do we mean by X" has one answer, not a different guess per session.

**Add a term here the first time it's ambiguous** â€” you don't need to front-load this before writing any code; populate it as terms come up.

| Term | Definition | Is NOT |
|---|---|---|
| e.g. Beatmap | An osu! difficulty/chart definition | A score, a replay |
| e.g. Pattern | A named, reusable arrangement of notes | A difficulty rating |

**Format note:** the "Is NOT" column matters as much as the definition â€” most real ambiguity is an AI conflating two adjacent-but-different concepts (e.g., mistaking a leaderboard for a ranking algorithm), not misunderstanding the term outright.
