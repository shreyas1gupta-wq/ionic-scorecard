# revers_5d — dedicated sensitivity/lookahead verification (Gate-4 sensitivity report)
**By:** Dr. Sameer Bhat (Overfit & Sensitivity Analyst, E-027) | **Date:** 2026-07-18
**Trigger:** SWING_MOMENTUM_LINEB_CORRECTED.md (Arjun Rao, 2026-07-18) flagged `revers_5d` — Line B's original
biased-universe test called it "failed forward"; the corrected survivorship-safe rerun shows fwd Sharpe 1.08 /
CAGR +21.4% — and explicitly did NOT certify it, citing "thin economic rationale for a 5-day reversal surviving
0.4% round-trip cost." This memo is the dedicated skeptical pass that was flagged for.

**Pre-registered thresholds (set before running anything below):** plateau = best param cell ≤20% above
neighborhood median; placebo = real result must clearly separate from 5-draw shuffle distribution (z≳2 as a
soft bar, and no single placebo draw should beat the real result); cost = edge must retain >50% of headline
Sharpe under a realistic (not extreme) cost stress; drop-one-year = no single year should account for >50% of
headline forward Sharpe. Any one miss = FAIL per charter's automatic Gate-4 red-flag list.

## [DATA] Lineage / reproduction
- Reused verbatim: `Shreyas_Ionic_AMC/04_RND_LAB/BROAD_RESEARCH_2036/lineb_corrected_backtest.py` (panel load,
  delist-loss realization, universe, signal fn, backtest engine) via `import lineb_corrected_backtest as lb` —
  no edits to the sibling's script or its saved outputs.
- Baseline reproduced exactly: BUILD Sharpe 0.42 / CAGR +7.8% / DD -77%, FWD Sharpe 1.08 / CAGR +21.4% / DD -21%
  — matches `lineb_corrected_results.csv` row for `revers_5d` to 3dp. Confirmed before running any stress test.
