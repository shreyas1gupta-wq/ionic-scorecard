# Book-Level Factor Co-Crash — the 7 legs unwinding TOGETHER

**Author:** Ritika Sharma, Portfolio Risk Manager | **Date:** 2026-07-17
**Charter:** RP-30/RP-34 style stress + correlation-regime monitor, applied to the completeness-critic's
gap — every leg here was validated on single-factor cross-sectional bear-regime IC only
(`regime_breakdown.regime_trend.bear` in each CAPSTONE_*/W4HW_leg_* card). Nobody checked whether the
7 legs' **long-short returns correlate with each other** in the months that hurt, i.e. whether the book
diversifies or co-crashes as a portfolio.

**[DATA]** unless flagged. Legs: EY (`value_EY`), residual-momentum (`mom_resid_peer`), MA-65 slope
(`trend_ma65_slope`), QMJ (`quality_QMJ`), net-issuance (`bs_issuance`), asset-growth
(`bs_asset_growth`), CFO/PAT (`quality_cfo_pat`).

## Method
Monthly quintile long-short (top-quintile minus bottom-quintile, equal-weighted, raw 1M forward return
`fwd_ret_1M_raw`) built fresh from `panel/capstone_legs.parquet` × `panel/panel_long.parquet` (not
pulled from existing cards — those store only summary stats, no return series). n≥20 names/date/leg
required. Two windows used because fundamentals coverage is uneven:
- **7-leg window**: 2017-06 → 2025-10 (n=101 months) — all 7 legs present. cfo_pat is the binding
  constraint (starts 2017-06; EY starts 2011-11; net-issuance/asset-growth start 2012-11).
- **6-leg window** (excl. CFO/PAT): 2012-11 → 2025-10 (n=156 months) — extends back far enough to
  reach Feb-2016, used as a robustness check.
- **GFC 2008-09 is NOT reachable** — fundamentals legs (EY, net-issuance, asset-growth, CFO/PAT) have
  no history before ~2011-12. Only 3 of the 7 legs (mom-resid, MA65-slope, QMJ) go back to 2005-06, so
  no genuine 7-leg GFC read exists. **[INFERENCE — honesty flag]**: this book's factor-crash evidence is
  drawn from 4 episodes over 2017-2025 (COVID crash, the Nov-2020 vaccine junk-rip, the 2022 rate-hike
  bear, and Jun-2024 election vol) — n=4, low, per the standing "few crash episodes" caveat. Consistent
  with the firm's crash-blind lesson: **every number below is crash-blind to a GFC/2008-style event.**

Stress months = the CIO's own pre-registered stress-replay set (RP-30: Mar-2020, 2022, Jun-2024) plus
the Nov-Dec-2020 vaccine rally, defined from exogenous market data (India VIX, Nifty500 return), not
from the composite's own losses — avoids circularity.

## 1. Do the legs co-crash or diversify?

Average pairwise correlation of the 7 legs' monthly long-short returns:

| | Normal months | Stress months |
|---|---|---|
| 7-leg window (n=101) | **0.068** | **0.109** (+60%) |
| 6-leg window (n=156) | **0.085** | **0.141** (+66%) |

Correlations do NOT go to 1 across the board — this is not a total co-crash. But the average masks a
sharp split. Correlation matrix in stress months (7-leg window):

```
                EY  mom_resid  ma65_slope   QMJ  net_issuance  asset_growth  cfo_pat
EY            1.00       0.23        0.46  0.34          0.43         -0.57    -0.13
mom_resid     0.23       1.00        0.75  0.68          0.69         -0.67    -0.06
ma65_slope    0.46       0.75        1.00  0.49          0.43         -0.66    -0.06
QMJ           0.34       0.68        0.49  1.00          0.81         -0.71     0.28
net_issuance  0.43       0.69        0.43  0.81          1.00         -0.69     0.35
asset_growth -0.57      -0.67       -0.66 -0.71         -0.69          1.00    -0.11
cfo_pat      -0.13      -0.06       -0.06  0.28          0.35         -0.11     1.00
```
vs. normal months, same order — momentum/QMJ/net-issuance correlations roughly HALVE:
`mom_resid–QMJ`: 0.41→0.68 (stress); `mom_resid–net_issuance`: 0.12→0.69 (stress);
`QMJ–net_issuance`: 0.23→0.82 (stress, both regimes — these two are effectively one signal).

