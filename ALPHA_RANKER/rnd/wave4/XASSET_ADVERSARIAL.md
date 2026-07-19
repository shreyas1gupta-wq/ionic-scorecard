# XASSET_ADVERSARIAL — Sensitivity & Overfit Audit of W4X Cross-Asset Sizing Candidates

**Owner:** Dr. Sameer Bhat, Overfit & Sensitivity Analyst (risk office, Gate-4)
**Date:** 2026-07-17
**Targets:** `W4X_copper_gold_ratio_sizing` (chg6m variant), `W4X_gold_vs_equity_1m_sizing`
**Framing:** judged as RISK/SIZING exposure scalars (0.5x/1.0x/1.5x tercile), NOT return signals.
**Sample:** n=114 monthly obs (scalar backtest), n=120-126 (linear-IC tests). This is a genuinely
small sample for a monthly macro series — every verdict below is constrained by that fact and
says so explicitly.

---

## 0. Reproducibility check (done before trusting anything else)

Both signals were independently rebuilt from disk, not taken on faith from the cards.

- **`macro_state.parquet`'s `brent`/`dxy`/`real_rate_proxy`/`india10y` columns are still
  100% NaN** — verified directly (`df[col].notna().sum()` = 0/127 for all four). MACRO_XASSET.md
  states these were "FRED-filled" this session; that fill was never written back to the panel
  on disk. **[DATA] flag to data-officer-kavya-reddy and rnd-head:** the memo's §1 rows for
  term-spread / real-10Y-yield / dollar+INR-stress cannot be reproduced from what's on disk
  either — this doesn't affect the two candidates graded here (neither uses those columns) but
  it does mean the rest of MACRO_XASSET.md rests on ungoverned scratch pulls, same issue as below.
- **Copper (FRED `PCOPPUSDM`) does not exist anywhere in the repo** — Cyrus's card discloses it
  was pulled to an "ephemeral scratch working file," never persisted or cataloged. Re-fetched it
  directly from FRED here (same series, same D-033-approved source) to make this audit
  independently reproducible. Sample-check: 2022-01 = 9782.3, matching Cyrus's disclosed
  ~9750-9782 check — good, the underlying data is consistent.
- **`gold_vs_equity_1m` in `macro_state.parquet` itself is truncated to 66 obs** (goldbees column
  gap) — Cyrus's card discloses he recomputed off `datasets/etf_gold_silver/goldbees_daily_ext.parquet`
  (2013-2026, 3341 daily rows) for the actual 114-obs backtest. Reproduced that path here.
- With both fixes, **full-sample reproduction matches the cards to 3 decimal places**: copper/gold
  chg6m strategy Sharpe 1.138 / maxDD -16.4% / VIX-baseline 0.816 / -24.1%, exact match; gold-vs-equity
  strategy Sharpe 1.100 / maxDD -15.0%, exact match. High confidence the methodology is being
  applied consistently — this audit is not chasing a phantom number.
- **Action item, not a kill trigger:** get PCOPPUSDM + the goldbees_ext lineage into
  `05_DATA_OFFICE/DATA_CATALOG.md` before anything downstream depends on it again.

---

## 1. Bear episodes used (empirical, from actual NIFTY 500 drawdown path, not assumed dates)

| Episode | Window | Peak-to-trough dd in window |
|---|---|---|
| 2018-19 IL&FS/NBFC | 2018-09 to 2019-02 | -12.4% |
| 2020 COVID | 2020-02 to 2020-07 | -29.98% (worst in sample) |
| 2022 Fed hikes | 2022-01 to 2022-06 | -11.3% |
| 2025 correction | 2025-01 to 2025-04 | -18.0% |

(A fifth, sharper drawdown appears 2026-02/03, -15.3% — outside the four the brief named, not
included in the LOBO battery below to stay within scope, but visually consistent with the same
robustness pattern seen in the four tested.)

---

