# MARKET_REGIME_MACRO — CAPE / yield-curve / credit-spread / Buffett-indicator / breadth-thrust
Author: Cyrus Daruwalla (Macro & Events Strategist, E-021). 2026-07-17.
Scope: the 5 classic macro/valuation regime gauges the Principal named, tested as candidate
inputs to the ABSOLUTE_SCORER_SPEC `M` term (`rnd/wave4/ABSOLUTE_SCORER_SPEC.md`). Judged on
ECONOMIC LOGIC + drop-one-bear / era-split ROBUSTNESS, not t-stat/DSR (regime data is inherently
low-n — the firm's low-t rule applies throughout). Tags: [DATA]=on-record fact, [INFERENCE]=my
construction, [OPINION]=my judgment.

**Non-overlap note:** this deliverable does NOT touch the valuation-percentile / cross-asset-ratio
work (owned by another concurrent agent — no `MARKET_REGIME.md` was found on disk at the time of
this session; if/when it lands, this file should be read alongside it, not merged into it). My 5
inputs only: CAPE-India, US term spread + India-10Y level, US credit spread, Buffett indicator
(official + proxy), breadth thrust.

Support files: `rnd/wave4/w4mac_support/w4mac_build_gauges.py` (build+test script, reproducible),
`w4mac_gauges_panel.parquet` (the assembled monthly panel), `w4mac_gauges_summary.json` (raw
correlation/robustness numbers). Cards: `rnd/cards/W4MAC_*.json` (one per gauge + the ensemble
verdict). New raw data persisted to `Shreyas_Ionic_AMC/05_DATA_OFFICE/data/` + DATA_CATALOG.md
entry (credit_spread_baa_aaa, buffett_indicator_india_official_worldbank, india_gdp_usd_annual_fred,
india_10y_gsec_fred).

---

## 0. Method (read once, applies to every gauge below)

- **Forward-return target:** official `datasets/index_daily/nifty500.parquet` only covers
  2016-2026. To test across more than one historical bear I built an EW-cube proxy index off
  `rnd/panel/cube_close_long.parquet` (cross-sectional MEDIAN daily return of the 976-name panel,
  cumulated, 2005-2025) — **[INFERENCE], not an investable index**, validated against the official
  NIFTY500 at **r=0.909** monthly-return correlation over the 2016-2025 overlap (n=119). Used only
  for forward 1Y/5Y return, 1Y forward max-drawdown, and 1Y forward realized vol targets, all
  computed from >=t+1 daily data (no lookahead into the feature side).
- **No lookahead on the feature side:** every gauge is either (a) an expanding z-score of its own
  history (`min_periods=24`, uses only <=t obs) or (b) merge_asof(direction='backward') onto the
  monthly panel date, so a reading is only visible once it would actually have existed. **One real
  bug caught and fixed in this pass:** an early draft joined the annual Buffett-proxy series by
  calendar year, which let e.g. January-2020 see December-2020's year-end market level — reworked
  to merge_asof-backward stamped at each year's actual last observation date before any numbers were
  produced. Flagging this explicitly per the task's data-integrity instruction (a prior agent's
  claimed-but-unpersisted FRED fill was the reason for that instruction) — every fetch below was
  written to parquet AND RE-READ from disk before being reported as filled (see per-series counts).
