# PREREG — Inverse-VRP Niche (the only place an option BUYER can structurally win)
**R&D Head: Aditya Verma | 2026-07-29 | pre-registered BEFORE any result is seen**

Premise under test: an option buyer loses on average because IV > RV (VRP). No directional
indicator fixes that (proven today, 17/17 trials dead, MFE/MAE≈1.00). The buyer wins ONLY where
**RV_realized(entry→exit) systematically exceeds IV_priced(entry)**, net of costs. This document
finds — or rules out — that condition, measured from REAL option prices only (Principal's method
law: no heuristic required-move formulas).

Split: build = 2021-05-24..2025-12-31. Held out = 2026-01-01..2026-06-03 (reported separately,
nothing selected on it). Costs: COST_STANDARDS (D-021) via the validated shared harness
`OPTION_PL_HARNESS_20260729/opt_pl.py` (real 1-min fills, dynamic slippage, zero-vol-bar = no fill).

## Common construction (niches 1 & 2)
Daily ATM IV: nearest expiry with 1≤DTE≤8 (skip 0DTE — avoids pin/last-day distortion), ATM
strike = round(spot/50)*50 at last available bar ≤15:25 IST. Straddle price = CE_close+PE_close
at that bar. IV backed out via Black-Scholes inversion (Brent's method) on
BS_call+BS_put = straddle_price, flat r=6.5% [INFERENCE — repo-rate proxy, index has no dividend
term needed for this]. This is a genuine IV BACKOUT from real traded prices, not a formula proxy.
Daily 10-day realized vol: annualized stdev of daily log spot returns, trailing 10 sessions.
Percentiles: EXPANDING window, day t's percentile computed from ONLY days <t (no lookahead),
min 60 prior obs before any percentile is defined.
Trade construction (both niches): BUY 1×ATM CE + 1×ATM PE of the reference expiry (synthetic
long straddle — the direct, direction-free test of "is cheap vol actually cheap"). Entry fills at
the next 1-min bar's open after the signal (opt_pl `entry_rule="next_bar"`). No stop/target (we
want the full realized-move outcome, not a truncated one). Hold to expiry, cash-settled at
intrinsic if still open (`expiry_handling="settle_intrinsic"` — legitimate here, this IS a
hold-to-expiry structure). `no_overlap=True` per leg-stream (skip a new signal while a prior
trade from this test is still open). cost_model="cost_standards", slippage_mode="dynamic".
Directional overlay (buy per a trend filter) is explicitly SKIPPED — trend/EMA direction calls
were killed today (K-001, 17/17); re-running the same direction call under a vol-conditioning
label would just re-litigate a closed question and inflate this family's trial count for free.

