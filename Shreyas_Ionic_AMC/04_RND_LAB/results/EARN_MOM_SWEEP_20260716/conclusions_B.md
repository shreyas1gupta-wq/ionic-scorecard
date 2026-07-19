# Family B conclusions — earnings + price-action mixed (Agent: Ishaan Gupta, ML)

Run: 2026-07-16. All 10 combos (B1-B10) executed via `run.py`, results.csv (11 B/A rows total),
ledgers/B*.csv written. one_day_lag_test re-run on the sole survivor (B3): PASS.

## Results table (net of 0.67% RT cost; sorted by excess_vs_placebo_mean)

| combo | signal·cut·filter·hold | n_trades | win% | mean_net% | mean_ex_top2% | cens% | sharpe | maxdd% | placebo_mean% | placebo_p95% | excess_vs_p_mean | **beats_p95** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **B3** | sue Q5(top-20%)·above_50dma·fixed:40 | 773 | 62.1 | 5.55 | 5.24 | 1.3 | 0.31 | -32.7 | 4.14 | 4.90 | +1.41 | **TRUE** |
| B9 | np_yoy Q10·reaction>3%·fixed:40 | 123 | 54.5 | 7.40 | 5.27 | 0.8 | 1.29 | -21.7 | 5.47 | 8.67 | +1.93 | False |
| B4 | np_yoy Q5·reaction>0·fixed:20 | 647 | 52.9 | 1.95 | 1.77 | 0.8 | 0.39 | -19.4 | 1.95 | 2.72 | -0.00 | False |
| B1 | np_yoy Q5·above_50dma·fixed:63 | 800 | 59.6 | 6.57 | 6.20 | 6.1 | 1.52 | -24.8 | 8.15 | 9.24 | -1.58 | False |
| B10 | sue Q5·above_50dma&ret_6m>0·fixed:63 | 610 | 61.1 | 6.27 | 5.99 | 7.7 | 1.10 | -24.8 | 8.08 | 9.14 | -1.81 | False |
| B2 | np_yoy Q5·ret_6m>0·fixed:63 | 849 | 58.3 | 6.31 | 5.98 | 7.9 | 1.54 | -24.9 | 8.90 | 10.01 | -2.59 | False |
| B6 | sue Q5·ret_12m_tophalf·fixed:63 | 632 | 58.7 | 5.67 | 5.35 | 5.1 | 1.09 | -25.1 | 8.01 | 9.32 | -2.33 | False |
| B7 | np_yoy Q5·above_200dma·fixed:63 | 869 | 58.0 | 6.19 | 5.84 | 7.1 | 1.48 | -25.1 | 9.00 | 9.97 | -2.82 | False |
| B5 | np_yoy Q5·near_52w_high>=0.85·fixed:63 | 710 | 59.7 | 6.75 | 6.33 | 6.9 | 1.59 | -24.3 | 8.98 | 10.25 | -2.22 | False |
| B8 | np_yoy Q5·above_50dma·dma:50 | 800 | 39.4 | 3.61 | 3.27 | 0.5 | 0.94 | -38.6 | 5.48 | 6.37 | -1.88 | False |

n_trades all in the hundreds except B9 (123 — the ≥3% reaction cut plus top-decile np_yoy is a
double narrow filter; underpowered, flag accordingly, don't over-read its +1.93 mean-excess).

## Leakage check
`run_one_day_lag_test` on B3 (the survivor): base mean_net_pct=5.552%, lagged(+1d)=5.214%,
collapse=6.1% -> **PASS, graceful decay, not same-bar leakage**.

## Verdict (3-5 lines)

Price-action gating does NOT generally rescue the earnings edge vs its own calendar-matched
placebo — 9 of 10 B combos still lose to the placebo exactly like the A-family smoke (A2, and
B1 itself) showed: the 63-day (and even 40-day) holding structure alone harvests market drift
that a random entry captures just as well or better. Fixed:63 + any np_yoy price filter
(B1/B2/B5/B6/B7) all land -1.6 to -2.8pp *behind* placebo_mean, several also behind placebo_p95
by a wide margin — the filter changes which names get in but not the core problem.

**One survivor: B3** (sue top-quintile · above_50dma · fixed:40) clears beats_placebo95
(mean 5.55% vs placebo p95 4.90%, +1.41pp excess vs placebo mean, t=9.95, n=773, cens only
1.3%, mean_ex_top2=5.24% so not fat-tail-dependent, and it passes the one-day-lag leakage
check at 6.1% collapse). The mechanism plausibly differs from the pure-drift combos: SUE
(standardized surprise, not raw YoY growth) is a genuinely different signal, the hold is
shorter (40td not 63td), and the placebo bar itself is much lower here (4.14%/4.90% vs
~8-9% for the fixed:63 np_yoy combos) — meaning the 40-day drift that random entries harvest
in this stock/period universe is smaller, so it is easier for a real signal to clear it. Two
caveats before treating this as a real edge: (1) portfolio-level sharpe is oddly low (0.31)
versus every other B combo (0.9-1.6) despite the best per-trade stats, and maxdd is the
deepest at -32.7% — worth Sameer Bhat's sensitivity pass before any escalation; (2) SPEC's
CLOSE-ONLY price panel means `reaction` and all price filters here (including B3's
above_50dma) have zero volume confirmation — a filter could be passing on illiquid/thin-volume
closes that would not have filled as modeled; this is a limitation on every B combo, not just
B3.

**Escalate B3 to Sameer Bhat (overfit/sensitivity) before any Gate-4 build** — it is the only
B-family combo that clears the placebo bar, but the sharpe/maxdd mismatch versus its peers is
unexplained and needs a second look before calling it real.
