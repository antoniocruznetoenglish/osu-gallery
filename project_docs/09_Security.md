# Security: osu gallery

> Answers "how do we avoid this getting hacked or leaking data." Skipping this doc isn't "we'll add security later" — it's "we decided, by default, to trust every input and every dependency." Fill this in during the same design pass as 03, not after something breaks.

**Last updated:** 2026-07-16
**Version:** 0.1 · **Status:** Frozen
**Edit cadence:** Should be stable once Frozen, same as 03. Any change here mid-implementation gets a `06_Decision_Log.md` entry.

---

## 0. Network Exposure

**Answer this first — it decides how much of the rest of this doc applies.**

| Question | Answer |
|---|---|
| Network exposure level | None (fully local, no listener) |
| If LAN-only or internet-facing: what's exposed | N/A — no network surface |
| Who else can reach it | Just this machine |

**If "None":** sections 2-4 below can stay minimal — note that explicitly rather than leaving them blank (blank looks unconsidered, "N/A — no network surface" looks decided).

**If LAN-only or Internet-facing:** sections 2-4 are mandatory, not optional.

## 1. Secrets & Credentials

| Question | Answer |
|---|---|
| What secrets exist | None (fully offline, no API keys, no authentication) |
| Where they're stored | N/A |
| What's explicitly NEVER committed | `.env` files, any configuration with secrets (N/A for this project) |
| Rotation plan | N/A — solo local project, no secrets |

## 2. Input Validation & Trust Boundaries

Only required in depth if Network Exposure above is not "None."

| Boundary | Trusted or untrusted input? | Validation approach |
|---|---|---|
| User-pasted .osu code block | Untrusted (could contain malformed data, unusual formatting) | Parse and validate structure, reject on parse errors with clear message |
| File system (saved patterns) | Semi-trusted (user's own files) | Sanitize filenames, validate paths, never execute code from saved files |
| Database (SQLite) | Trusted (local, single-user) | Use parameterized queries, never string-concatenate SQL |

**Rule of thumb:** anything crossing a process boundary (network request, file read, subprocess call, LLM output used to construct a command/query) is untrusted until validated — including output from your own LLM backend, which can hallucinate malformed or unexpected content.

## 3. Dependency & Supply Chain

| Question | Answer |
|---|---|
| Dependency approval process | Same as `03_Technical_Architecture.md` §1 — nothing added without a deliberate decision |
| Vulnerability check cadence | `pip-audit` before each release, or N/A for a never-shipped local tool |
| Do we run any third-party/downloaded model or script without review? | No — fully offline, no external models or scripts |

## 4. Attack Surface Specific to This Project

Name anything unusual for *this* project, not generic advice. Examples to prompt thinking, delete what doesn't apply:

- LLM prompt injection: N/A (no LLM in MVP)
- If a local server binds to `0.0.0.0` instead of `127.0.0.1`, it's reachable from the whole LAN — state which one is intended and why. N/A (no server)
- If scraped/personal data never leaves the machine (per `01_Product.md` §7), name what would violate that (e.g., an accidental telemetry call in a dependency). N/A (fully offline)

## 5. AI Agent Rules (mirrors into `05_AI_Collaboration_Rules.md`)

- Never hardcode a secret, API key, or credential in source — flag if one is needed and ask where it should live.
- Never disable a validation/sanitization step to "make a test pass" without flagging it explicitly.
- Never construct a shell command, SQL query, or file path via raw string concatenation of untrusted input — use parameterization or an allowlist.
- Any new network-facing endpoint is a Decision Log entry (`06_Decision_Log.md`), same tier as a dependency or architecture change.

## 6. Incident / Rollback Plan

Only needs real depth if Network Exposure is not "None."

| Question | Answer |
|---|---|
| If something is compromised, how do we know? | N/A (no network surface) |
| Rollback mechanism | Git revert + redeploy (if packaging in v2) |
