# TAIL_CONVEXITY — Payoff-SHAPE Audit of ALPHA_RANKER Signals

Author: Kabir Anand (Head of Hedging & Tail Risk), Shreyas_Ionic_AMC. Date: 2026-07-17.
Tags [DATA]/[INFERENCE]/[OPINION] used throughout per firm protocol.

**Task**: the entire ALPHA_RANKER corpus is scored on monthly rank-IC (linear, "does the
signal separate winners from losers on average"). The Principal's stated interest is a
different question entirely — a **convex payoff**: near-zero cost/signal most of the time,
a large positive payoff in the rare bad state. This is a genuine blind spot: nothing in the
corpus was built or screened for payoff SHAPE. This memo tests every leg + wave-4 candidate
for shape, not correlation.

## 0. Method

For each signal: rank cross-sectionally each month, form an equal-weight **top-quintile
minus bottom-quintile (LS)** portfolio on `fwd_ret_1M_raw` (disc-event months NaN'd, same
convention as `run_long_confirm.py`), dates with <15 priced names dropped (thin-universe
guard). From the monthly LS series compute: hit rate, avg win / avg loss, skew (raw, no
winsorizing — CVaR/raw-worst discipline), and the **conditional mean LS return** in (a) the
worst decile of NIFTY500 forward-1M months (25 of 248 months, cutoff ≤ −5.66%) and (b) three
named crash episodes: GFC (Aug-2008→Feb-2009, 7 months), COVID (Jan–Mar-2020, 3 months),
2022 rate-hike selloff (Dec-2021→Jun-2022, 7 months). Full month-by-month episode detail and
raw JSON in `rnd/wave4/tail_convexity_artifacts/`.

12 capstone legs (7 canonical + 5 dropped/secondary, from `capstone_legs.parquet`) rebuilt
directly from stored PIT scores — no rebuild risk. Wave-4 candidates rebuilt from their
**actual card-producing builder functions** (`builders_w4t_forensic.py` for clean-surplus and
depreciation-laxity, `builders_mom.py::build_beta_adjusted_mom` for H043) — same PIT joins as
the cards. **Amihud has no persisted builder** (the WAVE4_FINDINGS.md note "volume data is
5yr-only" confirms `cube_volume.parquet` only starts 2021-07); rebuilt here as a standard
trailing-21d Amihud illiquidity z-score from `cube_close_long`/`cube_volume` — **[INFERENCE]
a simplified reconstruction, NOT the exact size-residualized card construction** (that code
was not persisted). Read Amihud's numbers as directional only.

Low-n honesty: 3 crash episodes is not a statistically powered sample. Judgment is by
economic logic + cross-episode consistency + large per-month cross-sections (378–701 names
per crash month, so within-month noise is not the concern — episode-COUNT is).

## 1. Per-signal payoff shape

| Signal | Leg type | Hit rate | Avg win/loss | Skew | Worst 1M (date) | Worst-decile-mkt cond. | GFC ep. mean | COVID ep. mean | 2022 ep. mean | Shape |
|---|---|---|---|---|---|---|---|---|---|---|
| value_EY | canon-7 value | 0.57 | +2.6%/−2.6% | +0.29 | −9.4% (2011-10) | −1.2% | no data | **−2.6%** | +1.6% | LINEAR |
| value_dcf_revgap | secondary value | 0.57 | +2.3%/−2.1% | +0.11 | −10.7% (2017-04) | −2.8% | no data | −1.5% | +0.3% | LINEAR |
| value_marketstate_M3 | secondary value | 0.54 | +2.6%/−2.6% | −0.60 | −14.7% (2010-07) | +0.5% | no data | −2.2% | +1.4% | mild CONCAVE |
| value_smallcap_M2 | secondary value | 0.52 | +3.4%/−2.8% | +0.58 | −10.5% (2017-11) | +0.5% | no data | +1.9% | +1.2% | mild convex, thin-n |
| **mom_resid_peer** | canon-7 momentum | 0.65 | +2.8%/−3.6% | **−2.41** | **−31.1% (2009-04)** | +2.3% | +0.1% | −0.2%* | +1.1% | **CONCAVE — crash-prone** |
| trend_ma65_slope | canon-7 trend | 0.64 | +4.0%/−4.1% | −0.82 | −20.6% (2011-12) | +3.2% | +3.7% | −3.1% | +1.9% | mixed / mild CONCAVE |
| **quality_QMJ** | canon-7 quality | 0.52 | +4.6%/−5.2% | −1.62 | **−45.2% (2009-04)** | +8.3% | +1.8% | **+5.6%** | −1.1% | **MIXED: convex in the decline, concave at the rebound** |
| quality_cfo_pat | canon-7 forensic (thin-n) | 0.53 | +2.1%/−1.1% | **+1.30** | −3.5% (2018-05) | +2.4% | no data | **+4.6%** | +0.1% | **CONVEX-leaning, data-limited** |
| bs_issuance | canon-7 balance-sheet | 0.45 | +2.1%/−2.6% | −0.59 | −12.8% (2012-08) | +2.6% | no data | −0.2% | −0.2% | LINEAR / weak-mild concave |
| bs_asset_growth | canon-7 balance-sheet | 0.54 | +2.8%/−2.3% | +0.50 | −16.8% (2012-05) | −0.1% | no data | −0.6% | −0.5% | LINEAR |
| **defensive_BAB** | dropped (redundant w/QMJ) | 0.54 | +5.0%/−5.5% | −1.37 | **−45.4% (2009-04)** | +8.8% | +1.7% | **+11.7% (all 3 months +)** | −1.1% | **Same MIXED pattern as QMJ, most extreme** |
| seasonality | dropped (passenger) | 0.62 | +2.5%/−2.1% | −0.56 | −17.5% (2020-05) | +0.4% | −0.7% | +0.6% | +0.6% | LINEAR |
| W4_clean_surplus_health | wave-4 forensic candidate | 0.51 | +2.0%/−2.1% | **+3.04** | −7.1% (2016-03) | +1.9% | no data (post-2012 only) | +1.4% | +1.3% | **CONVEX-leaning, data-limited** |
| W4_dep_health | wave-4 forensic candidate | 0.52 | +1.4%/−1.6% | −0.06 | −4.7% (2024-07) | +1.5% | no data (post-2011 only) | +0.1% | −0.5% | LINEAR |
| W4_beta_adj_mom (H043) | wave-4 momentum candidate | 0.70 | +3.0%/−2.6% | −0.03 | −8.4% (2024-12) | +1.8% (n=2) | **no coverage** | **no coverage** | **no coverage** | **CANNOT ASSESS — starts 2022-07, misses all 3 episodes** |
| W4_amihud_illiq [simplified rebuild] | wave-4 liquidity candidate | 0.62 | +3.7%/−2.3% | +0.06 | −6.0% (2021-07) | −1.2% (n=2) | no coverage | no coverage | +1.2% (worst −4.6%) | **inconclusive, data-limited + simplified construction** |

\* mom_resid_peer's COVID *episode mean* (−0.2%) hides the real story: Jan/Feb-2020 were
+9.2%/+5.3%, but **March 2020 itself (the crash month) was −15.2%** — see §2.

## 2. The founding-lesson check, applied to equity legs

Kabir's standing lesson (options context) is "a high Sortino/average-tail number is a red
flag, not a green one, when it's built on a few lucky prints — always cross-check the raw
worst print." The **exact same trap appears here** in the "worst-decile-market-months
conditional mean" column: mom_resid_peer, QMJ and BAB all show a *positive* average LS
return across the 25 worst-market months (+2.3% / +8.3% / +8.8%). Read naively that says
"these signals hedge the tail." They do not, unconditionally:

- **mom_resid_peer**: −15.2% in March 2020 (the actual COVID crash month, n=609 names) and
  **−31.1% in April 2009** (n=396 names) — the single worst month in the entire 21-year
  dataset for this leg. The positive average is entirely a composition effect: most of the
  25 "worst decile" months are grinding slow declines where momentum's long winners still
  beat its losers; the catastrophic prints cluster at two specific **inflection points** (a
  sharp intra-crash reversal, and the V-shaped post-crash rebound) that a 25-month average
  buries. This is the textbook momentum-crash mechanism (short leg = distressed/high-beta
  names that melt up hardest exactly when the market snaps back) — **CONFIRMS the a priori
  expectation that momentum is concave/crash-prone**, and confirms it more precisely: the
  danger is not "momentum loses in a crash," it's "momentum loses at the crash's turning
  points" (in, and coming out of).
- **quality_QMJ / defensive_BAB**: genuinely protective *during the decline itself* — QMJ
  +5.6% and BAB +11.7% average across all three COVID months (BAB was positive in **all
  three**, the single cleanest crash-decline hedge found in this audit), and both positive
  through most of the GFC decline months (Aug–Dec 2008). But **both blow up in the identical
  single month, April 2009** (QMJ −45.2%, BAB −45.4%, on n=396–461 names — not a small-n
  fluke) — the post-GFC junk-rally rebound, where the short leg (low-quality/high-beta junk)
  outperforms violently. QMJ and BAB are ~redundant by construction (FINAL_MODEL.md already
  flagged BAB dropped as correlated with QMJ) so this is one finding, not two independent
  ones. **Practical read for a hedge overlay**: QMJ/BAB-style defensive tilts are a real
  protective asset on the way down, but they are NOT a "hold-through" hedge — they must be
  unwound at (or ahead of) the trough, or the rebound gives back the entire crash-period gain
  and more. A tilt with no exit discipline at the inflection is itself a hidden tail risk.

## 3. CONVEX (hedge-like) signals

No signal in this corpus is a clean, unconditional convex hedge (small/flat normal-times,
large positive payoff in every crash). The closest candidates, both **[INFERENCE], data-
limited, unconfirmed on GFC**:
- **quality_cfo_pat** (canon-7 forensic leg): positive skew (+1.30), win/loss ratio ~1.9x,
  positive in all three COVID months (+0.4%/+7.4%/+6.2%). Thin universe (104 of 249 usable
  dates — this leg only exists post-2008 and needs CFO/PAT data, a smaller coverage set),
  so treat the shape as promising, not proven.
- **W4_clean_surplus_health** (wave-4 forensic candidate): the highest positive skew measured
  (+3.04) of any signal tested, positive in 2 of 3 COVID months and 5 of 7 2022-selloff
  months. No GFC coverage (data starts 2012). This is the best-shaped candidate for a genuine
  convex tilt, but it is exactly the "FORWARD-TEST CANDIDATE" status WAVE4_FINDINGS.md already
  gave it for orthogonal-IC reasons — this memo adds an independent, shape-based reason to
  like it, not a new promotion.

## 4. CONCAVE (hidden tail-risk) signals — book-construction relevant even where linear IC looks fine

- **mom_resid_peer**: confirmed concave/crash-prone (§2). Any book sizing this leg on its
  IC/Sharpe alone is carrying an unpriced short-tail-option position dressed as a linear
  factor.
- **quality_QMJ / defensive_BAB**: conditionally concave — safe in the decline, dangerous
  at the rebound (§2). Flag for portfolio construction: fine as a crash-decline overlay with
  a hard unwind rule, dangerous as a static buy-and-hold tilt.
- **trend_ma65_slope**: milder version of the same whipsaw risk — negative skew (−0.82),
  worst month −20.6% is a whipsaw event (Dec-2011, not even a named crash), and it actually
  lost money in the COVID crash month itself (−3.1% episode mean) unlike momentum, which was
  flattered by a strong Jan/Feb.

## 5. Which signal protected the book in the crash months — vs the a priori expectation

The brief's prior was "value/EY, quality/QMJ, low-beta expected [to protect]; momentum
expected concave/crash-prone." Momentum is confirmed. The other prior is **half right**:

- **defensive_BAB is the standout crash-decline protector** (all 3 COVID months positive,
  best GFC-decline average) — but it is NOT in the frozen canonical 7 (dropped as redundant
  with QMJ) and it is NOT tradeable as a single-name options overlay (per the executability
  gate, single-stock India options are largely illiquid/absent) — as an equity-book TILT it
  is real; as an options hedge it is not directly constructible.
- **quality_QMJ** (in the canonical 7) shares BAB's protective decline behavior and its
  rebound-blowup risk in equal measure.
- **value_EY did NOT protect** in the one crash episode it has full data for (COVID,
  −2.6% episode mean, worst −5.3% in Jan-2020 pre-crash) — this contradicts the a priori
  expectation. Value/EY behaved like a slow-recovery factor here, not a crash-decline hedge.

## 6. Cross-asset/market-regime signal (not a stock-selection L/S trade)

The firm's existing market-level valuation regime signal (`richness_index`, built from
`market_state.parquet`'s `EY_hist_zscore_expanding`, documented in `MARKET_REGIME.md` — no
rebuild here, read directly from `w4mkt_richness_series.csv`) [DATA]:

| Episode | Richness level BEFORE | Richness AT trough/crash | Reached "160+ crash-risk" band? |
|---|---|---|---|
| GFC 2008-09 | 76–90 (2007, mildly cheap-side) | **47 at Nov-2008** (correctly the cheapest point in the 21yr series) | Never |
| COVID 2020 | 108–110 (Oct-2019→Feb-2020, moderately rich) | 97 at Mar-2020 | Never |
| 2022 selloff | 113–121 (elevated-rich through the whole window, ~121 just before) | eased to 113–118 by mid-2022 | Never |

This is a market-level exposure/timing gauge, not a cross-sectional payoff generator, so it
does not fit the convex/concave taxonomy directly. Its shape is **coincident, not leading**:
the index's most extreme "cheap" reading always lands AT or after the trough (Nov-2008,
Mar-2020), giving little advance warning of the crash itself; only in the 2022 episode did
it show a genuine pre-crisis "elevated, not cheap" read (113–121 through late 2021, ahead of
the correction). It never reached the Principal's own "160+ crash-risk" band in any of the
three episodes on record. **Practical use is exactly Kabir's own charter logic, not a new
finding**: it is a hedge-COST-timing gauge (buy protection when calm/cheap-regime rather than
rich/complacent-regime) rather than an independent tail-hedge signal in its own right.

## 7. Data limitations (state plainly, do not paper over)

- W4_beta_adj_mom (H043) starts **2022-07** — misses the 2022 selloff window entirely
  (which ends Jun-2022) as well as COVID and GFC. Zero crash-episode coverage. Cannot be
  assessed for tail behavior with data on disk today.
- W4_amihud_illiq: volume data (`cube_volume.parquet`) starts 2021-07 — only the tail end of
  the 2022 selloff is observable, and even that is on a **simplified, non-card-matching
  construction** (no size-residualization, the exact card build was not persisted). Directional
  only.
- W4_clean_surplus_health / W4_dep_health: no GFC coverage (fundamentals PIT availability
  starts 2011-12) — their convex-leaning read is COVID/2022-only, unconfirmed pre-2011.
- quality_cfo_pat: thin universe throughout (104 of 249 usable dates) — its convex-leaning
  read rests on a smaller, possibly non-representative subset of names each month.
- Only 3 crash episodes exist in the sample window at all (GFC, COVID, 2022) — every
  classification above is judged on economic-mechanism consistency across those 3, not
  significance. A 4th/5th crash episode (whenever it arrives) is the real test.
