# PRE-REGISTRATION — intraday NIFTY 50 option BUYING, corrected-cost re-test
Written 2026-07-30, BEFORE running `130_intraday_optbuy.py`. Owner: Arjun Rao (Head of Quant).
D-035 binding: kill criteria fixed here are NOT revisited after seeing output.

## Why this run is legitimate (not a re-run of the ~17 prior kills)
Two things changed since the 2026-07-01 REPORT.md and 2026-07-29 EMA kill: (1) the Rs25/lot/side
cost model replaces the retracted "0.30-0.50% breakeven" heuristic — theta, not commissions, is now
the binding constraint; (2) `sweep_priorday_reclaim` (10.03 pts/trade, t=3.10, n=1775 on SPOT) was
never priced through real 1-min OPTION P&L. Everything else here is confirmatory, not exploratory.

## PRIOR (stated up front, per D-035 honesty rule)
Two independent pieces of evidence make a NO the expected outcome, not a null default:
1. `FINAL_RANKING_20260730/recency_screen.csv`: `sweep_priorday_reclaim`-family PF is 1.48
   (t=5.58) pre-Oct-2024 vs **0.99 (t=-0.06) Oct-2024-onward and 0.96 (t=-0.22) in 2025 alone**,
   measured on the SPOT/futures expression. Options cannot resurrect a signal that is flat on the
   underlying — they only add theta and friction on top of it.
2. `REPORT.md` (2026-07-01) and `EMA_INTRADAY_BUYING_20260729/SUMMARY.md` killed ~14+3 other
   intraday buying structures on MFE/MAE~1.0 (no convexity) and coin-flip hit rates.
**Consequence: the era-split (pre-Oct-2024 vs Oct-2024-onward vs 2025-only) is a HEADLINE result,
reported for every cell, not an appendix.** If the option version shows a strong POOLED result
driven by 2021-2024 while 2024-10+ is flat/negative, the verdict is DECAYED, not tradeable — the
pooled number must not be quoted as the strategy's live edge.

## DATA / WINDOWS (fixed by Principal instruction, superseding the initial "2019" ask)
- **BUILD: 2021-05-24 -> 2025-12-31** (full extent of the intraday-capable 1-min option tree).
  March-2019 is impossible for intraday option P&L: the 1-min option tree starts 2021-05-27;
  bridging with daily bhavcopy would fabricate intraday fills the data cannot support. Stated,
  not silently skipped.
- **Sub-splits inside BUILD, reported for every surviving cell:**
  (a) 2021-05-24 -> 2024-09-30 (pre-SEBI-tightening)
  (b) 2024-10-01 -> 2025-12-31 (post-tightening)
  (c) 2025-01-01 -> 2025-12-31 (2025 only, inside (b), flagged separately per recency screen)
- **FORWARD / HOLDOUT: 2026-01-01 -> 2026-06-03.** Reported, never used to pick a cell, exit, DTE
  band or strike. Its n will be computed and its statistical power stated explicitly (not asserted).

## SIGNALS (reused verbatim from `EMA_INTRADAY_BUYING_20260729/signal_budget/measure_signal_budget.py`
so results stay comparable — same functions, same clip window 09:20-14:30, same 15-min/5-min bars)
1. **PRIMARY: `sweep_priorday_reclaim`** (`sweep_signals(bars15)["priorday_reclaim"]`) — 10.03 pts,
   t=3.10, n=1775 build (spot). Gets the full pre-registered grid below.
2. `sweep_intraday_continue` (`sweep_signals(bars15)["intraday_continue"]`) — 6.52 pts, t=2.94.
3. `volbrk_orb_volfilter` (`orb_vol_filter(bars5)`) — 5.60 pts, t=2.23.
4. `supertrend_15min_ATR10_x3` (`supertrend_flips(bars15, 10, 3)`) — 8.65 pts, t=2.30, thin n=156.
5. **FADE of `sweep_intraday_reclaim`**: same detector, `dir` column negated (original continuation
   dir was t=-3.64, significantly inverted -> the fade is the tradeable side per the standing
   reverse-the-strong-negative rule).
Signals 2-5 get ONE confirmatory cell each (anchor config, not a grid) — they are secondary leads,
not the primary hypothesis, and a full grid on each would blow the trials budget for no
proportionate information gain.

## INSTRUMENT / GRID (pre-registered, ≤3x3 core per Arjun Rao's charter, NOT tuned after running)
- Weekly/next-week expiry only, selected via `chain.nearest_expiry(day, min_dte, max_dte)`.
- Strike offsets (harness convention: +N = N steps OTM, -N = N steps ITM, both CE/PE):
  **ITM4 (-4, ~200pt ITM) / ATM (0) / OTM4 (+4, ~200pt OTM)** — the full extent of the Principal's
  +/-200pt band, chosen at the edges for maximum delta/theta contrast (ITM has the least-explored,
  highest-delta/lowest-theta% corner per the brief).
