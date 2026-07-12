# WS-4 ADVERSARIAL BATTERY — ANSWER KEY (GRADER ONLY)
Built 2026-07-12 per MASTER_PLAN WS-4 battery (iii). 20 tasks: 16 defective, 4 CLEAN
(T03, T07, T14, T19). Every planted defect is verified: each defective task folder
carries a `_verify.py` synthetic demonstration (run and confirmed 2026-07-12).

**SPOILER CONTAINMENT — this file, GRADING_RUBRIC.md, PROTOCOL.md and every
`_verify.py` must NEVER be shown to a test arm. Arms receive `task.md` only.**

Severity: CRITICAL = result fabricated / sign can flip · HIGH = result materially
inflated or verdict wrong · (no planted defect is below HIGH by design).

---

## T01 — data-landmine — tz mislabelling (CRITICAL)
**Defect.** `hf["date"] = hf["ts"].dt.date` on tz-aware UTC stamps (18:30 UTC =
next-day 00:00 IST) labels every daily bar one day EARLY. The signal panel is then
joined against the correctly-dated bhavcopy execution panel: the "signal at d"
contains the true close of d+1, so the reversal trades one day before it is
implementable (the "next session's close" entry is in fact the close the signal was
computed from).
**Line.** `hf["date"] = hf["ts"].dt.date` (no `tz_convert('Asia/Kolkata')`), combined
with the two-source join.
**Fix.** `hf["ts"].dt.tz_convert("Asia/Kolkata").dt.date` before pivoting; re-run.
**Accept.** "UTC .dt.date shifts the vendor bars one day vs the IST-dated panel —
one-day lookahead at the join"; "18:30 UTC stamp is next-day IST; must tz-convert
before taking the date"; "signal panel and execution panel are date-misaligned by
one day, giving the signal tomorrow's close".
**Secondary (no credit, no penalty).** 5bp/side may be light for single stocks;
`dates.index(d)` is O(n) slow; equal-weight 30 names without liquidity screen.

## T02 — lookahead — same-bar (close) execution, T3 (HIGH)
**Defect.** Signal needs the day's CLOSE (`ret` and `close > dma20` both use close of
t); the fill is booked AT that same close (`entry = df["close"].iloc[i]`). The
dip-day close cannot be bought after observing it; any overnight bounce after down
days is silently pocketed. Firm precedent: same-day-close vs D+1 convention alone
swung a strategy +0.99 -> -0.03 per Rs100.
**Line.** `entry = df["close"].iloc[i]` on the signal day.
**Fix.** Enter at the NEXT session's open (or pre-register an intraday proxy signal
computable before the close); re-run and quote the D+1 number as the verdict.
**Accept.** "Same-bar execution: signal computed on the close, filled at the same
close"; "entry must be next-day open — the close was not tradeable after the signal
existed"; "T3-class same-day-close fill inflates the edge with the overnight move".
**Secondary.** 3bp/side is optimistic for index futures crossing the spread twice —
minor; overlapping trades (3-session hold, signals can cluster) affects
independence of the t-stat, not the fill logic.

## T03 — CLEAN (stats theme)
**No material defect.** PIT membership stated, available_date-timestamped signal,
2021+ window matches the known publication-coverage constraint, next-open entry,
circuit/zero-volume no-fill, fixed same-exit for strategy AND placebos,
turnover-matched by construction, lag test degrades gracefully, denominators clean,
honest modest verdict (asks for sensitivity, not certification).
**Reject as false positives.** "92nd percentile is not significant enough" (it is a
finding, and the memo itself only asks to advance, not certify); "needs more placebo
baskets"; "no DSR/PBO yet" (memo explicitly routes to the sensitivity battery next);
"10-session fixed exit is arbitrary" (pre-registered and shared with placebos).
A grader may accept these as *comments* but they score as invented defects if
presented as things that make the result wrong or fake.

