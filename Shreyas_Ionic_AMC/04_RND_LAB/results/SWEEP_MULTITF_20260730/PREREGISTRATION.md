# PRE-REGISTRATION — Multi-timeframe liquidity-sweep / stop-hunt expansion
Arjun Rao (Quant Head), 2026-07-30. Written BEFORE any cell of this grid is run.
Baseline this expands: `SWEEP_11YR_20260729` (`sweep_priorday_reclaim`, 15-min detection,
prior-DAY hi/lo level, n=4378, config E CAGR 14.40%/MDD -21.66%/Sharpe 1.65/t=3.92;
config D CAGR 10.29%/MDD -12.81%/t=3.31). Simulator/detector code is REUSED verbatim
(`SWEEP_11YR_20260729/sweep_11yr.py::simulate/metrics/heatmap/rt_cost/kelly_from`) —
no new simulator is written. Windows unchanged: IS 2021-05-01..2025-12-31,
PRISTINE OOS 2015-01-09..2021-04-30 (never touched, contains COVID), FWD 2026-01-01..2026-05-14.
Sizing: **1-lot only.** (Kelly01 sizing in the baseline report.json produces degenerate
compounding blow-ups for configs D/E — e.g. config E kelly01 FWD_2026 CAGR reads
1.38e17%, Calmar 3.4e14 — an unbounded-reinvestment artifact, not a real number. Flagged
as a degenerate-detector finding; 1-lot is the only sizing used in this study.)
Configs reused unchanged: **D** (`stop=50,trail=40,hold_days=1`) and **E** (`stop=60,trail=60,
hold_days=3`) only — the two configs already proven to carry the multi-day edge; intraday
configs A/B/C/F are proven dead on the baseline level (PF 0.98-1.11) and are NOT rerun for
every new level (that would be exploring a known-dead cell, wasting trials budget).

## GRID (locked — no cell added or dropped after seeing results)

