# BACKTEST REPORT — ITM-Sell / 2x-OTM-Same-Side-Hedge Premium-Ratio System
Filed: 2026-07-18. Pre-registration: `PREREG.md` (same folder, filed before this report). Owner:
quant-head-arjun-rao persona. All figures below are [DATA] from the engine described in PREREG.md §3,
run against `Shreyas_Ionic_AMC/05_DATA_OFFICE/data/fo_bhavcopy_hist/` (NIFTY OPTIDX, 2011-2026) and
`datasets/index_daily/factor_navs_principal.parquet` (NIFTY 50 spot). P&L is in **NIFTY INDEX POINTS per
1 signal-unit** (1 short lot + 2 long hedge lots) throughout — lot-size-invariant, see PREREG §3.7.

---

## 0. VERDICT

**ALL FOUR pre-registered primary cells are KILLED.**

| Cell | Cadence/Structure | Window | K1 (ROM>0) | K2 (placebo) | K3 (lag) | Verdict |
|---|---|---|---|---|---|---|
| **M-A** | Monthly, two-sided | 2011-01→2026-07 | **FAIL** (wipeout) | **FAIL** (beats 7/100 shuffles) | n/a (already failed) | **KILLED** |
| **M-B** | Monthly, bull-only | 2011-01→2026-07 | **FAIL** (wipeout) | **FAIL** (beats 11/100 shuffles) | n/a (already failed) | **KILLED** |
| **W-A** | Weekly, two-sided | 2019-02→2026-07 | pass (+8.6%/yr on margin) | **FAIL** (beats 83/100, short of 95) | **FAIL** (collapses >100%, flips to loss) | **KILLED** |
| **W-B** | Weekly, bull-only | 2019-02→2026-07 | pass (+10.1%/yr on margin) | pass (beats 96/100, narrowly clears 95) | **FAIL** (collapses >100%, flips to loss) | **KILLED** |

