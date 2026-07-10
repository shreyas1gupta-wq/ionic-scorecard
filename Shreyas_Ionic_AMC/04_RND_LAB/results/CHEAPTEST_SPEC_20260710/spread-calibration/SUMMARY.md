# SPREAD/SLIPPAGE CALIBRATION — T5 fill-realism dependency (spread-calibration)
Date: 2026-07-10 | Owner: quant engineer (solo cheap-test) | Type: MEASUREMENT — **no kill threshold pre-registered** (per triage doc, data ask #5: "calibrate penalties vs angel_capture_2026 live captures before trusting 0DTE fills").

## Spec
Estimate effective-spread proxies from trade bars (no quote data exists firm-wide — bid-ask structurally missing per triage data-asks):
- **Part A** — NIFTY weekly index options 1-min (`intraday_options_strategy/datasets/raw/hf_index_options_1m/options/NIFTY/`), 146 of 262 expiry files sampled (ALL 2025-26, every 2nd 2024, every 3rd 2021-23), spot join vs `processed/nifty_1min.parquet` (ends 2026-05-14; later bars auto-dropped).
- **Part B** — Angel LIVE capture (`angel_capture_2026/minute/`), 86 single-stock front-month files, Jun-29 -> Jul-2026; ATM per minute via put-call parity argmin|CE-PE|.
- Proxies: (1) volume-weighted within-minute high-low (upper bound: spread + intraminute drift), (2) Roll(1984) estimator on 1-min traded closes per contract-day (central), (3) median |dClose| (tick-bounce scale). Traded bars only (volume>0); pre-09:15 dropped (guards.drop_preopen); timestamps already IST tz-aware in both sources.

## Part A — NIFTY weekly options, near-money (Roll effective spread, ROUND-TRIP index pts)

| Era | DTE | Bucket | n contract-days | Roll med | Roll p75 | med abs dClose | med premium |
|---|---|---|---|---|---|---|---|
| 2025-26 | 0DTE | ATM | 543 | **2.48** | 3.87 | 1.85 | 38.35 |
| 2025-26 | 0DTE | OTM1-2 | 728 | 1.17 | 2.01 | 0.70 | 13.49 |
| 2025-26 | 0DTE | ITM1-2 | 544 | 3.18 | 4.81 | 2.65 | 71.76 |
| 2025-26 | 1-2DTE | ATM | 752 | 2.20 | 3.81 | 1.85 | 95.96 |
| 2023-24 | 0DTE | ATM | 300 | 1.79 | 3.29 | 1.40 | 35.61 |
| 2021-22 | 0DTE | ATM | 225 | 0.70 | 1.46 | **0.00** | 36.85 |

**One-way** = Roll/2 -> 0DTE ATM ~ **1.24 pts median / 1.93 pts p75** (~3.2% / 5.0% of a Rs38 median 0DTE ATM premium). 2021-22 med|dClose|=0.00 flags stale/repeated prints in the oldest HF era — era trend is partly data-quality; trust the 2025-26 rows.

**Time-of-day (VW high-low per traded minute, 0DTE ATM 2025-26, pts):** open 09:15-30 = 10.7 | morning = 6.1 | midday = 4.7 | afternoon = 5.4 | close 15:00-30 = 3.4 (premium collapsed to Rs2.65 -> 62% of premium). First 15 minutes ~2x the rest of day; last 30 min extreme in %-of-premium terms. HL is an upper bound (contains gamma drift); Roll is the central estimate.

## Part B — Angel live single-stock captures (sanity vs COST_STANDARDS)
86 symbols, front expiry 2026-07-28. Roll round-trip **% of premium: median 1.12%, p75 1.65%** (n=2,993 contract-days) -> one-way ~ **0.56% / 0.83%**. VW HL% (ATM): open 4.7%, morning 2.1%, midday 2.5%, afternoon 1.5%, close 1.8%.
-> **COST_STANDARDS "single-stock near-ATM 0.5-1.5% premium one-way" is VALIDATED by live data** (measured central 0.6-0.8%, inside the band; opening auction window ~1.6x).

## Calibration vs COST_STANDARDS + the 0.5/1/2-pt grid (0DTE NIFTY ATM buys)
| Assumption | One-way pts | vs measured (Roll med 1.24 / p75 1.93) |
|---|---|---|
| COST_STANDARDS index-ATM floor max(1 tick, 0.25% prem) | ~0.10 | **~12x too low for 0DTE ATM** (fine for 3+DTE liquid ATM where premium is large) |
| Grid 0.5 pt | 0.5 | optimistic — below median; acceptable only for 1-2DTE midday resting-limit entries |
| Grid 1 pt | 1.0 | ~ Roll median one-way -> **BASE case** |
| Grid 2 pt | 2.0 | ~ Roll p75 one-way -> **STRESS case** (open 09:15-30, expiry afternoon, market orders) |

## RECOMMENDATION (for T5 0DTE test and any intraday NIFTY option costing)
1. **Use the 1-point grid as BASE one-way slippage, 2-point as the stress leg** of the mandatory 2x-cost promotion test. The 0.5-pt point should be reported but never used for pass/fail.
2. Apply a **2x multiplier on the 09:15-09:30 window** and **avoid/penalize 15:00+ 0DTE entries** (spread = 40-60% of remaining premium; effectively untradeable for buying).
3. COST_STANDARDS' 0.25%-premium index-ATM floor materially understates 0DTE ATM friction (0.10 vs ~1.24 pts). Flag to Tara Singh (Execution/TCA) for a COST_STANDARDS amendment via the D-021 process (post-mortem evidence + Principal sign-off) — **not amended here**; standards remain binding as written, so tests should take max(COST_STANDARDS floor, 1 pt) = 1 pt.
4. Caveat: Roll on 1-min trade closes conflates bid-ask bounce with genuine 1-min mean reversion -> treat 1 pt as central-to-conservative; true quoted spreads on calm minutes are tighter, but 0DTE fills happen disproportionately on fast minutes.

## Verdict
**MEASUREMENT COMPLETE (no kill bar). Recommended slippage point for the 0DTE tests: 1 index point one-way base / 2 points stress.**

## Files
- `spread_calibration.py` — script (guards: drop_preopen, traded-bars-only, IST tz)
- `nifty_spread_by_era_dte_money_tod.csv` — full HL table (era x DTE x moneyness x TOD)
- `nifty_roll_summary.csv`, `nifty_roll_contract_day.csv` — Roll estimator (summary + per contract-day)
- `nifty_recent_atm_hl_table.csv` — 2025-26 ATM/OTM1-2 by TOD
- `stock_angel_spread_by_money_tod.csv`, `stock_angel_roll_contract_day.csv` — live-capture calibration
- `run_log.txt` (first run, Part B crashed on all-NA pivot rows — fixed), `run_log2.txt` (clean full run)

Trial-ledger note: 0 strategy trials consumed (pure measurement, no signal evaluated).
