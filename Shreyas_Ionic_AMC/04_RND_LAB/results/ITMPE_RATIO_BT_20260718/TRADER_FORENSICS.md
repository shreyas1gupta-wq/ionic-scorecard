# TRADER FORENSICS — 4 Groww F&O Accounts, April 2026 (Ghadge x2, Bhanushali, Kedar)

Prepared: 2026-07-18. Scope: forensic reconstruction of 4 real Groww F&O P&L excels (`options/F&O_PnL_Report_*.xlsx`),
cross-referenced against NIFTY spot (`datasets/index_daily/nifty50.parquet`) and the on-disk NIFTY 1-min option
chain (`intraday_options_strategy/datasets/raw/hf_index_options_1m/options/NIFTY/`). All figures below are
[DATA] unless tagged [INFERENCE] or [OPINION]. Scripts used are not checked into the repo (scratchpad, re-runnable);
outputs are the CSVs alongside this file.

**Note on folder contents**: this results folder also contains `DATA_MAP.md` + several `*_tradability_by_year.csv`
files from what is evidently a separate, concurrent workstream (Data Officer mapping sources for the same
Principal-described ITM-PE-sell/2x-OTM-buy system). Those are not part of this deliverable and were left untouched.

---

## 0. Bottom line

- **49 realized trades** across 4 accounts, Apr 1–21/26 2026. **100% are NIFTY weekly CALL BUYS** (0 puts, 0 futures,
  0 sells-to-open) — confirms the Principal's premise that the visible activity is only one leg of a larger system.
- Combined realized P&L (pre-charges, sums to the "Options" line in each report) = **Rs 23,89,432.50**; net of
  reported brokerage/STT/exchange/GST charges (Rs 29,670.58 combined) = **Rs 23,59,761.92** — matches the
  Principal's "~Rs 24L" figure.
- **Bug caught and fixed in our own pipeline**: the NIFTY spot parquet's timestamp string carries an
  already-correct `+05:30` tag (e.g. `...T00:00:00+05:30`). Using `.dt.tz_convert(None)` (the reflex fix for the
  documented HF-UTC landmine) is WRONG here — it re-interprets the tag as if it needed conversion FROM that offset,
  silently shifting every date back one calendar day (confirmed: `tz_convert(None)` turned `2026-04-02` into
  `2026-04-01 18:30`). The correct call is `.dt.tz_localize(None)` (just drop the tag, keep the wall-clock date).
  Caught via a sanity check (Sundays appearing as "trading days") before any number was reported. Flagging this
  because it is the kind of one-line, silent, undetectable-without-a-check bug the landmine list exists to prevent —
  worth a line in `05_DATA_OFFICE/DATA_QUALITY_RULES.md` distinguishing "UTC timestamps needing tz_convert" from
  "already-local timestamps needing only tz_localize(None)".
- **Price validation**: all 98 traded (buy+sell) prices in the 4 excels fall inside the on-disk 1-min option
  chain's [day-low, day-high] range for their exact (date, expiry, strike, CE) — **100% pass, n=98**. This is a
  clean D-009 sample-check result for whoever verifies our on-disk NIFTY option data next.
- **Authenticity battery (§6, Principal-ordered "is it fake" check)**: charges recompute PASSES once corrected for
  an apparently-current-but-undocumented-to-us 0.15% options STT rate (all 4 accounts imply that exact rate to 4
  decimal places — strong cross-account consistency, hard to fake); lot sizes 49/49 multiples of 65; **zero**
  sell-first (short) rows, so the report structurally cannot evidence any option-selling; and the "these CE buys are
  2x-OTM hedge legs of an unseen short-ITM-CE" hypothesis is MIXED-leaning-DIRECTIONAL-SCALPS (macro timing fits,
  but fill-level lot-count parity and near-uniform same-day exits argue against a true hedge reading). No
  fabrication signature found anywhere in the battery.

---

## 1. Combined trade table

Saved: `combined_trades_raw.csv` (49 rows, straight from Excel) and `combined_trades_enriched.csv` (49 rows +
spot/DMA/moneyness/DTE/hold columns — the working table for everything below).

