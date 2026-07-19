# FINDINGS — long-only earnings-momentum sweep (30 combos)
DESK-100 · 2026-07-16 · screen-grade (single PIT window 2020-2024 dense, price ends 2026-01-22).
Universe: NIFTF500 PIT constituents. Entry D0+1 close. Costs 0.67% RT. **Headline control = a
calendar-matched random-entry placebo (K=200): "beat placebo p95" is the bar, not raw return.**

## VERDICT: no robust edge. 2 of 30 clear the placebo-95 bar — consistent with chance.
At 30 independent trials against a 95th-percentile threshold you expect ~1.5 false positives by
luck alone. We got **2 (B3, A10)** — barely above the noise floor. So the honest read is: **long-only
earnings-momentum, held for weeks, is ~entirely market-drift harvested by the holding structure, not
an information edge.** This confirms — now across 30 constructions — the prior PEAD conclusion
(TE_PEAD_MULTIYEAR PARK, PEAD_EARNINGS_TRAIL no-significance): random-day entry in the same stock for
the same duration beats earnings-day entry in 28/30 combos.

## The only two that cleared (treat as UNPROVEN, not discoveries)
| id | signal | filter | hold | n | mean net% | t | ex_top2% | cens% | placebo p95% | excess |
|---|---|---|---|---|---|---|---|---|---|---|
| **B3** | SUE top-quintile | above 50DMA | 40d | 773 | 5.55 | 9.95 | 5.24 | 1.3 | 4.90 | **+1.41pp** |
| A10 | SUE ≥ 2.0 | none | 40d | 982 | 4.08 | 8.59 | 3.83 | 1.6 | 3.94 | +0.84pp |

Coherent pattern: **both survivors are SUE (standardized unexpected earnings) with a SHORT ~40-day
hold** — not the raw YoY-growth cuts, and not the long 63/126d holds (those are the worst drift-
harvesters). B3 adds trend confirmation (above 50DMA). This is the one thread worth pulling, but:
- 2/30 clearing a single 200-draw placebo is within chance → needs a **fresh-seed placebo re-draw +
  Sameer's /sensitivity pass** before it earns a card. B3's portfolio Sharpe is oddly low (0.31) with
  the deepest DD (-32.7%) despite the best per-trade stats — unexplained, must resolve first.

## Do NOT trust these (artifacts caught)
- **A8 (eps_yoy)** — DEGENERATE: 29.6% censored, one name >30% of P&L, negative ex-top2, t=0.26. eps
  is 82% NaN at source. Excluded.
- **C10 surprise-weighted (13.2%)** and **C7 long-drift 126d (10.3%)** — big raw numbers that are pure
  drift/concentration: C7 has the WORST excess-vs-placebo of all 30 (-3.67pp); C10-SW needs a
  weight-concentration check (unbounded np_yoy weighting → few names dominate).
- **Turnaround (C1/C2/C6)** — the prior single-quarter lead (t=1.13, n=15) does NOT survive multi-year
  (n=254, t=4.77 in isolation but -0.56pp vs placebo). It's real drift in newly-profitable names, not
  an earnings edge.

## Full leaderboard: see results.csv (sorted by excess_vs_placebo). Per-family: conclusions_{A,B,C}.md.

## LIMITATIONS (honest)
- Single PIT window (dense 2020-2023, thin 2024-26); no era-split, no walk-forward/DSR/PBO → screen not cert.
- Price panel CLOSE-ONLY → price-action filters (50DMA, reaction, 52w-high) have NO volume confirmation.
- ~9% universe leak (renames/delistings unaliased). eps combo underpowered.

## OPS FLAG (for Manoj / DESK-100)
`run.py` results.csv is read-modify-write with NO lock → concurrent A/B/C runs silently clobbered
rows (recovered by re-running). Fix before re-use: file lock, OR per-family CSVs + merge step. Ledgers
were never at risk (per-combo files).

## NEXT (if pursued)
1. B3 confirmatory: fresh placebo seed + /sensitivity + resolve the low-Sharpe/deep-DD anomaly.
2. If B3 holds → SUE+trend, 40d hold = one /cheap-test card (NOT a certified sleeve yet).
3. Otherwise: earnings-momentum long-only is closed for this data window — the residual lives (if
   anywhere) in the beta/sector-HEDGED construction that TE_PEAD parked on, which long-only can't capture.