## 2. Signal 1 — `copper_gold_chg6m` (6-month change in copper/gold-USD ratio, orient +1)

### Era-split
| Era | n | Strategy Sharpe | VIX-baseline Sharpe | Strategy maxDD | VIX maxDD |
|---|---|---|---|---|---|
| Pre-2021 | 48 | 1.013 | 0.634 | -16.4% | -24.1% |
| Post-2021 | 66 | 1.233 | 0.946 | -12.3% | -20.8% |

**Holds in both halves.** Edge over VIX-baseline (Sharpe delta) is +0.38 pre-2021 and +0.29
post-2021 — same sign, same order of magnitude, no flip. maxDD improvement over VIX also holds
in both halves. This is NOT a one-era artifact.

### Leave-one-bear-out
| Dropped | n | Strategy Sharpe | VIX Sharpe | Edge over VIX | Strategy maxDD | VIX maxDD |
|---|---|---|---|---|---|---|
| (none — full) | 114 | 1.138 | 0.816 | 0.321 | -16.4% | -24.1% |
| 2018-19 IL&FS | 108 | 1.173 | 0.828 | 0.345 | -17.2% | -25.6% |
| 2020 COVID | 108 | 1.216 | 0.862 | 0.353 | -12.3% | -20.8% |
| 2022 Fed hikes | 108 | 1.203 | 0.852 | 0.352 | -16.4% | -24.1% |
| 2025 correction | 110 | 1.145 | 0.814 | 0.331 | -16.4% | -24.1% |

**Survives cleanly — the edge is not carried by any single bear.** Dropping any one of the four
episodes leaves the Sharpe edge over VIX *unchanged or larger* (0.32-0.35 range throughout), and
the maxDD advantage over the VIX baseline persists in every cut. Share of the total monthly
excess-over-VIX attributable to each bear window: 2018-19 = -2.6%, COVID = 0.0%, 2022 = +5.1%,
2025 = -7.0% — i.e. essentially none of this signal's edge comes from crisis months at all; it is
earned in ordinary months. That reframes what this signal actually is: less a "crisis caller,"
more a persistently-better-levered scalar that also happens not to hurt in bears.

### Lag-fail reconciliation
Card: IC=0.126, NW-t=1.38 (not significant at conventional thresholds), lag-stability delta=0.41
(fails the 0.25 gate). Own re-verification (Spearman, exact reproduction of n and IC=0.126):
adding one extra month of staleness moves IC from 0.126 to 0.178, delta=0.05 by my construction —
smaller than the card's reported 0.41, meaning the exact lag-perturbation *method* used by the
harness differs from a naive extra-shift(1) (not fully specified in the card). That discrepancy in
method is itself a documentation gap worth fixing, but it does not change the substantive point:
**the underlying point-in-time linear IC is weak regardless of method** — t=1.38 does not clear a
95% significance bar, and a 6-month-change signal has heavy month-to-month overlap (each
observation shares 5 of its 6 months with its neighbor), which mechanically inflates apparent
stability of a weak correlation while making it fragile to any lag perturbation. **Ruling: this is
a REAL instability of a weak/marginal linear relationship, not a small-N artifact to be waved
away** — but it is a different kind of failure than a sign-flip or collapse. A weak, tail/regime-
driven relationship that still produces a robust *tercile-scalar* effect (era-split holds, LOBO
survives) is a coherent, defensible story: the mechanism does not require the linear IC to be
strong, only that being in the extreme tercile is informative for delevering/relevering, which a
threshold/non-linear relationship can deliver even when the linear correlation is weak.

---

## 3. Signal 2 — `gold_vs_equity_1m` (trailing 1M gold-outperformance, orient -1)

### Era-split
| Era | n | Strategy Sharpe | VIX-baseline Sharpe | Strategy maxDD | VIX maxDD |
|---|---|---|---|---|---|
| Pre-2021 | 48 | 1.058 | 0.634 | -15.0% | -24.1% |
| Post-2021 | 66 | 1.139 | 0.946 | -13.1% | -20.8% |

