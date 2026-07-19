# FND_panel_pit — Survivorship-free PIT Panel Build Report (T5 remediation)

[DATA] Result: `ALPHA_RANKER/rnd/panel/panel_pit.parquet` built successfully.

## Data lineage
- Base: `rnd/panel/panel_long.parquet` (148297 rows, 969 symbols)
- PIT universe: `NIFTY500_TICKER_2005_2025_Final.xlsx` (repo root), Sheet1, 42 snapshots 2005-03-31 -> 2025-09-30
- Ticker match: 969/969 panel_long symbols exact-matched in the PIT file; 0 unmatched (dropped at every date): []
- Panel dates preceding the first snapshot (no eligible universe, dropped): 0

## Row counts
- panel_long rows: 148297
- panel_pit rows: 99415 (67.0% kept)
- panel_pit unique symbols (ever eligible at some date): 933
- panel_pit dates: 249, 2005-04-29 -> 2025-12-05

## Coverage by era

| era       |   rows_full |   rows_pit |   pct_kept |   avg_names_per_date_full |   avg_names_per_date_pit |
|:----------|------------:|-----------:|-----------:|--------------------------:|-------------------------:|
| 2005-2009 |       24003 |      17939 |       74.7 |                     429.2 |                    320.2 |
| 2010-2014 |       32073 |      22797 |       71.1 |                     543.6 |                    383.4 |
| 2015-2019 |       37537 |      24872 |       66.3 |                     646.6 |                    463.8 |
| 2020-2025 |       54684 |      33807 |       61.8 |                     782.7 |                    527.8 |

## Verdict
**REAL, survivorship-controlled at the index-membership level.** Filter is purely subtractive (never adds price-less rows); no future snapshot is ever used (backward merge_asof only). Weakest assumption: symbols unmatched to the PIT ticker list are dropped entirely rather than PIT-verified another way -- this is a conservative (bias-reducing) choice, not a lookahead risk, but it does mean the PIT panel's row count reduction combines TWO effects (genuine non-membership at date t, and the small unmatched-ticker dropout) -- see the unmatched list above, it is short.