The headline numbers for the weekly cells look genuinely attractive in isolation (positive CAGR, Sharpe
~0.5, no capital wipeout) — this is exactly why the pre-registered robustness battery matters: a 1-trading-
day execution lag (the minimum realistic slippage between "signal fires at close" and "order actually
fills") **erases the entire edge and flips it negative** for both weekly cells. That is a strong signal the
apparent edge is concentrated in same-instant execution at the exact DMA-crossover close, not a durable
structural premium — see §6.

Monthly cadence fails independently and for a different, more basic reason: it loses money outright
(cumulative loss exceeds its own average margin — a **CAPITAL_WIPEOUT**, see §2), and the signal actively
underperforms random noise (beats only 7 of 100 random same-frequency shuffles — a real edge should beat
essentially all of them; this one is worse than a coin flip). §7 explains why: weekly signal-checks inside a
slower monthly roll generate whipsaw costs that a permanently-held ("always-on") version of the same
structure does not pay.

---

## 1. Mechanics actually run (see PREREG.md §3 for the full spec)

Signal `bull = (close>20DMA) OR (close>50DMA)`, evaluated at close (no lookahead — a DMA of closes is known
at the same close it's computed from). Monthly primary: sell the monthly ITM PE/CE nearest Rs 500 premium,
buy 2x OTM same-side hedge nearest 15% of that premium, roll monthly, re-check the signal every Tuesday
(exit+flip next trading day on disagreement). Weekly primary: same structure at a Rs 220 premium target,
rolled every week (2019-02-11 onward only — weeklies didn't exist before). Expiry cash-settled at intrinsic
from the underlying's close (landmine #1 — never the option's own expiry-day print). Costs per
`COST_STANDARDS.md` (D-021): STT/exchange/stamp/slippage/GST on every real transaction, options-exercise STT
on ITM hedge legs at settlement, nothing charged on the settlement of the short leg itself (already paid at
open) or on legs expiring worthless.

**Strike-substitution rate: 0.0% for all four primary cells and all 78 sensitivity cells** — every cycle's
target strike (both short and hedge legs) was found with `CONTRACTS>0` on the actual entry/exit day, no
fallback ever needed. This confirms the data scout's prediction (DATA_MAP.md): premium-500/premium-220
targets sit closer to ATM (roughly 100-500 pts ITM, see §8) than the previously-scanned 300-700 pt band, and
are correspondingly more liquid.

---

## 2. Capital-base / equity-curve convention (read before the numbers below)

Per-cycle ROM is **not compounded geometrically**. A mid-cycle signal-flip exit can crystallize a
mark-to-market loss **larger than the position's own at-expiry worst-case bound** (the hedge's terminal
convexity hasn't caught up yet when you're forced to exit early) — compounding a return series through a
cycle like that sends geometric equity through zero, which is a fabricated number, not a real one. Instead:
**capital_base = average margin required over the window**; equity is the **arithmetic** cumulative sum of
net P&L against that fixed base. Where cumulative equity would have gone ≤0 at any point, this is flagged
**CAPITAL_WIPEOUT** and CAGR is reported as **undefined**, never invented. M-A, M-B (and their naked and
2019-restricted variants) all hit this flag.

---

## 3. Primary-cell results

| Metric | M-A | M-B | W-A | W-B |
|---|---:|---:|---:|---:|
| Cycles | 185 | 185 | 393 | 393 |
| Avg margin (capital base, pts) | 1,383.9 | 1,418.9 | 2,118.0 | 2,135.5 |
| Total return on capital base | **-401.3%** | **-166.0%** | **+86.7%** | **+106.4%** |
| CAGR on margin | undefined (wipeout) | undefined (wipeout) | **+8.6%/yr** | **+10.1%/yr** |
| Sharpe (annualized) | -0.10 | -0.01 | 0.49 | 0.53 |
| Calmar | n/a (wipeout) | n/a (wipeout) | 0.069 | 0.118 |
| MaxDD (% of capital base) | -568.8% | -241.8% | -124.0% | -85.5% |
| MaxDD (points) | -7,871.2 | -3,431.1 | -2,626.4 | -1,826.1 |
| Win rate (cycles) | 46.5% | 42.2% | 53.9% | 43.3% |
| Avg credit collected/cycle | 345.9 | 335.2 | 153.8 | 124.4 |
| Avg net P&L/cycle | -30.0 | -12.7 | +4.7 | +5.8 |
| Avg margin, naked-equivalent | 1,637.1 | 1,640.3 | 2,365.2 | 2,368.4 |

**Read**: monthly cadence loses ~13-30 pts/cycle on average and wipes out its own average margin roughly
4x over (M-A) or 1.7x over (M-B) across the 15.5-year history. Weekly cadence earns a modest but real
+4.7 to +5.8 pts/cycle average, compounding to high-single/low-double-digit annual CAGR-on-margin with
Sharpe ~0.5 — a genuinely different, better-behaved return profile, right up until the robustness battery
in §6.

---

## 4. Sensitivity grid (78 cells; full detail `sensitivity_grid.csv`) — this is a plateau, not a fluke

`signal x {20DMA,50DMA,AND,OR} x monthly_premium x {400,500,600} x hedge_frac x {10%,15%,25%} x cell x
{two_sided,bull_only}` = 72 monthly combos, plus `weekly_premium x {150,220,300} x cell` = 6 weekly combos,
all at cycle-resolution.

- **Monthly: 69 of 72 combinations hit CAPITAL_WIPEOUT.** The 3 that technically avoid the wipeout floor
  (`bull_only / 50DMA / 400 / 10%`, `bull_only / OR / 400 / 10%`, `bull_only / OR / 500 / 10%` — all at the
  lowest tested hedge fraction) are **still net losers** (CAGR -1.8% to -6.4%/yr) — they just don't lose
  enough to breach the average-margin floor within the window. **Every one of the 72 monthly combinations
  tested is flat-to-negative; none is a genuine winner.** The monthly-cadence failure is structural, not an
  artifact of the Rs 500 / 15% primary choice.
- **Weekly: all 6 combinations are positive, no wipeouts** — CAGR 1.6%-10.1%/yr, Sharpe 0.25-0.59. The
  weekly cadence's raw economic edge (before the lag test) is robust across the whole tested premium range,
  not cherry-picked at 220/15%.

---

## 5. Signal-gated vs ALWAYS-ON (same structure, no DMA gate at all, permanently short-PE-hedged)

| | Monthly | Weekly |
|---|---:|---:|
| Always-on CAGR on margin | **+4.3%/yr** | **+3.2%/yr** |
| Gated (Cell A) CAGR on margin | undefined (wipeout) | **+8.6%/yr** |
| Gated (Cell B) CAGR on margin | undefined (wipeout) | **+10.1%/yr** |

**The DMA gate has the OPPOSITE effect at the two cadences.** At monthly roll frequency, the weekly
Tuesday-check re-evaluates the signal far more often than the position rolls — every side-flip pays a full
round-trip of costs plus, more importantly, crystallizes a mid-cycle mark-to-market loss on whichever side
is being exited (see the Apr-2026 case study, §7). The un-gated always-on monthly structure, which never
whipsaws, is comfortably profitable (+4.3%/yr) — so **the DMA gate actively destroys value at monthly
cadence.** At weekly cadence there is no separate mid-cycle check (roll frequency = check frequency, PREREG
§3.3), so the signal's information is used cleanly: gated Cells A/B (+8.6%, +10.1%) both beat the always-on
version (+3.2%) by a wide margin — **the DMA gate adds real value at weekly cadence.**

---

## 6. Robustness battery: placebo + lag test (kill criteria 2 and 3)

100 shuffled-signal permutations (`seed=42`, fixed order) per primary cell, cycle-resolution; one-day
execution-lag test on the same cells.

| Cell | Real total return | Shuffled mean | Shuffled 95th pctile | Beats N/100 shuffles | Placebo | Lagged total return | Lag collapse | Lag verdict |
|---|---:|---:|---:|---:|---|---:|---:|---|
| M-A | -401.3% | -63.6% | +237.2% | **7/100** | **FAIL** | -406.8% | n/a | n/a (already failed) |
| M-B | -166.0% | +2.5% | +242.4% | **11/100** | **FAIL** | -423.5% | n/a | n/a (already failed) |
| W-A | +86.7% | -29.8% | +143.4% | **83/100** | **FAIL** (short of 95) | -31.9% | **137%** | **FAIL (collapses, flips to loss)** |
| W-B | +106.4% | +6.1% | +102.6% | **96/100** | pass (narrow) | -15.6% | **115%** | **FAIL (collapses, flips to loss)** |

All four numbers above are final (post-consistency-fix, `placebo_lag_results.json` in this folder).

**Placebo read**: M-A/M-B don't just fail to beat noise, they are *worse* than the median random shuffle for
M-A (real -401% vs random shuffles averaging modestly negative-to-positive) — the DMA-driven side-switching
at monthly cadence is actively harmful, not merely non-additive, consistent with §5's always-on comparison.
W-B narrowly clears the 95% bar; W-A does not.

**Lag read (the decisive test for the weekly cells)**: shifting every fill one trading day later collapses
W-A's total return from +86.7% to a **loss**, and does the same to W-B. This means the weekly edge is
concentrated in being able to transact at the *exact* closing print on the day the DMA crossover happens —
a razor-thin execution-timing dependency that any real-world latency (order routing, decision lag, even a
few minutes of same-session slippage let alone a full extra day) would likely erase. **This is the single
most decision-relevant finding in this report**: on raw economics the weekly structure looked like the
"business" the Principal was asking about; the lag test says that business is a same-day-execution
artifact, not a durable premium.

---

## 7. Bear-side (short ITM CE in downtrends) standalone contribution

| | M-A (monthly) | W-A (weekly) |
|---|---:|---:|
| CE-side cycles | 50 | 113 |
| Sum net P&L (pts) | **-5,551.2** | +24.6 |
| Avg net P&L/cycle | **-111.0** | +0.2 |
| Win rate | 36.0% | 51.3% |

The bear leg is the single biggest drag at **monthly** cadence — exactly the risk the Principal flagged
("historically dangerous in sharp V-recoveries"). At **weekly** cadence the same leg is roughly breakeven:
the shorter holding period means a short ITM CE doesn't have time to get run over by a multi-week rally
before the position is re-evaluated.

**Concrete case check — the Apr-2026 episode the Principal asked to be measured honestly** (from
`ev_M-A.csv`, cycle expiring 2026-04-28):
1. **2026-04-02** (roll day): NIFTY at 22,713.1, below both DMAs → **enter CE-hedged** (sell 22,700 CE @
   680.05, buy 2x 24,200 CE @ 106.05).
2. **2026-04-21**: signal flips bullish (NIFTY's 50DMA reclaim date — matches `TRADER_FORENSICS.md`'s
   independent finding on the real Groww trader accounts exactly) at spot 24,576.6 (+7.4% since entry) →
   **exit the CE structure at a loss of -420.25 pts**, immediately **enter PE-hedged** (sell 25,000 PE @
   487.25, buy 2x 24,000 PE @ 73.65) the same day.
3. **2026-04-28** (expiry): spot pulls back to 23,995.7 (a -580.9 pt reversal in one week) → the
   freshly-entered PE structure **also loses, -655.75 pts**.

Net cycle P&L: **-1,091.1 pts — the single worst cycle in the entire 15.5-year M-A backtest.** This is a
direct, dated illustration of the whipsaw risk: the bear-side CE leg lost on the way up, and the
signal-flip mechanic then bought into the bullish reversal right as it crested, losing again on the way
back down. It is not a hypothetical — it is exactly what the pre-registered mechanics produce when fed the
real Apr-2026 price path, and it independently corroborates `TRADER_FORENSICS.md`'s reconstruction of the
same window from the real trader accounts.

---

## 8. Empirical premium→ITM-depth mapping (validates/refutes the analytical estimate)

Full table: `premium_itm_depth_mapping.csv`. Selected years:

| Year | Monthly (target Rs 500): avg ITM depth (pts) | avg realized premium | avg India VIX | Weekly (target Rs 220): avg ITM depth (pts) | avg realized premium | avg VIX |
|---|---:|---:|---:|---:|---:|---:|
| 2011 | 502.1 | 504.0 | n/a | — | — | — |
| 2016 | 515.1 | 500.7 | 16.3 | — | — | — |
| 2019 | 476.3 | 493.9 | 17.0 | 215.8 | 223.5 | 16.3 |
| 2020 | 389.6 | 503.8 | 27.5 | 157.5 | 226.7 | 26.9 |
| 2022 | 352.6 | 496.9 | 19.5 | 132.6 | 221.9 | 19.0 |
| 2024 | 373.3 | 506.0 | 15.2 | 142.1 | 221.8 | 14.4 |
| 2026 (partial) | 302.8 | 511.7 | 15.9 | 92.7 | 233.2 | 16.5 |

**Read**: the Principal's analytical "~240 weekly-equivalent" estimate for a Rs 500 monthly target is in the
right neighborhood but on the high side — realized weekly ITM depth for a Rs 220 target sits mostly in the
**130-220 pt** range (not 240+), and both monthly and weekly ITM depth *shrink* in high-VIX years (2020,
2022) as implied vol does more of the premium's work per point of moneyness — the adaptive, IV-aware
behavior the Principal's spec anticipated is confirmed directly in the data, not just theoretically. Depth
has also been trending down over calendar time at both cadences (each column's last row < first row) —
consistent with structurally higher IV / richer option pricing in recent NIFTY history relative to spot
level, not a data artifact (VIX itself doesn't show a matching one-way trend, so this is a moneyness-premium
relationship shift, not simply "vol went up").

---

## 9. Margin model — the Principal's core economic point

`margin_hedged = max(worst_case_expiry_loss, exchange_style_estimate)`, `worst_case_expiry_loss =
max(0, |K_short-K_hedge| - net_credit)`, `exchange_style_estimate = max(0, 0.12×spot - 2×hedge_premium)`;
`margin_naked = 0.13 × spot` (SPAN+exposure point estimate inside the task's quoted 12-15% range).

| | Monthly | Weekly |
|---|---:|---:|
| Avg hedged margin (pts) | 1,383.9 (M-A) / 1,418.9 (M-B) | 2,118.0 (W-A) / 2,135.5 (W-B) |
| Avg naked margin (pts) | 1,637.1 / 1,640.3 | 2,365.2 / 2,368.4 |
| **Margin-drop ratio** | **1.18x - 1.19x** | **1.12x** |
| Naked CAGR on margin | undefined (wipeout, M-A); +9.1%/yr (M-B) | +21.7%/yr (W-A) / +22.5%/yr (W-B) |
| Hedged CAGR on margin | undefined; undefined | +8.6%/yr / +10.1%/yr |

**This is an important, honest correction to the Principal's expectation.** The pre-registered margin
formula gives a margin-drop ratio of **~1.1-1.2x, not the 2.5-4x the Principal expected.** The reason: the
`exchange_style_estimate` term (a ~12%-notional floor offset only by the small hedge premium actually paid)
dominates the `worst_case_expiry_loss` term for most of the sample — because a hedge only 10-15% of the
short's credit sits *close* to the short strike in practice (a small OTM offset for a deep-ITM short), so
the structural (`K_short-K_hedge`) bound is often nearly as large as the naked exposure itself. **The
2.5-4x margin relief the Principal is picturing requires the hedge to sit meaningfully further OTM than
"10-15% of the short's credit" naturally produces** — at these premium targets that ratio buys a hedge only
a few hundred points away, not the wide structural gap needed for NSE's real hedge-margin benefit to kick in
at that magnitude. Return-on-margin is **higher on the naked side for every cell** because the naked
position collects the full short credit with no hedge drag and (per §9's own hedge-margin formula) pays
only a modestly larger margin for it — the hedge's cost (20-30% of credit, per PREREG's disclosed estimate)
is not fully offset by the modest margin relief this formula grants it. **Net verdict: at these specific
strike choices, the hedge does not clearly earn its cost on a margin-efficiency basis** — see also §10 for
the crash-window view, which is more favorable to the hedge but still mixed.

---

## 10. Hedged vs Naked — full period vs crash windows (does the hedge earn its cost?)

**Full-period average** (already in §9): naked comfortably outperforms hedged for both cadences (naked
CAGR 9-22%/yr vs hedged CAGR either undefined/wipeout or 8.6-10.1%/yr) — hedging costs money in normal
markets, as expected.

**Crash windows** (`crash_windows.json`, cycle-level, hedged vs naked):

| Window | Monthly hedged worst cycle | Monthly naked worst cycle | Weekly hedged worst cycle | Weekly naked worst cycle |
|---|---:|---:|---:|---:|
| COVID Mar-2020 | +139.7 (no loss) | +486.7 (no loss) | **-127.0** | -881.6 |
| 2022 H1 rate-hike | **-834.5** | -663.7 | -404.9 | -467.1 |
| Apr-2026 dip | **-1,091.1** | -1,728.1 | -242.5 | -173.7 |

**Read**: the hedge is **mixed, not a reliable crash-protector in this exact construction.**
- Weekly, COVID: hedge cut the worst-week loss from -881.6 to -127.0 (an **86% reduction**) — a real, large
  win for the hedge in the single worst crash tested.
- Monthly, Apr-2026: hedge cut the worst-cycle loss from -1,728.1 to -1,091.1 (a **37% reduction**) — also
  a genuine win.
- Monthly, 2022 H1: hedge made the worst cycle **WORSE** (-834.5 vs -663.7 naked) — cost extra without
  paying off.
- Weekly, Apr-2026: hedge also made the worst cycle **worse** (-242.5 vs -173.7 naked).

Kill-criterion 4 ("the hedge must materially reduce crash losses") is **not a clean pass**: 2 of 4
cell×window combinations checked show the hedge helping, 2 show it hurting. The one unambiguous win (COVID,
weekly) is also the most severe crash tested, which argues for keeping the hedge concept but suggests the
specific 10-15%-of-credit sizing rule may not be the right one — a wider, cheaper hedge might behave more
consistently as tail insurance. This is flagged as a **sensitivity direction for a future pass**, not
re-engineered here (would require a new pre-registration).

---

## 11. Weekly-vs-Monthly head-to-head (overlapping 2019-02 → 2026-07 window — the Principal's real question)

| | Monthly two-sided (M-A, 2019+) | Weekly two-sided (W-A) | Monthly bull-only (M-B, 2019+) | Weekly bull-only (W-B) |
|---|---:|---:|---:|---:|
| Cycles | 88 | 393 | 88 | 393 |
| Total credit (theta) collected (pts) | 30,194.8 | 60,438.8 | 29,276.5 | 48,905.8 |
| Total costs paid (pts) | 570.2 | 424.6 | 386.8 | 337.3 |
| Total net P&L (pts) | **-4,798.0** | **+1,836.2** | **-1,223.5** | **+2,273.0** |
| Avg margin (pts) | 2,031.4 | 2,118.0 | 2,068.3 | 2,135.5 |
| Pin-risk episodes (\|spot_final-K_short\|<50pts) | 7 | 50 | 6 | 45 |
| MaxDD (pts) | -7,871.2 | -2,626.4 | -3,431.1 | -1,826.1 |

**Weekly wins decisively on every axis over the identical 2019-2026 window**: it collects roughly 2x the
total theta (more, smaller-premium cycles compound favorably), pays *less* total cost despite 4.5x more
cycles (each weekly transaction is cheaper in absolute points, and the shorter holding period avoids the
big whipsaw losses that dominate monthly's cost line), nets solidly positive P&L where monthly is deeply
negative, and draws down roughly a third as much in points. **Pin-risk is much more frequent at weekly
cadence in absolute count (50 vs 7 episodes) simply because there are 4.5x more expiries** — but per-cycle
pin-risk rate is actually similar (50/393=12.7% vs 7/88=8.0%), not dramatically worse.

**Answer to "which cadence is the better business": weekly, unambiguously, on every axis measured here** —
right up until §6's lag test, which kills both. The honest conclusion is not "trade weekly instead of
monthly" but "the weekly structure's raw edge is real-looking on paper but appears to be a same-day
execution-timing artifact that a live desk could not reliably capture."

---

## 12. Cost stress (2x, per COST_STANDARDS promotion rule)

| Cell | Base total return | 2x-cost total return | Base avg cost/cycle | 2x avg cost/cycle |
|---|---:|---:|---:|---:|
| M-A | -401.3% | -485.6% | 6.3 pts | 12.6 pts |
| M-B | -166.0% | -222.0% | 4.3 pts | 8.6 pts |
| W-A | +86.7% | +66.6% | 1.1 pts | 2.2 pts |
| W-B | +106.4% | +90.6% | 0.9 pts | 1.7 pts |

Costs are a second-order effect relative to the structural findings above: doubling all transaction costs
does not flip any verdict (the weekly cells were never going to fail on cost, they fail on the lag test;
the monthly cells were never going to pass regardless of cost assumptions).

---

## 13. Determinism

The full M-A primary run (daily-MTM) was executed twice in independent Python processes; the cycles, events,
and daily-MTM tables were concatenated and SHA-256 hashed. **Both runs produced an identical hash
(`044ea7af9402d254...`) — byte-for-byte match, confirmed.** No unseeded randomness anywhere in the
primary/sensitivity path; the one random element (placebo shuffles) is `RandomState(42)`, called in a fixed
order, and is itself fully reproducible run-to-run.

---

## 14. Files in this folder

- `PREREG.md` — pre-registration (filed before this report).
- `BACKTEST_REPORT.md` — this file.
- `trade_ledger.csv` — every fill (entry/exit/expiry), all 4 primary cells, 2,470 rows.
- `equity_curves.csv` — daily equity curves (capital-base + realized + running in-cycle MTM), 8 cells
  (4 primary + naked-M-A + naked-W-A + always-on-M + always-on-W for comparison), 20,160 rows.
- `ITMPE_RATIO_BACKTEST_RESULTS.xlsx` — Principal-facing workbook (Summary, PrimaryCells, SensitivityGrid,
  CrashWindows, TradeLedger).
- `DATA_MAP.md`, `TRADER_FORENSICS.md` — sibling data-scout and forensic passes this build relied on.

## 15. Known limitations (carried from PREREG.md §7, restated)

- Lot-size history pre-2021-07 unverified in this environment — all headline metrics are lot-size-invariant
  % figures, unaffected.
- Margin/SPAN formula is a documented approximation (§9), not a real exchange SPAN file.
- Equity-curve convention is arithmetic-on-fixed-base, not geometric compounding (§2) — a deliberate,
  disclosed choice given cycles can lose more than their own at-expiry worst-case bound.
- Sensitivity grid run at cycle-resolution, not daily MTM (compute-time trade-off, disclosed in PREREG §5).
- The margin-drop-ratio finding (§9, ~1.1-1.2x vs the Principal's expected 2.5-4x) is itself the most
  important number to sanity-check before any further work on this structure — it directly contradicts the
  premise that motivated the design, and is not an artifact of any single assumption (worst-case and
  exchange-style estimates were checked separately in the code review that produced this report).
