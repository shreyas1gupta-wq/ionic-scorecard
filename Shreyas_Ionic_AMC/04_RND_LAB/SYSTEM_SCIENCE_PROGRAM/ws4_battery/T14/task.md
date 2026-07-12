# T14 — Review request: selected-nights overnight long, results memo

Memo for an overnight index sleeve. Review the claims and methodology as written.

---

## Overnight selected-nights long — validation summary (2019-2025)

**Signal.** Hold NIFTY futures long overnight only on "selected" nights: prior
20-session realized-vol percentile below 60 AND favourable weekday bucket. Both inputs
are computed at 15:00 from data through 14:59. Entry: futures bought 15:25-15:28
(marketable limit). Exit: next session 09:16-09:20 TWAP. Selected: ~55% of nights
(138/yr average).

**Result.** Gross edge on selected nights **+3.1bp/night**; costs 1.2bp/night round
trip (exchange + impact, futures); net **+1.9bp/night**, ~+2.6%/yr on notional.
Sharpe 1.21 on nightly P&L. t-stat 3.8 over 962 selected nights.

**Controls run.**
- *Unconditional-drift control:* ALL nights in the window earn +0.9bp/night on average
  (the index's ordinary overnight drift). An exposure-matched random-nights baseline
  (55% of nights, same count) earns +0.9bp/night net of the same costs. The selection
  adds **+2.2bp/night over matched exposure** — the claim is selection, not
  "overnight drift in costume".
- *Same-exit placebo:* 500 random night-subsets of identical size, run through the
  identical entry/exit engine and costs. Strategy at the 97th percentile.
- *One-day-lag test:* all inputs lagged one extra session: +3.1bp -> +2.2bp gross
  (graceful degradation, no collapse).
- *Era splits:* 2019-20 +2.4bp, 2021-22 +3.6bp, 2023-25 +3.2bp gross per night.
- *Costs:* taken from the approved futures cost standard; entry uses marketable limits
  and books no fill on the 3 nights the 15:25-15:28 window was limit-locked.

**Capacity/limits.** Futures-only, front month, ~Rs 40cr capacity at 5% participation.
Worst night -1.9%; worst month -1.7%.

**Verdict sought.** Diversifier-grade sleeve (net return modest but uncorrelated with
the day-session books). Recommend the orthogonality check vs existing sleeves next,
then paper.

---

**Review this. Identify any defects that would make the result wrong or fake. Be specific.**
