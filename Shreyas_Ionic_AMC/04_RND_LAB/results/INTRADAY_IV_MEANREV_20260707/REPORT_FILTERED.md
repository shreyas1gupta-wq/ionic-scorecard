# Intraday IV mean-reversion — event-day filter and stop-loss fix attempts — 2026-07-07
Agent's own report-file write was skipped per the leaf-agent no-report-file convention; content below is verbatim from its final report.

## Verdict: NO fix recovers a net-positive result. Do not advance.

Neither the event-day filter, nor any of three stop-loss alternatives, nor the two combined versions turns the straddle_70 baseline positive. Every variant loses, fails the sign gate, and fails the 2x-cost gate. The baseline engine was reproduced exactly (0.0 point difference) before testing any fix.

## Results (all vs baseline: straddle, 70th-percentile IV trigger, 2.0x-credit stop)

| Variant | N | win% | W/L | PF | net/trade | net total | %spot | Sharpe(net) | Sharpe(gross) | Sharpe(2x) | worst day |
|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline_2.0 | 1191 | 52.3 | 0.80 | 0.87 | -1.59 | -1893 | -0.0074 | -0.59 | +0.71 | -1.89 | -249.9 |
| eventfilt_core_2.0 (Fix 1) | 1157 | 52.4 | 0.81 | 0.89 | -1.36 | -1574 | -0.0062 | -0.52 | +0.83 | -1.85 | -249.9 |
| eventfilt_ext_2.0 (+state events) | 1151 | 52.2 | 0.81 | 0.88 | -1.46 | -1685 | -0.0068 | -0.56 | +0.78 | -1.89 | -249.9 |
| sl_3.0 (Fix 2a, wider stop) | 1191 | 52.6 | 0.79 | 0.88 | -1.56 | -1854 | -0.0074 | -0.57 | +0.67 | -1.80 | -344.1 |
| sl_volscaled 2-3x (Fix 2b) | 1191 | 52.6 | 0.80 | 0.89 | -1.43 | -1707 | -0.0067 | -0.52 | +0.75 | -1.78 | -350.8 |
| sl_none / EOD-only (Fix 2c) | 1191 | 52.7 | 0.80 | 0.89 | -1.41 | -1684 | -0.0067 | -0.51 | +0.72 | -1.73 | -401.1 |
| combined_evt_none (Fix 3) | 1157 | 52.8 | 0.81 | 0.90 | -1.19 | -1382 | -0.0056 | -0.43 | +0.81 | -1.67 | -401.1 |
| combined_evt_3.0 (Fix 3) | 1157 | 52.7 | 0.80 | 0.89 | -1.34 | -1551 | -0.0064 | -0.50 | +0.76 | -1.75 | -344.1 |

No variant's Sharpe fell below -2 (range -0.43 to -0.59), so no reversed twins were required under the standing rule. Gross Sharpe stays positive throughout (+0.67 to +0.83) — the real mean-reversion edge still exists and is still eaten by two-sided cost, unchanged by any of these fixes.

## Why the fixes fail

**The event filter is nearly useless on the cell that actually matters.** On the 2.0x baseline, only 2 of 45 stop-trades (accounting for -354 of the total -5,062 stop-drag) sit on scheduled-event days; the other 43 are unscheduled. The top-5 tail days across every stop variant (2025-05-15, 2024-01-23, 2022-06-16, 2024-10-03, 2024-09-12) are all unscheduled market shocks — global routs, midcap crashes, geopolitical days — that no macro calendar could have flagged in advance. The filter never even improves the single worst day (stays at -249.9). Worse, several scheduled-event days were actually profitable reverts (2024-02-01 +106, 2024-08-08 RBI day +95, 2022-03-10 +77), so filtering them out removes real edge along with the tail it was meant to cut — recovering only about 17% of the loss (-1893 to -1574) while remaining deeply negative. Note also that the original report's headline -578 election-day loss was specific to the 1.5x-stop cell; on the actual best (2.0x) cell, that same election day only cost -95.

**"Better stop" is a drag-versus-tail seesaw with no winning seat.** Removing or widening the stop cuts the -5,062 stop-drag (mean improves from -1.59 to -1.41), but the tail balloons in exchange: worst day goes from -250 (2.0x stop) to -344 (3.0x) to -351 (vol-scaled) to -401 (no stop at all). The stop that limits the tail costs more in whipsaw; the stop that cuts the whipsaw drag exposes a bigger gap. Volatility-scaling the stop (widening it exactly when IV is already elevated) is backwards for this purpose — it widens precisely on the days that gap hardest. Even the best combination tested (event filter plus no stop) still nets -1.19 points/trade, Sharpe(net) -0.43, Sharpe(2x) -1.67.

## Weakest assumption
Same as the original report: the 0.25%-of-premium slippage floor is optimistic on exactly the unscheduled shock days that now dominate the tail, so realized results are likely worse than shown here, not better. The 2x-slippage-stress column already sits at -1.67 to -1.89 across every variant.

## Event-calendar note
No usable historical macro calendar existed on disk for this check (the firm's `MACRO_CALENDAR.md` is forward-looking only; the NSE board-meetings JSON files are corporate earnings dates, not macro events). The agent hardcoded an ex-ante list of RBI Monetary Policy Committee decision dates, Union Budget dates (including the full 2024-07-23 budget), and the 2024-06-04 general election result, sourced from RBI press releases, indiabudget.gov.in, and the Election Commission of India. Flagged limitations: the 2026 RBI dates are rhythm-based estimates rather than confirmed dates, the 2022-05-04 RBI move was an off-cycle surprise that could not have been pre-scheduled, and any real deployment would need a properly maintained event feed rather than this static list. None of this changes the verdict, since the tail damage lives almost entirely on unscheduled shock days that no calendar, however well maintained, could have caught.

## Bottom line
Skipping roughly 5-7 scheduled event days per year is nowhere near enough — the strategy's tail risk lives on unscheduled market shocks, and its core is already cost-negative independent of the tail. The kill stands.

## Files
`Shreyas_Ionic_AMC/04_RND_LAB/results/INTRADAY_IV_MEANREV_20260707/` contains the 7 new variant trade CSVs plus the 4 SL-variant files (`trades_base_sl{2.0,3.0,volscaled,none}.csv`, with event-day flags included), `_variants_metrics.json`, and an empty `_drops_variants.json` (zero drops in any variant).
