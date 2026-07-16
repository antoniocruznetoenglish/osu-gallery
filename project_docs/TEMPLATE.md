# Feature: [Name] (F[n])

**Status:** Draft / In Progress / Done
**Product ref:** `01_Product.md` F[n]

> This file is meant to be fed to an AI agent on its own â€” that's the whole point of it living outside `04_Implementation_Roadmap.md`. Keep it self-contained: a reader shouldn't need the other docs open to understand the contract, though it should reference them by section for detail.

| Field | Detail |
|---|---|
| Purpose | |
| Requirements | |
| UI changes | Which screens from `02_System_Design.md` Â§2, and how |
| Data changes | New/changed fields, referencing `03_Technical_Architecture.md` Â§4 |
| API/interface changes | |
| Dependencies needed | Must already be approved in `03_Technical_Architecture.md` Â§1, or added there first |
| Feasibility Check passed? | Ran `04_Implementation_Roadmap.md` Â§0 â€” any flags raised and how resolved |
| Security considerations | Does this touch untrusted input, secrets, or a network-facing surface? Reference `09_Security.md` if yes; "None" is a valid, explicit answer |
| Testing | What must be covered before this counts as done â€” reference `10_Testing_Strategy.md` Â§2 for the layer(s) touched |
| Health/observability impact | Does this add a new failure mode that should be visible in logs/health checks per `03_Technical_Architecture.md` Â§8? |
| Docs to update | Which of 01-03/09/10 change as a result |
| Acceptance criteria | Concrete, checkable conditions for "this works" |

---

<!-- Copy this file per P0/P1 feature: project_docs/features/F002_your-feature.md, etc.
Small P2 features don't need this â€” a line in 04_Implementation_Roadmap.md's Feature Log is enough. -->
