# Implementation Roadmap 5: Parser Spec Compliance & Timing Accuracy

> **Where this plan came from:** `MapWizard.Tools` (the repo added to the local
> filesystem MCP) doesn't actually contain a parser — it depends on a separate
> NuGet package, `MapWizard.BeatmapParser` v1.0.6, whose source isn't present
> in any of the folders added so far (`E:\MapWizard`, `E:\MapWizard\Other Repos`).
> What *is* present is `Other Repos\osu file format.md` — a saved copy of the
> official osu! file format reference. That's what this roadmap is built
> against: the authoritative spec, not MapWizard's specific implementation.
> If the actual `MapWizard.BeatmapParser` source becomes available later,
> re-diff this plan against it, but nothing here should be blocked on that.
>
> **Why this is a new roadmap file, not a `13_Bugfix` entry:** per
> `13_Bugfix_and_Refactor_Backlog.md` §0's own rule, a new numbered roadmap
> is for genuinely new, large, forward-looking work — not "fix what the last
> one claimed to fix." The parser was already substantially rewritten since
> the last time it was audited (field order is now correct: `x,y,time,type,
> hitSound,objectParams,hitSample`, combo colour is correctly derived from
> the new-combo and colour-skip bits instead of read as a fake field). What's
> below is new, deeper work on top of that: real curve-type coverage and a
> timing/velocity subsystem that doesn't exist yet. Two small leftover
> regressions found during this session's re-verification (BUG-107, BUG-108)
> were logged in `13_Bugfix_and_Refactor_Backlog.md` instead, since those really
> are "finish what the last fix missed."

**Created:** 2026-07-17
**Status:** Planned (not started)

---

## Task Summary

| # | Task | Priority | Depends On |
|---|---|---|---|
| 1 | Add Perfect-circle (`P`) slider curve support — still missing | Critical | — |
| 2 | Fix inverted BPM calculation | Critical | — |
| 3 | Replace per-slider `multiplier`/`tick_rate` guesswork with real `[Difficulty]` + inherited-timing-point velocity | High | Task 2 |
| 4 | Report BPM as a range when a map has multiple uninherited timing points | Medium | Task 2 |
| 5 | Cast hit object `x`/`y` through `float` before `int` | Low | — |
| 6 | Add default values for optional trailing `[TimingPoints]` fields | Low | Task 2 |
| 7 | Replace parser test fixtures with samples covering all four curve types + multi-timing-point maps | High | Tasks 1–3 |

---

## Task 1: Perfect-Circle (`P`) Slider Support — Still Missing

**Problem:** The official format defines four slider curve types: `B`
(bézier), `C` (centripetal catmull-rom), `L` (linear), `P` (perfect circle,
limited to exactly three points). The current parser's slider regex and
path-type check still only accept `L`, `B`, `C` — plus an invalid `O` that
was never a real curve type to begin with. This is the same gap flagged
in an earlier bugfix pass, and it survived the parser's field-order rewrite
because none of the "real .osu file" test fixtures used a `P`-type slider.
Perfect-circle curves are extremely common in real maps (most simple arcs
and circular jumps use them), so any real map that includes one silently
drops that entire hit object — not just the curve, the whole slider — since
the malformed line raises `ParseError`, which is caught and skipped one
level up.

**Goal:** `P`-type sliders parse correctly, including the "more than 3
points falls back to bézier" rule the spec calls out explicitly for this
curve type.

**Files to change:**
- `osu_gallery/parser/osu_file.py` — `_parse_hit_object`'s slider regex, `_parse_slider_path`

**Implementation plan:**

1. In `_parse_hit_object`, change:
   ```python
   slider_match = re.match(
       r"^([LBCO]\|(?:[\d.:|]+)),(\d+),([\d.]+)(?:,(.*))?$",
       slider_body,
   )
   ```
   to:
   ```python
   slider_match = re.match(
       r"^([LBCP]\|(?:[\d.:|]+)),(\d+),([\d.]+)(?:,(.*))?$",
       slider_body,
   )
   ```
   (Drop the invalid `O`, add the real `P`.)

