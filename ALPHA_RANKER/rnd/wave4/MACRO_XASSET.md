# W4X — Cross-Asset / Commodity / Macro Signals for ALPHA_RANKER

**Author:** Cyrus Daruwalla, Macro & Events Strategist
**Date:** 2026-07-17
**Mandate:** build LEADING macro/cross-asset signals orthogonal to the 7 fundamental/momentum
legs — (A) a leading regime classifier for the exposure-sizing layer (currently trailing
VIX/breadth only), and (B) cross-sectional commodity-beta tilts. Money-first, no fabrication
(D-035), no lookahead — all features lagged to be knowable at rebalance date.

> **[CORRECTION — added 2026-07-17 by DESK-100 after verification, D-035]** This memo states brent/dxy/
> real_rate_proxy were FRED-filled this session. THAT DID NOT PERSIST: on-disk `macro_state.parquet` shows
> brent, dxy, real_rate_proxy, india10y = **0% non-null**, and goldbees = 53% non-null. Therefore every
> result in this memo that DEPENDS on those columns (rates/fx sizing, real-rate style-timing, oil-sector
> cross-section) is **UNVERIFIED / not reproducible from disk** and must not be quoted. The two PARK
> candidates (copper/gold ratio, gold-vs-equity) were independently reproduced by the overfit analyst
> (XASSET_ADVERSARIAL.md) from a working data path and their PARK-NEEDS-MORE-DATA verdict stands on THAT,
> not on this memo. ACTION: data-officer to actually run + PERSIST the macro_state enrichment before any
> cross-asset signal is re-tested.

---

## 0. Data notes (read before trusting any number below)

`ALPHA_RANKER/rnd/panel/macro_state.parquet` — as documented in `rnd/lib/macro_state.py` —
carries `brent`, `dxy`, `india10y`, `real_rate_proxy` as **100% NaN, deliberately PARKED**
(no source on disk at the time it was built; stooq blocked). This session filled three of
those four gaps via **FRED** (D-033 auto-fetch, pre-approved for official/reliable sources),
sample-checked against known historical values before use:

| FRED series | maps to | sample check | result |
|---|---|---|---|
| DFII10 | US real 10Y yield (TIPS) | 2020-03-19 = 0.62 (expect ~0.35-1.0 range around the COVID real-yield spike) | OK |
| DCOILBRENTEU | Brent crude | 2020-04-21 = 9.12 (exact); 2022-06-08 = 129.2 vs known ~122.8 | OK |
| DTWEXBGS | Fed broad USD index (DXY proxy) | range/level sanity only | OK |
| PCOPPUSDM | Global copper price, monthly | 2022-01 = 9782 vs known ~9750 | OK |

India 10Y G-sec remains genuinely unavailable (RBI DBIE / home-network fetch needed) — still
parked, not fabricated. Copper via yfinance `HG=F` was **not attempted** — FRED's `PCOPPUSDM`
solved the gap with a better-provenance official source in the same pull, so the
yfinance/HINDCOPPER fallback path specified in the brief was unnecessary.

These four series are **not yet in `05_DATA_OFFICE/DATA_CATALOG.md`** — this agent fetched
them to a scratch working file for this analysis only, out of role scope to formalize the
catalog entry. **Flag to data-officer-kavya-reddy** if any signal below is pursued further.

Sample sizes are the binding constraint on everything in this memo: `macro_state.parquet` has
127 monthly rows (2016-2026). For the 1Y-horizon target the effective independent sample after
overlap-deflation is **~10 years** — no amount of cleverness makes a macro regime call
statistically provable on 10 independent yearly draws. Read every "KILL" below as "not provably
better than noise at this sample size," not "definitely worthless."

---

## 1. Leading risk-regime signal for the sizing layer