## NICHE 1 — IV-percentile trough (Q2 of the 2026-07-29 ROADMAP, executed for real this time)
Cells (3): (a) BASELINE — unconditional, every trading day is a signal (shared with Niche 2).
(b) BOTTOM decile — iv_pct ≤10. (c) TOP decile — iv_pct ≥90.
**PRE-REGISTERED KILL:** bottom-decile straddle NET mean pts/trade ≤ 0 → KILL (cheap-IV entries
lose money outright). **KILL (ordering test):** top-decile NET mean ≥ bottom-decile NET mean →
KILL (the percentile has no discriminating power — cheap and expensive IV pay the same).
**SURVIVE (Q5 candidate):** bottom-decile NET mean > 0 AND > baseline AND > top-decile. t-stat is
reported but NOT a hard gate at this n (per the firm's low-t power-aware convention) — a
directionally-correct, economically material effect at low t is a forward-test candidate, not a
kill, but a NEGATIVE or wrong-ordering effect at any t is a kill.

## NICHE 2 — Post-compression expansion, REALIZED vol trough (multi-day, not the killed intraday
Keltner version)
Cell (1, new — reuses Niche 1's baseline): rv_pct ≤10 (trailing-10d realized vol in its own
bottom decile) → same straddle construction as Niche 1.
**PRE-REGISTERED KILL:** RV-trough NET mean ≤ 0, OR RV-trough NET mean ≤ baseline → KILL (pure
historical calm, independent of whether IV was cheap, does not identify a buyable edge — RV
mean-reverting off a compressed base is not sufficient if IV re-prices concurrently, exactly the
ROADMAP's tautology warning).
**Cross-check (not a separate trial):** correlation / overlap between Niche 1's bottom-decile set
and Niche 2's RV-trough set — tells us whether IV-cheapness and RV-calm are the same information
or genuinely different signals.

## NICHE 3 — Overnight tail BUY (mirror of NS-1, which killed the SELL side 2026-07-25)
Population: every NIFTY weekly-expiry night, D−1 last bar ≤15:25 → D0 first bar ≥09:15, full
2021-05→2026-06 sample (n≈258-259, same population as NS-1 for direct comparability).
5 cells: strike distance d ∈ {0% (ATM), 0.5%, 1.0%, 1.5%, 2.0%} OTM, BUY 1×CE(d)+1×PE(d) (long
strangle/straddle), dynamically rounded to the nearest 50-pt step off THAT night's spot (not a
fixed step count — spot roughly 60% higher in 2026 than 2021, a fixed step count would drift the
effective % across the sample). Exit at D0's first bar ≥09:15 via `opt_pl.round_trip_costs`
(same cost engine, `expiry_handling="trade_out"` so a night landing on expiry eve doesn't get
diverted into intrinsic settlement — we need the REAL traded open-print, not intrinsic, to keep
the exit timing honest).
**PRE-REGISTERED KILL:** net pts/night ≤0 at EVERY d → KILL.
**PRE-REGISTERED FRAGILITY GATE (not a kill, a mandatory disclosure):** if net >0 at some d, report
top1_profit_share = single best night's net P&L ÷ total positive net P&L. **>50% → label the
result a lottery ticket, not a strategy, with the number attached, regardless of the sign of the
mean.** ≤50% AND net>0 → genuine convexity finding, flag for Q5 Gate-4.

## NICHE 4 — Scheduled-event windows
**Checked before running anything:** `05_DATA_OFFICE/DATA_CATALOG.md`, `05_DATA_OFFICE/` file
listing, and a repo-wide search for rbi/mpc/fomc/budget calendar files. **No D-009-verified PIT
macro-event calendar (RBI MPC dates, Union Budget dates, FOMC dates) exists on disk for NIFTY.**
`datasets/earnings_pit/` is single-stock earnings — not an index-level scheduled-event calendar,
and the ROADMAP's `board_meetings_all.json` is corporate-action-level, not macro. Per the task's
own instruction: **SKIP the main test rather than fabricate a calendar.** Sourcing RBI's official
MPC calendar would be a new external source requiring D-009 verification — out of scope for this
arm, flagged for Kavya Reddy as a data-catalog gap, not solved here.
**Zero-new-data bonus check (descriptive only, NOT a kill/confirm trial):** Union Budget day is a
fixed public-calendar fact (always Feb 1 since 2017, no dataset needed) — test the straddle
construction on the 5 Budget days 2022-2026 using data already on disk. n=5 is explicitly
underpowered; reported for completeness, ruled on nothing.

## Trials ledger (this family — NEW family, zero prior trials; distinct from K-001 (17) and
NS-1 (5), per RESEARCH_SOP DSR-honesty)
| # | cell | n(expected) |
|---|---|---|
| 1 | Niche1/2 baseline (all days, straddle) | ~all build+H1 trading days |
| 2 | Niche 1 bottom-decile IV | ~10% of days |
| 3 | Niche 1 top-decile IV | ~10% of days |
| 4 | Niche 2 RV-trough | ~10% of days |
| 5-9 | Niche 3, 5 strike distances | ~258-259 nights each |
| 10 | Niche 4 Budget-day bonus (non-decisive) | 5 |
**= 10 trials pre-registered before running.**