- DTE bands: **0-1 / 2-4 / 5-10** (the full range the 1-min tree holds).
- **Core grid for the PRIMARY signal: DTE(3) x STRIKE(3) = 9 cells, ANCHOR exit** (trail_pct=0.35,
  stop_pct=0.50 safety floor, allow_opposite_signal_exit=True, no fixed target — "trailing beats
  fixed targets" is an established lesson, carried over rather than re-litigated).
- **Exit-sensitivity sweep for the PRIMARY signal, at the anchor cell (DTE 2-4, ATM), 5 more cells:**
  trail25 (trail_pct=0.25), trail50 (trail_pct=0.50), hardstop30 (stop_pct=0.30 only, no trail),
  hardstop40 (stop_pct=0.40 only, no trail), delta1-only (allow_opposite_signal_exit=True,
  stop_pct=0.60 safety floor only, no trail/target).
- Primary total: 9 + 5 = **14 cells.**
- Secondary signals (2-5 above): 1 cell each at ATM / DTE 2-4 / anchor exit = **4 cells.**
- **SANITY re-check** (mandatory before trusting any positive result): re-run the harness's
  random-entry control (>=1500 random intraday timestamps, uniform 09:20-14:30, random direction)
  under THIS EXACT cost model (Rs25/lot/side via `BROKERAGE_PER_ORDER=25`, ATM, DTE 2-4, anchor
  exit). PASS = net P&L < 0. FAIL = harness/cost bug, STOP, do not trust any other cell = **1 cell.**
- **TOTAL PRE-REGISTERED TRIALS THIS STUDY: 19.** All 19 enter the trials ledger
  (`OVERFIT_AUDIT_20260729/TRIALS_LEDGER.csv`) regardless of outcome.
- All exits: flat by 15:25 (`squareoff_hhmm="15:25"`, `max_hold_days=0` — intraday only, per
  mandate; the DTE axis selects WHICH expiry's premium is bought, not a multi-day hold).
  `expiry_handling="trade_out"` so a 0-1 DTE cell still gets a genuine 1-min traded exit at 15:25
  rather than riding to expiry-intrinsic settlement (this is real 1-min HF data, not a bhavcopy
  settle print, so landmine #9 does not apply to this choice).

## COSTS (Principal-supplied, authoritative)
`opt_pl.OptCfg(cost_model="cost_standards")` with the module global `BROKERAGE_PER_ORDER`
monkey-patched from Rs20 -> **Rs25** before any call (matches "Rs25/lot/side" exactly). Slippage
left at the harness default (`slippage_pct=0.005`, `slippage_mode="dynamic"`, i.e. COST_STANDARDS'
2x/3x thin-bar stress) — this already IS the firm's 2x-stress convention on top of the base
Rs25/side + STT/exch/GST/stamp, so no further manual stress multiplier is layered on. Reported:
avg all-in round-trip cost in premium points per cell, for comparison against the ~1.2-1.7pt
Principal estimate.

## KILL CRITERIA (fixed now; a clean NO on all of these is a fully acceptable, EXPECTED result)
A cell is a candidate ONLY if ALL of:
  K1. NET P&L > 0 pooled over BUILD, AND net P&L > 0 separately in BOTH the pre-Oct-2024 AND the
      Oct-2024-onward sub-split (a pooled-only positive with a dead recent half = DECAYED, not a
      pass — reported as such, not quoted as the headline).
  K2. Newey-West t-stat on daily net P&L >= 2.0 in the POOLED build.
  K3. Largest single trade's share of total net profit <= 30% (else FRAGILE).
  K4. >= 30 filled trades in the cell (per-parameter trade-count floor, Arjun Rao's charter).
  K5. The random-entry SANITY control (above) still nets negative.
Any cell failing K1-K5 is reported as KILLED for that cell, not softened. A candidate clearing all
five is NOT a certified strategy — it is a forward-test nomination requiring DSR/PBO with the
firm's full cumulative trial count, red-team review, and the held-out 2026H1 confirmation before
any further step.

## REPORTING (non-negotiable, per Arjun Rao's charter + this mandate)
- GROSS and NET always reported separately, monthly win-rate on both.
- CAGR and maxDD ALWAYS reported as a pair, with the explicit leverage (capital deployed in
  premium, concurrent positions, worst-day loss as % of capital) behind any CAGR claim.
- Full return distribution: hit rate, median, skew, p95, max trade, largest-trade profit share.
- Fill/reject-reason breakdown (nothing silently dropped).
- Honest trials count carried into `OVERFIT_AUDIT_20260729/TRIALS_LEDGER.csv`.