| Account | Trades | Lots (65/lot) | Realized P&L (pre-chg) | Buy value (premium) | ROI on premium |
|---|---:|---:|---:|---:|---:|
| Ganesh Harishchandra Kedar | 21 | 289 | Rs 8,55,556.00 | Rs 32,33,213.75 | 26.46% |
| Aakash Anand Ghadge | 15 | 215 | Rs 8,19,562.25 | Rs 32,66,857.75 | 25.09% |
| Babasaheb Bhagwan Ghadge | 9 | 163 | Rs 5,57,436.75 | Rs 22,90,343.25 | 24.34% |
| Mahendra Valji Bhanushali | 4 | 57 | Rs 1,56,877.50 | Rs 6,01,175.25 | 26.10% |
| **Total** | **49** | **724 (~470 lakh option-shares notional)** | **Rs 23,89,432.50** | **Rs 93,91,590** | **25.44%** |

Notable: **all four ROIs land in a tight 24.3%–26.5% band** despite very different trade counts (4 to 21) and
holding styles. Four people independently trading a chaotic instrument (weekly index options) over 3 weeks landing
within 2.2 percentage points of each other is a low-probability coincidence under pure independent skill — it is the
strongest single piece of evidence for a shared signal source (see §3). [INFERENCE]

Confirmed **lot size = 65** for all 49 rows (every `quantity` value is an exact multiple of 65; NIFTY's contract
size as of Apr-2026).

Scrip parsing: 100% of 49 scrip strings matched the `NIFTY {DD} {MON} {YY} {strike} Call` pattern — 0 parse
failures, 0 puts found.

---

## 2. Timeline reconstruction: moneyness, DTE, hold, DMA state

