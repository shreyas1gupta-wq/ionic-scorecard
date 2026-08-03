# KNOWN DEFECT — chain_features_15min.parquet consumer picks a NON-FRONT expiry in 25.6% of buckets
Flagged 2026-08-03 (OPEN_ITEMS_20260803), discovered by `NEWDIM_LEVELS_20260731`. Do not re-use the
broken path below without applying the fix.

## The bug
`chain_features_15min.parquet` (built by `../BACKTEST_QUEUE_20260730/done/150_indicator_mine_features.py`)
has **one row per (bucket, expiry)** — every expiry alive on a given date (weekly near, weekly next,
often a monthly too) contributes its own row for the same 15-min bucket timestamp.

Both `../BACKTEST_QUEUE_20260730/done/155_indicator_mine_signals.py::load_feat()` and this folder's
own `_dev_mine155.py::load_feat()` collapse this to one row per bucket with:
```python
f = f.drop_duplicates("bucket").sort_values("bucket").reset_index(drop=True)
```
`drop_duplicates("bucket")` keeps whichever row is FIRST in file order for a given bucket — the file
is NOT expiry-ordered, so this is effectively an ARBITRARY choice among the expiries alive that day,
not necessarily the front (nearest, min-DTE, most-liquid) one.

**Measured impact** (`NEWDIM_LEVELS_20260731/chain_front.py`, re-verified independently in
`OPEN_ITEMS_20260803/task1_a6_isolate.py`): the naive first-row pick disagrees with the correct
min-DTE expiry in **25.6% of buckets**.

## What this affects
Every Family-A cell in `stage1_report.json` (A1-A10: CE/PE volume imbalance, OTM strike
concentration, the A5/A6 VWAP-proxy bands, A7-A10 OI-quadrant momentum) was computed on this
mis-selected feature table. **A6_vwap_proxy_continue** (reported +4.153 index pts, t=2.576, placebo
p=0.000, n=9,655 — cited to the Principal as the 2nd-best cell in the book) is the cell this was
isolated for; see `OPEN_ITEMS_20260803/task1_a6_isolation.json` (and its accompanying summary) for
the corrected-gross-vs-defect-vs-methodology breakdown. A1-A5, A7-A10 were NOT re-run under this
audit pass — they carry the same defect and their `stage1_report.json` numbers should be treated as
unverified until similarly isolated.

## The fix
`NEWDIM_LEVELS_20260731/chain_front.py` — parses `expiry`, computes `dte = expiry_date -
bucket_date`, drops `dte<0` (stale/expired rows), and keeps the MINIMUM-DTE row per bucket
(deterministic, no reliance on file order). Its output,
`NEWDIM_LEVELS_20260731/chain_front_15min.parquet`, is the corrected feature table — reuse THIS, or
re-derive with the same min-DTE logic, rather than `load_feat()`'s bare `drop_duplicates("bucket")`.

## What was NOT done here (by design, per Principal instruction)
This note does NOT silently rewrite `stage1_report.json`, `chain_features_15min.parquet`, or any
other historical result file in this folder — those stand unedited, as filed, with this flag
pointing at the defect. `promoted_cells.json` (A6/A7/A8/B2/C1/C2 promoted to Stage-2) is likewise
left as-is; Stage-2 itself never completed for A6 (`156_indicator_mine_stage2.py` crashed on a
`pandas` truth-value bug before producing option P&L for any cell — see
`../BACKTEST_QUEUE_20260730/logs/156_indicator_mine_stage2.log`), so no Stage-2 number exists to be
wrong in the first place.
