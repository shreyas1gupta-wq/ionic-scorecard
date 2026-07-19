# PREVIEW — 2025-2026 only, ~18 cycles, ungated (no placebo/lag), NOT CERTIFIED

**Full-history gated run in progress elsewhere — this is a restricted-window speed pass only.**
Mechanics: EXACTLY `PREREG.md` §1-§2 (Cell A two-sided, Cell B bull-only), monthly expiry only.
Window: 2025-01-01 → 2026-06-30 expiry (data available through 2026-07-10; the in-progress
2026-07 cycle is excluded — no expiry data to cash-settle it). **18 complete monthly cycles.**
Skipped per instruction: placebo battery, one-day-lag test, sensitivity grid (kill criteria
#2/#3 from `PREREG.md` §5 are therefore **not evaluated** here — see caveats).

Owner: quant-head-arjun-rao persona. Script: `run_preview_backtest.py` (this folder).

---

## 0. Headline verdict (informational only — not a certified kill/pass)

Both cells are **net-of-cost losers** over this 18-cycle window, at a magnitude far larger than
fees/slippage can explain (total fees: Cell A ₹5,547, Cell B ₹3,263 — i.e., costs are ~2% of the
loss, not the driver). If this sign held under the full battery, **Cell A and Cell B would both
fail kill-criterion #1** (net ROM < 0). This is descriptive, not a certification — see §5 caveats.

## 1. Headline table

| Metric | Cell A (two-sided) | Cell B (bull-only) |
|---|---|---|
| Cycles (complete) | 18 (12 in 2025 @ lot 75, 6 in 2026 @ lot 65) | 18 (same split) |
| **Total P&L — points/lot-unit** | **−4,528.3 pts** | **−1,913.0 pts** |
| **Total P&L — rupees** (illustrative lot 75/65) | **−₹3,06,274** | **−₹1,33,577** |
| Total P&L — 2×-cost stress (rupees) | −₹3,19,107 | −₹1,41,057 |
| **ROM, annualized (geometric)** | **−74.8%** | **−40.4%** |
| ROM, total window (compounded) | −87.4% | −54.0% |
| Return on fixed ₹10L notional (window total) | −30.6% | −13.4% |
| Win-rate by monthly cycle | 8/18 = 44.4% | 6/18 = 33.3% |
| Max drawdown (₹, daily-MTM equity, mixed-lot-era) | −₹4,15,691 | −₹2,25,458 |
| **Worst cycle** | Cycle 16, **2026-04-01→04-28**, entry signal=BEAR, **−₹73,501** | Cycle 7, **2025-06-27→07-31**, entry signal=BULL, **−₹58,538** |
| Bull-entry vs bear-entry cycle counts | 10 bull / 8 bear | 10 bull / 8 bear |
| Avg per-cycle P&L, bear-entry cycles | −₹18,266 (n=8) | −₹2,798 (n=8, mostly cash) |
| Avg per-cycle P&L, bull-entry cycles | −₹16,015 (n=10) | −₹11,119 (n=10) |
| **Bear-side (short-ITM-CE) contribution** | **−₹1,14,832** (14 CE entries) | n/a (no CE exposure by design) |
| Bull-side (short-ITM-PE) contribution | −₹1,91,442 (18 PE entries) | −₹1,33,577 (all 18 entries) |
| Avg entry credit (short leg, per unit) | 505.36 pts (target 500) | 495.53 pts |
| Avg hedge cost (2 lots, per unit) | 144.84 pts | 149.54 pts |
| Avg margin (hedged), per lot-unit | 2,776.0 pts | 2,791.3 pts |
| Avg naked-short margin (12% notional), per lot-unit | 2,920.9 pts | 2,940.8 pts |
| **Margin drop ratio (hedged/naked)** | **0.950** (range 0.918–0.999) | **0.949** (range 0.944–0.953) |

**Worst cycle, what actually happened (Cell A, cycle 16):** entered short ITM-CE on 2026-04-01
at spot 22,679 (VIX spiked to 25.0 that day). The market rallied hard through April — the SAME
move `TRADER_FORENSICS.md` documents real traders profiting from on the CE-BUY side (+162.5% on
their 2026-04-06 entry). Our CE short got run over: closed the flip on 2026-04-22 at 1,754 vs an
entry of 723.70 (already an unusually high entry premium at a shallow 29.4-pt ITM depth — see §4).
The subsequent PE re-entry (bull side, opened same day) then reversed into a sharp pullback into
the April-28 expiry and lost again on settlement. Both legs of the cycle lost — a double whipsaw.

## 2. Deliverables in this folder

- `equity_curve.png` — both cells, daily-MTM (solid) + realized-only staircase (dotted) +
  2×-cost (dashed), with a drawdown subplot below.
- `quick_trade_ledger.csv` — 208 rows, every leg open/close/settle event (entry/exit dates,
  strike, side, premium in/out, ITM/OTM depth, stale-fill flag, fees, cashflow, net & 2×-cost).
- `quick_margin_detail.csv` — 52 rows, per structure-open: K_short, K_hedge, net credit, worst-case
  bound, exchange-style estimate, margin used, naked-margin comparison, drop ratio.
- `premium_itm_depth_mapping.csv` — 52 rows, every entry's (date, side, strike, spot, premium,
  ITM depth, India VIX close).