## T04 — lookahead — quarter-end vs available_date, T1 (CRITICAL)
**Defect.** Portfolio formed on "the first trading day AFTER the quarter ends" using
that quarter's revenue. Indian quarterly results are published up to ~45 days after
quarter end; the screen sorts on numbers nobody has yet. Any announcement-day
repricing of the surprise is captured illegitimately.
**Line.** `rebal_day = close.index[close.index.searchsorted(qe, side="right")]`
driven by `quarter_end`, with no publication-date column anywhere in the code.
**Fix.** Join on `available_date` (publication date) via `merge_asof(...,
direction="backward")`, or lag quarter_end by the statutory 45 days; rebalance only
on data already public.
**Accept.** "Trades on quarter-end date but results come out ~45 days later";
"missing available_date / publication-lag — PIT violation"; "earnings lookahead:
uses the quarter's fundamentals before the filing exists".
**Secondary.** Revenue YoY on positive bases is fine (no base-effect issue here);
membership handling is correct as written.

## T05 — statistics — base-effect growth ranking (CRITICAL)
**Defect.** `growth = (eps - eps_prev) / eps_prev` ranked by `nlargest`. Percent
growth on near-zero or negative bases is meaningless: penny-EPS bases explode
(39.5x), DEEPENING losses sign-flip to positive "growth" (see SUNWINDPWR
-1.20 -> -2.55 shown as +1.13), and genuine turnarounds to profit rank at the bottom
(TURNCORP -5.00 -> +1.00 shown as -1.20). The "fastest growers" basket is
denominator noise plus deteriorating loss-makers — the sample table in the task
shows exactly this.
**Line.** the `growth` division + `nlargest(20, "growth")`.
**Fix.** Require a positive material base (eps_prev above a threshold), or rank on
delta-EPS scaled by price/assets (denominator-free), never percent-of-base on a
signable quantity.
**Accept.** "Division by near-zero/negative EPS base — sign flips and explosions
dominate the ranking"; "denominator disease / base effect: percent growth invalid
when the base can be ~0 or negative"; "the sample table shows worsening loss-makers
ranked top-10 and a real turnaround ranked last".
**Secondary.** PIT handling (asof_date) is explicitly correct; timing is not the
issue here.

## T06 — lookahead — settlement beyond max(data), T8 (HIGH)
**Defect.** Expiry calendar runs to Jul-2026 but data ends 2026-06-30. For the
Jul-2026 cycle (entered ~Jun-15 at T-45), `spot.asof(exp)` silently returns the last
available close, so an OPEN position is "settled" near its entry level and booked as
a near-full-premium win. No guard `exp <= spot.index.max()` exists, so every future
rerun keeps booking phantom wins for unfinished cycles. Same class as the firm's
S-04 incident (84 fabricated future-settlement wins).
**Line.** `settle_spot = spot.asof(exp)` with the calendar extending past the data
end and no max-date guard.
**Fix.** Assert `exp <= spot.index.max()`; drop unfinished cycles or report them as
OPEN, never settled.
**Accept.** ".asof past the end of data returns a stale price — the July-2026 cycle
is fabricated"; "settles positions after max(available data), booking wins for open
trades"; "missing expiry<=data-end guard; future expiries marked at the last close".
**Secondary.** Strike selection off the PRIOR close and same-day premium capture at
entry are acceptable conventions here; the 84% hit rate itself is plausible for
short strangles.

## T07 — CLEAN (data-landmine theme)
**No material defect.** Decision on Tuesday data after Tuesday's close; execution
next day at leg OPEN prints; expiry chosen on YESTERDAY'S liquidity (CONTRACTS>0,
causal) with a conservative same-day no-fill re-check; exit cash-settled at
intrinsic from the INDEX close (correctly avoids expiry-day option SETTLE_PR);
max-date guard stated; slippage/costs charged; event weeks skipped.
**Reject as false positives.** "Uses SETTLE_PR wrong" (it never reads option
SETTLE_PR); "CONTRACTS>0 on entry day is lookahead" (selection uses Tuesday's
CONTRACTS — causal; the Wednesday check only SKIPS untradeable entries,
conservative); "bhavcopy OPEN not tradeable" (open prints are executable prices;
slippage is charged on top); "no stop-loss" (defined-risk structure — wings cap it).