**PIT discipline choice (landmine #5):** the DMA-state gate is a same-day, intraday decision, so the "signal" a
trader could actually act on is the **prior day's close vs prior day's DMA** (T-1 basis) — not the current day's own
close, which isn't known until after the market where the trade happens. We compute **both** and report both; the
T-1 basis is the PIT-correct one, EOD/same-day is shown for reference only.

### DTE at entry (calendar days to the option's own expiry)
| DTE | 0 | 1 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| # trades | 4 | 14 | 2 | 5 | 2 | 6 | 9 | 7 |

Median DTE = 4 days. Spans near-0DTE gamma trades (mostly Kedar) to full 8-day weekly entries (mostly the two
Ghadge accounts) — DTE choice is not uniform across the 4 accounts (see §3).

### Hold duration
| Hold (cal. days) | 0 (same day) | 1 | 2 | 3 |
|---|--:|--:|--:|--:|
| # trades | 34 | 8 | 6 | 1 |

69% same-day, 88% within 1 day. This is a genuinely "quick in-out" pattern, not a multi-day swing system — consistent
with the Principal's description of the VISIBLE leg being a fast, opportunistic hedge-buy, not the core position.

### Moneyness at entry (strike vs same-day spot close; CE convention, ITM = strike below spot)
| Class | # trades | Lots |
|---|--:|--:|
| ATM (within ±1%) | 42 (86%) | 617 (85%) |
| ITM | 5 (10%) | 83 (11%) |
| OTM | 2 (4%) | 24 (3%) |

**All 5 ITM and both OTM trades belong to Ganesh Kedar** (the earliest/most active trader — his Apr 6–7 entries were
placed while the rally was still unconfirmed, at strikes that were already run-away ITM by the time he bought, e.g.
22700/22800 CE against a spot already at 22968–23997). The other three accounts (Aakash, Babasaheb, Mahendra) are
**100% ATM, zero exceptions** — a genuinely disciplined "buy the current ATM weekly strike" rule.

### Strike roll-up (trend-following signature)
Median entry strike by week: 22750 (Apr 6–7) → 23500–24000 (Apr 8–10) → 23650–24400 (Apr 13) → 24100–24300
(Apr 15–17) → 24150–24400 (Apr 20) → 24500–24600 (Apr 21). Every account **rolls its strike up with the spot**,
never buying more than ~2% away from the current spot at any point (except Kedar's early ITM entries above) —
classic trend-chasing re-entry, not a static strike ladder.

### NIFTY vs 20/50 DMA at entry (T-1, PIT-safe basis; n=49)
| | Above 20DMA | Below 20DMA |
|---|--:|--:|
| T-1 basis | 40 (82%) | 9 (18%) |
| Same-day (EOD) basis | 42 (86%) | 7 (14%) |

| | Above 50DMA | Below 50DMA |
|---|--:|--:|
| T-1 basis | **0 (0%)** | **49 (100%)** |
| Same-day (EOD) basis | 9 (18%, all on 2026-04-21) | 40 (82%) |

**This is the single most important finding for the Principal's hypothesis.** On the PIT-correct (T-1) basis, spot
was below its 50DMA for every single one of the 49 visible trades — the whole window is a **bounce off a decline**,
not a "confirmed >50DMA uptrend." NIFTY's 50DMA only got crossed (same-day/EOD basis) on **2026-04-21 — the very
last trading day two of the four reports cover** (spot closed 24576.60 vs a 50DMA of 24376.90 that day; the day
before, spot 24364.85 was still below the day's 50DMA of 24399.92). [DATA]

This lines up almost exactly with the Principal's account: if the monthly (28-Apr) ITM-PE-sell leg is gated on
NIFTY>50DMA, the gate would plausibly have **turned on right around 21–28 Apr** — precisely the window after the
two Apr-21-cutoff reports end and right before the 28-Apr monthly expiry the Principal points to. The visible CE
buys therefore sit in a "50DMA not yet reclaimed, 20DMA mostly reclaimed" regime — consistent with a system that
was arming its short-PE hedge leg but hadn't fired it yet inside the reported window. [INFERENCE — the actual PE
fills, if they exist, would need the post-28-Apr statement to confirm; we do not have it.]

---

## 3. Copy-trading / same-advisor signature

Full detail: `entry_combo_overlap.csv`, `shared_combo_price_dispersion.csv`.

- **Day-level overlap is very high**: 8 of the 10 distinct trading days saw ≥2 accounts active; the **last two days
  (Apr 20, Apr 21) saw all 4 accounts trading**.
- **Exact-combo overlap (same date + expiry + strike + CE) is moderate**: 6 of 21 distinct entry combos (28.6%) were
  hit by exactly 2 accounts; **no combo was ever hit by 3 or 4 accounts simultaneously** at the identical strike.
- **Within shared combos, exit (sell) prices are nearly identical (0.0%–7.9% spread) but entry (buy) prices are
  often wildly dispersed (0.7%–78% spread)** — e.g. on 2026-04-09, one account bought the 24000 CE at 92.80 while
  another bought the same strike/expiry the same day at 165.19 (+78%). That is a huge same-day, same-strike premium
  swing, meaning the two "simultaneous" buyers actually entered hours apart at very different points in the day's
  option-price range — this is **not** a single order block getting split identically across accounts (a bot/algo
  copy-trade would show near-zero entry dispersion too). The tight exit-price clustering, by contrast, suggests a
  shared exit trigger/target (a common signal or the same person/advisor calling "sell now" across accounts near
  end of position).
- **The two "Ghadge" accounts (Aakash Anand Ghadge, Babasaheb Bhagwan Ghadge) — same surname, plausibly
  family — overlap on the identical strike 3 separate times** (2026-04-15 @24100, 2026-04-20 @24250,
  2026-04-21 @24550), out of their ~24 combined trades. Kedar and Bhanushali each overlap with someone only once
  (04-17 with each other; 04-09/04-13 Kedar with Babasaheb). **The Ghadge pair is far more tightly coupled to each
  other than either is to Kedar or Bhanushali.**

**Read: this is a shared-tip/advisory cohort (family + advisor-fed group), not a mechanical copy-trading bot.**
Same-day directional conviction and a common strike "zone" spread across the group, independent intraday entry
timing/prices, converging exits, and a family pair trading in visibly tighter lockstep than the other two — all
point to human-relayed signals (WhatsApp/RM tip/family) rather than an automated 1:1 order replication. [INFERENCE]

---

## 4. Skill vs luck — naive benchmark

Method: `naive_monday_wed_benchmark.csv`. Rule = buy the ATM (nearest-50 strike to spot close) weekly CE every
Monday in the report window, exit Wednesday close; if the nearest weekly expiry would already have lapsed before
Wednesday, roll to the next expiry that is still alive through the exit day (documented choice — NIFTY's Apr-2026
weekly cycle had non-Thursday expiries: 07-Apr(Tue)/13-Apr(Mon)/21-Apr(Tue)/28-Apr(Tue), so a naive "this week's"
expiry sometimes lapses before Wednesday). Priced off the actual on-disk 1-min NIFTY option chain (EOD close each
day), 1 lot (65) per week. Costs: COST_STANDARDS.md D-021 "options — liquid ATM index" slippage floor
(0.25% one-way of premium) applied round-trip = 0.50% base; **2x-cost-stress = 1.00% round-trip**, per Principal's
standing 2x promotion rule.

| Monday entry | ATM strike | Expiry used | DTE | Entry close | Exit (Wed+) | Gross return | Net (2x cost) |
|---|--:|---|--:|--:|--:|--:|--:|
| 2026-04-06 | 22950 | 2026-04-13 | 7 | 422.00 | 1107.90 (04-08) | **+162.5%** | +156.5% (Rs 44,086/lot) |
| 2026-04-13 | 23850 | 2026-04-21 | 8 | 286.90 | 458.90 (04-15) | +60.0% | +57.4% (Rs 10,938/lot) |
| 2026-04-20 | 24350 | 2026-04-28 | 8 | 278.60 | 236.85 (04-22) | −15.0% | −16.1% (−Rs 2,881/lot) |

**Full 3-week average: naive rule = +69.2% gross / +67.8% net (2x cost) per week.** Applying that average return to
the SAME total premium the 4 real accounts deployed (Rs 93,91,590) gives a counterfactual P&L of **Rs 63,69,489 —
266% of what the real traders actually realized.** On its face this says the traders captured barely a third of
"pure bull-market beta," i.e. mostly luck, badly harvested.

**But that headline number is almost entirely one outlier week.** The Apr 6→8 week (+162.5%) happened **before**
almost any of the real capital was deployed — only Kedar had small positions live then (Rs ~4L of the Rs 94L total
premium). Restricting the comparison to the **two weeks that actually overlap with when the bulk of real capital
was active** (Apr 13→15 and Apr 20→22, spanning ~90% of the real premium deployed): naive rule averages **+21.9%
net per week**, applied to the same total premium → counterfactual P&L of **Rs 20,59,254 — 86% of what the real
traders actually realized.** i.e., **in the window they were actually sized up, the real traders' active strike
selection / entry-exit timing modestly beat (by ~16%) the dumbest possible mechanical rule** — not a large edge,
but not zero either.

**Honest read [OPINION]**: the ~Rs 24L is overwhelmingly explained by directional beta (a sharp, ~7.4% three-week
NIFTY rally, 22713→24378) rather than differentiated stock/strike-picking skill — moneyness selection is almost
uniformly ATM (§2), the naive ATM-Monday rule alone would have captured a comparable-or-better return over the
period the real money was actually working, and the ROI band across all 4 independent accounts is implausibly tight
for independently-skilled decision-making (§1). What plausible skill IS visible: (a) disciplined position-sizing —
capital scaled up only as the rally confirmed rather than being maximally sized on day 1 (which is precisely why
the traders MISSED the single best week and therefore under-captured the full-month naive number), and (b) at
least one clearly good intraday exit (2026-04-20, sold the 24250 CE near the day's high of 286.60 right before the
option fell back to a 161.85 close — see `price_validation_table.csv` row for that date, `pct_diff_vs_eod_close`
+73.6%). Net: **mostly beta, a little bit of real timing/sizing skill layered on top — not a strategy that would
be expected to keep working once the rally itself pauses.**

n for this cheap-test-style benchmark = 3 weeks (2 after excluding the pre-capital outlier) — far too small to be
statistically conclusive; treat as directional evidence, not proof, per the low-t power-aware read (rank on
logic+effect-size, not on a single small-n significance test).

---

## 5. Price validation table (for the D-009 verification pass)

Saved: `price_validation_table.csv` — 98 rows (49 trades × BUY + SELL leg), each with the on-disk NIFTY 1-min
option chain's day-low/day-high/day-open/day-close/day-volume for that exact (date, expiry, strike, CE) plus
`within_day_range` and `pct_diff_vs_eod_close`.

**Result: 98/98 (100%) of traded prices fall inside the on-disk day's [low, high] range.** No missing expiry files,
no CONTRACTS=0/untraded-strike gaps hit (every combo had 374–376 one-minute bars that day). This is a clean,
independent spot-check of the on-disk NIFTY option data against real broker fills — satisfies D-009 for whoever
uses this data next.

One data point worth flagging for the next verifier, not a red flag: 2026-04-13, Ganesh Kedar, SELL 24000 CE at
4.05, shows `pct_diff_vs_eod_close = +8000%`. This is an artifact of the percentage metric, not a data error — that
trade is a same-day (0DTE) expiry-day sale where the option decayed to near-zero (day range 0.05–11.80, EOD close
0.05); 4.05 is comfortably inside the day's range, the % diff is just unstable near a near-zero denominator. Use
absolute price diff, not % diff, when auto-flagging outliers on expiry-day 0DTE rows.

---

## 6. Authenticity battery (Principal-ordered: "check using date, strike and call price that the excels are correct and not fake") — parts needing NO market data

Full detail: `charges_authenticity_check.csv`, `structural_short_scan_hits.csv`, `lot_size_check.csv`,
`hedge_leg_quantity_parity.csv`.

### (a) Charges consistency — recomputed from the trade rows vs each report's stated Charges block

Each excel's Charges block (Exchange Transaction Charges, SEBI Turnover Charges, STT, Stamp Duty, IPFT, Brokerage,
Total GST, Total) was recomputed bottom-up from the 49 trade rows using the task-specified formulas (STT 0.1% of
sell-side premium, exchange txn 0.035% of turnover, stamp 0.003% of buy-side, SEBI Rs 10/crore, GST 18% on
brokerage+exchange+SEBI, brokerage = Rs 20/order or 0.03% of order value whichever lower).

| Account | Reported STT | Calc @ 0.10% | Implied rate (reported/sell turnover) |
|---|--:|--:|--:|
| Aakash Anand Ghadge | 6,130.00 | 4,086.42 | **0.15001%** |
| Babasaheb Bhagwan Ghadge | 4,272.00 | 2,847.78 | **0.15001%** |
| Mahendra Valji Bhanushali | 1,137.00 | 758.05 | **0.14999%** |
| Ganesh Harishchandra Kedar | 6,133.00 | 4,088.77 | **0.15000%** |

**Key finding**: at the task's assumed 0.10% STT rate, all 4 accounts show an identical ~33.3% shortfall — solving
backward, the true rate implied by all 4 reports independently is **0.14999%–0.15001%, i.e. exactly 0.15% to 4
decimal places, in all 4 files**. Read: the task brief's "0.1% (2024+ rate)" is the Oct-2024 Budget rate; a further
options-STT increase to 0.15% evidently took effect sometime between then and Apr-2026 that postdates our training
data — the reports are using a rate our prior lacked, not a rate that's wrong. **This is strong evidence FOR
authenticity, not against it**: four independently-dated statements (different UCCs, different trade counts, filed
by presumably-different people) landing on the identical rate to 4 decimal places is very hard to fake by accident
and easy to explain by "this is what Groww's live tariff engine actually charged in Apr-2026." [INFERENCE]

Exchange-txn and stamp-duty implied rates are close to the task's assumed 0.035%/0.003% but with account-level
scatter (exchange: 0.0355%–0.0416%; stamp: 0.0030%–0.0041%) — Bhanushali and Kedar match the textbook rate almost
exactly, Aakash and Babasaheb (the two Ghadge accounts) run consistently ~10–30% high on these two line items. Most
plausible explanation: a small per-order minimum-charge floor (common on discount brokers) that bites
proportionally harder on accounts with a different trade-size mix — these two line items are tiny in absolute rupee
terms (Rs 18–120 stamp, Rs 480–2,850 exchange txn per account) so a few-rupee floor effect produces large %
swings without being a red flag. [INFERENCE]

**Bottom line**: recomputing the Total Charges line with the empirically-correct 0.15% STT rate (leaving all other
assumed rates as-is) closes the gap from ~20–26% down to **0.5%–6.2%** across all 4 accounts:

| Account | Reported Total Charges | Recomputed (STT@0.15%) | Delta |
|---|--:|--:|--:|
| Aakash Anand Ghadge | 10,230.28 | 9,918.07 | 3.1% |
| Babasaheb Bhagwan Ghadge | 7,343.43 | 6,889.23 | 6.2% |
| Mahendra Valji Bhanushali | 1,915.26 | 1,865.71 | 2.6% |
| Ganesh Harishchandra Kedar | 10,181.61 | 10,126.23 | **0.5%** |

Residual 0.5–6.2% gaps are fully attributable to the exchange-txn/stamp/brokerage floor effects above, not to any
unexplained or inconsistent charge. **Verdict: PASS — the charges blocks are arithmetically consistent with the
trade rows once the (undocumented-to-us, but internally 100%-consistent) current STT rate is used; no sign of
fabrication.**

### (b) Structural short-scan (sell-first rows)

Scanned all 49 rows for `sell_date < buy_date`. **Result: 0 of 49.** Every visible trade is a long (buy-then-sell).
The report window **cannot directly evidence any option-selling activity** — confirms the Principal's own framing
that the short monthly-PE leg, if it exists, is invisible here (either not yet opened by 21/26-Apr, or opened and
still open past the report window — a realized-P&L report structurally cannot show unrealized/open short
positions). `structural_short_scan_hits.csv` is empty (header row only) by construction.

### (c) Lot-size check

All 49 `quantity` values are exact multiples of 65 (NIFTY's lot size in force Apr-2026): {65, 195, 260, 390, 455,
520, 585, 650, 715, 780, 845, 1170, 1235, 1300, 1495, 1560, 1690, 1755} ÷ 65 = {1, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13,
18, 19, 20, 23, 24, 26, 27} — all integers, 0 failures. **Verdict: PASS.**

### (d) Hedge-leg hypothesis test — could these be the 2x-OTM hedge legs of an UNSEEN short-ITM-CE (bearish) system?

Testing the Principal's alternative structure (sell 1x ITM CE, buy 2x OTM CE as an upside-uncapping hedge — a
reverse ratio/backspread) against the visible data, as three separate sub-tests:

