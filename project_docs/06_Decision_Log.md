# Decision Log: osu gallery

**Version:** 0.1 Â· **Status:** Living (append-only, never Frozen)

> Append-only. Never edit or delete a past entry â€” if a decision gets reversed, add a new entry that supersedes it and say so. This is what answers "why did we choose X" six months from now, for you and for any AI session that asks.

**When to add an entry:** any time `03_Technical_Architecture.md` changes, a significant architectural call in `02_System_Design.md` is made (module boundaries, data ownership, etc.), a new network-facing surface is added (`09_Security.md`), or an unresolved item from a Feasibility Check (`04_Implementation_Roadmap.md` Â§0) gets resolved. Small implementation details don't need one â€” this is for choices that would be annoying to silently re-litigate.

---

### ADR-001: [Decision title, e.g. "Use SQLite for structured storage"]

| Field | Detail |
|---|---|
| Date | 2026-07-16 |
| Status | Proposed / Accepted / Superseded by ADR-### |
| Context | What problem/question prompted this decision? |
| Why now | What made this the right moment to decide, not later? |
| Decision | What was chosen |
| Alternatives considered | List each, with one line on why it lost |
| Tradeoffs | What this gives up, not just what it gains |
| **Future revisit trigger** | The specific condition under which this should be reopened â€” e.g. "If concurrent multi-writer access becomes necessary." Not "someday," a checkable condition. |

---

### ADR-002: [next decision]

| Field | Detail |
|---|---|
| Date | |
| Status | |
| Context | |
| Why now | |
| Decision | |
| Alternatives considered | |
| Tradeoffs | |
| **Future revisit trigger** | |

---

<!-- Copy the block above for each new decision. Keep entries short â€” a paragraph of context and a table, not an essay. If you're writing more than that, the decision is probably actually two decisions.

The Future Revisit Trigger field is the highest-value line in this file: it converts "should we reconsider X?" from an open-ended debate into a yes/no check against a condition you already wrote down. -->
