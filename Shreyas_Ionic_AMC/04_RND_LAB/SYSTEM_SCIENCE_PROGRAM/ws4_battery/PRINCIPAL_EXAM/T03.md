# T03 — Review request: post-earnings drift sleeve, results memo

A results memo submitted for gate review. The underlying code is not attached; review
the claims and methodology as written.

---

## Post-earnings positive-surprise long — validation summary (2021-2025)

**Universe.** NIFTY-200 members, membership taken as-of each date from the 42-snapshot
point-in-time constituent file (Mar/Sep snapshots). Window restricted to 2021-2025
because publication-date coverage in the earnings dataset is reliable only from 2021.

**Signal.** Positive earnings surprise: reported quarterly EPS above the trailing-4-quarter
trend extrapolation by more than one trend residual sigma. Signals are timestamped on the
`available_date` (publication date) of the filing, never the quarter-end.

**Execution.** Enter at the next session's OPEN after `available_date`. Entries skipped
when the open was locked at the upper circuit or the first-15-minute volume was zero
(9 entries dropped this way). Exit at the close of the 10th session after entry, no
exceptions. Costs: 25bp per side all-in (brokerage + impact at large/midcap slippage
standard).

**Result.** 412 trades. Mean net edge **+0.42% of spot per trade** (avg +Rs 3.1 per share
on an avg entry price of Rs 740); t-stat 3.4 (per-trade std 2.5%). Win rate 58%.
On a fixed Rs 50L notional with max 8 concurrent positions: CAGR 9.8%, Sharpe 1.1,
max DD -7.9%.

**Controls run.**
- *Placebo battery:* 200 random-entry baskets drawn from the same universe-dates, same
  trade count, and the SAME 10-session exit engine. Placebo mean +0.06%/trade; the
  strategy sits at the 92nd percentile of the placebo distribution. (Same trade count and
  identical holding period means the comparison is turnover-matched by construction.)
- *One-day-lag test:* lagging every input one extra day degrades the edge +0.42% -> +0.31%
  (graceful decay, no collapse).
- *Era splits:* 2021-22 +0.51%, 2023 +0.29%, 2024-25 +0.44% per trade.
- *Denominator check:* edge reported in % of spot and rupee points per share above;
  no per-premium or net-debit denominators anywhere.

**Verdict sought.** Entry edge appears real against matched nulls but the standalone
return is below the register bar. Recommend advancing to the sensitivity battery
(parameter surfaces, subsamples), NOT direct register entry.

---

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**