- `results_bundle.json` — full cycle-by-cycle P&L for both cells, machine-readable.
- `run_log.txt` — full stdout of the run (data lineage, row counts, warnings).

## 3. Data lineage (per DATA_MAP.md, re-verified this pass)

- Spot: `datasets/index_daily/nse_official_all_indices.parquet`, filter `index_name=='Nifty 50'`
  (**note**: DATA_MAP.md's suggested filter value `'NIFTY 50'` does not match this file's actual
  string — it is `'Nifty 50'` [mixed case]; corrected here, re-verified 2026-07-18). 2,599 rows,
  2016-01-01 → 2026-07-16 — covers the window with a 14-month DMA-lookback buffer to spare.
- Options: `Shreyas_Ionic_AMC/05_DATA_OFFICE/data/fo_bhavcopy_hist/fo_idx_{2024,2025,2026}.parquet`,
  filtered `SYMBOL=='NIFTY' & INSTRUMENT=='OPTIDX' & OPTION_TYP in (CE,PE)`. Combined 1,027,199 rows,
  2024-01-01 → 2026-07-10. 2024 included only as DMA/roll-continuity buffer before the window start.
- `is_monthly` flag: DATA_MAP.md §4.1 method (last EXPIRY_DT within its own (year,month) group).
  18 monthly expiries land in [2025-01-01, 2026-07-10]: 2025-01-30 through 2026-06-30. The
  in-progress 2026-07-30 cycle is excluded (no expiry-day data yet to cash-settle it).
- Lot size: **75 for all 2025-expiry cycles, 65 for all 2026-expiry cycles** — per this task's own
  brief, NOT independently re-verified this pass (PREREG.md's only confirmed data point remains
  Apr-2026=65, from `TRADER_FORENSICS.md`'s real-trade quantity multiples). The exact revision date
  is unknown; using expiry-year as the cutover is a labeled approximation. **Primary metrics (ROM,
  10L-notional-illustrative-%, points/lot-unit) are what should be trusted; rupee totals carry
  this unverified assumption.**

## 4. Guards / landmines checked

- **Landmine #1 (expiry SETTLE_PR)**: never read. All 36 expiry-settlement legs (18 cycles × up to
  2 legs held-to-expiry per cell, less the failed cycle-15 entry) cash-settled at
  `max(0, K-spot_close)` / `max(0, spot_close-K)` from the underlying's real close. Confirmed via
  ledger inspection (e.g., cycle 3 cell A: CE short+hedge both settled at intrinsic 0.0, matching
  an OTM-at-expiry outcome, not a garbage SETTLE_PR read).
- **PIT discipline**: 20/50 DMA computed from closes through day *t*, acted at day *t* close — no
  lookahead (per PREREG §2.9, DATA_MAP §6).
- **CONTRACTS>0 liquidity gate**: enforced on every strike search. **Zero stale-fill flags** across
  all 208 ledger rows — every chosen strike traded on its transaction day (consistent with
  DATA_MAP's 83-94% 2025-2026 tradability claim; this preview did not need the untraded-strike
  fallback in normal operation). One exception: **Cell A cycle 15 (2026-02-25) — no ITM-CE strike
  found at all** (band+liquidity filter returned empty), so the structure-open FAILED. That cycle
  is a genuine liquidity GAP, not a flat/neutral outcome — Cell A held **zero exposure** for the
  full Feb25→Mar31 cycle it should have been short-CE for. This is a real data limitation, not
  something to silently smooth over.