- **Robustness battery, not t-stats:** for each gauge, (i) full-sample correlation with fwd 1Y/5Y
  return and fwd 1Y drawdown, (ii) era-split (first half vs second half of the gauge's own valid
  date range) sign check, (iii) drop-one-bear (GFC-2008, COVID-2020, HIKE-2022 — whichever fall
  inside the gauge's valid range) sign check. A gauge that flips sign under either test is flagged
  as fragile regardless of how large its full-sample number looks.

---

## 1. CAPE-India — buildable, weak, structurally can't reach 2008

Built P/E10 = aggregate market cap / trailing-120-month mean aggregate net profit (both from
`stock_valuation_pit.parquet`), **NOMINAL** (no India CPI anywhere on disk to deflate — confirmed
again this session, matches `macro_state.py`'s prior PARKED note). First valid reading 2015-03
(130/249 months non-null) — the 120-month lookback is a hard floor, so **this construction can
never see 2008 no matter how much price history exists**.

- Full-sample corr: fwd 1Y = 0.114 (n=94), fwd 5Y = 0.904 (n=45, **inflated by 60-month window
  overlap — effectively ~2-3 independent periods, not 45; do not quote this number as strong**),
  fwd maxdd = 0.086.
- Era-split (2017-20 vs 2021-24): stable (0.48 / 0.51).
- Drop-one (only COVID and HIKE-2022 reachable): **sign flips** when COVID is dropped (-0.016 vs
  full 0.114).
- Contrast vs plain trailing EY (`market_state.EY_hist_zscore_expanding`, full history from 2007):
  the existing simple valuation-band is BOTH longer-history and more era-stable than this CAPE
  construction on this data. CAPE-India, at least in this nominal, non-CPI-adjusted form, is not an
  upgrade on the plain trailing measure.

Card: `rnd/cards/W4MAC_cape_india.json`.

## 2. Yield curve — US term spread unstable; India-10Y level newly UNBLOCKED, slope still blocked

US term spread (10Y-2Y, from `macro_state.parquet`, 2016-2026, n=119 valid): full-sample corr with
fwd 1Y = **-0.26**, fwd 5Y = -0.459 — but **era-split sign FLIPS cleanly** (+0.53 in 2016-2020 vs
-0.60 in 2020-2024). [OPINION] my read: the 2020-22 zero-rate-then-fastest-hike-cycle regime
decoupled the textbook US-curve/global-risk relationship from India-equity direction. Drop-one is
sign-stable, but that is cold comfort given the era-split failure — **do not trust this gauge's sign
as fixed.**

**Genuine new finding:** India 10Y G-sec yield IS fetchable from FRED — series `INDIRLTLT01STM`
succeeded (2011-12→2026-05, n=174, D-009 pass: 2011-12=8.56%, 2020-21 range 6.0-6.5%, 2025-26 range
6.6-7.2%, all consistent with published history) — where `INDIRLTLT01INM` (still 404s) and stooq
(JS-challenge) had been marked hard-blocked before. **This is only the LEVEL, not a slope** — no
India short-end (2Y/91-day T-bill) series was found on disk or via any FRED ID tried, so a true India
curve slope remains genuinely blocked; flagging to Data Officer (also added to DATA_CATALOG.md with
an action item to swap the ID in `macro_state.py` and unpark the `india10y` column). A 3-month-change
derivative of the level was tested as a stand-in and is weak/era-unstable (corr 1Y=-0.073, era-split
flips) — exploratory only, not a shippable signal yet.

Card: `rnd/cards/W4MAC_yield_curve.json`.

## 3. Credit spread (BAA-AAA) — buildable, most internally-consistent sign of the whole battery

FRED BAA + AAA, 1919-2026 (n=1290, D-009 pass: 1919-01 BAA=7.12 exact; re-read from disk confirmed
1290/1290 non-null after write). Oriented "tight spread = risk-on = bullish" per the naive prior —
the EMPIRICAL sign came out negative and is **stable under BOTH era-split (-0.10 → -0.65, same
sign) and all-3-bear drop-one (-0.202/-0.187/-0.191, essentially invariant)** — the cleanest
robustness profile of any single gauge tested. [OPINION] Read correctly this is not
anti-economic-logic: it says tight/compressed spreads (late-cycle complacency) precede WEAKER
forward India returns and wide/stressed spreads (capitulation) precede stronger ones — a
well-documented CONTRARIAN credit-spread pattern, not a coincident risk gauge. My initial sign
convention was the wrong prior, not the data. Weak on crash-risk directly (maxdd corr only 0.107).
Global (US-sourced), appropriately a corroborating rather than primary India input.

Card: `rnd/cards/W4MAC_credit_spread.json`.

## 4. Buffett indicator (market-cap/GDP) — best crash-risk signal found, but GFC-concentrated

Official series (FRED `DDDM01INA156NWDB`, World Bank, 2000-2020) D-009 confirmed against the
well-known India history (2007=161.2% pre-GFC peak, 2008=66.0% post-crash — both match published
figures exactly) but **STALE, no post-2020 print**. Built a PROXY (our-universe aggregate mktcap
from `stock_valuation_pit.parquet` ÷ India GDP in INR, FRED `MKTGDPINA646NWDB` × USDINR) to extend
to present — **validated at r=0.965 vs the official series over the 16-year overlap**, strong
enough to trust the proxy trend past 2020 (current reading: 2024≈139%, 2025≈135%).

- Full-sample corr: fwd 1Y = **0.362** (best of the battery), fwd 5Y = 0.309, **fwd maxdd = 0.489**
  — the strongest crash-risk predictor found, more than 5x the plain EY-valuation-band's -0.088
  (wrong-signed).
- Drop-one: sign never flips (0.124 GFC-dropped / 0.361 / 0.387) but **magnitude nearly halves
  without GFC** — a real, disclosable concentration, exactly what ABSOLUTE_SCORER_SPEC §4.2's
  leave-one-bear-out gate exists to catch.
- Era-split: **fails** (+0.49 in 2007-16 vs -0.12 in 2016-24) — 2016-2024 was a period of
  persistent India market-cap/GDP re-rating (71%→139% by-year proxy series) where "expensive"
  did not reliably precede weak returns; the market kept structurally re-rating rather than
  mean-reverting on the old schedule.

Card: `rnd/cards/W4MAC_buffett_indicator.json`.

## 5. Breadth thrust (3m change in %>200DMA) — weakest magnitude, most boringly stable

Uses the existing `market_state.breadth_pct_above_200dma` (already on disk, from
`cube_close_long.parquet`) but tests its 3-month CHANGE (thrust/momentum) rather than its level
(the level already feeds the validated `s_mkt` exposure scalar per ABSOLUTE_SCORER_SPEC — this is
the incremental piece). Weakest correlations of the battery on every axis (1Y=0.105, 5Y=0.118,
maxdd=0.167) but **passes both era-split (0.13→0.06, same sign) and all-3-bear drop-one
(0.058/0.124/0.096, always positive)** — the only gauge besides credit spread that is clean on both
robustness axes simultaneously. A classic Zweig discrete 10-day-threshold thrust flag was considered
but not built — too sparse (a few dozen occurrences over 20 years) to test meaningfully under this
task's low-t discipline; the continuous 3-month version is the more usable soft input.

Card: `rnd/cards/W4MAC_breadth_thrust.json`.

---

## 6. Ensemble vs valuation-band-alone — the actual answer to the task's core question

Built an unweighted mean of oriented (positive=cheap/bullish) z-scores: `ensemble_all` (all 7
gauges incl. valband+india10y), `ensemble_new4` (my 4 new: CAPE, term-spread, credit-spread,
Buffett), `ensemble_new5_w_breadth` (+breadth-thrust). Compared against `g_valband_EY` (the
existing baseline valuation-band, `market_state.EY_hist_zscore_expanding`) and against
`g_buffett` alone (the single strongest new gauge).

| | corr fwd 1Y | corr fwd 5Y | corr fwd maxdd | era-split stable? | drop-one stable? | drop-one range |
|---|---|---|---|---|---|---|
| **g_valband_EY alone** | 0.26 | 0.277 | -0.088 | **yes** | **no** | -0.025 to 0.27 (flips) |
| **g_buffett alone** | **0.362** | 0.309 | **0.489** | no | yes | 0.124 to 0.387 |
| ensemble_all (7) | 0.112 | 0.102 | 0.204 | no | no | -0.016 to 0.116 |
| ensemble_new4 | 0.063 | -0.022 | 0.328 | no | **yes (tight)** | 0.057 to 0.075 |
| ensemble_new5_w_breadth | 0.086 | 0.074 | 0.257 | no | **yes (tight)** | 0.029 to 0.088 |

**Three honest findings, no clean "ensemble wins":**
1. **Raw magnitude:** single gauges beat every ensemble on both return-prediction and crash-risk.
   Unweighted averaging with genuinely weak/unstable legs (CAPE, term-spread, india10y-change)
   dilutes the strong ones — Buffett-alone's 0.489 maxdd correlation drops to 0.257-0.328 once
   blended.
2. **Drop-one-bear robustness (the exact thing ABSOLUTE_SCORER_SPEC §4.2 gates on):** here the
   picture flips. `g_valband_EY`'s return-edge is NOT dropone-stable — it nearly vanishes without
   2008 in the sample, more concentrated in a single crisis than its full-sample number suggests.
   The 4- and 5-gauge ensembles (not the noisier all-7 blend) ARE dropone-stable, with an unusually
   TIGHT range across which bear is excluded (0.057-0.075) — i.e. their sign and rough magnitude do
   not hinge on any one historical crisis the way the single best gauges do.
3. **Era-split:** nothing survives cleanly except `g_valband_EY` and `g_breadth_thrust`
   individually — every multi-gauge blend fails a simple pre/post-2015-16 split, because
   term-spread and Buffett-proxy each flip sign around then for unrelated reasons (Fed policy
   regime vs India structural re-rating), and averaging carries that instability through rather
   than cancelling it.

**Recommendation [OPINION]:** keep the plain valuation-band (EY) as `M`'s primary input, exactly as
ABSOLUTE_SCORER_SPEC currently specifies — it remains the best era-stable return-signal on this
data. ADD the Buffett indicator as a SEPARATE, explicitly-labeled crash-risk conditioner (0.489
maxdd correlation is too strong and too GFC-disclosed to bury inside an unweighted average) rather
than folding all 4-5 new gauges into one blended `M`. Credit spread and breadth-thrust are the two
gauges clean enough on both robustness axes to be trusted as small corroborating tilts if a
multi-gauge design is wanted later; CAPE-India (in its current nominal, no-CPI form) and the raw US
term-spread sign are not trustworthy enough to ship as-is.

Card: `rnd/cards/W4MAC_ensemble_vs_valband.json`.

---

## Data-officer action items (flagged, not actioned beyond this session)
1. `macro_state.py`: swap India-10Y from the blocked `INDIRLTLT01INM` to the working
   `INDIRLTLT01STM` and unpark the `india10y` column; still needs an India short-end series
   (2Y/91-day T-bill) to build a real curve slope.
2. `DATA_CATALOG.md`'s 2026-07-11 "FRED (proxy reset)" block note is now STALE — FRED works fine as
   of 2026-07-17 via `truststore.inject_into_ssl()` + direct `fredgraph.csv`; re-check before
   re-flagging FRED as blocked in future sessions.
3. India CPI/WPI/GDP-nowcast: still not found anywhere on disk (confirms `BOOKS_PAPERS_IDEAS.md`'s
   prior finding) — needed for a real (inflation-adjusted) CAPE and a real-rate regime gauge.
