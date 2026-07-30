# PRE-REGISTRATION — Indicator mine for intraday DIRECTIONAL NAKED OPTION BUYING
Owner: Arjun Rao (Head of Quant). Written 2026-07-30, BEFORE running any of the code below.
Any deviation discovered after seeing results will be logged verbatim, not silently absorbed.

## Mandate (as given)
Naked long options only (0.40-0.80 delta band), hard stop-loss on every trade, target >100%
CAGR at <25% maxDD. Honest prior (established today on THIS data): 23 price-derived triggers
measured 1-6pt edges (best 10.03pt, t=3.10); MA/RSI 0/56 survived placebo; regime gates 0/28;
confluence stacking buys appearance not significance. Every price-only family has failed.
**Therefore this mine is restricted to families that introduce information the OHLC price
series does not already contain** — option-chain volume/OI and India VIX — plus a minimal,
capped extension of the ONE proven price trigger to bar sizes not yet tested. No fresh
Ichimoku/Bollinger/MACD/Stochastic/ADX/CCI/Williams-%R/Aroon/TRIX/Vortex hunt (poor prior,
explicitly out of scope per the task brief).

## Data (verified before use, this session)
- Option chain: `intraday_options_strategy/buying/chain.py` (`build_expiry_index`), raw files
  `.../hf_index_options_1m/options/NIFTY/{expiry}.parquet`. 261 valid expiries 2021-05-27 ..
  2026-06-02 (1 stub skipped: 2026-06-09, per chain.py's own filter).
- **Volume population verified 2026-07-30 (5-point sample across 2021/2023/2025x2/2026):
  99.3-100% nonzero every year.** OI population: **100% in 2021/2023, drops to ~34-35% from
  2025-03 onward** (matches SHARED_CONTEXT's prior finding). OI-dependent cells therefore
  report a 2021-2024 (full pop) / 2025-2026 (thin pop, ~35%) split and are flagged accordingly.
- India VIX 1-min: `intraday_options_strategy/datasets/processed/vix_1min.parquet`, 1,047,167
  rows, 2015-01-09 .. 2026-05-14 (naive IST minute index, single `vix` column). **Ends
  2026-05-14, ~2.5 weeks before the option/spot data's 2026-06-02/03 end** — VIX-dependent
  cells are truncated there; stated explicitly, not silently padded.
- NIFTY 1-min spot: same file/landmines as every other arm this week (index volume=0/unusable,
  filter time>=09:15, drop pre-open auction prints).
- **Denominator-disease guard applied up front:** raw put/call volume RATIO (PCR) blows up
  as either side approaches zero — this is the exact "net-debit denominator" landmine in a new
  costume. Every option-chain-volume signal below uses the BOUNDED, stable form
  `(CE_vol-PE_vol)/(CE_vol+PE_vol) in [-1,1]`, never a raw ratio.

## Pre-registered indicator list (locked, 15 cells across 3 families)

### Family A — OPTION-CHAIN VOLUME/OI (orthogonal information; primary budget). 10 cells.
Computed on 15-min buckets from the ACTIVE weekly chain (each expiry file already IS that
front-week chain's own life, per chain.py's own construction — no separate DTE filter needed).
1. **A1 CE-PE volume imbalance, call-heavy**: imb=(CE_vol-PE_vol)/(CE_vol+PE_vol) over the
   bucket; z-score over trailing 60min (session-reset); fires when z>=+2. Direction: measured
   empirically (signed forward move), not assumed.
2. **A2 CE-PE volume imbalance, put-heavy**: mirror of A1, z<=-2.
3. **A3 OTM-call strike concentration**: within each bucket, max single OTM-call-strike volume
   share of total OTM-call volume that bucket; fires at top-decile share (>=0.40, fixed not
   tuned on outcome). Direction measured empirically.
4. **A4 OTM-put strike concentration**: mirror of A3 on PE side.
5. **A5 option-volume-weighted VWAP-proxy, reclaim**: `vwap_proxy = cumsum(spot_close *
   total_opt_vol)/cumsum(total_opt_vol)` intraday (session-reset; total_opt_vol=CE_vol+PE_vol
   substitutes for the index's own unusable volume=0). Band = +-1.5x rolling 30-min stdev of
   (spot-vwap_proxy). Signal = bar sweeps outside band then CLOSES back inside (mirrors the
   ONE proven price trigger `sweep_priorday_reclaim`'s structure, swapping a static price
   level for a volume-weighted one).
6. **A6 same VWAP-proxy band, continue**: bar sweeps outside AND closes outside (continuation
   variant, mirrors `sweep_..._continue`).
7-10. **A7-A10 near-ATM OI momentum quadrant** (strikes within 3% of spot, CE+PE OI summed —
   *[OPINION] adaptation: classic OI-quadrant analysis uses futures OI; we only have options
   OI, so this is combined near-ATM options OI as a positioning proxy, not the textbook
   construction — flagged, not hidden*): 15-min ΔOI vs Δprice sign -> {price_up&OI_up
   (long-buildup), price_up&OI_down (short-covering), price_down&OI_up (short-buildup),
   price_down&OI_down (long-unwind)}. Reported split 2021-2024 (full OI pop) vs 2025-2026
   (~35% pop, thin — stated, never hidden).

### Family B — INDIA VIX DYNAMICS (semi-orthogonal). 3 cells.
11. **B1 VIX-RV divergence, high**: 30-min realized vol (annualized, close-to-close) vs
    same-scale VIX level; z-score of (VIX-RV) over trailing 60-min; fires z>=+2.
12. **B2 VIX-RV divergence, low**: mirror, z<=-2.
13. **B3 VIX rate-of-change spike**: |ΔVIX| over trailing 15-min in the extreme decile (fixed
    threshold, not outcome-tuned); direction of the spot forward move measured, not assumed
    (both VIX-up-spike and VIX-down-spike bucketed and reported).

### Family C — MULTI-TIMEFRAME EXTENSION of the one proven price trigger. 2 cells.
Capped, minimal, price-only — justified ONLY because `sweep_priorday_reclaim` already cleared
every gate today (t=3.10) at 15-min, and today's late-session test found 15-min beat 3-min
(contra the usual bar-size assumption), so the untested question "does it keep improving past
15-min or peak there" is a direct, disciplined follow-up, not a fresh fishing trip.
14. **C1** `sweep_priorday_reclaim`, IDENTICAL definition, 30-min bars.
15. **C2** `sweep_priorday_reclaim`, IDENTICAL definition, 45-min bars.

**TOTAL TRIALS THIS MINE: 15.** Firm cumulative trials after this row (per
OVERFIT_AUDIT_20260729/TRIALS_LEDGER.csv, standing at 466 as of the MA/RSI row): **466+15=481**.
Bonferroni bar at m=481: p < 0.05/481 ~ 0.000104 (materially unchanged from the 0.000107 bar
already in force — this mine does not meaningfully move the firm's multiple-testing burden).

## Method (locked)
- **Split**: build 2021-05..2025-12, forward 2026-01..2026-06 HELD OUT (reported, never
  selected on). VIX truncates the forward window at 2026-05-14.
- **Entry**: next 1-min spot bar's OPEN strictly after the signal bar CLOSES. No same-bar fill.
- **Horizon**: reuses the EXACT machinery already reviewed for this exact data
  (`EMA_INTRADAY_BUYING_20260729/stage1_signal_test.py` + `signal_budget/measure_signal_budget.py`:
  `load_spot`, `resample`, `nw_tstat`, `forward_stats`, horizons {15,30,60,120,to-15:25}, best
  horizon = argmax(mean_pct) per cell — **the TRIALS_LEDGER already logs this as a 5x
  sub-trial multiplier per named cell (23 cells -> 115 sub-trials)**; this mine's 15 named
  cells are therefore honestly 15x5=75 sub-trials for DSR/PBO accounting, stated here so no
  later synthesis undercounts it the way the original 23-trigger prose once did.
- **Placebo**: reuses the SAME random-day placebo already reviewed (`stage1_signal_test.py:
  placebo()` — same count/time-of-day/direction mix, random day reassignment, N=200 draws,
  fixed seed 20260730). Placebo p = fraction of placebo draws at least as extreme as the
  observed mean. This is a HARD KILL per the task's binding method, not a soft/tiering stat.

## HARD KILLS (pre-registered, non-negotiable, per task's binding method)
1. Fails its own placebo (p >= 0.10 two-sided on the best-horizon mean).
2. Any lookahead / same-bar fill (structurally excluded by the entry rule above; verified by
   `assert_next_bar` from `lib/guards.py` before any cell is reported).
3. >30% of total signed edge from one trade/day (`largest_day_share` from the reused
   `summarize_cell`, same field already computed today).
4. maxDD > 25% (Stage-2 option P&L only — Stage-1 is spot-move measurement, no equity curve).
5. Fills on zero/near-zero option volume at the selected 0.40-0.80-delta strike (Stage-2 only;
   require volume>0 on both entry and exit bars for the traded contract, and report the
   volume distribution of selected legs so 1-2-lot fills are visible, not just gated).

## SOFT (sets tier only, never kills): t-stat / Bonferroni / DSR/PBO.
Tier labels: CERTIFIED / FORWARD-TEST CANDIDATE / UNDERPOWERED-UNRESOLVED / DEAD.

## Stage-2 promotion bar (compute budget discipline, not a hard kill)
A Stage-1 cell proceeds to the FULL option-buying simulation (delta-band strike selection,
real 1-min option P&L, hard stop, CAGR/maxDD) only if it clears its OWN placebo (hard kill
above) **and** shows a best-horizon mean signed edge >= +2.0 NIFTY points in the empirically
discovered trade direction (half of the ~4pt theta/cost-plausibility floor implied by this
week's cost work — a low bar for "worth the compute", not a certification bar). Cells that
fail this are reported in the Stage-1 table only (all 15 reported regardless, per "report ALL
buckets, not just the profitable ones").

## Stage-2 option-buying construction (locked)
- **Strike/delta**: Black-Scholes delta, hand-vectorized (numpy + scipy.stats.norm; per
  `options-python-libs` skill, py_vollib_vectorized is broken on this stack — never used).
  sigma = same-day India VIX level /100 (session-level, real measured IV proxy, never an
  assumed constant — per this mandate's METHOD LAW). T = calendar days to the nearest 0-7DTE
  expiry /365, floored at 1 trading hour to avoid a T->0 blowup on expiry day. r=0. Select the
  strike whose |delta| falls in [0.40,0.80], nearest to 0.60 if multiple qualify. CE if the
  cell's empirical direction is bullish, PE if bearish.
- **Entry**: option's OWN next-1-min-bar OPEN after the spot signal bar closes (same no-same-
  bar rule applied to the traded instrument, not just the spot proxy).
- **Exit — ENDPOINT convention (exact, no favourable intra-bar resolution)**: hard stop-loss at
  35% of entry premium, checked against each bar's LOW (long option, so a low breach = adverse
  = correctly conservative, no ambiguity to resolve in our favour); if not stopped, exact-
  endpoint exit at the fixed 60-minute mark's CLOSE (or 15:25 close if 60min would spill past
  session end). No profit target -> no stop-vs-target same-bar ambiguity to adjudicate.
- **Costs**: 1.67 premium points round trip (Rs25/lot/side + slippage, per this task's cost
  spec), lot=65. Subtracted from every trade's point P&L.
- **Capital/CAGR convention** [OPINION, stated explicitly — no standing dynamic-margin rule
  exists for NAKED LONG buying, only for short structures]: 1 lot/trade fixed sizing (rupee
  outlay is inherently dynamic since it scales with the day's actual premium); capital base =
  3x the 95th-percentile single-trade premium outlay actually observed on BUILD, sized so a
  100%-premium-loss single trade cannot itself exceed ~33% of capital. maxDD reported against
  this base, in both % and rupees.
- **Costs/era/held-out reporting**: exclude scheduled event days (elections/budget, same list
  used all week) as a secondary reported cut, not a selection step; report pre-Oct-2024 /
  post-Oct-2024 splits; report 2026 H1 held-out, never selected on.

## Principal's scoring bar (restated, unchanged)
median trade profit > +5 pts AND RR (avg win / abs(avg loss)) >= 1.5. A clean NO is fully
acceptable and expected — the honest prior says most of this will fail; the task is to MEASURE
it properly, not to find a way to pass it.

## RAM discipline (binding, this machine has ~2.6-3GB free of 15.6GB, has segfaulted 3x today)
Feature extraction (150_*) reads ONLY the columns needed (timestamp/strike/option_type/volume/
open_interest) via `pyarrow.parquet.read_table(path, columns=[...])`, never `chain.load_expiry`
directly (its internal `drop_duplicates` on the full 12-column frame is the exact call that
MemoryError'd job 140 today at expiry ~176/257). No `pivot`/`unstack` on per-minute-per-strike
data (the exact op that also crashed inside pandas' pivot_table this morning) — every
aggregation here is groupby+agg on progressively smaller intermediate tables. Explicit
`del df; gc.collect()` after every expiry; retry once after a 2s pause on MemoryError, then
skip-and-log (never silently drop — skipped expiries are counted and reported).