2. In `_parse_slider_path`, change:
   ```python
   if path_type not in ("L", "B", "C"):
   ```
   to:
   ```python
   if path_type not in ("L", "B", "C", "P"):
   ```

3. Handle `P`'s point-parsing the same way `C` is currently handled
   (groups of 3 control points), since both use the same "collect all
   points" branch in the current code — no new branch needed structurally.

4. Add the "more than 3 points degrades to bézier" rule: after parsing a
   `P`-type segment, if the resulting point count (including the hit
   object's own position as the first point) is anything other than
   exactly 3, re-tag the segment's `path_type` as `"B"` instead of `"P"`.
   This matches the spec's explicit fallback behavior and avoids downstream
   rendering code having to special-case a "perfect circle" that isn't
   actually 3 points.

**Tests to add:**
- `test_parse_perfect_circle_slider` — a real 3-point `P|x:y|x:y` slider parses without error, path segment has `path_type == "P"`.
- `test_perfect_circle_more_than_3_points_degrades_to_bezier` — a `P`-type slider with 4+ points parses with `path_type == "B"` instead.
- `test_perfect_circle_with_2_points_is_still_valid` — 2-point (line-degenerate) `P` sliders don't crash the parser (edge case some editors historically produced).

---

## Task 2: Fix Inverted BPM Calculation

**Problem:** `_parse_timing_points()` has the uninherited/inherited logic
backwards relative to the spec. Per the format: an **uninherited** timing
point's `beatLength` is **positive** and directly gives BPM as
`60000 / beatLength`. An **inherited** timing point's `beatLength` is
**negative** and represents a slider-velocity percentage multiplier, not
a BPM value at all. The current code does the opposite — it only computes
`bpm` when `ms_per_beat < 0` (treating an SV multiplier as if it were a
beat length), and explicitly does nothing (`pass`) when `ms_per_beat > 0`,
which is where the actual BPM lives. The practical effect: any map with
only one, normal, single-BPM timing point (the overwhelming majority of
real maps) computes `bpm = 0.0`, and any map that happens to also have an
inherited (green line) timing point will compute a nonsense "BPM" from
that SV percentage instead.

**Goal:** BPM is computed from the correct (positive, uninherited) timing
points, matching the worked example in the spec: a timing point with
`beatLength = 333.33` is BPM 180 (`60000 / 333.33`).

**Files to change:**
- `osu_gallery/parser/osu_file.py` — `_parse_timing_points`

**Implementation plan:**

1. Rewrite the loop so it only considers **positive** `beatLength` values
   (uninherited timing points) as BPM sources, and skips negative values
   entirely for this calculation (they're inherited SV multipliers — Task 3
   is where those actually get used, for slider velocity).
2. Use the **first** uninherited timing point's BPM as the map's headline
   BPM (matching what players/mappers expect to see as "the" BPM of a map),
   not the last one parsed — current code has no defined precedence since it
   overwrites `bpm` on every matching line without picking a clear "first
   wins" or "most common wins" strategy. First-wins is the simpler, spec-
   consistent choice for now (see Task 4 for handling multi-BPM maps properly
   later).
3. Also read the `uninherited` field (7th comma-separated value, `0` or `1`)
   directly instead of inferring it from the sign of `beatLength` — the spec
   defines both a sign convention *and* an explicit flag; older or hand-edited
   files occasionally have a positive `beatLength` on a line explicitly
   flagged `uninherited=0`, which the sign-only check would misclassify.
   Prefer the explicit flag when both are present; fall back to the sign
   check only if the flag field is missing (very old format versions).
4. Guard against `beatLength == 0` (division by zero) — return `0.0` for
   that line rather than crashing or producing `inf`.

**Tests to add:**
- `test_bpm_single_uninherited_timing_point` — `10000,333.33,4,0,0,100,1,1` → BPM 180 (matches the spec's own worked example).
- `test_bpm_ignores_inherited_negative_timing_points` — a map with one uninherited point and one inherited (negative, SV-only) point still reports the uninherited point's BPM, not something derived from the negative value.
- `test_bpm_uses_uninherited_flag_over_sign_when_present` — a contrived case where the flag and sign would disagree; flag wins.
- `test_bpm_zero_beatlength_does_not_crash` — malformed `beatLength=0` returns `0.0`, not an exception or `inf`.

---

## Task 3: Real Slider Velocity — Stop Misreading Per-Object Fields

**Problem:** `SliderData.multiplier`/`tick_rate` are currently populated
from `opt_parts[3]`/`opt_parts[4]` of a slider's trailing optional fields.
But per the spec, slider objectParams only ever have five parts —
`curveType|curvePoints,slides,length,edgeSounds,edgeSets` — there's no
per-slider "multiplier" or "tick rate" field at all. Those concepts exist
only at the map level (`SliderMultiplier`/`SliderTickRate` in `[Difficulty]`,
which the parser already reads correctly into `osu.difficulty`), modified
per-timing-section by the effective **inherited** timing point's negative
`beatLength` (a percentage: e.g. `-50` doubles velocity, clipped in practice
to a sane range). Right now `opt_parts[3]`/`[4]` are actually reading into
whatever position `edgeSounds`/`edgeSets` happen to occupy — meaningless
values that don't correspond to velocity at all.

**Goal:** Actual slider velocity/duration for a given slider is computed
from the map's base `SliderMultiplier` and the effective inherited timing
point covering that slider's start time, per the spec's own formula:
`length / (SliderMultiplier * 100 * SV) * beatLength` gives the time in ms
for one pass of the slider, where `SV` is `1` if there's no covering
inherited point.

**Files to change:**
- `osu_gallery/parser/models.py` — `SliderData` (drop the misleading per-object `multiplier`/`tick_rate` fields, or repurpose them clearly as "effective," computed post-hoc)
- `osu_gallery/parser/osu_file.py` — `_parse_slider_data`, `_parse_timing_points` (or a new `_parse_timing_points_full` that returns structured timing points instead of just a float)

**Implementation plan:**

1. Stop parsing `multiplier`/`tick_rate` out of a slider's own comma fields
   entirely — there's nothing there to parse. Remove `multiplier_str`/
   `tick_rate_str` extraction from `_parse_slider_data`'s call site.
2. Introduce a small `TimingPoint` structure (offset, beat_length, is_uninherited)
   and have timing-point parsing build a full ordered list, not just a
   single float BPM. This is the natural extension of Task 2's fix — same
   section, same loop, just keep the whole list instead of collapsing it
   to one number immediately.
3. Add a helper that, given a hit object's `time` and the ordered timing
   point list, finds the effective inherited SV multiplier and the parent
   uninherited `beat_length` covering that time (walk backwards through the
   list for the most recent timing point at or before `time`, same approach
   the spec's own example uses).
4. Compute each slider's actual duration/velocity from that, store it on
   the `HitObject`/`SliderData` as a clearly-named computed field (e.g.
   `effective_velocity_multiplier`, `duration_ms`) rather than reusing the
   old misleading field names.
5. This doesn't need to change anything about the current static thumbnail
   rendering (which draws the curve shape, not playback timing) — it's
   groundwork for anything that later needs accurate slider duration
   (animated previews, per the Extensibility Roadmap in `04_Implementation_
   Roadmap.md` §2), and for not storing wrong data that looks plausible.

**Tests to add:**
- `test_slider_velocity_no_inherited_point` — a slider with no covering inherited timing point uses `SV = 1`.
- `test_slider_velocity_with_inherited_point` — a slider covered by an inherited timing point with `beatLength = -50` computes `SV = 2.0`.
- `test_slider_duration_matches_spec_formula` — a slider with known `length`, `SliderMultiplier`, `SV`, and `beatLength` produces the exact duration the spec's formula predicts.
- `test_slider_data_no_longer_has_fake_multiplier_field` — regression test confirming the old misleading fields are gone or renamed, so nothing downstream can accidentally read them again.

---

## Task 4: BPM Range for Multi-BPM Maps

**Problem:** Task 2 makes single-BPM maps correct, but maps with multiple
uninherited timing points (BPM changes mid-map) will still only report
whichever one Task 2's "first wins" rule picks. Mappers and players
generally expect to see a range (e.g. "160–200 BPM") for maps like that.

**Goal:** `OsuFile` exposes both a primary BPM (first uninherited point, for
backward compatibility with existing DB/UI code that expects one number)
and, when there's more than one distinct uninherited BPM, a `bpm_min`/
`bpm_max` pair.

**Files to change:**
- `osu_gallery/parser/models.py` — add `bpm_min`/`bpm_max` to `OsuFile`
- `osu_gallery/parser/osu_file.py` — compute both while building the timing point list from Task 3
- `osu_gallery/db/models.py`, `osu_gallery/db/database.py` — add `timing_bpm_min`/`timing_bpm_max` columns (nullable/defaulting to `timing_bpm` when there's only one value), migration
- `osu_gallery/ui/_preview_pane.py` — display `"160–200 BPM"` when min≠max, otherwise the existing single-number display

**Implementation plan:** straightforward extension once Task 3's full
timing point list exists — this is a low-effort follow-on, not a separate
parsing pass. Keep `timing_bpm` as the single-number field everything
already depends on (first uninherited BPM) so this task adds columns
rather than changing existing ones.

**Tests to add:**
- `test_bpm_range_single_bpm_map` — `bpm_min == bpm_max == timing_bpm` for a normal map.
- `test_bpm_range_multi_bpm_map` — a map with two distinct uninherited BPMs reports the correct min/max.
- `test_preview_pane_shows_bpm_range_when_applicable` — UI test confirming the "–" range format only appears when min≠max.

---

## Task 5: Float-Then-Int Coordinate Casting

**Problem:** The hit object regex requires `x`/`y` to match `[\d.]+` and
the code casts them with `float(...)` already (this part is fine) — but
worth double-checking this holds for genuinely malformed/older files where
a coordinate might have a leading `+`/`-` sign (negative coordinates do
occur near screen edges in some real maps and converts). Currently the
regex `[\d.]+` has no allowance for a minus sign, so a hit object at a
negative x or y (rare but real) would fail to match and get silently
dropped, the same failure mode as the P-slider bug.

**Files to change:** `osu_gallery/parser/osu_file.py` — the hit object regex in `_parse_hit_object` and `_extract_hit_sample`

**Implementation plan:** change `([\d.]+),([\d.]+)` to `(-?[\d.]+),(-?[\d.]+)` for both `x` and `y` capture groups (both occurrences of the regex — `_parse_hit_object` and `_extract_hit_sample` currently duplicate this pattern; fix both or extract it to a shared constant while touching this).

**Tests to add:**
- `test_hit_object_negative_x_coordinate` — a hit object with `x = -5` parses successfully instead of raising `ParseError`.

---

## Task 6: Defaults for Optional Trailing `[TimingPoints]` Fields

**Problem:** Very old `.osu` format versions can omit trailing fields on a
timing point line (meter, sample type/set, volume, uninherited flag, kiai
effects). A parser that assumes a fixed field count will reject those
lines outright. Low priority since it only affects importing older-format
maps, but cheap to add while already touching this code for Tasks 2–4.

**Files to change:** `osu_gallery/parser/osu_file.py` — wherever the Task 3 timing point structure parses each line

**Implementation plan:** when splitting a timing point line, use safe
indexed access with per-field defaults instead of unpacking a fixed number
of comma-separated values — same idea already used elsewhere in this
parser for `_safe_float`/`_safe_int` on `[Difficulty]`/`[General]` fields.
Defaults per the spec: `meter=4`, `sampleSet=0`, `sampleIndex=0`,
`volume=100`, `uninherited=1`, `effects=0`.

**Tests to add:**
- `test_timing_point_missing_trailing_fields` — a timing point line with only `time,beatLength` parses using the documented defaults for everything else.

---

## Task 7: Replace/Extend Parser Test Fixtures

**Problem:** The P-slider gap (Task 1) went unnoticed through a prior
parser rewrite specifically because none of the "real .osu file" reference
tests exercised that curve type. Per `13_Bugfix_and_Refactor_Backlog.md`
§2's rule against tests that tolerate known failures, this task exists to
make sure the next rewrite doesn't repeat the pattern.

**Files to change:** `tests/test_parser.py`, `tests/conftest.py`

**Implementation plan:**
1. Confirm (or build, if it doesn't already exist) a real-file fixture that
   includes at least one slider of each of the four curve types (`B`, `C`,
   `L`, `P`), at least two uninherited timing points at different BPMs, and
   at least one inherited timing point with a non-trivial SV change.
2. Every task above gets its test(s) run against this shared fixture in
   addition to the small targeted unit tests listed per-task, so a future
   change can't silently regress one curve type while "fixing" another.
3. Explicitly forbidden per the coding standards addition already made in
   `13_Bugfix_and_Refactor_Backlog.md` §2: no `try/except <Error>: pass`
   around any of these assertions. If a case can legitimately still fail
   given known limitations (e.g. osu!mania hold notes, which this project
   doesn't target), mark it `@pytest.mark.skip(reason="...")` with an
   explicit reason instead of swallowing an exception silently.

---

## Execution Order

```
Step 1: Task 1 (P-slider) — independent, fixes a currently-active data-loss bug
Step 2: Task 2 (BPM inversion) — independent, fixes a currently-active correctness bug
Step 3: Task 3 (real slider velocity) — depends on Task 2's timing point list
Step 4: Task 4 (BPM range) — depends on Task 3's timing point list
Step 5: Task 5 (negative coordinates) — independent, small
Step 6: Task 6 (old-format timing point defaults) — depends on Task 3's structure existing
Step 7: Task 7 (test fixtures) — should track each task as it lands, not be saved for the end
```

**Parallelization opportunities:** Tasks 1, 2, and 5 touch different code
paths and can be done in any order or in parallel. Tasks 3, 4, and 6 form
a dependent chain through the new timing point structure.

---

## Database Schema Changes

```sql
-- Task 4 only
ALTER TABLE pattern ADD COLUMN timing_bpm_min REAL NOT NULL DEFAULT 0.0;
ALTER TABLE pattern ADD COLUMN timing_bpm_max REAL NOT NULL DEFAULT 0.0;
```

Tasks 1, 2, 3, 5, 6 are parser-internal and don't touch the database schema.

---

## Risk Assessment

| Risk | Mitigation |
|---|---|
| Rewriting timing point parsing (Task 2/3) could regress the working parts of BPM/`circle_count`/`slider_count` that already function correctly | Keep the existing `timing_bpm` field's public behavior for single-BPM maps identical before/after; add tests for that explicitly, not just the new multi-BPM cases |
| Real maps may have quirks beyond this doc's coverage (e.g. taiko/mania-converted content, extremely old format versions) | Scope explicitly to osu!standard per this project's existing focus; log anything mania/taiko-specific as a skipped test with a reason, not a silent pass |
| Task 3's "effective velocity" computation is the most complex piece and has no current consumer in the UI | Land it as parser-internal groundwork only in this roadmap; wiring it into an actual animated-preview feature is separately tracked in `04_Implementation_Roadmap.md` §2 Extensibility Roadmap, not in scope here |
| Perfect-circle degrade-to-bezier rule (Task 1) could be missed if only tested with well-formed 3-point sliders | Explicit test for the >3-point degrade case, not just the happy path |

---

## Definition of Done for This Roadmap

- [ ] Task 1: `P`-type sliders parse correctly, including the >3-point bézier fallback
- [ ] Task 2: BPM computed from positive/uninherited timing points, matches spec's worked example
- [ ] Task 3: Slider velocity/duration computed from `[Difficulty]` + effective inherited timing point, not fake per-object fields
- [ ] Task 4: BPM range exposed and displayed when a map has multiple distinct BPMs
- [ ] Task 5: Negative hit object coordinates parse without error
- [ ] Task 6: Old-format timing point lines with missing trailing fields parse using spec defaults
- [ ] Task 7: Shared multi-curve-type, multi-timing-point test fixture in place; no bug-tolerating try/except patterns introduced
- [ ] Full existing test suite still passes
- [ ] `ruff` linting passes with no errors
- [ ] Database migration (Task 4) backward-compatible
- [ ] Feature logged in `04_Implementation_Roadmap.md` §5 Feature Log
- [ ] Any newly-discovered issues logged in `13_Bugfix_and_Refactor_Backlog.md`, not silently fixed without a record