- Signal construction (`lineb_corrected_backtest.py:129-133`): `revers(win)` = `-(px.iloc[-1] / px.iloc[-1-win] - 1)`,
  i.e. negative 5-trading-day return AS OF the rebalance date `d` itself (including `d`'s own close), ranked
  cross-sectionally, top-30 equal-weight, held from `d+1` to the next rebalance (~21 trading days later).
  Mechanically the 5-day formation window and the 21-day holding window do NOT overlap in this engine (holding
  starts the day after `d`) — the sibling's overlap hypothesis is **not literally true** as coded. The real
  fragility is different: see lag test below.
- Scripts used for this verification (not part of the sibling's deliverable, written fresh for this audit):
  `verify_revers5d.py`, `verify_revers5d_paramgrid.py` (scratchpad, available on request) — both import the
  sibling's module directly rather than re-deriving the panel/engine, per "verify from disk" discipline.

## (a) Parameter surface — reversal lookback window
Only signal-specific free parameter is the lookback window (registered value = 5 trading days). Grid ±up to 4x:

| win (days) | BUILD Sharpe | FWD Sharpe | FWD CAGR |
|---|---|---|---|
| 3 | 0.46 | 0.68 | +12.5% |
| 4 | 0.44 | 0.70 | +13.0% |
| **5 (registered)** | **0.42** | **1.08** | **+21.4%** |
| 6 | 0.45 | 0.90 | +17.0% |
| 7 | 0.43 | 0.99 | +19.5% |
| 10 | 0.51 | 0.73 | +13.1% |
| 15 | 0.38 | 0.52 | +8.8% |
| 21 | 0.46 | 0.57 | +9.9% |

Neighborhood (win=3,4,6,7) FWD Sharpe median = 0.80. Registered cell (win=5, FWD Sharpe 1.08) sits **35% above**
the neighborhood median. **PLATEAU TEST: FAIL** (threshold was ≤20%). Note BUILD Sharpe is flat and unremarkable
across the entire grid (0.38-0.51) — the spike is a forward-window-only artifact of the exact win=5 choice, which
is itself a single-spike-parameter-cell automatic Gate-4 FAIL condition per charter.

## (b) Perturbation battery

| Test | Result | Verdict |
|---|---|---|
| Lag: form signal on `d` (registered, same-day close) | FWD Sharpe 1.08 | baseline |
| Lag: form signal on `d-1` instead of `d` (removes same-day-close dependency) | FWD Sharpe 1.08→**0.93** (-14%) | fragile |
| Lag: same signal timing, +1 extra day of execution delay (entry `d+2` not `d+1`) | FWD Sharpe 1.08→1.05 (-3%) | passes |
| Control: `mom_12_1` under identical `d-1` signal-timing shift | FWD Sharpe 0.86→**0.89** (+3%, no degradation) | contrast |
| Cost: RT 0.4% (registered) | FWD Sharpe 1.08 | baseline |
| Cost: RT 0.8% | FWD Sharpe 1.08→**0.84** (-22%) | fragile |
| Cost: RT 1.2% | FWD Sharpe 1.08→**0.60** (-44%) | **>50% of edge gone — FAIL zone entered** |
| Cost: RT 2.0% | FWD Sharpe 1.08→0.14 (-87%) | dead |
| Turnover (measured, not assumed) | avg 94.3% one-way name-replacement per monthly rebalance | ~full book turns over every month |
| Placebo shuffle (5 draws, seed=42, symbol-relabel on returns only, signal untouched) | real 1.08 vs placebo mean 0.757, std 0.257 (draws: 0.74, 1.19, 0.83, 0.61, 0.42) | **z≈1.26 — does NOT clearly separate; one placebo draw (1.19) beats the real result — FAIL** |

**Reading the lag test against the control:** `revers_5d` degrades meaningfully (-14%) when the exact same-day
close is removed from signal formation, while `mom_12_1` is essentially unaffected (+3%) under the identical
perturbation. A 252-day momentum signal barely notices losing 1 of 252 data points; a 5-day reversal signal
losing 1 of 5 is a 20% information change — the backtest is quietly leaning on same-day-close information that a
real trading process (decide, then execute) cannot honestly have. This is a genuine, if partial, lookahead-style
fragility (not a full T1-T10 overlap bug, but the same family of issue: precision-of-timing dependency).

**Reading the turnover number:** 94.3% average one-way turnover on a *monthly* rebalance means the strategy is
essentially selecting an almost entirely new top-30 basket every month — mechanically consistent with a "buy
whoever just crashed hardest" filter, since the identity of "biggest 5-day loser" changes completely from month
to month. Given the firm's own COST_STANDARDS doctrine that circuit-locked/thin-volume names see 2-3x the
blanket slippage assumption (`06_TRADING_DESK/COST_STANDARDS.md` / `lib/execution_realism.py`), and that a
"biggest recent decliner" filter disproportionately selects exactly those thin-volume, possibly circuit-affected
names, a realistic round-trip cost for this specific strategy is very plausibly in the 0.8-1.2% zone tested above
— which is precisely where more than half the headline edge disappears.

## (c) Subsample stability

| Split | Result |
|---|---|
| Yearly Sharpe, full sample (2005-2025) | Wild swings: 2008 **-1.82**, 2009 **+2.66**, 2011 -1.41, 2013 -0.78, 2018 **-1.47**, 2019 -0.03, 2020 +1.05, 2023 **+3.24**, 2025 +0.08 — boom-bust profile, not a stable factor |
| Drop-one-year, forward window only (2022-2025) | excl 2022→1.42, **excl 2023→0.55** (from 1.08 baseline, -49%), excl 2024→0.95, excl 2025→1.45 |

**Drop-one-year: FAIL.** Excluding 2023 alone nearly halves the entire forward-window headline (Sharpe
1.08→0.55, CAGR +21.4%→+9.9%). A single calendar year is doing roughly half the work of a 4-year "forward-robust"
claim. Combined with the yearly-Sharpe table, the pattern (deep negative in 2008/2011/2013/2018, extreme positive
in 2009/2023) reads as a crash-recovery-beta proxy — buying the names that just fell hardest tends to pay off
big in V-shaped market rebound years (2009 GFC bounce, 2023 India mid/smallcap rally) and lose big in grinding
correction years — rather than a persistent, name-specific overreaction-correction effect.

## DSR/PBO
Not computed. The sensitivity battery above already returns independent FAILs on three separate pre-registered
gates (parameter plateau, placebo separation, drop-one-year concentration) plus a fragile-zone cost result — per
charter, any ONE of these is an automatic Gate-4 FAIL, and a DSR/PBO computation on a signal that is already this
construction-fragile would not change the certification outcome. [OPINION] If Arjun/CIO want the honest-trials
count logged in the family ledger regardless (e.g. to formally close the "failed forward → looks real" story for
the /oos-audit trail), that is a cheap follow-up; it is not gating this verdict.

## [INFERENCE] Economic rationale check
Academic short-term reversal (Jegadeesh 1990, Lehmann 1990) is a **weekly** formation-and-holding effect: profits
concentrate in the days immediately following the shock and decay within 1-4 weeks. This construction forms the
signal on a 5-day window but **holds for a full ~21-trading-day month** — a horizon mismatch against the
literature the "reversal" label is borrowing credibility from. Three weeks of a one-month hold are exposed to
whatever happens *after* any genuine short-horizon overreaction-correction has already played out, which is
exactly where a falling-knife/distress continuation risk lives (visible in the -74% to -79% build-period max
drawdowns across the whole win-grid, the worst of any signal in the battery per the sibling's memo). Nothing in
this construction distinguishes "stock oversold on no news, due for a bounce" from "stock in genuine, ongoing
distress heading toward the delist register" — the two would look identical to a pure 5-day-return signal, and
the delist-loss realization only fires once, at the actual delisting date, which can be well after this
signal would have already exited a name that continued falling. [OPINION] This is a plausible mechanism for why
the edge is thin/fragile rather than a proven root cause — it was not separately quantified here (would require
tagging holdings against the delist register by date, a natural next cheap test if this is escalated again) —
but it is consistent with everything else in this battery: no persistent, articulable reason ("liquidity
provision" or "overreaction correction") survives contact with the numbers.

## Verdict: **OVERFIT**
Fails independently on parameter-plateau (35% spike over neighborhood median), placebo-separation (z≈1.26, one
of 5 placebo draws beats the real result), and drop-one-year concentration (nearly half the forward Sharpe is
one calendar year, 2023) — any one of these is an automatic Gate-4 FAIL per charter, and this signal fails all
three plus sits in the cost-fragile zone once turnover-realistic costs are applied. This is a stronger verdict
than FRAGILE-AT: the battery does not show a signal that merely needs a caveat on one axis, it shows a result
that is largely reproducible by shuffling which stock gets which return series, evaporates when the win parameter
moves off its exact registered value, and is driven by one outlier year.

**Single most fragile assumption:** the blanket 0.4% round-trip cost applied uniformly to a strategy that
mechanically selects the most-recently-crashed (and therefore most illiquid/likely circuit-affected) names in the
universe every month at ~94% turnover — combined with landing on the exact win=5 parameter cell rather than any
neighboring value. Recommend: do NOT cite `revers_5d`'s forward Sharpe 1.08 in any IC memo or register entry;
Line B's original "failed forward" framing was directionally closer to the truth than the corrected-panel number,
even though the corrected panel itself is legitimate (this is a construction/robustness failure of the signal,
not a reversion of the survivorship-bias fix).

## Lookahead note (D-028 lens)
No T1-class hard overlap bug found (formation and holding windows are mechanically disjoint, `d+1` onward). The
softer finding — forward Sharpe degrades 14% when signal formation is shifted off the exact rebalance-day close,
while a comparison momentum signal is unaffected by the same shift — is a timing-precision fragility, not a full
lookahead violation, and is disclosed above rather than filed as a separate LOOKAHEAD_AUDIT.md entry (this memo's
scope per the assigning task is the sensitivity/verification pass on `revers_5d` specifically).