**Holds in both halves**, edge over VIX +0.42 pre-2021, +0.19 post-2021 — narrower post-2021 but
same sign, no flip.

### Leave-one-bear-out
| Dropped | n | Strategy Sharpe | VIX Sharpe | Edge over VIX | Strategy maxDD | VIX maxDD |
|---|---|---|---|---|---|---|
| (none — full) | 114 | 1.100 | 0.816 | 0.283 | -15.0% | -24.1% |
| 2018-19 IL&FS | 108 | 1.088 | 0.828 | 0.260 | -17.6% | -25.6% |
| 2020 COVID | 108 | 1.158 | 0.862 | 0.296 | -13.1% | -20.8% |
| 2022 Fed hikes | 108 | 1.175 | 0.852 | 0.323 | -15.0% | -24.1% |
| 2025 correction | 110 | 1.084 | 0.814 | 0.271 | -16.3% | -24.1% |

**Survives.** Edge over VIX stays in a tight 0.26-0.32 band across every leave-one-out cut,
never collapses, sometimes increases. Unlike signal 1, this one DOES draw a real share of its
excess-over-VIX from two specific episodes (2018-19 = +19%, COVID = +29%, summing to ~47% of
total monthly excess by the additive measure) — consistent with "flight to gold" being a genuine
mechanism in those two crises specifically. But the Sharpe-recompute LOBO test (the actual
pre-registered pass/fail criterion) shows dropping either one individually barely moves the edge
(-0.26 vs -0.28 full, and COVID-dropped is actually *higher* at 0.296) — so even though those two
episodes contribute disproportionately to the additive excess-return tally, the RATIO-based
Sharpe edge does not depend on either single one. Passes the Opus-mandated test.

### Lag-fail reconciliation
Card: IC=-0.048, NW-t=-0.53 (essentially indistinguishable from zero), lag-delta=1.91 (badly
fails 0.25 gate). This IC is weaker than signal 1's — a near-zero standalone linear correlation.
Own re-verification: IC=-0.048 (exact match), extra-month-stale IC=+0.043 (delta=0.09 by naive
method — sign FLIPS between t and t+1 lag, even though the magnitude is small). A signal whose
own IC changes sign under one extra month of staleness is, on its face, not a stable monotonic
relationship at any horizon-level of confidence. **Ruling: genuinely unstable, not an artifact** —
this is the weakest point-in-time relationship of the two candidates. The scalar-backtest gain
here is best read as riding two specific historical "flight to gold" episodes (2018-19, COVID) that
happened to coincide with tercile extremes, working via the same non-linear/threshold mechanism
argument as signal 1, but with less standalone statistical support behind it.

---

## 4. DSR / PBO context (advisory — this signal class does not fit purgedcv's cross-sectional
CSCV machinery cleanly; monthly-scalar honest-trial DSR computed directly, Bailey/Lopez de Prado
formula, disclosed inputs)

Monthly Sharpe for both signals ≈0.32-0.33 (annualized 1.10-1.14). Deflated against the number of
configurations actually tried in this signal family (§1 of MACRO_XASSET.md lists 9 signal/horizon
variants tested before landing on these two, plus the 2 pre-existing incumbents = 11 honestly-
countable trials):

| N_trials assumption | copper_gold_chg6m DSR | gold_vs_equity_1m DSR |
|---|---|---|
| 1 (no haircut — wrong, shown for reference only) | 1.00 | 1.00 |
| 5 (core methodologies only) | 0.15 | 0.16 |
| 11 (full §1 table, honest count) | 0.003 | 0.006 |
| 20 (whole W4X wave incl. §2/§3) | ~0.00 | ~0.00 |