**Method:** two independent tests per signal — (a) linear-IC test (Spearman correlation,
signal at t vs forward NIFTY 500 return, with the harness's own lag-stability gate
[delta≤0.25] and a placebo control adapted for a single time series — see card for the
adaptation math, since the harness's raw `|IC|≤0.02` placebo bound is calibrated for
cross-sectional panels with hundreds of names per date, not a 120-obs single series); and
(b) an **exposure-scalar backtest** (expanding-window terciles → 0.5x/1.0x/1.5x exposure on
next month's NIFTY 500 return), judged against buy-and-hold, the incumbent India-VIX-alone
scalar, the incumbent %>200DMA breadth scalar, AND a 200-trial random-signal placebo (same
tercile mechanism, pure noise) to establish the noise floor for this specific method.

**Random-noise floor (the control that makes the rest of this table meaningful):** Sharpe
mean 0.744, std 0.152, p95 = 1.020, over 200 trials. Buy-and-hold itself: Sharpe 0.797, maxDD
-30.0%, ann.ret 13.7%.

| Signal | Horizon | Linear IC | NW-t | Lag gate | Scalar Sharpe | Scalar maxDD | z vs noise | Verdict |
|---|---|---|---|---|---|---|---|---|
| **Copper/Gold ratio, 6m Δ** | 1M | 0.126 | 1.38 | **FAIL** (Δ=0.41) | **1.138** | **-16.4%** | **2.59** | **CANDIDATE** |
| **Gold-vs-equity 1m momentum** | 1M | -0.048 | -0.53 | FAIL | **1.100** | -15.0% | **2.34** | **CANDIDATE** |
| Copper/Gold ratio, level | 1Y | -0.361 | -1.07 | pass | 0.936 | -16.9% | 1.26 | KILL |
| Term spread (US 10Y-2Y) | 1M | 0.056 | 0.63 | fail | 0.969 | -15.5% | 1.48 | KILL |
| Real 10Y yield (DFII10), level | 1Y | -0.187 | -0.53 | pass | 0.598 | -42.5% | -0.96 | KILL |
| Real 10Y yield, 3m Δ | 1M | -0.025 | -0.27 | fail | 0.651 | -42.5% | -0.61 | KILL |
| Dollar+INR combined stress | 1M | 0.041 | 0.45 | fail | 0.770 | -31.7% | 0.17 | KILL |
| DXY (broad USD) 3m Δ | 1M | 0.053 | 0.58 | fail | — | — | — | KILL |
| USDINR 3m Δ | 1M | 0.031 | 0.35 | fail | — | — | — | KILL |
| *BASELINE: India VIX level (incumbent)* | 1M | 0.120 | 1.35 | pass | 0.816 | -24.1% | 0.47 | *(weak, doesn't clear noise alone)* |
| *BASELINE: US VIX level (incumbent-adjacent)* | 1Y | 0.274 | 0.78 | pass | 1.042 | -18.9% | 1.96 | *(borderline)* |
| *BASELINE: %>200DMA breadth (incumbent)* | 1M | 0.009 | 0.10 | fail | 1.049 | -21.1% | 2.01 | *(borderline)* |

**Honest finding #1:** at n≈114-127 monthly observations, even the two signals ALREADY in
production (India VIX, %>200DMA breadth) barely clear the random-noise floor individually
(z≈0.5-2.0) when judged by this linear/scalar test in isolation. Their known real-world value
(CONSOLIDATION.md: breadth scalar "halved maxDD") likely comes from being blended/used inside
a fuller model, not from a standalone linear timing relationship — so this test framework is
not unfairly hard on the new candidates; it applies the same yardstick to the old ones.

**Honest finding #2:** two cross-asset candidates — **copper/gold ratio 6-month change** and
**gold-vs-equity 1-month momentum** — beat every incumbent (India VIX, US VIX, breadth) on
BOTH Sharpe and maxDD in the scalar backtest, and clear the random-noise floor at the highest
z-scores of the whole study (2.59 and 2.34). But both **fail the linear-IC lag-stability gate**
(delta 0.41 and 1.91, both >> 0.25 threshold) — the point-in-time correlation is weak/unstable
even though the realized scaling performance is strong. That internal conflict is a real
yellow flag: it suggests the scalar-backtest gain may be concentrated in a small number of
large regime turns (plausibly 2020 COVID, 2022 Fed hikes) rather than a stable month-to-month
relationship — exactly what an era-split test would catch.

**Verdict: MAYBE.** Cross-asset does not yet definitively beat trailing VIX for sizing — no
signal SURVIVES both tests cleanly — but two candidates show real, noise-floor-beating
improvement over the incumbent VIX-alone scalar and deserve the next gate. **Recommend routing
`W4X_copper_gold_ratio_sizing` (chg6m variant) and `W4X_gold_vs_equity_1m_sizing` to
overfit-analyst-sameer-bhat for an era-split/subsample-stability + PBO pass before any
sizing-layer change** — per the stop-condition (one refinement done; further tuning here would
just be researcher degrees of freedom).

---

## 2. Cross-sectional commodity-beta (sector-conditioned, panel_long, 21yr)

**Data landmine surfaced:** panel_long's sector taxonomy has only 20 broad buckets and
`Oil Gas & Consumable Fuels` conflates upstream E&P (commodity producer) with downstream
OMC/refiners (commodity consumer) — no sub-industry column exists to split them. This is
disclosed, not silently patched.

| Test | n (months) | IC | NW-t | Lag gate | Verdict |
|---|---|---|---|---|---|
| Metals & Mining spread vs copper 3m trend | 242 | 0.015 | 0.24 | FAIL | KILL |
| Oil Gas & Consumable Fuels spread vs Brent 3m trend | 242 | -0.031 | -0.47 | FAIL | KILL |
| Automobile & Auto Components spread vs Brent 3m trend | 242 | -0.099 | -1.54 | FAIL | KILL |

**Verdict: KILL, all three.** Automobile-vs-Brent is correctly signed (autos underperform when
oil trends up — cost-side margin squeeze) and closest to the significance bar, but misses it
and fails the lag-stability gate. **Blocked, not killed outright:** a clean commodity-consumer
basket (paints/tyres/aviation/OMC specifically, as the brief asked) needs a finer sub-industry
mapping than panel_long currently carries — added to the BLOCKED list below.

---

## 3. Real-rate regime as value-vs-momentum style timing

Tested via each stock's existing `ff_beta_HML` (value tilt) / `ff_beta_WML` (momentum tilt)
loadings' cross-sectional IC on `fwd_ret_1M_resid`, split by US real-rate (DFII10) 3m-change
regime, on the full 21yr panel_long (89 rising-regime months, 99 falling-regime months —
well-powered, no overlap issue since horizon=rebalance step).

| Loading | Rising-rate IC (t-stat) | Falling-rate IC (t-stat) |
|---|---|---|
| HML (value) | 0.004 (t=0.43) | -0.017 (t=-1.50) |
| WML (momentum) | **0.025 (t=2.86)** | **0.022 (t=2.37)** |

**Verdict: KILL** for "switch to value when real rates rise" as an actionable rule. Momentum's
IC is robustly positive and significant in BOTH regimes — it does not need a rate-regime timer
to work on this panel. Value has no reliably positive IC in either regime. [OPINION] The
value-momentum gap does narrow somewhat in rising-rate months (-0.021 vs -0.039) — directionally
consistent with the textbook thesis — but never comes close to flipping, so it is not a usable
signal at this magnitude.

---

## 4. Signal-by-signal return table (as requested)

| Signal | Horizon | Signed IC | NW-t (IC_IR proxy) | Lag/Placebo | Verdict |
|---|---|---|---|---|---|
| Copper/Gold ratio, 6m Δ (scalar) | 1M | 0.126 | 1.38 | lag FAIL / placebo pass | **CANDIDATE** |
| Gold-vs-equity 1m momentum (scalar) | 1M | -0.048 | -0.53 | lag FAIL / placebo pass | **CANDIDATE** |
| Copper/Gold ratio, level | 1Y | -0.361 | -1.07 | lag pass / placebo pass | KILL |
| Real 10Y yield (DFII10), level | 1Y | -0.187 | -0.53 | lag pass / placebo pass | KILL |
| Term spread (US 10Y-2Y) | 1M/1Y | 0.056 / 0.037 | 0.63 / 0.10 | lag FAIL both | KILL |
| Dollar+INR combined stress | 1M/1Y | 0.041 / -0.069 | 0.45 / -0.19 | lag FAIL both | KILL |
| Metals & Mining vs copper trend (x-sec) | 1M | 0.015 | 0.24 | lag FAIL | KILL |
| Oil&Gas vs Brent trend (x-sec, conflated) | 1M | -0.031 | -0.47 | lag FAIL | KILL |
| Automobile vs Brent trend (x-sec, consumer control) | 1M | -0.099 | -1.54 | lag FAIL | KILL (closest miss) |
| Real-rate regime → value/momentum switch | 1M | see §3 | momentum t=2.4-2.9; value n.s. | n/a | KILL |
| BASELINE India VIX level (incumbent) | 1M | 0.120 | 1.35 | lag pass | (weak, reference only) |
| BASELINE %>200DMA breadth (incumbent) | 1M | 0.009 | 0.10 | lag FAIL | (reference only) |

---

## 5. BLOCKED list (untested, needs more data — not fabricated, not killed)

1. **India 10Y G-sec yield** — no source on disk; FRED/stooq both blocked for this specific
   series. Needs RBI DBIE portal or home-network fetch. Would sharpen `real_rate_proxy` to an
   India-specific real rate (current DFII10 is US-only).
2. **Clean commodity-consumer sector basket** (paints, tyres, aviation, OMC specifically, split
   out from the coarse `Oil Gas & Consumable Fuels` / `Chemicals` / `Services` buckets) — needs
   a finer NSE/BSE sub-industry classification than panel_long's 20-sector column carries.
   The Automobile-vs-Brent proxy (§2) is the closest available substitute and nearly clears
   significance — a real sub-industry split would likely sharpen it further.
3. **India CPI/WPI** — still nothing on disk; would allow a genuine India real-rate proxy
   (India 10Y minus India CPI) instead of the US-only DFII10 used throughout this memo.
4. **FII/DII flow data** — mentioned in this agent's charter (regime notes) but not available
   on disk per prior sessions' notes; would be a natural companion cross-asset/flow signal.

---

## Bottom line

Per-signal verdicts and the cross-asset-vs-trailing-VIX call are summarized in §4 and §1.
**No signal reaches SURVIVOR grade** at this sample size — that is itself the honest,
money-first result, not a failure to find something. Two CANDIDATES (copper/gold ratio 6m
change, gold-vs-equity 1m momentum) are worth Sameer Bhat's era-split/PBO pass before any
sizing-layer change is considered; everything else in objectives 1-3 is a clean KILL with
disclosed reasoning, and one BLOCKED item (India real rate) would meaningfully improve the
next attempt at this whole line if the data ever becomes available.