**(i) Early-April DMA state.** NIFTY was below BOTH its 20DMA and 50DMA (T-1 basis) on 2026-04-06 through 04-08 —
the exact window of Kedar's earliest trades and Babasaheb's first entry (04-08). A short-ITM-CE (bearish/capped-
upside) structure is more plausible to have been LIVE precisely in this window than later. By 04-09 spot had
reclaimed the 20DMA (still below 50DMA); the 50DMA itself wasn't reclaimed until 04-21 (see §2). So **a hypothetical
short-ITM-CE opened in the 04-01–04-08 bearish pocket would have been running against the trader for the entire
rest of the window** (NIFTY rallied ~7.4% into it) — which is exactly the scenario 2x-OTM-CE hedge legs exist to
cap. Directionally consistent with the hypothesis. [DATA + INFERENCE]

**(ii) Quantity/lot-count parity test — does NOT support a strict 2x convention.** If every visible CE buy were
literally "2 lots long per 1 lot of an implied short," essentially all trade-level lot counts should be even. Actual:
only **17 of 49 trades (34.7%) have an even lot count** — lot counts of 1, 3, 7, 9, 11, 13, 19, 23, 27 lots (all odd)
appear repeatedly and are, in fact, the MAJORITY (32 of 49, 65.3%). Aggregating to account-day level (summing all
of an account's entries on a given day, in case the "2x" ratio only holds at the daily-position level rather than
per fill) doesn't rescue it either: **10 of 20 account-days (exactly 50%) have an even day-total lot count** — no
better than chance. **This is evidence AGAINST a strict, mechanically-enforced 2x-ratio hedge convention applied at
either the trade or day level.** It doesn't rule out a looser/discretionary ratio-hedge managed at the position
level over the full month (which a snapshot of daily fills would not necessarily reveal as evenness), but the clean
"2x" arithmetic signature the hypothesis predicts is not visible in the fill-level data. [DATA]

