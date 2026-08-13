# OPENING-WINDOW PATTERNS — first-15min U-shapes and first-30min structures
**2026-07-30 · DESK-100 · 75 cells · 0 survive · U-shape is actively NEGATIVE**

## The ask
Principal: *"CAN WE ALSO CHECK FIRST 15MIN U SHAPE REVERSALS OR FIRST 30MIN PATTERNS SEPERATELY"*

## Verdict
**0 of 75 cells clears the Bonferroni bar of t≈4.14.** Not one reached the placebo stage. And the
15-minute U-shape — the specific idea — is not neutral, it is **consistently and significantly
LOSING**.

## The U-shape family, all 40 cells (the direct answer)
Built from 1-MINUTE bars so the shape is actually resolvable inside the window.

| cell | n | /mo | win | mean pts | avg RR | exp_R | t_NW |
|---|---|---|---|---|---|---|---|
| N_UP_DOWN_30m \| BE_1R_trail *(best in family)* | 197 | 1.9 | 50.8% | +6.51 | 1.24 | +0.111 | **1.23** |
| U_DOWN_UP_30m \| BE_1R_trail | 245 | 2.1 | 43.3% | +3.15 | 1.46 | −0.081 | 0.61 |
| **U_DOWN_UP_15m \| RR1.5** | 211 | 2.0 | **34.6%** | **−12.11** | 1.20 | −0.315 | **−2.71** |
| **U_DOWN_UP_15m \| RR2.5** | 211 | 2.0 | 31.8% | −12.54 | 1.35 | −0.307 | −2.71 |
| **U_DOWN_UP_15m \| PARTIAL_1R_trail** | 211 | 2.0 | 37.0% | **−13.29** | 1.00 | −0.334 | **−3.09** |
| V_SHARP_15m \| RR2.5 | 133 | 1.5 | 31.6% | −13.02 | 1.33 | −0.300 | −2.64 |

Best t_NW in the entire family: **1.23** against a bar of 4.14. Every one of the five 15-minute
U-shape exits loses double digits with a win rate of 32-37%. The 30-minute version is ~zero. The
only mildly positive member is the INVERTED U (arch that fails → short) at t_NW 1.23, which is noise.

**On reversing it** (the standing rule for strongly negative results): gross of the 5.47-point round
trip, `U_DOWN_UP_15m|RR1.5` is −12.11 + 5.47 = −6.64. Reversed that is +6.64 − 5.47 = **+1.17 pts** —
so roughly half the loss is direction and half is cost, and flipping the trade does not rescue it.
Not worth a run.

## First-30min structures — the best of a bad set
| cell | n | /mo | win | mean | avg RR | exp_R | t_NW | pre | post | held-out |
|---|---|---|---|---|---|---|---|---|---|---|
| NARROW_OR_BREAK_DN \| RR2.5 | 497 | 4.0 | 46.7% | +9.94 | 1.54 | 0.127 | 2.60 | +8.07 | +18.50 | +41.38 (n=14) |
| NARROW_OR_BREAK_DN \| BE_1R_trail | 497 | 4.0 | 49.9% | +10.17 | 1.39 | 0.146 | 2.53 | +8.42 | +15.67 | +47.92 (n=14) |
| OR_BREAK_DN \| BE_1R_trail | 1486 | 10.8 | 47.6% | +3.18 | 1.24 | 0.042 | 1.61 | +2.67 | +3.43 | +17.40 (n=43) |
| GAP_FADE \| BE_1R_trail | 1210 | 8.9 | 44.5% | +2.53 | 1.37 | −0.005 | 1.08 | +4.12 | **−7.42** | −13.16 |

The most interesting cell is **narrow-opening-range then DOWNSIDE break** — a narrow first 30 min
(bottom trailing tercile of OR-width/ATR) that then breaks down. It improves across eras
(+8.07 → +18.50 → +41.38) and has avg RR 1.54. But t_NW 2.60 is well under the 4.14 bar, it fires
only **4.0×/month** (below the Principal's 10-100 band), and the held-out slice is 14 trades. Not a
finding — a candidate to re-check when 2026-27 data accumulates.

Note the asymmetry worth remembering: **the DOWNSIDE opening break works and the upside one does
not**, which is the opposite sign to the candle-formation result where only bullish patterns paid.
That is consistent with opening breaks being a liquidity/vol effect rather than a drift effect.

## Why the opening window was worth its own test
`STRUCTURAL_EDGES_20260730` had already measured first-30min-vs-midday absolute return against a
RANDOM-WINDOW null and it came back **REAL** — the only intraday-seasonality cell that did
(last-30min did NOT). Intraday seasonality was also era-stable, corr(era1, era3) = 0.893 across 75
buckets. So there was a genuine prior here. The prior was about **volatility**, and it does not
convert into a directional edge.

## Controls applied
- One trade per day per pattern, so the concurrency defect that inflated the 15-min candle sweep's
  t-stat ~10× cannot arise here by construction.
- All exits through `lib/pathsafe`: target = resting limit, stop resolves ADVERSELY, both intra-bar
  bounds returned. **0 of 75 cells flagged unreliable.**
- Newey-West t at 5 lags reported alongside the naive t.
- Era split Oct-2024, 2026 held out, scheduled event days excluded, costs era-correct (4.47/5.97
  index pts + 0.5 slippage).
- Random-DAY placebo was built and armed but **no cell qualified to enter it** — which is itself the
  verdict.

## Files
`opening_patterns.py` · `cells.csv` (75 cells) · `placebo.csv` (empty by design) · `meta.json` ·
`run_log.txt`