- **Cost model**: COST_STANDARDS.md D-021 rates applied per leg per fill (STT sell-side, exchange
  both sides, brokerage/order, SEBI, GST, stamp buy-side, slippage `max(0.05, 0.25%×premium)`
  one-way). 2×-cost stress computed by doubling every component per the standard's "2× ALL of the
  above" definition.

## 5. Caveats (in order of importance)

1. **The single most important caveat**: the weekly-Tuesday-check + 1-trading-day-lag flip
   mechanic, combined with a lagging trend signal (20/50 DMA), structurally forces exits AFTER an
   adverse move has already happened. Every one of the 15 Cell-A flip events in this window closed
   the outgoing short leg at a materially HIGHER premium than its entry (e.g., 504→756, 496→1043,
   512→1513, 724→1754) — i.e., the flip mechanic never once caught a reversal early; it always paid
   for one that already occurred. That is a structural property of this signal/structure pairing,
   not a data artifact — it is very likely the dominant driver of the loss in this specific window,
   more than any single "bad month." The full-history run's placebo+lag battery (skipped here) is
   exactly the right test to confirm whether this pattern is signal-driven or coincidental to
   2025-2026's whipsaw character.
2. **Kill criteria #2 (placebo) and #3 (one-day-lag) are NOT evaluated in this preview** — both are
   explicitly designed to catch exactly the failure mode in caveat #1. Do not treat the negative
   sign here as a certified kill; treat it as a strong prior that the full battery should confirm.
3. **Margin formula barely credits the hedge**: `margin_drop_ratio` ≈ 0.95 means the hedge only
   reduces required margin ~5% vs a naked short, because PREREG's `exchange_style_estimate` (12%
   notional − 2×hedge premium) dominates the true bounded-loss formula (`worst_case_expiry_loss`)
   in every single observed cycle — the structure's real capped-loss economics are never the
   binding constraint under this proxy. A real exchange SPAN engine would likely grant more margin
   relief for a defined-max-loss ratio spread; this is a disclosed simplification (PREREG §2.7), not
   a bug, but it means the reported ROM is understated relative to what real margin efficiency might
   allow, IF the hedge's crash-protection property is real (kill criterion #4, also not run here).
4. **Premium-to-ITM-depth relationship is unstable, not fixed**: targeting a flat "≈₹500 premium"
   realized ITM depths ranging **29.4 to 570.4 points** (mean 336.3, median 351.9, std 166.1 for
   Cell A — well below the intended 300-700 band on the low end in several cycles). The extreme:
   2026-04-01, VIX spiked to 25.0, and a strike only 29.4 pts ITM already carried premium 723.70
   (elevated time-value, not intrinsic) — the nearest-to-target search picked it, landing far
   outside the intended moneyness band. A fixed premium target does not deliver a fixed ITM depth;
   it drifts with IV. (Full mapping: `premium_itm_depth_mapping.csv`.)
5. **A genuine bug was caught and fixed mid-run**: an early version of this script accumulated
   interim daily mark-to-market deltas INTO THE SAME running total as the lump-sum entry/exit
   cashflows, double-counting every holding period's price move. Caught by manually reconciling
   cycle 16/Cell A's ledger cashflows (summed to −₹73,501) against the reported cycle P&L
   (originally −₹137,361). Fixed by making `daily_pnl` realized-cashflow-only (the authoritative,
   auditable source for every headline number) and rebuilding the chart's smoother MTM line as a
   separate overlay that provably nets to zero at every realization event. All numbers in this
   report are POST-fix.
6. Cell A cycle 15 had zero exposure due to the liquidity-gap entry failure noted in §4 — treat
   Cell A's 18-cycle sample as 17 genuine bear/bull decisions + 1 missing observation, not 18 clean
   trials.
7. Lot-size assumption (§3) is unverified for 2025; primary/trustworthy numbers are the points and
   ROM/%% lines in the headline table, not the rupee totals.
8. n=18 cycles is a small sample for any of these point estimates (win-rate, worst-cycle, etc.) —
   this preview does not attempt DSR/PBO/plateau (that's explicitly the full run's job).