### Part 1 — Level source x Detection timeframe (main grid)
| # | Level | Detection tf(s) tested |
|---|---|---|
| 1 | prior-DAY hi/lo (baseline @15m done) | 5min, 1h, 4h (NEW — answers "coarser tf" question on the proven level) |
| 2 | prior-WEEK hi/lo | 15min, 1h, 4h |
| 3 | prior-MONTH hi/lo | 15min, 1h, 4h |
| 4 | prior-DAY CLOSE (scalar level, both-direction) | 15min, 1h, 4h |
| 5 | ROUND NUMBER (nearest 100-pt level to previous bar's close, dynamic) | 15min, 1h, 4h |
| 6 | GAP EDGE (today's own open, same-day) | 5min, 15min |
| 7 | OPENING RANGE (09:15-09:45 hi/lo, same-day, signal masked to t>=09:50) | 5min, 15min |
| 8 | SWING PIVOT fractal N=3, confirmed with lag, on 15m bars | 15min (native) |
| 9 | SWING PIVOT fractal N=3 on 1h bars | 1h (native) |
| 10 | SWING PIVOT fractal N=3 on 4h bars | 4h (native) |
| 11 | SWING PIVOT fractal N=3 on DAILY bars | 15min (intraday detection of a daily-swing level) AND 1h |

Combos: 3+3+3+3+3+2+2+1+1+1+2 = **27 level/tf combos x 2 configs (D,E) = 54 cells.**

### Part 2 — Sweep-quality filters (cheap post-filter, reuses Part-1 trade sets, no resimulation)
Applied to the single best-performing NEW combo from Part 1 (by Calmar) plus the
original baseline (prior-day @15m) for comparison, config D and E:
- **Penetration depth** in ATR(14,daily) units at the reversal bar: top-tercile (deepest) vs
  bottom-tercile (shallowest) poke, middle tercile dropped (report both extremes only,
  not a 3-way stack, to avoid the confluence trap).
- **Reversal speed**: bars-to-reclaim within the signal bar's own timeframe, top vs bottom
  tercile of speed.
- **Trend agreement**: sweep WITH prevailing trend (20-day SMA slope same sign as swept
  direction) vs AGAINST trend — 2 buckets, no tercile.
Cells: 2 base combos x 2 configs x (2+2+2 filter buckets) = **24 cells.**

### Part 3 — Option-chain OI/volume confirmation (2021-05 onward ONLY — option data window)
Baseline prior-day-reclaim signals (IS_2021_2025 subset, n=1769) split by whether the
swept level's nearest 50-pt strike carries top-quartile OI (that day's cross-section) at
signal time vs not. Configs D and E, 1-lot.
Cells: 2 buckets x 2 configs = **4 cells.**

### TOTAL HONEST TRIALS THIS STUDY: 54 + 24 + 4 = **82 cells.**
This adds to the firm's cumulative trials ledger (≈349 before today per SHARED_CONTEXT);
the significance bar for THIS sub-study alone (Bonferroni, two-sided, m=82,
alpha_fw=0.05 => alpha_cell=0.05/82=6.1e-4 => |z|≈3.43) is reported alongside each result.
Nothing here is a "validated" claim on its own — it is hypothesis generation per the
firm's BREADTH PROTOCOL; promotion requires the session-wide DSR/PBO pass owed separately.

## KILL / KEEP CRITERIA (fixed before running — do not soften after seeing numbers)
1. **Underpowered, do not interpret**: n < 100 trades over 11.34yr → discard the cell,
   report n only, no stat claim (below the firm's ~30-trades/parameter floor once you
   account for the 2 embedded exit parameters (stop, trail) of configs D/E).
2. **KILL** (no edge): |t_nw_daily| < 2.0 on ALL_11yr, regardless of raw CAGR.
3. **FRAGILE / not yet claimable**: 2.0 <= t < 3.43 (this study's Bonferroni bar) OR
   OOS_PRE_2015_2021 PF <= 1.05 (fails to hold on the pristine untouched segment) OR
   max_trade_share >= 0.30 (one trade drives the result).
4. **PROMISING (forward-test candidate only, never "validated")**: t >= 3.43 AND
   OOS_PRE_2015_2021 PF > 1.05 AND max_trade_share < 0.30 AND n >= 100.
5. **OVERFIT SUSPECT — auto-flag regardless of t**: mean gross pts > 2x the baseline's
   comparable config's mean (12.01-14.66pt for E, 9.63-9.91pt for D) AND n < 200. High
   mean + low n is exactly the failure mode the session already caught once today.
6. **Low-MDD test**: a level/filter counts as a genuine low-MDD improvement over the
   baseline (E: -21.66%, D: -12.81%) ONLY if maxDD improves AND CAGR does not collapse
   proportionally more than the DD improvement (i.e. Calmar must be >= the baseline's
   Calmar: E=0.66, D=0.80). Improving MDD by giving up more CAGR than that is not a win —
   rank everything on Calmar, not CAGR, per the Principal's stated priority.
7. FWD_2026 is reported for every surviving cell but is NOT a selection criterion (5
   months, thin power, and 2025 H2 was the worst stretch in the 11-yr sample per config D
   — this is flagged as an honest live-decay concern, not used to kill or promote).

## PIT / lookahead discipline for the new level types (checked before running)
- Week/month levels: keyed by (ISO year, ISO week) / (year, month); a day's level = the
  PRIOR completed week/month's hi-lo, constant through the current week/month — known in
  full before the current week/month starts.
- Prior-day close: yesterday's close, known at today's open.
- Gap edge / opening range: same-day levels but PIT-safe because (a) gap edge = today's
  own first-bar open, used only for later bars of the SAME day; (b) opening range =
  09:15-09:45 range, masked so no signal fires before 09:50 (5-min buffer past window
  close, so the range is fully known before it's tested against).
- Round numbers: nearest 100-pt level computed from the PREVIOUS bar's close (never the
  current bar being tested).
- Swing pivots (all timeframes): N=3-bar fractal, confirmed only N bars after the pivot
  bar (`pd.merge_asof(..., direction="backward", allow_exact_matches=False)` — strictly
  BEFORE the signal bar). Early history with no confirmed pivot yet is skipped, same
  convention as the original code's `if d not in prior_hi: continue`.