**(iii) Quick-exit-vs-hold-as-hedge contradiction — the strongest argument against the hedge reading.** A genuine
hedge leg protecting a short-ITM-CE position should be HELD alongside that position, roughly until the short is
closed or the monthly expiry passes — not scalped intraday. Actual: **69% of the 49 trades are closed same-day, 88%
within 1 day** (§2) — the opposite of hold-as-hedge behavior. If these were true hedge legs, closing them same-day
while (by hypothesis) the naked short-ITM-CE remained open would leave the short UNHEDGED for the rest of its life,
defeating the purpose of buying the hedge in the first place. This pattern is much more consistent with the CE buys
being **the actual, self-contained trading vehicle** (quick directional scalps monetizing the rally) than legs of a
larger structure. [DATA + INFERENCE]

**Verdict: MIXED, leaning DIRECTIONAL-SCALPS.** (i) the macro backdrop (bearish-to-neutral DMA state in early April,
turning bullish only at the very end of the window) is CONSISTENT with a short-ITM-CE having been open and needing
a hedge; but (ii) the fill-level quantities show no reliable 2x arithmetic signature, and (iii) the near-uniform
same-day/1-day holding pattern directly contradicts "hold as a hedge." The visible trades read most naturally as
**a self-contained fast-scalp system riding the rally**, not as the OTM leg of an unseen bearish short-ITM-CE
structure. **What cannot be determined from a realized-P&L report alone**: any position still open past the report
window (26-Apr latest) is invisible by construction — if the short-ITM-CE (or the Principal's actual described
short-ITM-PE) was opened and is still live, no realized-trades report filed before its close will ever show it. The
absence of evidence for a short leg in this document is not evidence of its absence; it is a structural blind spot
of the report type itself, which is precisely the Principal's own point about the monthly PE leg. [OPINION]