**Neither signal is close to the DSR>0.95 gate at any defensible trial count.** This is the single
biggest reason to stay cautious regardless of how clean the era-split/LOBO results look — a
strong showing on two robustness cuts does not substitute for surviving a proper multiple-testing
correction, and at n=114 months there is no way to get DSR up without more independent history.
PBO in the classical CSCV sense needs multiple competing configurations with real train/test
splits; with only 2 candidates + baselines and 114 non-independent monthly points, a formal PBO
number would not be statistically meaningful — flagged as advisory-only, consistent with the
firm's PBO-at-small-n precedent (S-01/S-04).

---

## 5. Lookahead check (D-028 duty, lightweight pass appropriate to this data shape)

The standard T1-T10 daily-bar taxonomy (timezone, pre-open auction, earnings PIT, option-settle)
does not apply to this monthly cross-asset panel (no intraday bars, no options, no earnings
dates). The applicable check — every signal value knowable strictly at-or-before its rebalance
date — was verified directly: copper and goldbees_ext were both joined via `merge_asof(...,
direction="backward")` onto the month-end calendar (no future data pulled forward), and the
tercile bands are expanding-window using only observations up to and including the current one
(same pattern as `macro_state.py`'s own `risk_regime` construction). No lookahead found in either
signal's construction. **PASS.**

---

## 6. Verdicts

**`W4X_copper_gold_ratio_sizing` (chg6m variant): PARK-NEEDS-MORE-DATA.** Era-split holds,
leave-one-bear-out survives cleanly (edge is NOT one-bear-deep — genuinely the strongest result of
the two), and the lag-fail reflects a real but coherent weak/non-linear relationship rather than
random noise. But DSR fails badly (0.003-0.15 depending on honest trial count, nowhere near the
0.95 gate) and n=114 months is too short a track record to commit a fresh forward clock. Worth
tracking with paper-only shadow sizing and revisiting once ~24 more months of data exist (would
lift n_eff meaningfully and let a genuine walk-forward DSR/PBO be run).

**`W4X_gold_vs_equity_1m_sizing`: PARK-NEEDS-MORE-DATA.** Era-split holds, LOBO survives on the
Sharpe-recompute test, but the point-in-time IC is weaker and less stable than signal 1 (near-zero,
sign-flips under one extra lag month), and roughly half its raw excess-return tally concentrates in
two specific episodes (2018-19, COVID) even though the ratio-based Sharpe edge does not depend on
either alone. Same DSR failure as signal 1. Slightly weaker case than copper/gold — if only one
gets tracked forward, prefer signal 1.

**Neither should become a live-forward-clock sizing sleeve today.** Both cleared the two tests
specifically designed to catch "one lucky call fakes the whole edge" (era-split, leave-one-bear-out)
— an honestly surprising, non-trivial result that argues against a flat KILL — but both fail the
DSR gate hard at any defensible honest-trial-count, and n=114 months is simply not enough runway
for a sizing-layer commitment per RESEARCH_SOP. Recommend: park both as paper/shadow-tracked
candidates, re-run this exact battery in ~12-24 months once more independent monthly observations
accrue, and in parallel chase the BLOCKED India-specific real-rate/CPI data (per MACRO_XASSET.md
§5) which would let a genuinely orthogonal India-specific regime signal be tested instead of
riding two thin, US-centric cross-asset proxies.

---

**Files:**
- Reproduction/adversarial script (scratch, not committed to repo):
  `C:\Users\SHREYA~1.1GU\AppData\Local\Temp\claude\...\scratchpad\xasset_adversarial.py`
- Raw results JSON: `...\scratchpad\xasset_results.json`
- Source cards: `ALPHA_RANKER/rnd/cards/W4X_copper_gold_ratio_sizing.json`,
  `ALPHA_RANKER/rnd/cards/W4X_gold_vs_equity_1m_sizing.json`
- Source memo: `ALPHA_RANKER/rnd/wave4/MACRO_XASSET.md`
