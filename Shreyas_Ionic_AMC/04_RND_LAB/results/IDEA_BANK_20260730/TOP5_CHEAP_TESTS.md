
# TOP 5 CHEAP TESTS — executable specs, no further design needed
Companion to `IDEA_BANK.md` (same folder). Each spec below names exact files, columns, formulas, splits,
and pre-registered kill criteria. Whoever runs these: **write the kill criteria to disk BEFORE running**,
per firm discipline (D-035) — do not tune after seeing a result. Costs: none of these five require option
P&L simulation (per the mandate); all are descriptive/regression cheap tests. All 5 have data ALREADY ON
DISK — no Data Officer gate needed to start.

---

## TEST 1 — NS-2: does SENSEX's implied-vol premium over NIFTY exceed its realized-vol premium?
**Files:**
- `intraday_options_strategy/datasets/raw/hf_index_options_1m/index/SENSEX.parquet` (1-min spot)
- `intraday_options_strategy/datasets/raw/hf_index_options_1m/options/SENSEX/{expiry}.parquet` (144 files)
- `intraday_options_strategy/datasets/raw/hf_index_options_1m/index/NIFTY.parquet`
- `intraday_options_strategy/datasets/raw/hf_index_options_1m/options/NIFTY/{expiry}.parquet`
- Reuse `intraday_options_strategy/buying/chain.py` (`build_expiry_index`, `load_expiry`, `nearest_expiry`)
  for both indices — do not rewrite the loader.

**Method:**
1. For each trading day `d` in the overlap window (SENSEX file coverage: 2023-08→2026-05), find the front
   0DTE-or-nearest expiry for each index (`nearest_expiry(d, min_dte=0, max_dte=9)`).
