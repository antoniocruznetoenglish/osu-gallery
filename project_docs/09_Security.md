# Security: osu gallery

> Answers "how do we avoid this getting hacked or leaking data." Skipping this doc isn't "we'll add security later" â€” it's "we decided, by default, to trust every input and every dependency." Fill this in during the same design pass as 03, not after something breaks.

**Last updated:** 2026-07-16
**Version:** 0.1 Â· **Status:** Draft / Review / Frozen / Deprecated
**Edit cadence:** Should be stable once Frozen, same as 03. Any change here mid-implementation gets a `06_Decision_Log.md` entry.

---

## 0. Network Exposure

**Answer this first â€” it decides how much of the rest of this doc applies.**

| Question | Answer |
|---|---|
| Network exposure level | None (fully local, no listener) / LAN-only (homelab) / Internet-facing / Varies (list which components) |
| If LAN-only or internet-facing: what's exposed | e.g., web UI port, API endpoint, remote access |
| Who else can reach it | Just this machine / other machines on my LAN / anyone on the internet |

**If "None":** sections 2-4 below can stay minimal â€” note that explicitly rather than leaving them blank (blank looks unconsidered, "N/A â€” no network surface" looks decided).

**If LAN-only or Internet-facing:** sections 2-4 are mandatory, not optional.

## 1. Secrets & Credentials

| Question | Answer |
|---|---|
| What secrets exist | e.g., API keys, DB passwords, session tokens, cookies |
| Where they're stored | e.g., `.env` (gitignored), OS keychain, config file outside repo |
| What's explicitly NEVER committed | List file patterns â€” enforce via `.gitignore` from day one |
| Rotation plan | If a secret leaks, how is it rotated? (can be "N/A â€” solo local project" if genuinely true) |

## 2. Input Validation & Trust Boundaries

Only required in depth if Network Exposure above is not "None."

| Boundary | Trusted or untrusted input? | Validation approach |
|---|---|---|
| e.g., user-submitted form field | Untrusted | Server-side validation, never trust client-side alone |
| e.g., file upload | Untrusted | Type/size checks, sandboxed storage path, never executed |
| e.g., data from local scraper/dataset | Semi-trusted (your own pipeline, but still sanitize before render/query) | |

**Rule of thumb:** anything crossing a process boundary (network request, file read, subprocess call, LLM output used to construct a command/query) is untrusted until validated â€” including output from your own LLM backend, which can hallucinate malformed or unexpected content.

## 3. Dependency & Supply Chain

| Question | Answer |
|---|---|
| Dependency approval process | Same as `03_Technical_Architecture.md` Â§1 â€” nothing added without a deliberate decision |
| Vulnerability check cadence | e.g., `npm audit` / `pip-audit` before each release, or N/A for a never-shipped local tool |
| Do we run any third-party/downloaded model or script without review? | If yes, name the trust boundary â€” a downloaded GGUF or plugin is still code/data from an untrusted source |

## 4. Attack Surface Specific to This Project

Name anything unusual for *this* project, not generic advice. Examples to prompt thinking, delete what doesn't apply:

- LLM prompt injection: if any user-controlled or scraped text is fed into a prompt whose output triggers an action (file write, command execution, API call), that's an injection surface. State the mitigation (e.g., "LLM output is never directly executed; always passed through a validation/allowlist step").
- If a local server binds to `0.0.0.0` instead of `127.0.0.1`, it's reachable from the whole LAN â€” state which one is intended and why.
- If scraped/personal data never leaves the machine (per `01_Product.md` Â§7), name what would violate that (e.g., an accidental telemetry call in a dependency).

## 5. AI Agent Rules (mirrors into `05_AI_Collaboration_Rules.md`)

- Never hardcode a secret, API key, or credential in source â€” flag if one is needed and ask where it should live.
- Never disable a validation/sanitization step to "make a test pass" without flagging it explicitly.
- Never construct a shell command, SQL query, or file path via raw string concatenation of untrusted input â€” use parameterization or an allowlist.
- Any new network-facing endpoint is a Decision Log entry (`06_Decision_Log.md`), same tier as a dependency or architecture change.

## 6. Incident / Rollback Plan

Only needs real depth if Network Exposure is not "None."

| Question | Answer |
|---|---|
| If something is compromised, how do we know? | Ties to `03_Technical_Architecture.md` Â§8 (Operability) â€” logs, health checks |
| Rollback mechanism | e.g., git revert + redeploy, restore from backup |
