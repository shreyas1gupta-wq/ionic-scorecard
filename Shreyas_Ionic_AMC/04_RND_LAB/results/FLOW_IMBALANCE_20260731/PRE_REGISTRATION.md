# FLOW_IMBALANCE_20260731 — pre-registration (written BEFORE any signal/backtest code ran)

## Gate zero (answered by coordinator, cited not re-derived)
OI updates intraday (median gap ~2min on raw prints) BUT `open_interest==0` in the raw 1-min series
means "not reported this bar", not "zero OI" (65.3% of rows are this placeholder; naive diff inflates
flow 110x). FIX: 0->NaN per (strike,option_type,trading_day), ffill within day only, no cross-day/
cross-expiry bleed. Effective OI resolution ~2-3min -> build flow on 5-MIN buckets, not 1-min.

## Metric (chosen a priori, before inspecting any output)
Preferred: (b) net bullish flow = (put_writing_cr + call_buying_cr) - (call_writing_cr + put_buying_cr).
Reason stated in advance: the Principal's own example cites BOTH put writing (44cr) and call buying
(21cr) as bullish evidence and nets them against the bearish side — (b) is the literal decode of that,
(a) (put_writing - call_writing) is reported alongside as a robustness check, not the primary metric.

## Classification (per strike, option_type, 5-min bucket, after OI ffill)
  dOI>0 & dPrice>0 (option's OWN premium) -> long buildup (buying)
  dOI>0 & dPrice<0 -> short buildup (WRITING)
  dOI<0 & dPrice>0 -> short covering
  dOI<0 & dPrice<0 -> long unwind
value_cr = |dOI| * bucket_close_premium * 65 (lot size, Principal-specified) / 1e7
Anomaly gate: |dOI|/prior_level > 0.40 -> excluded from value sums, tallied separately, checked for
clustering by time-of-day / DTE (expect settlement-driven clustering on 0DTE near close).
0DTE handling: buckets after 15:20 on the expiry day itself are EXCLUDED from classification (OI
mechanically collapses toward zero as contracts settle/close out — not a directional bet).
Universe: near-ATM band = day's 09:15 spot +/- 8 strikes (strike step = modal diff of that day's
listed strikes). OTM-wing contribution reported separately, not folded into the primary metric.

## Normalisation (no lookahead)
Expanding intraday z-score of the bucket metric, computed ONLY from buckets 1..k-1 of the SAME
trading day (state resets every day). Minimum 6 prior buckets (30min warm-up) before a bucket is
signal-eligible -> earliest possible signal ~10:00.

## Signal + two-stage confirmation (fixed BEFORE looking at hit rates)
Fire: |z| >= 2.0 (single a priori threshold; not tuned on this data).
Confirm: within window W in {3,5,10,15,20} minutes of the signal bucket's END, a NIFTY spot 1-min bar
CLOSES beyond the signal bucket's own high (if z>=+2, bullish) / low (if z<=-2, bearish).
Entry: next 1-min bar's OPEN after the confirming bar's close (no same-bar fill).
Exit: pathsafe.simulate_exit, stop=15 index pts, target=RR*stop for RR in {1.0,1.5,2.0}, flat by 15:20
close if neither hit (timeout). PESSIMISTIC bound quoted per pathsafe R2/R3.
One position at a time: a new entry is skipped while a prior trade from this study is still open.

## Splits (every cell reported on all of, not just the winners)
DTE bucket: 0 / 1 / 2-4 / 5+.  Expiry type: weekly vs monthly.
Era: pre- vs post-2024-10-01 (SEBI F&O tightening, Herfindahl break).
Held-out: 2026-01..2026-06 reported for promoted cells only, never selected on.

## Trial count (declared before running, for Bonferroni)
Core grid: 5 confirmation windows x 3 RR x 4 DTE buckets = 60 cells (metric b only; metric a and the
weekly/monthly split are reported as robustness views of the SAME 60 cells' underlying trades, not
counted as new independent trials). Added to the firm's running total (m=481, t_bar~3.8 per
INDICATOR_MINE_20260730/stage1_report.json) -> new m~541 -> t_bar ~= 3.9 (two-sided, p<0.05/541).

## Costs
Underlying/futures-equivalent index points. Pre-2024-10-01: 4.47 pts RT; post: 5.97 pts RT; +0.5 pt
slippage each side already folded into those RT figures per task brief. NET pts = gross - cost.

## Random-entry placebo (mandatory, matched)
For every real signal that reaches a trade, draw 200 random entry timestamps matched on (time-of-day
30-min bucket, DTE bucket, era) from all tradable bars in that stratum, run the IDENTICAL exit rule,
same one-at-a-time constraint. p = fraction of placebo-mean pts >= real mean pts (one-sided).

## Kill criteria (pre-registered, hard)
- Fails placebo (p>0.05) on its own DTE bucket -> DEAD in that bucket, reported not hidden.
- profit concentration >30% from one trade -> FRAGILE, flagged regardless of t-stat.
- maxDD (points, running sum) > firm cap proxy -> flagged.
- Anything that only clears in ONE era (pre OR post Oct-2024) -> FITTED PATCH, not promoted.