2. At a fixed snapshot (09:20-09:30 mean trade price, matching today's in-flight
   `OPTION_SURFACE_SIGNALS_20260729` convention for a same-epoch comparison — if that window shows high
   missingness for either index, widen to 09:15-11:00 exactly as that script's addendum already did),
   solve ATM straddle implied vol for both SENSEX and NIFTY via `vollib.black_scholes.implied_volatility`
   (r=6.5%, q=0, T=DTE/365). Apply the IV sanity cap (1%,100%) from KNOWLEDGE_BASE lesson on the 2026-07
   INFY IV=133% blowup — drop/clip outside this band.
3. `IMPLIED_GAP_t = IV_ATM_SENSEX(t) − IV_ATM_NIFTY(t)`.
4. `REALIZED_GAP_t = RV_20d_SENSEX(t) − RV_20d_NIFTY(t)`, close-to-close annualized realized vol on the
   1-min-derived daily closes, trailing 20 trading days ending at t (causal, no lookahead).
5. OLS: `IMPLIED_GAP_t = a + b * REALIZED_GAP_t + e_t`, Newey-West HAC (lag=5).

**Pre-registered kill:** if `b` is not statistically distinguishable from 1 AND the intercept `a` is not
statistically distinguishable from 0 (i.e., implied gap is explained 1:1 by realized gap, no persistent
excess) → **KILL, the 1.22x premium is fair value.** If `a` is significantly positive (excess implied
premium beyond what realized vol justifies) → does NOT kill, proceeds to Gate-3 structure design.
**Report separately:** SENSEX option chain liquidity (mean daily volume/OI per contract) alongside the
verdict — a real excess with near-zero SENSEX liquidity is a capacity note, not a green light.
**Output:** `results/IDEA_BANK_20260730/TEST1_NS2_dispersion/` — write `VERDICT.md` with `a`, `b`, HAC t-stats,
n, and the liquidity table.

---

## TEST 2 — Expiry-day regime break (Nov-2024 / Sep-2025 SEBI structural changes)
**Files:**
- `05_DATA_OFFICE/data/fo_bhavcopy_hist/fo_idx_{2011..2026}.parquet` (SYMBOL=='NIFTY', gate CONTRACTS>0)
- `intraday_options_strategy/datasets/raw/hf_index_options_1m/index/NIFTY.parquet` (for intraday expiry-day range)

**Regime split (exact, dated boundaries — do not adjust):**
- Regime A: all NIFTY weekly expiries **before 2024-11-21** (pre-SEBI-tightening, Thursday expiry, multi-index
  weeklies still live on NSE).
- Regime B: expiries **2024-11-21 → 2025-08-31** (single-weekly-per-exchange in force, still Thursday).
- Regime C: expiries **on/after 2025-09-02** (Tuesday expiry, per the Sep-2025 exchange-schedule swap).

**Metrics, computed per expiry day, each regime pooled separately:**
1. Expiry-day realized range: `(intraday high − intraday low) / prior close` from 1-min NIFTY bars, time≥09:15
   only (pre-open-auction guard, per CLAUDE.md landmine #2).
2. Pin strength: absolute distance of the 15:30 close from the nearest ₹50-strike, as % of spot.
3. Expiry-day close-to-close return, signed and absolute.

**Test:** Welch's t-test (unequal variance) + Kolmogorov-Smirnov on each metric, Regime A vs B, and B vs C
separately (do not pool A+B vs C, that conflates two distinct changes).

**Pre-registered kill:** if NONE of the three metrics shows a distinguishable shift (p<0.05 uncorrected, since
this is a first-look screen not a certification) in EITHER regime comparison → **KILL as a standalone
regime-detection idea**; route any residual interest to Sameer as a footnote on S1-F's existing parameter
review, not a new R&D item. If a shift IS found, the NEXT step (not part of this cheap test) is checking
whether it's actionable via S1-F's own entry-distance/timing rule, not a new structure.
**Output:** `results/IDEA_BANK_20260730/TEST2_expiry_regime/VERDICT.md` — table of the three metrics × three
regimes (mean, std, n) + the four pairwise test p-values.

---

## TEST 3 — Client/Pro index-option positioning vs forward NIFTY return
**Files:**
- `05_DATA_OFFICE/data/participant_oi/participant_oi_normalized.parquet` — 10,505 rows, columns confirmed
  by direct read: `Client Type, Future Index Long, Future Index Short, Future Stock Long, Future Stock Short,
  Option Index Call Long, Option Index Put Long, Option Index Call Short, Option Index Put Short,
  Option Stock Call Long, Option Stock Put Long, Option Stock Call Short, Option Stock Put Short,
  Total Long Contracts, Total Short Contracts, date`. Filter `Client Type` in `{Client, Pro}`.
- `intraday_options_strategy/datasets/raw/hf_index_options_1m/index/NIFTY.parquet` for forward returns
  (close at 15:25 or last bar of day, time≥09:15 guard).

**Signal construction (compute BOTH, report both, do not cherry-pick):**
- `CLIENT_SKEW_t = (Option Index Call Long_t − Option Index Call Short_t) − (Option Index Put Long_t −
  Option Index Put Short_t)`, for `Client Type == 'Client'`, z-scored on a trailing 60-day expanding-or-
  rolling window (causal — no lookahead into the z-score's own mean/std).
- `PRO_MINUS_CLIENT_t = (net Pro index-option position) − (net Client index-option position)`, same
  z-scoring, using `net = (Call Long − Call Short) + (Put Long − Put Short)`.

**Targets:** forward 1/3/5-day NIFTY log return, from the same-day close used to timestamp the signal
(participant OI is published T+1 by NSE convention — **verify the file's `date` column is the OI AS-OF date,
not the publish date, before assuming same-day usability; if it's as-of-date, entry must be next trading day's
open at the earliest — this is a real lookahead risk, check it FIRST**).

**Method:** OLS per signal per horizon, Newey-West HAC (lag=h). **Placebo:** date-shuffled version of each
signal, 200 draws, real |t| must exceed the 95th percentile of the placebo distribution AND itself clear |t|≥2.

**Pre-registered kill:** KILL if either signal fails on ALL horizons, or passes but the two signals'
correlation with each other exceeds 0.6 (i.e., they're the same bet twice — report as ONE finding, not two,
per the trials-ledger honesty rule already flagged in `IDEA_BANK.md` §4.1).
**Output:** `results/IDEA_BANK_20260730/TEST3_participant_oi_options/VERDICT.md` — both signals × 3 horizons
= 6 cells, all reported, plus the cross-signal correlation and the publish-date-lookahead check result
stated explicitly before any t-stat is trusted.

---

## TEST 4 — Cross-asset overnight gap-SIZE predictor, conditioning NS-1's resurrection
**Files:**
- `results/DTE_1DTE_BACKTEST_20260725/gaps_1dte.csv` — 259 rows, columns `day, strike, prem_dm1_1525,
  prem_d0_open, gap_ratio, spot_dm1, spot_d0_open` (this is the base night-list; NS-1's own 5-arm dataset
  used the same night population at 5 strike distances — if that per-arm P&L file can't be found, regenerate
  it from `intraday_options_strategy/buying/chain.py` + `engine.py` at d∈{0,0.5,1.0,1.5,2.0}% exactly per
  `ideas/20260725_NEW_STRATEGY_GENESIS.md`'s frozen NS-1 spec — do not alter the spec while regenerating).
- `05_DATA_OFFICE/data/usdinr_fred_daily.parquet` (FRED DEXINUS)
- `05_DATA_OFFICE/data/us_sp500_daily.parquet` (SPX daily close)

**Signal construction (causal — only information available by D-1 evening / before D0 09:15):**
- `USDINR_MOVE_t = |log(USDINR_close[D-1] / USDINR_close[D-2])|` (most recent available FX print before the
  Indian overnight gap begins).
- `SPX_MOVE_t = |log(SPX_close[D-1, US session] / SPX_close[D-2, US session])|` — note the US session for
  "D-1" closes AFTER Indian market close the same calendar day, so this is genuinely available information
  by the time NIFTY opens on D0; get the calendar alignment right (US Friday close informs Indian Monday
  open, not Friday's own NIFTY session).

**Target:** `|gap_ratio_t − 1|` from `gaps_1dte.csv` (size of the overnight premium move, direction-agnostic)
AND separately `|log(spot_d0_open/spot_dm1)|` (size of the underlying gap itself — the more direct target).

**Method:** OLS of each target on each predictor (4 cells: 2 predictors × 2 targets), plus the joint
regression with both predictors. Newey-West not needed (non-overlapping daily obs, no horizon overlap).

**Pre-registered kill:** KILL if no predictor clears |t|≥2 for either target. If a predictor DOES clear the
bar, the DECISIVE follow-up (not optional, part of this same cheap test): re-run NS-1's own 5-arm P&L
(`net pts/night` and `worst-night/mean` ratio, exact metrics from the K-Killed-Ideas NS-1 write-up) restricted
to the bottom-tercile-predicted-gap nights only. **KILL the resurrection attempt specifically** if the
worst/mean ratio in that filtered subset still exceeds 50× (NS-1's original bar was 3×; 50× is a deliberately
generous relaxation to check whether filtering helps AT ALL before demanding it clear the original bar).
**Output:** `results/IDEA_BANK_20260730/TEST4_ns1_conditioner/VERDICT.md` — the 4+2 regression cells, then
(if triggered) the filtered-subset P&L table with worst/mean ratio stated explicitly.

---

## TEST 5 — India VIX vol-of-vol regime bucket vs forward realized range
**Files:**
- NSE all-indices daily close archive: `indices_close/indices_{yyyy}.parquet` (per DATA_CATALOG row
  "NSE all-indices daily close (incl India VIX OHLC...)", 2011-2026, verified 2026-07-11) — filter to the
  India VIX row/symbol.
- `intraday_options_strategy/datasets/raw/hf_index_options_1m/index/NIFTY.parquet` for forward realized range.

**Signal:** `VOV_t = rolling_std(India_VIX_close, window=15 trading days)`, computed causally (window ends
at t, no centering). Quintile-bucket `VOV_t` (recompute quintile breakpoints on an EXPANDING window up to t,
never using future data to set the breakpoints).

**Target:** forward 5-day realized range of NIFTY, `(max(high[t+1..t+5]) − min(low[t+1..t+5])) / close_t`,
time≥09:15 guard applied throughout.

**Method:** compare the top-vs-bottom VOV quintile's target distributions (Mann-Whitney U, since range is
skewed) + report the mean spread. **Placebo:** same test on a date-shuffled VOV series, 200 draws.

**Pre-registered kill:** KILL if the top-minus-bottom quintile spread does not clear the 95th percentile of
the placebo distribution, OR if the pattern is non-monotonic across all 5 quintiles (not just top-vs-bottom).
**Output:** `results/IDEA_BANK_20260730/TEST5_vol_of_vol/VERDICT.md` — 5-quintile table (mean/median target,
n) + Mann-Whitney U statistic + placebo percentile.

---

## Sequencing note
Tests 1-3 and 5 are fully independent and can run in parallel (respecting D-023's 3-parallel-agent cap).
Test 4 should run AFTER confirming NS-1's per-arm P&L file location (or accepting the regeneration cost),
since it's the only one with a real "file might not exist" risk (the 5-arm dataset behind the KILLED_IDEAS
NS-1 numbers was not found on disk during this prospecting pass — only the underlying `gaps_1dte.csv` was
located). Every VERDICT.md must state PASS/KILL against the pre-registered criterion above, verbatim,
before any of these five graduates to a one-pager or Gate-3 spec.