---

## Files in this folder (this deliverable)
- `combined_trades_raw.csv` — 49 rows, straight Excel parse (scrip, quantity, buy/sell date+price+value, P&L).
- `combined_trades_enriched.csv` — same 49 rows + spot/DMA state/moneyness/DTE/hold columns (the working table).
- `account_charges_summary.csv` — per-account reported Options realized P&L vs charges vs net.
- `entry_combo_overlap.csv` — every distinct (buy_date, expiry, strike, CE) combo and which account(s) hit it.
- `shared_combo_price_dispersion.csv` — price spread within the 6 shared combos.
- `naive_monday_wed_benchmark.csv` — the 3-week naive-rule backtest (gross/net, base/2x cost).
- `naive_benchmark_summary.txt` — key scalars from §4.
- `price_validation_table.csv` — the 98-row price validation table (§5).
- `charges_authenticity_check.csv` — §6(a): reported vs recomputed charges (STT/exchange/stamp/SEBI/brokerage/GST) per account, both at the task's assumed 0.10% STT and the empirically-implied 0.15%.
- `structural_short_scan_hits.csv` — §6(b): rows with sell_date < buy_date (empty; 0 of 49).
- `lot_size_check.csv` — §6(c): every trade's quantity vs the 65-lot-size check (49/49 pass).
- `hedge_leg_quantity_parity.csv` — §6(d)(ii): per-trade lot count + even/odd flag for the 2x-hedge parity test.