**Verdict: 5 of 7 legs (EY, mom-resid, MA65-slope, QMJ, net-issuance) CO-CRASH.** In normal months they
look like distinct, low-correlated factors (0.05-0.4). In stress they collapse toward a single "avoid
junk / ride the winners" axis and move together (0.4-0.8). **2 of 7 legs DIVERSIFY**: asset-growth
(strongly negative to all 5, -0.57 to -0.71 in stress, more negative than in calm months) and CFO/PAT
(near-zero to all, mildly diversifying, not a hedge).

## 2. Composite worst joint drawdown

7-leg equal-weight composite, worst drawdown: **-12.25%**, peak 2020-02 → trough 2020-12 (11 months).
6-leg composite (excl. CFO/PAT, same window): **-16.47%** — deeper, because CFO/PAT was itself one of
the two offsetting legs; removing it widens the hole.

Leg contribution over that drawdown window (cumulative return, 7-leg):

| EY | mom_resid | ma65_slope | QMJ | net_issuance | asset_growth | cfo_pat |
|---|---|---|---|---|---|---|
| -11.0% | **-34.8%** | -25.6% | -28.5% | -12.3% | **+28.7%** | **+25.8%** |

This is a **single co-crash event, not idiosyncratic** — 5 legs net negative over the same 11 months,
momentum and QMJ worst hit. The other 2 (asset-growth, CFO/PAT) nearly halved what the drawdown would
have been on a 5-leg-only book.

Worst single months (composite, 7-leg book):

| Month | Composite | Legs down | Note |
|---|---|---|---|
| 2020-05 | **-6.50%** | 6/7 | worst single month — the post-crash **rebound**, not the crash itself (mom_resid -20.2%, ma65_slope -14.5%, QMJ -13.7%, net_issuance -8.7%, EY -6.1%; only asset_growth +19.0%) |
| 2020-10 | -3.22% | 6/7 | pre-vaccine junk build-up (QMJ -11.6% worst) |
| 2020-03 | -3.16% | 3/7 | the COVID crash month proper — LESS co-crash than the rebound months that followed |
| 2019-10 | -3.09% | 6/7 | idiosyncratic wobble, not in the pre-registered stress set |
| 2025-04 | -2.81% | 6/7 | idiosyncratic (tariff-shock month) |

**Key pattern: the crash month itself (Mar-2020) was NOT the worst co-crash month — the REBOUND
(Apr-May 2020) was.** This matches the task's framing exactly: junk-rip / post-bottom-rebound is the
dangerous regime for this book, more than the drawdown that precedes it.

By contrast, **2022 (rate-hike bear) was NOT a co-crash** — EY +31.5% cum, MA65-slope +23.5% cum over
the year, most legs flat-to-positive; QMJ -2.8% only mild drag. 2022 was a value-over-growth de-rating,
which the EY leg is built to catch — the book's crash risk is regime-specific (junk-rally years), not
"any bear market."

## 3. Offset check — does value/quality/low-issuance hedge momentum?

**No.** `mom_resid` correlation to EY, QMJ, net_issuance all rise from weak/normal-regime (0.08-0.41) to
much stronger in stress (0.23-0.69) — i.e. these three look diversifying in calm markets and stop being
diversifying exactly when it matters. QMJ and net-issuance in particular are effectively **one signal**
(0.81-0.82 correlated in both regimes) — "quality" and "low-issuance" are the same avoid-junk axis
wearing two names, not two independent bets.