## T08 — data-landmine — pre-open auction bar as open (HIGH)
**Defect.** `day_open = g.iloc[0]["open"]` takes the first print the vendor ships,
which is the 09:00 pre-open AUCTION print, not the 09:15 continuous-session open.
The gap is misclassified on every day the auction print deviates, AND the fade is
"filled" at the auction price, which does not exist in the continuous session —
auction-vs-open deviation becomes instant fake P&L (firm measurement: ~94% of naive
2026 gap calculations corrupted by this bar).
**Line.** `day_open = g.iloc[0]["open"]` with no time filter.
**Fix.** Filter to `t >= time(9,15)`; real open = first continuous-session bar;
entry price must be a >=09:15 print.
**Accept.** "First bar of the day is the 09:00 pre-open auction, not the real
open"; "gap and entry price use the auction print — untradeable"; "missing >=09:15
session filter".
**Secondary.** prev_close from the same file's last <=15:30 bar is fine; 1bp/side
futures cost is acceptable.

## T09 — lookahead — shift sign error, feature from the future (CRITICAL)
**Defect.** `df["adv_dec"] = (df["advances"] / df["declines"]).shift(-1)` feeds day
t+1's breadth into day t's signal — and the position holds exactly the t+1 session
(open t+1 -> open t+2). The entry "confirms" with the breadth of the session it is
about to trade. Every other feature is causal; this one line fabricates the edge.
**Line.** the `.shift(-1)` on `adv_dec`.
**Fix.** `shift(0)` (day t's breadth, knowable at the close) or `shift(1)`; standing
rule: grep for `.shift(-` on any feature; `.shift(-n)` is forbidden without a LABEL
tag.
**Accept.** "shift(-1) on breadth = tomorrow's advance/decline used at t";
"sign-flipped shift leaks the held session's breadth into the entry"; "adv_dec is
future data; all other features are lagged correctly".
**Secondary.** `df["o2o_next"] = open.shift(-2)/open.shift(-1)-1` is the EXECUTION
return aligned to the decision date — a standard, legitimate pattern (calling THIS
the leak instead of adv_dec scores 0-1, not 2); costs modelled thinly but present.

## T10 — statistics — daily-corr diversification artifact (HIGH)
**Defect.** The "uncorrelated" claim rests on DAILY correlations for a sleeve that is
flat ~80% of days (flat days book 0). Episodic sleeves mechanically show ~0 daily
correlation while sharing a factor at the monthly/drawdown horizon — the memo's own
worst-month table shows EVT-1 negative in ALL FIVE of the book's worst months. The
root-N Sharpe projection (1.05 -> 1.38) built on daily-corr independence is invalid,
and sizing (20% risk weight) is decided on that artifact.
**Mechanism.** correlation measured at the wrong horizon for an asynchronous/episodic
return stream.
**Fix.** Quote monthly (or drawdown-window) correlation and re-derive the stacking
math from it; check tail coincidence explicitly (worst-month overlap).
**Accept.** "Daily corr on a mostly-flat sleeve is an artifact — measure monthly";
"the worst-month table contradicts the independence claim: it loses exactly when
the book loses"; "root-N stacking needs independence at the horizon where drawdowns
live, not at daily frequency".
**Secondary.** Standalone Sharpe 0.94 below book average also weakens stacking math
(bonus observation, not required for full credit).

## T11 — lookahead — centered rolling window, T6/T7 (CRITICAL)
**Defect.** `iv.rolling(11, center=True).mean()` uses 5 FUTURE sessions in the
smoother. "IV > 1.15x local average" then fires preferentially at local IV peaks —
identifiable as peaks only because the window saw IV fall afterwards. A short-vol
entry conditioned on that is selling tops with hindsight; the +2.1%/trade is
manufactured.
**Line.** `center=True` in the rolling mean.
**Fix.** `center=False` (trailing window); re-run the whole battery.
**Accept.** "Centered moving average looks 5 days into the future"; "the smoother is
non-causal — entries are hindsight IV peaks"; "rolling(center=True) on a live signal
is lookahead".
**Secondary.** Next-open entry, liquidity skip and exit rule are all fine.

## T12 — data-landmine — expiry-day option SETTLE_PR (CRITICAL)
**Defect.** On the EXPIRY DAY, an option row's SETTLE_PR in the NSE F&O bhavcopy is
the UNDERLYING's final settlement level (e.g. 19,253.80), not the option's value.
`debit = ce_x + pe_x` buys back both legs at ~2x the index level: tens of thousands
of fake loss points per week. The task's own summary shows the tell — four-digit
losses concentrated ON expiry dates with tiny index moves ("pin risk" cannot produce
-23,912 pts on an ATM straddle). Firm incident 2026-07-11: -15,428-pt fake losses.
**Line.** reading `.SETTLE_PR` from the expiry-day rows as the exit price.
**Fix.** Never read expiry-day option SETTLE_PR; cash-settle each leg at intrinsic
computed from the underlying's final settlement price.
**Accept.** "Expiry-day SETTLE_PR is the underlying settlement level, not the option
price"; "exit debit ~= 2x index level — settle at intrinsic from the underlying
instead"; "the -20k point 'pin risk' weeks are the field-semantics bug, not risk".
**Secondary.** Entry CONTRACTS>0 gate and prior-close strike selection are correct;
CLOSE prints at entry acceptable.

## T13 — lookahead — universe membership from today's list, T5 (CRITICAL)
**Defect.** `nifty500_constituents.csv` is the index provider's CURRENT (2026-07)
list, applied to 2013-2025. Membership in today's index is an outcome: winners grew
into it, losers fell out or delisted. Screening the 2013 cross-section through
today's list pre-selects winners regardless of the price panel being
survivorship-complete — the momentum CAGR is contaminated before any signal quality
is measured.
**Line.** the `read_csv(...)["Symbol"].tolist()` universe + the filtering of the
panel columns by it.
**Fix.** Point-in-time membership: the 42-snapshot constituent history, as-of each
rebalance date (Mar/Sep snapshot on or before).
**Accept.** "Universe is today's constituents applied historically — survivorship /
index-inclusion lookahead"; "membership must be as-of date from the PIT snapshot
file"; "the panel is survivorship-complete but the universe filter re-introduces
the bias".
**Secondary.** 12-1 momentum construction (`shift(21).pct_change(231)`) is causal
and correct; fills/costs are handled.

## T14 — CLEAN (stats theme)
**No material defect.** The obvious trap — "overnight drift in costume" — is
explicitly controlled: an exposure-matched random-nights baseline (+0.9bp) is
subtracted from the claim (+3.1bp), the placebo battery shares the identical
entry/exit engine, the lag test degrades gracefully, costs and no-fill nights are
handled, eras are stable, and the verdict is modest (diversifier-grade, asks for
orthogonality next).
**Reject as false positives.** "It's just overnight drift" (the memo's
exposure-matched control isolates +2.2bp above drift); "same-day 15:25 entry on a
15:00 signal is lookahead" (signal inputs are from <=14:59 data, execution 25+ min
later — causal); "1.2bp/night costs unrealistic" (futures round-trip at approved
standard; plausible); "Sharpe 1.21 too high to believe" (not a defect claim).

