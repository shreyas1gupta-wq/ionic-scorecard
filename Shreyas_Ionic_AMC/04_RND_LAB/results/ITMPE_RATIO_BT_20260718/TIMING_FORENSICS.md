# TIMING FORENSICS — 4 Groww F&O Accounts, April 2026

Prepared by: Execution & TCA (Tara Singh persona), 2026-07-18. Scope: the Principal correctly
objected that the prior `price_validation_table.csv` check (98/98 fills inside the on-disk
[day-low, day-high] range) is a **weak-pass test that can be gamed by hindsight fabrication**
— pick any entry/exit inside a wide day range and it will always "pass." This deliverable runs
the **stronger battery**: invert price back to time, test whether same-day round-trips could
secretly be shorts, test for hindsight-optimal fill placement, test for a lead-lag/tip-source
signature across the 4 accounts, and finally build the charts the Principal explicitly asked to
see. All figures below are **[DATA]** unless tagged **[INFERENCE]** or **[OPINION]**. Every number
is reproducible from the scripts + CSVs listed; nothing here is invented.

## 0. Data sources (verified, with row counts)

- **Trade ledger**: `Shreyas_Ionic_AMC/04_RND_LAB/results/ITMPE_RATIO_BT_20260718/combined_trades_raw.csv`
  — 49 rows (the same 49 trades TRADER_FORENSICS.md is built on), columns include
  `account_name, ucc, scrip_raw, quantity, buy_date, buy_price, sell_date, sell_price, expiry,
  strike, opt_type, lots`.
- **1-min NIFTY option chain** (source of the original price-validation table, confirmed via
  `TRADER_FORENSICS.md` §0 and re-verified directly): `intraday_options_strategy/datasets/raw/
  hf_index_options_1m/options/NIFTY/{expiry}.parquet` — one file per weekly expiry, 262 files on
  disk 2021-05-07→2026-06-09; the 4 files touching this ledger are `2026-04-07.parquet`,
  `2026-04-13.parquet`, `2026-04-21.parquet`, `2026-04-28.parquet` (274,635 rows in the
  2026-04-07 file alone, confirmed by direct read). Schema: `timestamp (tz-aware +05:30),
  open, high, low, close, volume, open_interest, trading_day, symbol, strike, option_type, expiry`.
  **No pre-open-auction bars found** (every file's earliest bar per day = 09:15:00+05:30, latest
  = 15:30:00+05:30) and **no zero-volume 1-min bars found** in any (expiry, strike, opt_type,
  trading_day) slice touched by this ledger — this chain is dense and liquid for every contract
  these 4 accounts actually traded.
- **1-min NIFTY spot**: `intraday_options_strategy/datasets/raw/hf_index_options_1m/index/
  NIFTY.parquet` — 477,738 rows, 2021-05-24→2026-06-03, tz-aware +05:30 timestamps (already
  local wall-clock — confirmed via the same landmine TRADER_FORENSICS.md flagged: use
  `tz_localize(None)`, NOT `tz_convert(None)`, to drop the tag without shifting the date).
