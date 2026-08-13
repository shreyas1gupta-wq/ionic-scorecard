# QFRA 2.0 "8-Year Recommendation History" Rebuild -- Findings

**Owner:** Manoj Pillai (Ops/Platform). **Date:** 2026-08-04.
**Script:** `Shreyas_Ionic_AMC/09_PRODUCT/scripts/qfra2_history_rebuild.py` (new, read-only vs source).
**Outputs:** `Shreyas_Ionic_AMC/03_RESEARCH_DESK/qfra2_pac_prep/QFRA2_history_rebuilt.{csv,md}`
**Source (read-only, untouched):**
`C:\Users\Shreyas.1Gupta\Downloads\Mf_qfra2-20260529T103217Z-3-001\Mf_qfra2\mr_x_framework\outputs\recommendations\QFRA2_recommendation_history.csv` (+ `.md` beside it).
**Rendering being replaced:** the hand-built `HIST` dict in `mr_x_framework/src/qfra2_deck_v4.py` (~line 333-349), which feeds the "8-year track record" slides.

## [DATA] What the source actually contains

Verified with pandas, not by eye: 272 data rows = 8 categories x 17 periods x 2 ranks, **every
(period, category) pair has exactly rank 1 and rank 2 present, no nulls, no rank-1==rank-2 dupes.**
Periods run 2018-H1 through 2026-H1 contiguous, no skipped half-year. `source` column: 224 rows
"reconstructed" (2018-H1..2024-H2, cached point-in-time panel), 48 rows "live" (2025-H1 onward,
live engine runs) -- that split is a provenance note on the source, not a gap.

**This means Defect 2 (missing periods) is 100% a rendering artifact, not a data hole.** The
source CSV -- and even the plain `.md` beside it -- already lists all 17 periods per category. No
carry-forward inference was needed to fill a gap, because there is no gap. [INFERENCE] applies
only to which COLUMN (slot 1 vs slot 2) a fund is placed in, never to whether a period/holding
exists. Confirmed no data problem to flag on this front.

The actual defect source is `qfra2_deck_v4.py`'s hardcoded `HIST` dict, which is manually curated
down to "each row = a change" (its own in-slide caption) -- i.e. someone hand-collapsed the full
per-period table into transition rows, and that collapsed version is what ships in the deck.

## Defect 1 -- slot churn, confirmed with a real example

`HIST["Large Cap"]` includes the transition `("2020-H2", "Nippon India Large Cap", "JM Large
Cap")` then `("2022-H1", "JM Large Cap", "ICICI Pru Bluechip")`. **JM Large Cap Fund-Reg(G) is
continuously held for both these rows** (2020-H2 through 2024-H2, unbroken) -- but it is printed
as "Pick 2" in the first row and "Pick 1" in the second, purely because Nippon (the *other* pick)
rolled off and ICICI Pru Bluechip took its place. A reader cannot tell JM Large Cap was held the
whole time; it looks like two different events.

**Fix:** `build_stable_slots()` in the new script assigns slot1/slot2 by fund identity: both slots
carry forward unchanged whenever their occupant is still in the pair; a replacement always lands
in the *departing* fund's slot. A continuing fund can never move columns.

**Verification (independent re-derivation from the OUTPUT, not from the algorithm's own bookkeeping
-- `verify_zero_stable_swaps()`):**