## T15 — lookahead — full-sample normalization, T6 (HIGH)
**Defect.** `mu = hist["iv"].mean(); sd = hist["iv"].std()` over the FULL 2015-2025
series. A 2016 entry decision uses a mean/std that contain the 2020 COVID spike and
the post-2020 regime: both the entry threshold (z>1) and the crash filter (z<2.5)
are calibrated with future information. Entry sets differ materially from any
implementable rule (verified: pre-break entries nearly vanish under the full-sample
stats), and the "Mar-2020 skipped by the crash filter" claim is itself a product of
the leak.
**Line.** full-sample `mean()`/`std()` feeding `iv_z`.
**Fix.** Trailing-window (e.g. 252d, lagged) or expanding-window-lagged statistics;
re-run; `audit_full_sample_stats()` catches this pattern.
**Accept.** "Z-score uses full-sample mean/std — normalization leakage"; "the crash
filter knows about COVID before it happens"; "stats must be trailing/as-of, not
whole-history".
**Secondary.** Next-open entry and liquidity handling are fine.

## T16 — statistics — turnover-cost confound (HIGH)
**Defect.** The hurdle (monthly-refresh random baskets, ~330%/yr one-way) churns
~8.7x the strategy (semiannual, 38%/yr); both are charged 45bp/side. Cost drag:
hurdle ~2.97pp/yr vs strategy ~0.34pp/yr, so ~2.6pp of the claimed +3.1pp "net edge"
is the comparator paying more costs. Gross-vs-gross (the memo's own table) the edge
is +0.3pp — noise. The statistical gates passed because they test the number, not
the comparator. Certifying "+3.1pp selection edge" is wrong.
**Mechanism.** un-matched turnover between strategy and null.
**Fix.** Turnover-matched placebo (semiannually-refreshed random baskets), or
compare gross-vs-gross and charge strategy costs explicitly. Full credit requires
doing (or gesturing at) the drag arithmetic or citing the gross rows.
**Accept.** "The hurdle pays ~2.6pp more costs — the net edge is cost savings, not
selection"; "compare against a turnover-matched null; gross edge is only 0.3pp";
"low-churn strategies always 'beat' full-churn random baskets net of costs".
**Secondary.** Noting that p95-clearing also collapses under matching: correct,
bonus.

## T17 — lookahead — argmax-over-window entry, T9 (CRITICAL)
**Defect.** `win.loc[win["ff"].idxmax()]` picks the best-priced day of the ENTIRE
T-30..T-10 window. Knowing day d was the window maximum requires having seen every
day after d — no causal trader can do it. Entering at the window extreme fabricates
edge from pure noise (verified: +3.5%/cycle on a driftless walk). The
next-session-open fill does NOT repair it: identifying the peak still requires the
unseen remainder of the window. Firm precedent: forward_factor v2's argmax entry.
**Line.** `idxmax()` over the full window followed by entry at that day.
**Fix.** Pre-registered causal trigger — first crossing of a fixed ff threshold, or
a fixed entry lead; re-run.
**Accept.** "Argmax over the window is hindsight entry-day selection"; "picking the
peak-ff day needs the whole window — non-causal"; "perfect entry timing inside the
window; use first-threshold-cross instead".
**Secondary.** Liquidity skip and T-2 exit are fine.

## T18 — data-landmine — Angel ONE_DAY fromdate with intraday time (HIGH)
**Defect.** ONE_DAY candles are stamped 00:00 IST (stated in the task). A fromdate
of `"<entry_date> 09:15"` is AFTER the entry day's 00:00 stamp, so the API silently
omits the entry-day bar; the audit then finds no entry-day bar and flags the leg
UNFILLABLE. 501/501 UNFILLABLE including deep-liquid ATM NIFTY weeklies is the
tell — an impossible real-world liquidity result that should have triggered a sanity
check. The recommendation to void the week's paper results is wrong. (Firm incident
2026-07-10, same bug.)
**Line.** `"fromdate": leg.entry_date.strftime("%Y-%m-%d") + " 09:15"`.
**Fix.** `fromdate = (entry_date - 1 day) 00:00` (or entry_date 00:00) for daily
candles; re-run the audit; treat 100%-UNFILLABLE outputs as a red flag for the tool,
not the market.
**Accept.** "fromdate 09:15 excludes the 00:00-stamped entry-day bar — the API
drops it silently"; "request window starts after the daily bar's timestamp";
"the UNFILLABLE verdict is a query artifact; use 00:00 fromdate".
**Secondary.** Rate-limit sleep and the THIN participation check are fine.

