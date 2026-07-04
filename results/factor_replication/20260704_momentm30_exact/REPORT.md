# D-M4 EXACT REPLICATION REPORT — NIFTY200 Momentum 30 + NIFTY100 LowVol 30 v2
Run: `results/factor_replication/20260704_momentm30_exact/` · Arjun Rao (E-004) · 2026-07-04
Benchmark: `datasets/index_daily/factor_navs_principal.parquet` (official NAV, D-009 verified)

## ONE-LINE ANSWER (Principal's "how much error")
- **NIFTY200 MOMENTUM 30** (best variant `mom_Aincl_mcap`): high-coverage era 2020→2026-01 **TE = 6.9%, daily corr = 0.956**. Full-period (2005→) TE 15.6% / corr 0.73 — diagnosed as a missing-price-history artifact, NOT methodology (see root cause). Post-2018 every year corr 0.93–0.98.
- **NIFTY100 LOW VOL 30 v2** (real N100 membership): full-period **TE 8.0%** (v1 was 13.4%), **2016→2026 TE 2.7–4.9% with corr 0.95–0.97 every year** — the <6% target MET wherever universe coverage is full.

## Variants
`mom_Aincl_mcap` (6M+12M incl recent month, liquidity-proxy mcap tilt) tracked best; `mom_Bexcl_mcap` statistical tie (2020+ TE 6.92% vs 6.96%) — the recent-month-exclusion convention cannot be distinguished from tracking data (honest methodology-recovery limit). mcap proxy beat equal-weight by ~0.2–0.3% TE.

## Root-cause diagnosis of the pre-2018 error (done BEFORE reporting)
- Lag test clean (corr peaks at lag 0) → no date/same-bar bug.
- Replica CAGR 9.85% vs official 17.8%, below even the parent index → selection starved of names, not inverted (score sanity: 23/30 overlap with plain 12M momentum).
- **Root cause = universe price-history coverage in the HF panel:** only 63% of the 2007 universe has a full 252d history (rises to 94% by 2022). 2007 and 2012 produced a 0.0% replica return — no valid basket.
- Ticker-alias fix (23 clean 1:1 renames) lifted coverage but not TE (0.732→0.730) — the early gap is history DEPTH, not naming. Fabrication-risk mappings deliberately excluded (HDFC→HDFCBANK, merger many-to-ones, TATAMOTORS absent).

## Deviations from NSE written methodology
| # | Deviation | Est. TE cost |
|---|---|---|
| D1 | free-float mcap unavailable → liquidity proxy (close × 20d median vol), not float×IWF | ~1–2% |
| D2 | 5% cap on mcap variant only | <0.5% |
| D3 | effective date = last trading day of review month; Mar/Sep snapshots forward-filled to Jun/Dec | ~0.5–1% |
| D4 | panel ends 2026-01-22 vs NAV 2026-02-27 — common window used | 0 |
| D5 | no IWF/divisor maintenance | small, episodic |
| D6 | **early-era price-history hole (dominant)** — entire 2005–17 error | data limit, not method |

To close further: niftyindices factsheets (actual constituents diff, true float weights, recent-month convention) + full-depth 2005→ price panel (recovers D6, highest leverage).

## Lookahead self-audit (D-028): PASS-WITH-FLAGS (0 FAIL, 1 WARN)
WARN = cross-sectional z-score inside momentum_scores() — manually cleared (per-rebalance-date, not full-sample). T5: members_asof() most-recent-on-or-before, empty before first snapshot, 42 N200 + 214 N100 snapshots. T7/L5: scores from close.loc[:asof] only; weights applied NEXT trading day; returns booked in-period.

## Files
replicate_factor_indices.py · config.json · headline_summary.csv · era_stats.csv · daily_{variant}.csv ×5 · peryear_*.csv · run2.log

## STATUS NOTE (added at filing, 2026-07-04)
Principal follow-up ordered same day: (1) confirm comparison is frictionless (NSE NAVs carry no transaction costs), (2) corporate-action adjustment forensics on the price panel, (3) early-era coverage cross-check vs `Nifty500_Master_Dataset_2005_2025.xlsx` (1200 tickers incl delisted, 2005→) + `Nifty500_Delisted_2005_2025.xlsx` — the master dataset may FIX D6 on-disk. Forensics run: see `20260704_data_forensics/`.