The only two legs that offset momentum are **asset-growth** (mom_resid corr: stress -0.67, normal
-0.16 — genuine, strengthening hedge) and **CFO/PAT** (mom_resid corr: stress -0.06, normal +0.23 — a
diversifier that goes flat/uncorrelated in stress rather than a hedge). **[INFERENCE]**: asset-growth's
long leg (low-investment/conservative-capex names) is plausibly picking up the same beaten-down,
capex-slashed cyclicals that rip hardest in a junk rebound — the mechanism, not just the correlation
coefficient, would need a name-level check to confirm; flagged as inference, not verified.

## 4. Sizing implication — is the breadth/VIX scalar enough?

**No — it protects against the wrong axis for this specific risk.** Checked `market_state.parquet` /
`macro_state.parquet` against the two worst co-crash windows:

- **May-2020** (worst single month, -6.5%): breadth 21.6% above 200dma, India VIX 30.2, regime "high"
  → the scalar was correctly near its floor here. De-gross worked as designed for THIS month.
- **Nov-Dec-2020** (the vaccine junk-rip, QMJ -19.2% cum over the quarter): breadth had already surged
  to **90.9% → 97.2%** above 200dma, VIX had fallen to 19.8-21.1. Breadth this high normally reads as
  "healthy broad rally, safe to run full size" to an exposure scalar built on `%>200DMA × VIX-regime`
  (`ABSOLUTE_SCORER_SPEC.md §1,4`) — **exactly when QMJ and net-issuance were getting run over by the
  junk they're short.** A broad-participation rally and a junk-rip look identical to a breadth gauge;
  they are opposite outcomes for a quality/momentum/low-issuance book.

The scalar is also **uniform across all 7 legs** — one multiplier applied to the whole book (per spec,
"identical scalar for every name"). It can shrink the book's overall gross when the market looks risky,
but it has no mechanism to rotate AWAY from the 5 co-crashing legs INTO the 2 offsetting ones
(asset-growth, CFO/PAT) — it cannot see the leg-level correlation break documented in §1, because it
was never built to.

**Recommendation to CIO**: the existing breadth/VIX scalar covers market-beta risk; it does not cover
factor-composition risk. An explicit **junk-rip / de-gross conditioning specific to the
momentum+QMJ+net-issuance+EY+MA65-slope cluster** (e.g., a small-cap/junk-basket relative-strength
trigger, or simply capping combined gross on those 5 legs when they're all scoring the same direction)
would close the gap the breadth/VIX scalar leaves open. Sizing judgment call is the CIO's; this is the
number, not the veto.

## Honesty flags
- n=4 stress episodes (2017-2025 window) — low-n, judged on consistency across the 4, not statistical
  significance. GFC 2008-09 unreachable with fundamentals legs — **crash-blind to a true GFC/2008-style
  event**, per the standing 2026-07 lesson.
- Quintile (not decile) long-short construction, built fresh — may not exactly reproduce each leg's
  registered CAPSTONE card numbers, but is internally consistent for a correlation study.
- Feb-2016 (6-leg, excl. CFO/PAT) was mild for this book (composite ~+0.8% over Jan-Apr 2016, no legs
  materially co-crashed) — a genuine counter-example to "junk-rips always hurt this book"; noted, not
  suppressed.

## Files
- `rnd/panel/capstone_legs.parquet`, `rnd/panel/panel_long.parquet`, `rnd/panel/market_state.parquet`,
  `rnd/panel/macro_state.parquet` — source data (unchanged).
- Build/analysis scripts and intermediate CSVs: `C:\tmp\cocrash\build_leg_returns.py`,
  `C:\tmp\cocrash\analyze_cocrash.py`, `C:\tmp\cocrash\leg_ls_returns_1M_with_composite.parquet`,
  `C:\tmp\cocrash\corr_stress_7leg.csv`, `C:\tmp\cocrash\corr_normal_7leg.csv`,
  `C:\tmp\cocrash\full7_window.csv`, `C:\tmp\cocrash\full6_window.csv` (scratch — not firm-canonical,
  rerun from source parquet if this needs to be reproduced/audited).