## T19 — CLEAN (data-landmine theme)
**No material defect.** Survivorship-complete union panel INCLUDING delisted names,
stale-price mask applied, PIT membership as-of each rebalance, causal 12-1 momentum,
next-open entries with circuit/zero-volume no-fill, delisting losses realized
explicitly, and a turnover-matched random-basket null from the same panel. The 93rd
percentile / +4.3pp over null p50 claim is internally consistent and honestly
framed.
**Reject as false positives.** "Mar/Sep snapshots are stale between snapshot dates"
(that IS the point-in-time convention — the snapshots are the correct as-of data);
"momentum uses shift(21).pct_change(231) — lookahead" (it is t-252..t-21, causal);
"stale mask hides losses" (the mask excludes fabricated frozen prints — it removes
fake data, standing rule); "no stop-loss / high maxDD" (risk characteristics, not
result-validity defects).

## T20 — statistics — placebo without the same exit engine (HIGH)
**Defect.** Strategy exits +2%/-4%/20d (asymmetric target/stop, avg 6.2d); placebos
exit at a fixed 5th-session close. On an upward-drifting market the exit-engine
mismatch ALONE manufactures the separation with zero entry skill: the near target
converts drift+noise into ~60%+ win rates (vs ~52% for time exits) and the longer
average hold harvests more drift per trade (verified: +13.8pp win-rate and positive
mean gap with random entries in both arms). The "99th percentile" certifies the
exit rule, not the entry signal.
**Mechanism.** null arm differs from the strategy arm in the exit engine, so the
comparison cannot attribute the difference to entries.
**Fix.** Run the 500 placebo baskets through the IDENTICAL +2%/-4%/20d exit engine;
only entry selection may differ between strategy and null. (Matching average hold
"approximately" is not enough — the asymmetric barrier shape drives the win rate.)
**Accept.** "Placebo must share the exact exit engine — target/stop vs time exit
manufactures the gap"; "a 2%-target/4%-stop yields ~60% wins on drift alone; the
placebo's 52% is an apples-to-oranges null"; "same-exit placebo violation: the
percentile measures the exit asymmetry, not the entry".
**Secondary.** 30bp/side both arms is fine; trade-overlap/independence caveats are
comments, not the defect.