| | Continuing-fund slot swaps |
|---|---|
| BEFORE (naive rank-as-slot, i.e. today's method) | **15** (across all 8 categories) |
| AFTER (stable slots) | **0** |

Per-category naive swap counts: Large Cap 1, Large & Mid Cap 4, Mid Cap 0, Flexi Cap 3, Multi Cap
6, Small Cap 0, Focused 0, Value/Contra 1. (Mid Cap, Small Cap, Focused show 0 because their
"slot-1" incumbent happened to stay rank-1 for its entire tenure in the old data too -- the bug is
real but was silently getting lucky in those three; Large & Mid Cap and Multi Cap were the worst
offenders.) The script's own `main()` re-asserts the AFTER count is exactly 0 and will raise
`AssertionError` (hard fail, not silent) if a future edit to the algorithm ever reintroduces a
swap.

## Defect 2 -- missing periods, fixed by not collapsing

Every one of the 136 (category, period) rows is now emitted. "Changed (shown pre-fix)" = the row
would have appeared in the old changes-only table; "Held (hidden pre-fix)" = it was previously
invisible.

| Category | Periods | Shown pre-fix | Hidden pre-fix |
|---|---|---|---|
| Large Cap | 17 | 5 | 12 |
| Large & Mid Cap | 17 | 7 | 10 |
| Mid Cap | 17 | 6 | 11 |
| Flexi Cap | 17 | 5 | 12 |
| Multi Cap | 17 | 7 | 10 |
| Small Cap | 17 | 3 | 14 |
| Focused | 17 | 5 | 12 |
| Value/Contra | 17 | 5 | 12 |
| **TOTAL** | **136** | **43** | **93** |

93 of 136 category-periods (68%) were invisible in the old rendering. Small Cap was the worst case
named in the brief (3 shown of 17 -- 82% hidden); confirmed exactly: old table jumps
2018-H1 -> 2021-H1 -> 2025-H1, this rebuild shows all 17.

Note: all 8 categories in the source were rebuilt, including Focused and Value/Contra, which the
deck's separate "Decision/ask" slide calls out-of-scope *for capital deployment* -- that is an
adoption decision unrelated to whether their historical table is correct, so I did not drop them.

## Data problems found: none on the table-correctness front

No missing holding, no ambiguous period, no rank ties. The only two judgment calls made, both
disclosed and mechanical (never fabricate a fund or a date):

1. **Full-turnover tie-break.** 6 of the 43 "changed" events replace *both* funds at once (e.g.
   Large Cap and Small Cap both flip their whole pair at 2025-H1). With no continuing fund to
   anchor a slot to, the script assigns that period's own rank-1 -> slot1, rank-2 -> slot2 as a
   documented, deterministic tie-break -- both funds are real rows for that period; only the
   column choice is arbitrary. Flagged in the CSV `note` column as `"both replaced (full
   turnover)"` so it is auditable, not hidden.
2. **Display short names** (`slot1_fund_short`/`slot2_fund_short`, additive columns, CSV's
   canonical `slot1_fund`/`slot2_fund` are always the untouched source string): a deterministic
   suffix-strip (drops trailing `Fund(G)`, `-Reg(G)`, `- Growth Option - Direct Plan`, etc.),
   anchored at end-of-string so it never touches a distinguishing tail like "Series II" vs "Series
   VII" (both Sundaram Value Fund entries verified intact and distinct).

## Row count per category / slide-fit recommendation [OPINION]

Every category now has **17 rows** (constant, since there are no gaps) with a 4-column table
(Period, Slot 1, Slot 2, Status). Fund name strings run up to 46 chars full / 31 chars shortened.

- **A 17-row x 3-text-column table does not comfortably fit two-per-slide** the way the old
  5-7-row transition tables did (that layout, `hist_table()` in `qfra2_deck_v4.py`, stacks two
  tables per slide at ~0.3in/row -- 17 rows alone is ~5.1in, already most of a slide's body height
  before a second table is added).
- **Recommended primary slide visual: a compact heat-strip/grid, not a text table** -- one row per
  category (8), one column per period (17), shaded by held/changed, which is exactly what a
  17-period x 8-category matrix is built for and reads as a pattern ("this book barely moves") at
  a glance. Pair it with a short callout list of just the most recent 1-2 changes per category
  (already have the data: filter `changed_flag==True` sorted by period descending).
- **Keep the full 17-row per-category table** (already generated in
  `QFRA2_history_rebuilt.md`) **as an appendix/backup slide per category** (or a linked doc) for
  anyone auditing a specific fund's tenure -- that is the followable, no-gaps table the Principal
  asked for; it is just too tall to be the headline slide visual for all 8 categories at once.
- Did not build the heat-strip image itself (out of scope for this pass -- deliverable was CSV +
  markdown); flagging the recommendation now so whoever next touches `qfra2_deck_v4.py` doesn't
  default back to hand-curated transition rows.

## Validation commands run

```
python qfra2_history_rebuild.py          # exit 0, wrote 136-row CSV + MD
python qfra2_history_rebuild.py          # re-run: byte-identical stdout -> idempotent, confirmed
```
Guard tests (in-memory corrupted copies only, source file never touched): missing column, a
genuine 1-rank gap, and a rank-1==rank-2 duplicate were each fed to `validate_source()` and each
correctly raised `AssertionError`; the real source passes clean. Full detail and per-category
tables: `QFRA2_history_rebuilt.md` in this folder.
