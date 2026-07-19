# Harness annualization fix + money-first rescore refresh

Owner: Manoj Pillai (Ops/Platform Engineer), 2026-07-17. Fix-it duty per
CONSOLIDATION.md "HARNESS FIXES NEEDED" item 4 (flagged again this wave).
No live capital involved — this is scoring/ranking plumbing only.

## What changed

### 1. `rnd/lib/harness.py` — new horizon-aware annualization (additive, non-destructive)
- Added `HORIZON_YEARS = {"1M": 1/12, "1Y": 1.0, "5Y": 5.0}` (module-level).
- Added `annualize_ls_return(mean_period_return, horizon)`: correctly scales a
  RAW (non-annualized) long-short mean return by how many years the
  forward-return label itself spans — `*12` only for 1M, `*1` for 1Y (the
  label is already annual), `/5` for 5Y (the label is a 5-year cumulative
  return).
- In `evaluate()`, this feeds **two new, additive** card fields:
  `long_short.ann_return_LS_horizon_aware` and
  `costs.net_of_cost_ann_return_horizon_aware`.
- **The old fields (`long_short.ann_return_LS`, `costs.net_of_cost_ann_return`,
  the `periods_per_year=12` line) are UNTOUCHED.** `verdict()` still reads the
  old `net_of_cost_ann_return` key, so the PROMOTE/PARK/KILL gate is
  byte-for-byte unchanged for every card, old and new. No historical card on
  disk was rewritten or mutated by this change — it only affects cards
  `evaluate()` writes from now on (which get the new fields *in addition to*
  the old, unchanged ones).

### 2. `rnd/pragmatic_score_v2.py` — one defensive one-liner (unblocking, not a magnitude change)
`recompute_dsr_per_family()` crashed (`AttributeError: 'float' object has no
attribute 'get'`) on a handful of on-disk `*_SUMMARY.json` files that reuse
the key `"dsr"` for an unrelated p-value-like float from a different card
schema (not a `harness.evaluate()` card at all — those always write `dsr` as
a dict). Added an `isinstance(dsr_block, dict)` guard that treats it as
missing instead of crashing. This is the same class of pre-existing
non-standard/"junk" card already tolerated elsewhere in the script via `g()`'s
isinstance guards (18 such null-id rows existed in the scoreboard **before**
this task); the guard just stops it from crashing the whole run. No effect on
any genuine `evaluate()`-produced card.

pragmatic_score_v2.py's own `horizon_aware_annualization()` (written
2026-07-17, same day, by Sameer Bhat per its module docstring) already
recovers the correct annualization independently — by inverting the OLD
`ann_return_LS` (`/12` then `/HORIZON_YEARS[horizon]`) — so it did **not**
depend on the harness.py fix to work; the harness.py fix is for future
`evaluate()` runs to carry the honest number natively rather than needing the
inversion trick. Ranking within a horizon is a monotonic rescale of v1, so
**no rank/verdict change**, only magnitude.

## Why this matters (bug recap)
`evaluate()`'s old code always multiplied the mean long-short decile-spread
return by `periods_per_year=12`, regardless of horizon:
- **1M**: correct (label IS a 1-month return; ×12 gives an honest annual figure).
- **1Y**: WRONG — label is already a 1-year return; the old code inflated true
  annual return ~12x.
- **5Y**: WRONG — label is a 5-year cumulative return; the old code inflated
  it ~60x (should divide by 5, not multiply by 12).

Cost drag (`ann_cost_drag`) was NOT touched — turnover is measured on the
monthly rebalance grid regardless of label horizon, so `*12` there was
already correct and stays correct.

## Validation — before/after magnitude (same cards, scoreboard_v2.csv columns `gross_LS_v1` vs `gross_LS_v2`/`net_LS_v2`)

| card | horizon | v1 (old, buggy) ann. return | v2 gross (corrected) | v2 net-of-cost (corrected) |
|---|---|---:|---:|---:|
| `CANONICAL_7LEG_1Y` | 1Y | **+369.6%/yr** | +30.8%/yr | +28.4%/yr |
| `LONG_H014_earnings_yield_5Y` | 5Y | **+414.2%/yr** | +6.9%/yr | +5.9%/yr |
| `W4T_distress7_1Y_resid` | 1Y | **−298.3%/yr** | −24.9%/yr | −25.4%/yr |
| `W4T_distress7_5Y_resid` | 5Y | **−5,884.7%/yr** | −98.1%/yr | −98.6%/yr |
| `W4T_MOMQUAL_RA_1Y` | 1Y | **+185.4%/yr** | +15.5%/yr | +13.3%/yr |

Ratios check out exactly against the fix's own arithmetic: 1Y rows are v1/12
(e.g. 369.6/12=30.8); 5Y rows are v1/60 (e.g. 414.2/60=6.9,
5884.7/60=98.1). Earnings-yield 5Y net (~5.9%/yr) is now in the same honest
single-digit-percent ballpark CONSOLIDATION.md's original spot-check flagged
("EY net LS ~2%/yr, NOT 34%") — magnitude corrected, no fabrication, ranking
(within-horizon order) preserved because the correction is a fixed monotonic
rescale per horizon.

## Row counts (scoreboard_v2.csv regenerated over current cards/*.json)

- **Before this task** (backup kept at `rnd/scoreboard_v2.csv.before_38card_refresh.bak`):
  430 data rows / 413 distinct card ids.
- **After re-running `pragmatic_score_v2.py`** over the current on-disk
  snapshot: **500 data rows** (501 lines incl. header).
- **Cards on disk at time of final re-run: 509** (`OK` status: 500,
  `FAIL_GATE`: 95, `PROMOTE*`: 207, `CANDIDATE`: 43) — NOTE: the cards/
  directory is being actively written to by concurrent wave-4 research work
  in this same session, so this count is a point-in-time snapshot, not a
  static "39 missing cards" figure. As of the final re-run, **63 distinct
  OK-status cards that existed on disk but were absent from the
  pre-task scoreboard now have corrected `net_LS_v2`/`gross_LS_v2`** (56 of
  their 63 scoreboard rows populated with a number; the other 5 rows are
  pre-existing non-`evaluate()`-schema duplicate files — same "junk" class
  already present in the baseline, not genuine gaps — see item 2 above).
- Verified by direct re-read of `scoreboard_v2.csv` after the run (not
  claimed from the script's own stdout alone).

## Runtime
`pragmatic_score_v2.py` runs in well under a minute (reads only on-disk
JSON cards + `trials_counter.json`/`backlog.json`, no panel/data reload). No
schedule — run on demand after any batch of new cards, or fold into a future
end-of-wave checkpoint. Not a cron job; no capture-task dependency.

## Rollback
- `harness.py`: the two new fields are purely additive; deleting the
  `annualize_ls_return()` function + its two call sites + the
  `HORIZON_YEARS` dict restores the file exactly to pre-fix behavior (no
  other line touched).
- `pragmatic_score_v2.py`: the `isinstance(dsr_block, dict)` guard is a
  4-line no-op for any well-formed card; removing it only restores the crash
  on the malformed `*_SUMMARY.json` files.
- `scoreboard_v2.csv`: previous version preserved at
  `rnd/scoreboard_v2.csv.before_38card_refresh.bak` (430 rows) if a revert is
  ever needed. `scoreboard.csv` (v1) was never touched.
