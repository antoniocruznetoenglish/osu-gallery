# AI Context Brief: osu gallery

**Version:** 0.1 Â· **Status:** Draft / Review / Frozen / Deprecated *(regenerate whenever this drifts from 01-03, 09, 10)*

> This is the whole seed context in under a page. Regenerate it by hand whenever 01-03 (or 09/10) change meaningfully â€” it should never drift far from the source docs. Paste this at the top of a fresh session, especially on a smaller local model where full docs won't fit the context window.

```
PROJECT: [name]
PURPOSE: [1-2 sentences]

CORE LOOP: [User does X â†’ system does Y â†’ user gets Z]

INTERFACE: [CLI / GUI / Web / API â€” and which screens exist]

STACK (frozen â€” do not deviate without asking):
  Language:
  UI/GUI framework:
  Backend:
  AI/LLM backend: [priority order, e.g. local-gguf > Ollama > cloud]
  Storage:

MODULE BOUNDARIES (see 02_System_Design.md Â§1 for full detail):
  UI:        [responsibility] â€” NEVER [violation]
  Backend:   [responsibility] â€” NEVER [violation]
  Storage:   [responsibility] â€” NEVER [violation]

DATA: [what's stored, where, rebuild-vs-preserve summary]

HARDWARE CEILING: [e.g., i5-12400f + RTX 3060 12GB / i7-4770 + RX 5700 8GB]

SECURITY POSTURE (see 09_Security.md for full detail):
  Network exposure: [None / LAN-only / Internet-facing / Varies]
  Secrets storage: [where, if any exist]

NON-NEGOTIABLE CONSTRAINTS:
  -
  -

EXPLICIT NON-GOALS (do not build these):
  -
  -

AI RULES:
  - No new dependencies without asking (see 03_Technical_Architecture.md Â§1)
  - No new modules/screens without asking (see 02_System_Design.md)
  - Architectural changes get a Decision Log entry first (06_Decision_Log.md)
  - Never hardcode secrets; treat untrusted/LLM output as untrusted before executing it (09_Security.md)
  - New logic ships with a test in the same change (10_Testing_Strategy.md)
  - Full rules: 05_AI_Collaboration_Rules.md

CURRENT TASK: [feature ID from 01_Product.md, or "none â€” design phase"]
```

## Mandatory pre-flight check

This travels with the brief so it applies even on tasks that don't load `05_AI_Collaboration_Rules.md`. Before generating any code, answer these in a short checklist â€” don't skip straight to code:

1. **Target module:** which boundary from `02_System_Design.md` Â§1 am I operating inside, and what is it explicitly forbidden from doing?
2. **Dependency audit:** does this introduce any import/library not already listed in `03_Technical_Architecture.md` Â§1?
3. **State footprint:** does this touch existing data structures, or is it isolated to this feature's view/logic?
4. **Trust boundary:** does this touch untrusted input (network, file, user, LLM output) â€” and if so, is it validated before use, per `09_Security.md`?
5. **Test coverage:** does this land in a layer `10_Testing_Strategy.md` Â§2 requires coverage for â€” and if so, is a test included?

If any answer is uncertain, say so and wait â€” don't guess and proceed.
