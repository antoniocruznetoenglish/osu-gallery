# AI Collaboration Rules: osu gallery

> Paste this file (or point your agent at it â€” e.g., as `AGENTS.md` context) at the start of every coding session. It's the single source of truth for both you and any AI touching this repo. Keep it short enough to actually get read.

---

## Mandatory rules

1. **Never introduce a new framework, library, or dependency without asking first.** Check `03_Technical_Architecture.md` â€” if it's not listed, it's not approved.
2. **Never invent UI layout or screens.** Check `02_System_Design.md` Â§2 â€” if a screen isn't listed there, ask before building it.
3. **Never move logic across module boundaries** defined in `02_System_Design.md` Â§1 (e.g., business logic into the UI layer, persistence into the backend logic layer). If a module's "Explicitly NOT responsible for" list is violated, stop and flag it.
4. **Update the design docs before implementing architectural changes** â€” not after. If a feature genuinely needs a new module, new dependency, or new data store, that's a `02`/`03` edit first, code second.
5. **Ask before adding dependencies**, even small ones. A one-line "can I use X for Y" beats a silent pip install.
6. **Keep modules loosely coupled, highly cohesive** â€” a module should be replaceable without rewriting its neighbors.
7. **Every feature maps to an entry in `01_Product.md` Â§5.** If you're building something with no user story, stop and ask whether it belongs.
8. **Any change to `03_Technical_Architecture.md` gets a Decision Log entry first** (`06_Decision_Log.md`) â€” reasoning and rejected alternatives, not just the new choice. "Why" without a paper trail is how the same debate happens twice.
9. **Check `08_Glossary.md` before assuming what a domain term means**, and add a term there the first time it matters â€” not just the first time it's ambiguous. Overloaded terms (e.g., "session" meaning login session vs. AI context session vs. websocket session) are worth documenting before they cause a mix-up, not after.
10. **Run the Feasibility Check** (`04_Implementation_Roadmap.md` Â§0) before agreeing to build a non-trivial feature. If the request needs something never specified in 01-03, that's a gap to resolve â€” not an assumption to quietly fill in.

## Security rules (see `09_Security.md` for full detail)

11. Never hardcode a secret, API key, token, or credential in source. If one's needed, ask where it should be stored (`.env`, OS keychain, etc.) per `09_Security.md` Â§1.
12. Never construct a shell command, SQL query, or file path via raw string concatenation of untrusted input (user input, scraped data, LLM output). Use parameterization or an allowlist instead.
13. Treat LLM output as untrusted input if it's ever used to trigger an action (file write, command, API call) â€” validate before executing, per `09_Security.md` Â§4.
14. Any new network-facing surface (port, endpoint, listener) is a Decision Log entry first, same tier as a dependency change.

## Code quality rules (see `12_Coding_Standards.md` for full detail)

15. Match the style/linting/formatting choice in `03_Technical_Architecture.md` Â§1 and `11_Contributing.md` Â§4 â€” run the formatter before considering a change done.
16. One function/class, one responsibility â€” split validation, computation, and persistence into separate units rather than combining them.
17. No duplicated constants or logic â€” extract once, reference everywhere. A value defined twice will eventually drift out of sync with itself.
18. If a function needs an explanatory comment to break down what each section does, that's a signal to split it, not a signal to add the comment and move on.
19. Comment *why*, not *what* â€” the code should already say what it does.
20. No dead code or commented-out blocks left in a diff "just in case" â€” that's what version control and `06_Decision_Log.md` are for.
21. Never leave a catch/except block empty or silent â€” every caught error is logged, handled, or re-raised. No bare `pass`/`continue`.
22. Use specific exception/error types, not generic `Exception`/`Error` â€” and fail fast on unrecoverable errors rather than continuing in a broken state.
23. Every public function gets a docstring (inputs, outputs, exceptions raised) before a task is considered done.
24. Use structured logging (JSON) through the project's established setup, never raw `print`/`console.log`, in anything committed â€” and never log secrets, tokens, or credentials.

## Testing rules (see `10_Testing_Strategy.md` for full detail)

25. New logic in a layer covered by `10_Testing_Strategy.md` Â§2 ships with a test in the same change.
26. A bug fix includes a regression test that fails before the fix and passes after.
27. Never weaken an assertion or silently skip a test to get a suite green â€” flag the real failure instead.

## Planning Rule

Before writing any code, an agent must:

1. Summarize the task in its own words.
2. Identify which module(s) from `02_System_Design.md` Â§1 are affected.
3. List the specific files likely to change.
4. State any assumptions being made.
5. **If an assumption touches architecture, a dependency, a module boundary, security posture, or something never specified in 01-03 â€” wait for confirmation before writing code.** Otherwise, proceed.

This one habit catches most hallucinated architecture before it becomes a diff. It costs one short paragraph per task.

## Definition of Done

A feature isn't finished until all of these are true â€” this is the checklist an agent should self-verify against before calling something complete:

- [ ] Implemented per its Feature Specification (`04_Implementation_Roadmap.md` Â§4), if it had one
- [ ] Feasibility Check passed (`04_Implementation_Roadmap.md` Â§0) with no unresolved flags
- [ ] Tests added or updated per `10_Testing_Strategy.md`, and the existing suite still passes
- [ ] No dependency used that isn't listed in `03_Technical_Architecture.md` Â§1
- [ ] No secret, credential, or untrusted-input-as-command pattern introduced (`09_Security.md`)
- [ ] No empty/silent exception handler, and no raw `print`/`console.log` used for logging (`12_Coding_Standards.md`)
- [ ] Formatter/linter run per `03_Technical_Architecture.md` Â§1
- [ ] Docs updated if the implementation changed the design (01/02/03/09 as relevant)
- [ ] Logged in `04_Implementation_Roadmap.md` Â§5 (Feature Log), and in `CHANGELOG.md` if shipping in a release
- [ ] No unresolved TODOs left in the diff

## When starting a session

Reference the specific doc section relevant to the task, not the whole repo:

> "Using `02_System_Design.md` Â§1 (Module Map) and `03_Technical_Architecture.md` Â§4 (Data Models), implement [feature] as described in `01_Product.md` F[n]. Do not add dependencies beyond what's listed in Â§1 of 03."

## When something doesn't fit

If a request doesn't map cleanly onto the existing docs â€” new module, new dependency, ambiguous scope, or fails the Feasibility Check â€” the correct move is to **stop and ask**, not guess and proceed. Log the question in `04_Implementation_Roadmap.md` Â§3 (Open Questions) if it can't be resolved immediately.
