# Coding Standards: osu gallery

> Covers clean code, error handling, documentation, and logging conventions â€” the layer between "the code works" and "the code is maintainable by a future session with no memory of this one." Promoted out of `05_AI_Collaboration_Rules.md`'s Code Quality Rules â€” that section holds the enforced summary; this doc holds the reasoning and detail.

**Last updated:** 2026-07-16
**Version:** 0.1 Â· **Status:** Draft / Review / Frozen / Deprecated

---

## 1. Clean Code

| Principle | Rule |
|---|---|
| Naming | Names say what something is/does without needing a comment to explain it. One casing convention per project, stated here once decided: __________ |
| Single Responsibility | One function/class, one reason to change. Split validation, computation, and persistence into separate units rather than combining them. |
| Single source of truth | A constant or business rule lives in exactly one place and is referenced elsewhere â€” never copy-pasted. Duplication is how a value silently drifts out of sync with itself. |
| Folder structure | Organize by feature/domain â€” matches `02_System_Design.md` Â§1's module map â€” not by file type (no `components/` + `containers/` split for the same concern). |
| Formatting | Enforced by the linter/formatter in `03_Technical_Architecture.md` Â§1, not by memory across sessions. |

## 2. Error Handling

- Never leave a catch/except block empty or silent. Every caught error is logged, handled, or re-raised â€” no bare `pass`/`continue`.
- Use specific exception/error types (`ValidationError`, `ConfigMissingError`), not generic `Exception`/`Error`.
- Fail fast on unrecoverable errors (missing config, invalid startup state) instead of continuing in a broken state.
- Retry only transient failures (network, rate limits), with bounded attempts. Never retry a logic error.
- Log full detail internally; never leak stack traces or internal paths in user-facing or API responses.
- If input crosses a trust boundary (see `09_Security.md` Â§4), validate right at the boundary â€” don't let a bad value travel three functions deep before the failure surfaces.

## 3. Documentation (code-level)

> Distinct from `project_docs/` itself â€” this is what lives *in* the code: docstrings, inline comments, per-directory READMEs.

- Every public function/method gets a docstring: inputs, outputs, exceptions raised.
- Inline comments explain *why*, not *what* â€” mirrors `05_AI_Collaboration_Rules.md` Â§19. The code already says what it does.
- Docs update in the same commit as the code they describe. Delete stale docs immediately rather than letting them linger.
- Don't duplicate an explanation that already lives in `project_docs/` â€” link to it instead of re-writing it.

## 4. Logging

| Level | Use for |
|---|---|
| DEBUG / TRACE | Verbosity only â€” local troubleshooting, off by default in normal operation |
| INFO | Noteworthy events in normal operation (job started/finished, request handled) |
| WARN | Abnormal but non-fatal â€” something to watch |
| ERROR | An operation failed â€” needs attention |
| FATAL | The whole process is going down |

- Structured logs (JSON), not raw `print`/`console.log`, for anything committed.
- Include a correlation/request/task ID in log entries where applicable â€” not just a bare message string.
- Never log secrets, tokens, passwords, or personal data â€” this also keeps them out of an agent's context window in a later session.
- Logs answer "what happened in this one case," not "what's the overall trend." Don't build alerting logic against log text when a counter or health check (`03_Technical_Architecture.md` Â§8) would do the job more reliably.

## 5. What an AI Agent Must Do

Mirrors into `05_AI_Collaboration_Rules.md` Code Quality Rules and Definition of Done:

1. No empty or silent exception handler in any diff â€” ever.
2. Every public function has a docstring before the task is considered done.
3. Logging goes through the project's established structured-logging setup â€” never raw `print`/`console.log` in committed code.
4. Naming/casing convention and folder structure are fixed per project (Â§1 above) â€” don't improvise a new one mid-session.
5. If a task seems to require violating one of these, stop and ask rather than silently deviating.

## 6. Local-Model-Specific Note

A smaller local model under context pressure is the most likely source of a swallowed exception or a skipped docstring â€” it's optimizing for "make it run," not "make it maintainable." Feed it this doc's relevant section (not the whole file) alongside the code it's touching, and spot-check its diff against Â§5 before accepting it.