---

## Quick reference table

| task | verdict | class | one-line ground truth |
|---|---|---|---|
| T01 | DEFECT (CRITICAL) | data-landmine | UTC .dt.date labels vendor dailies 1 day early vs IST panel |
| T02 | DEFECT (HIGH) | lookahead | signal on close, filled at same close (T3) |
| T03 | CLEAN | stats theme | honest PEAD memo, full same-exit placebo battery |
| T04 | DEFECT (CRITICAL) | lookahead | trades quarter-end fundamentals ~45d before publication (T1) |
| T05 | DEFECT (CRITICAL) | statistics | % growth on ~0/negative EPS base; sign flips rank the basket |
| T06 | DEFECT (HIGH) | lookahead | .asof settles a cycle expiring beyond max(data) (T8) |
| T07 | CLEAN | landmine theme | condor engine: causal liquidity gate + intrinsic settle |
| T08 | DEFECT (HIGH) | data-landmine | 09:00 auction print used as open and as fill price |
| T09 | DEFECT (CRITICAL) | lookahead | .shift(-1) on breadth feature = held session's own data |
| T10 | DEFECT (HIGH) | statistics | daily corr on episodic sleeve; monthly corr is the truth |
| T11 | DEFECT (CRITICAL) | lookahead | rolling(center=True) smoother sees 5 future sessions (T6) |
| T12 | DEFECT (CRITICAL) | data-landmine | expiry-day option SETTLE_PR = underlying level, not option price |
| T13 | DEFECT (CRITICAL) | lookahead | today's constituent list applied to 2013-2025 (T5) |
| T14 | CLEAN | stats theme | overnight sleeve WITH exposure-matched drift control + lag test |
| T15 | DEFECT (HIGH) | lookahead | z-score from full-sample mean/std (T6) |
| T16 | DEFECT (HIGH) | statistics | hurdle churns 8.7x; net "edge" is the cost differential |
| T17 | DEFECT (CRITICAL) | lookahead | idxmax entry over the whole window (T9, FF-v2 precedent) |
| T18 | DEFECT (HIGH) | data-landmine | ONE_DAY fromdate 09:15 silently drops the 00:00-stamped entry bar |
| T19 | CLEAN | landmine theme | union panel + PIT membership + explicit delisting handling |
| T20 | DEFECT (HIGH) | statistics | placebo exit engine differs from strategy exit engine |
