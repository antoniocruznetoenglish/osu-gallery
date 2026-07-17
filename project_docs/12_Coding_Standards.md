# Coding Standards: osu gallery

> Covers clean code, error handling, documentation, and logging conventions — the layer between "the code works" and "the code is maintainable by a future session with no memory of this one." Promoted out of `05_AI_Collaboration_Rules.md`'s Code Quality Rules — that section holds the enforced summary; this doc holds the reasoning and detail.

**Last updated:** 2026-07-16
**Version:** 0.1 · **Status:** Draft / Review / Frozen / Deprecated

---

## 1. Clean Code

| Principle | Rule |
|---|---|
| Naming | Names say what something is/does without needing a comment to explain it. One casing convention per project, stated here once decided: snake_case for functions/variables, PascalCase for classes |
| Single Responsibility | One function/class, one reason to change. Split validation, computation, and persistence into separate units rather than combining them. |
| Single source of truth | A constant or business rule lives in exactly one place and is referenced elsewhere — never copy-pasted. Duplication is how a value silently drifts out of sync with itself. |
| Folder structure | Organize by feature/domain — matches `02_System_Design.md` §1's module map — not by file type (no `components/` + `containers/` split for the same concern). |
| Formatting | Enforced by ruff in `03_Technical_Architecture.md` §1, not by memory across sessions. |

## 2. Error Handling

- Never leave a catch/except block empty or silent. Every caught error is logged, handled, or re-raised — no bare `pass`/`continue`.
- Use specific exception/error types (`ValidationError`, `ConfigMissingError`), not generic `Exception`/`Error`.
- Fail fast on unrecoverable errors (missing config, invalid startup state) instead of continuing in a broken state.
- Retry only transient failures (network, rate limits), with bounded attempts. Never retry a logic error.
- Log full detail internally; never leak stack traces or internal paths in user-facing or API responses.
- If input crosses a trust boundary (see `09_Security.md` §4), validate right at the boundary — don't let a bad value travel three functions deep before the failure surfaces.

## 3. Documentation (code-level)

> Distinct from `project_docs/` itself — this is what lives *in* the code: docstrings, inline comments, per-directory READMEs.

- Every public function/method gets a docstring: inputs, outputs, exceptions raised.
- Inline comments explain *why*, not *what* — mirrors `05_AI_Collaboration_Rules.md` §19. The code already says what it does.
- Docs update in the same commit as the code they describe. Delete stale docs immediately rather than letting them linger.
- Don't duplicate an explanation that already lives in `project_docs/` — link to it instead of re-writing it.

## 4. Logging

| Level | Use for |
|---|---|
| DEBUG / TRACE | Verbosity only — local troubleshooting, off by default in normal operation |
| INFO | Noteworthy events in normal operation (job started/finished, request handled) |
| WARN | Abnormal but non-fatal — something to watch |
| ERROR | An operation failed — needs attention |
| FATAL | The whole process is going down |

- Structured logs (JSON), not raw `print`/`console.log`, for anything committed.
- Include a correlation/request/task ID in log entries where applicable — not just a bare message string.
- Never log secrets, tokens, passwords, or personal data — this also keeps them out of an agent's context window in a later session.
- Logs answer "what happened in this one case," not "what's the overall trend." Don't build alerting logic against log text when a counter or health check (`03_Technical_Architecture.md` §8) would do the job more reliably.

## 5. What an AI Agent Must Do

Mirrors into `05_AI_Collaboration_Rules.md` Code Quality Rules and Definition of Done:

1. No empty or silent exception handler in any diff — ever.
2. Every public function has a docstring before the task is considered done.
3. Logging goes through the project's established structured-logging setup — never raw `print`/`console.log` in committed code.
4. Naming/casing convention and folder structure are fixed per project (§1 above) — don't improvise a new one mid-session.
5. If a task seems to require violating one of these, stop and ask rather than silently deviating.
6. Never soften a test assertion to tolerate a known bug — if a test path can raise, assert it does not and log the bug in the backlog's open items instead of wrapping the call in `try/except <Error>: pass`.

## 6. Local-Model-Specific Note

A smaller local model under context pressure is the most likely source of a swallowed exception or a skipped docstring — it's optimizing for "make it run," not "make it maintainable." Feed it this doc's relevant section (not the whole file) alongside the code it's touching, and spot-check its diff against §5 before accepting it.

## 7. Test Integrity

A test must never `try/except <SpecificError>: pass` (or `pytest.raises` used as an "either is fine" escape hatch) around the exact code path the test claims to verify. If a call can legitimately raise, the test asserts it does *not*, and the underlying bug gets a line in the backlog's open items (§1 of `13_Bugfix_and_Refactor_Backlog.md`) instead of a pass-either-way assertion. An AI agent should be told explicitly not to "make the test pass" by loosening the assertion — the fix belongs in the code being tested, not the test.