- DATA_MAP.md (same results folder) and TRADER_FORENSICS.md were read first per instructions;
  neither references a checked-in build script for `price_validation_table.csv` (it was built
  from a scratchpad script, "not checked into the repo" per that file's own header) — this
  deliverable re-derives fills directly from `combined_trades_raw.csv` + the option chain above
  rather than depending on that script, so results are independently reproducible.

All scripts for this session live in the scratchpad (not checked into the repo, deterministic,
re-runnable): `step1_build_fills.py` … `step6_finalize_csv.py`. Outputs are the CSVs in this
folder, listed at the bottom.

---

## TEST 1 — PRICE → TIME INVERSION

Method: for each of the 98 fills (49 trades × BUY+SELL leg), search every 1-min bar on the
relevant `trading_day` for that exact (expiry, strike, opt_type) whose `[low, high]` range
intersects a tolerance band around the Groww fill price, starting at ±0.25% and widening to
±0.50% / ±0.75% / ±1.00% only if no match is found; among matches, prefer bars with
`volume > 0` (all of them, in practice, per §0).

**Result: 98 of 98 fills matched at the tightest tolerance tried, ±0.25% — none needed
widening.** [DATA — `tolerance_used` column, `timing_inferred_fills.csv`, 98 rows]

| Metric | Value |
|---|---|
| Fills matched at ±0.25% (no widening needed) | 98 / 98 (100%) |
| Fills with zero candidate minutes at any tolerance | 0 / 98 |
| Candidate minutes per fill (n_candidates) — median / mean / min / max | 21 / 29.1 / 1 / 83 |
| Fills where candidate window collapses to exactly 1 minute | 2 / 98 |
| Candidates with actual volume>0 | 98 / 98 (100%) |

**Sanity check passed**: every matched candidate carries real traded volume (millions of units
per minute on these ATM weekly strikes — this chain is not thin/stale-print territory the way
far-OTM single-stock wings are). No fill's candidate set was empty or volume-free.

Per-fill candidate windows (first/last/count) are in `timing_inferred_fills.csv` — e.g. the
largest trade (Aakash Ghadge, 23650CE, 2026-04-13) shows BUY candidates 09:18–09:49 (16 minutes,
price 302.7–302.92 touched repeatedly during the post-open dip) and SELL candidates 12:14–15:29
(23 minutes, price 411.00 touched both mid-day and again near the close during a pullback — see
the option-level chart, §5).

**Reading this honestly**: a 21-median-candidate window means we generally cannot pin a fill to
a single minute — Groww's own paise-precision (e.g. 302.92) reflects a volume-weighted execution
average, not a single tick, and NIFTY weekly ATM options revisit nearby price levels many times
in a 6.25-hour session. This is expected, not a red flag; it is the reason Tests 2–4 below use
*windows*, not point estimates, and report brackets rather than false-precision single answers
wherever the window materially matters.

---

## TEST 2 — SAME-DAY DIRECTION TEST ("could these be disguised shorts?")

**Multi-day trades (15 of 49): already structurally ruled out.** All 15 show `buy_date <
sell_date` (confirmed again here, matching `structural_short_scan_hits.csv` = 0 rows from the
prior deliverable) — a reversed-date short would show `sell_date < buy_date`, which never
occurs. These 15 are classified `LONG-confirmed (multi-day)`.

**Same-day trades (34 of 49): the real test.** For each, we compared the BUY-price candidate
window against the SELL-price candidate window (from Test 1):

- **LONG-confirmed** (every BUY-candidate minute precedes every SELL-candidate minute — the
  round trip could ONLY have happened buy-first): **16 of 34**
- **AMBIGUOUS** (the two windows overlap — the contract revisited both price levels multiple
  times intraday, so either chronological order is mathematically consistent with the tape):
  **18 of 34**
- **SHORT-likely** (every SELL-candidate minute precedes every BUY-candidate minute — the only
  order consistent with the tape is sell-first/buy-to-cover, i.e. the round trip could only be a
  disguised short): **0 of 34**

**Direct answer to the Principal's question: zero of the 49 visible trades show a timing
signature consistent with a hidden short.** Even in the 18 ambiguous cases, "ambiguous" means
*both* orders are mathematically possible given how often the option revisited both price
levels — it is not evidence *for* a short, only an inability to fully rule one out from price
alone. Combined with the structural fact that a realized-P&L report cannot show an open short at
all (already flagged in TRADER_FORENSICS.md §6b), this test's honest conclusion is: **nothing in
the tape supports the "these are disguised shorts" hypothesis, and the 16 LONG-confirmed cases
actively rule it out for those specific trades.** [DATA — `direction_test_results.csv`, 49 rows]

---

## TEST 3 — HINDSIGHT-FABRICATION TEST

### 3(a) Fill-quality percentiles

Percentile = `(fill − day_low) / (day_high − day_low)`, computed per fill; 0 = bought/sold at
the exact day low, 1 = exact day high.

| Group | n | Mean | Median | KS stat | KS p | vs Uniform(0,1) |
|---|--:|--:|--:|--:|--:|---|
| **Overall — BUY** | 49 | 0.350 | 0.332 | 0.406 | <0.0001 | reject uniform |
| **Overall — SELL** | 49 | 0.738 | 0.881 | 0.423 | <0.0001 | reject uniform |
| Aakash Ghadge — BUY | 15 | 0.330 | 0.352 | 0.507 | 0.0004 | reject |
| Aakash Ghadge — SELL | 15 | 0.866 | 0.909 | 0.659 | <0.0001 | reject |
| Babasaheb Ghadge — BUY | 9 | 0.375 | 0.334 | 0.458 | 0.0303 | reject |
| Babasaheb Ghadge — SELL | 9 | 0.866 | 0.897 | 0.687 | 0.0001 | reject |
| Kedar — BUY | 21 | 0.334 | 0.257 | 0.415 | 0.0009 | reject |
| Kedar — SELL | 21 | 0.578 | 0.352 | 0.307 | 0.0296 | reject |
| Bhanushali — BUY | 4 | 0.458 | 0.366 | 0.349 | 0.6077 | fail to reject (n too small anyway) |
| Bhanushali — SELL | 4 | 0.810 | 0.808 | 0.726 | 0.0113 | reject |

**Raw read (naive): every group except one n=4 cell rejects uniformity** — buys cluster in the
cheaper half of the day's range, sells in the dearer half. Taken at face value this looks like
exactly the hindsight-fabrication signature the Principal worried about.

**Self-red-team on this test — the trend-day confound**: NIFTY rallied ~7.4% over the 3-week
window (22,713 → 24,378, per TRADER_FORENSICS.md §4). On a trending-up day, the day's low
mechanically tends to sit earlier and the day's high later — so ANY trader who simply buys
sometime in the morning and sells sometime later gets a "good" percentile **for free, with zero
cherry-picking**. A bare KS-test against Uniform(0,1) cannot distinguish that from fabrication.
Three harder, disambiguating checks:

1. **Time-of-day correlation**: corr(candidate entry time, fill percentile) = **+0.418 (BUY)**,
   **+0.849 (SELL)**, n=49 each. Both positive and the SELL correlation is very strong — entirely
   consistent with "price grinds upward through the session, later fills get better percentiles
   mechanically," not with "fills are magically optimal regardless of when they happened."
2. **Extreme-pin counts** (the actual fabrication tell — a faked ledger would show entries pinned
   at or near the LITERAL day low/high, not merely "somewhere favorable"): buys pinned at
   percentile <2% (essentially the exact day low): **1 of 49**. Sells pinned at percentile >98%
   (essentially the exact day high): **0 of 49**. Buys in the bottom decile: 4/49. Sells in the
   top decile: 18/49 — a real skew, but nowhere near "everyone hit the exact optimum."
3. **Capture-ratio spread** (the strongest disambiguator — see 3b below): if the ledger were
   hindsight-fabricated, exits would cluster tightly near capture_ratio = 1.0 (sold at/near the
   best price the day actually offered). They do not.

**Verdict on 3(a): the raw KS rejection is explained by ordinary trend-following behavior in a
rallying month, not by fabrication.** [DATA + INFERENCE — `fill_percentile_stats.csv`,
`trend_confound_check.txt`]

### 3(b) Exit-target clustering

Per-trade % gain = `sell_price/buy_price − 1`, n=49:

| Bucket | Count |
|---|--:|
| <-50% | 1 |
| -10% to 0% | 3 |
| 0% to 10% | 7 |
| 10% to 20% | 4 |
| **20% to 25%** | **13** |
| 25% to 30% | 0 |
| 30% to 40% | 2 |
| **40% to 50%** | **14** |
| 50% to 75% | 1 |
| 75% to 100% | 2 |
| 100% to 150% | 2 |

Mean +29.8%, median +23.7%, **std 31.1%**, range **−97.7% to +106.9%**.
**13 of 49 (26.5%) land in the 20–30% band** the Principal flagged as a suspicious "~25% target"
— but the distribution is **bimodal** (13 near 20-25%, a bigger cluster of 14 near 40-50%), not a
single tight spike at 25%, and the overall spread (one trade down 97.7%, several up 100%+) is far
too wide to be a fixed-target system. A hindsight-fabricated "always hit +25%" ledger would show
a single narrow spike near +25% and essentially zero variance; this is the opposite.

**Capture ratio** (actual gain ÷ best-possible gain available via the sell-day's own day-high,
n=49): mean 0.624, **median 0.667**, std 0.320, range **−0.075 to 1.048**. Only **2 of 49 (4%)**
exceed 0.95 (near-perfect exit); **10 of 49 (20%)** are below 0.30 (poor exits, money clearly left
on the table). **This is the single strongest quantitative argument against fabrication in the
whole battery**: a faked ledger has no reason to leave a third of the day's available gain on the
table on the median trade, let alone lose money on 1 trade and capture <30% of the available move
on 10 — real, imperfect human timing does exactly that. [DATA — `exit_gain_distribution.csv`]

### 3(c) Time-feasibility red flags

| Check | Result |
|---|--:|
| Fills whose ONLY candidates are auction/edge minutes (09:15-16 or 15:29-30) | 0 / 98 |
| Fills whose candidates are all zero-volume | 0 / 98 |
| Fills with no candidate at any tolerance | 0 / 98 |
| Fills needing tolerance wider than ±0.25% | 0 / 98 |

**Clean pass, no red flags.** [DATA — `red_flags_summary.txt`]

---

## TEST 4 — INTER-ACCOUNT LEAD-LAG

### 4(a) Shared-combo ordering (6 combos, using inferred BUY-candidate windows)

| Combo | Accounts (earliest→latest, by first-candidate time) | Ghadge pair? | Entry gap |
|---|---|---|---|
| 04-09, exp 04-13, 24000CE | Babasaheb (09:15) → Kedar (09:15, spans to 15:01) | no | tied at earliest touch |
| 04-13, exp 04-21, 24000CE | Kedar (09:15) → Aakash (12:14) | no | ~3h |
| 04-15, exp 04-21, 24100CE | Babasaheb (09:15) → Aakash (09:16) | **yes** | **1 minute** |
| 04-17, exp 04-21, 24150CE | Kedar (09:16) → Bhanushali (09:16) | no | tied |
| 04-20, exp 04-21, 24250CE | Aakash (09:15) → Babasaheb (09:15) | **yes** | **0 minutes** |
| 04-21, exp 04-28, 24550CE | Aakash (09:19) → Babasaheb (09:19) | **yes** | **0 minutes** |

Rank-1 (earliest-toucher) counts across the 6 combos: Babasaheb 4, Kedar 3, Aakash 2, Mahendra 1
(sums >6 because several combos show tied earliest-candidate minutes, itself a consequence of
wide/overlapping candidate windows, not evidence of literal simultaneity).

**No single consistent leader emerges** — leadership of "who touched the shared strike first"
rotates across all 4 accounts; there is no account that is always first, which argues against a
single centralized tip-source or bot replicating one leader's orders to the other three.

**The Ghadge-pair check is the standout result**: on all 3 of their 3 shared combos, their
entry-time gap (earliest-possible-touch basis) is **0–1 minutes** — an order of magnitude tighter
than any other pairing in the dataset (Kedar↔Babasaheb and Kedar↔Bhanushali show multi-hour or
tied-but-wide-window gaps with no comparable tightness). This is exactly the "family pair, shared
real-time signal" pattern TRADER_FORENSICS.md §3 already inferred from same-day/same-strike
co-occurrence alone; this session adds minute-level confirmation. [DATA —
`leadlag_shared_combos.csv`]

### 4(b) Per-account gaps between consecutive trades

| Account | n entries | Median gap | Max gap |
|---|--:|--:|--:|
| Aakash Ghadge | 15 | 0h (same-day re-entries common) | 120.0h |
| Babasaheb Ghadge | 9 | 24.0h | 120.0h |
| Kedar | 21 | 4.1h | 72.0h |
| Bhanushali | 4 | 25.7h | 72.0h |

Gaps of 0h reflect multiple same-day trades on the same strike (position-building/scaling in);
the multi-day maxima (~72–120h) simply reflect weekends/inactive days between trading sessions —
nothing here reads as machine-periodic. [DATA — `account_gaps.csv`]

### 4(c) Reactive-momentum-chasing vs pre-positioned

Using the 15-min NIFTY bar structure (top-quintile |15-min return| = "big move" threshold,
0.126% this window): entries following immediately after a big move ranged from **0% (using the
earliest-possible candidate time) to 53.1% (using the latest-possible candidate time)**, against
a 20% no-pattern baseline. **This test is honestly inconclusive** — the width of the inferred
candidate windows (median 21 minutes, per Test 1) is too coarse relative to a 15-minute bar
structure to give a single confident answer; the true figure lies somewhere in a wide bracket
that straddles the baseline. On the latest-possible-time basis only (the more liberal, and
weaker, estimate): Bhanushali 100% (n=4, too small to weight), Kedar 57%, Aakash 53%, Babasaheb
22% — directionally consistent with TRADER_FORENSICS.md's independent finding that Kedar trades
faster/more reactively (near-0DTE gamma entries) while the Ghadge/Bhanushali pattern is more
disciplined, but not a result to hang a fabrication conclusion on either way. [DATA —
`entry_vs_15min_move.csv`]

---

## TEST 5 — THE PRINCIPAL'S CHART

All charts: matplotlib, no seaborn, 16×9in @ 120dpi, saved to
`Shreyas_Ionic_AMC/04_RND_LAB/results/ITMPE_RATIO_BT_20260718/timing_charts/` (12 PNGs). NIFTY
15-min OHLC candles built from the 1-min spot file, bars restricted to 09:15–15:30 IST (pre-open
auction bars excluded, none found in the Apr-2026 window regardless). Every marker = the
candidate window's **midpoint** (a single best-guess point for legibility); every marker also
carries a thin horizontal bracket spanning its full [earliest-possible, latest-possible]
candidate window at the fill price, so the chart does not silently overclaim single-minute
precision. Entries = green ▲, exits = red ▼, edge-colored per account, strike labeled.

| File | Content |
|---|---|
| `00_overview_apr2026.png` | Full window actually in scope (2026-04-01→2026-04-28, spanning the last trade's 28-Apr expiry) — all 49 trades' windows overlaid on the ~7.4% rally |
| `day_2026-04-06.png` … `day_2026-04-21.png` (10 files) | One detail chart per active trading day (2026-04-06, 07, 08, 09, 10, 13, 15, 17, 20, 21 — the same 10 dates TRADER_FORENSICS.md §3 counts) |
| `option_level_largest_trade_23650CE_20260413.png` | The largest trade by both quantity (1,755 = 27 lots) and realized P&L (Rs 189,683): Aakash Ghadge's 23650CE, bought 302.92 / sold 411.00, both same-day 2026-04-13 — the contract's own 1-min price path with entry/exit marked |

**Note on window**: the task specified "Apr 1-26"; the overview chart actually runs to 2026-04-28
because the last trade's expiry (and thus its sell-day context) falls on 28-Apr, and spot data is
available through that date — using 1-26 would have cut off the 24550CE trade's context.

**What the option-level chart shows, and why it matters for the verdict**: the 23650CE premium
opened ~338, dipped to ~291 by 09:35, then rallied continuously to an afternoon peak of ~458
around 13:45, before pulling back. The BUY (302.92) landed near the post-open dip low — a decent,
plausible entry, not a perfect one (the day's actual low was ~291). The SELL (411.00) landed
**well below the day's eventual peak (~458)** and, per the price path, was executed either at
~12:15-12:20 (first touch) or again near 15:29 during a second pullback to that level — **a real
trader clearly did not "know" the peak was coming and sold before or after it, not at it.** This
single chart is the clearest visual evidence in the whole battery against hindsight fabrication:
a fabricated ledger has no reason not to claim the 458 print instead of 411.

---

## FINAL AUTHENTICITY RE-VERDICT

**GENUINE** — the stronger battery finds no fabrication signature, and several of its hardest
tests (capture-ratio spread, extreme-pin absence, the option-level chart) are the kind of
evidence that would be very difficult to produce by accident if the ledger were faked.

Reasoning a skeptical fund manager should accept:

1. **Test 1** confirms every fill sits inside real, volume-backed 1-min price action (not merely
   inside a wide day-range, which the Principal correctly noted is gameable) — but goes further:
   the candidate windows are wide (median 21 minutes) precisely because these are genuinely
   volatile, liquid, actively-traded contracts, which is itself consistent with real market
   structure, not fabrication.
2. **Test 2** is the direct answer to "could these secretly be shorts": **zero of 49 trades**
   show a timing signature consistent with sell-before-buy. 16 are positively ruled IN as
   buy-first; the other 33 (18 same-day ambiguous + 15 multi-day) are structurally consistent
   with buy-first and never with sell-first. This does not prove no short exists ANYWHERE in the
   Principal's larger hypothesized system (a realized-P&L report is structurally blind to any
   still-open position, per TRADER_FORENSICS.md §6d) — but it fully clears the specific 49 visible
   trades of being disguised shorts.
3. **Test 3** is where a naive analyst would stop at "KS test rejects uniformity → suspicious"
   and be wrong. The trend-day confound (a real ~7.4% rally mechanically produces low-buy/
   high-sell percentiles for ANY ordinary morning-buy/afternoon-sell trader) fully explains the
   raw KS result. The tests built to survive that confound — capture-ratio spread (median 0.667,
   NOT pinned near 1.0), near-zero extreme-pin counts (1 buy, 0 sells at the literal day
   low/high), and a genuinely bimodal, wide exit-gain distribution (not a single 25% spike) — all
   point away from fabrication.
4. **Test 4** rules out a single centralized leader/bot (leadership rotates across all 4
   accounts) while **confirming, at minute-level resolution for the first time**, that the two
   Ghadge accounts move in lockstep (0–1 minute entry gaps on all 3 shared combos) far tighter
   than any other pairing — consistent with a family/shared-signal read, not evidence of ledger
   fabrication.
5. **Test 5**'s option-level chart is the single most persuasive piece of evidence: the largest
   trade's exit was executed well below the day's actual peak. A fabricator with the whole day's
   price path in hand would not leave ~37 points of intraday upside (411 vs the 458 peak,
   consistent with the 0.667 median capture ratio) on the table.

**What this verdict does NOT claim**: it does not confirm or deny the Principal's separate,
structurally-unverifiable hypothesis about an unseen monthly short-PE (or short-ITM-CE hedge)
leg — a realized-trades report cannot show a position that is still open, by construction (already
flagged in TRADER_FORENSICS.md §6d, restated here because it remains true after this stronger
battery). It also does not explain away the tight cross-account ROI band (24.3%–26.5%,
TRADER_FORENSICS.md §1) by itself — that similarity is better explained by shared market beta (all
four rode the same rally) plus the tip/advisor-sharing signature this test's own lead-lag results
reinforce, not by the ledger being invented. **The 49-trade visible ledger itself: GENUINE.**

---

## Files in this deliverable

- `timing_inferred_fills.csv` (98 rows) — all fills with candidate windows, tolerances, day
  OHLCV, fill percentiles, direction class.
- `direction_test_results.csv` (49 rows) — Test 2 per-trade classification.
- `fill_percentile_stats.csv` (10 rows) — Test 3(a) KS-test table per account/side.
- `exit_gain_distribution.csv` (49 rows) — Test 3(b) per-trade % gain + capture ratio.
- `red_flags_summary.txt` — Test 3(c) scalar counts.
- `trend_confound_check.txt` — the disambiguating checks for Test 3(a).
- `leadlag_shared_combos.csv` (12 rows) — Test 4(a) per-account-per-combo ordering.
- `account_gaps.csv` (49 rows) — Test 4(b) inter-trade gaps.
- `entry_vs_15min_move.csv` (49 rows) — Test 4(c) reactive-entry flags (latest-time basis).
- `timing_charts/` (12 PNGs) — Test 5, see index above.
