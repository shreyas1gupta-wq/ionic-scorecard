# PRE-REGISTRATION — ARM 1 (BULLISH SWEEP x DTE x MONEYNESS), option-buying expression

**Written BEFORE any backtest cell was executed.** Firm order D-035. Nothing below is
edited after results are seen; amendments, if any, are appended at the bottom with a
timestamp and a reason, never by rewriting the original text.

- Author: DESK-100 subagent (Arm 1)
- Date: 2026-07-29
- Output dir: `Shreyas_Ionic_AMC/04_RND_LAB/results/OPTION_BUY_ARMS_20260729/bullish-sweep-dte/`
  (the orchestrator handed me the literal path `undefined/OPTION_BUY_ARMS_undefined/...` —
  a string-interpolation bug in the calling script. I used the firm's
  `04_RND_LAB/results/<NAME>_<YYYYMMDD>/` convention instead.)

## 1. Question

The spot-level signal budget measured earlier today says `sweep_priorday_reclaim` carries
**+0.0560% / 10.03 pts / t=3.10 / n=1775 / conc=0.13** of signed forward move, the only
trigger in the family that clears the ~6.5-pt futures round-trip cost bar. Futures
expression of the *EMA* family was already killed today (costs 2.6x gross edge).

Question for this arm: **does a LONG SINGLE-LEG OPTION expression of the sweep trigger pay
after real 1-min option fills and binding COST_STANDARDS costs — and does the answer depend
on DTE?** The Principal's hypothesis under test: a "trend catcher" needs a different DTE
than a short "bull pulse". We test it by holding the exit rule fixed and moving DTE.

Method law (Principal, this session): **no formula proxy for required move.** Every rupee
below is measured on real 1-min option prints via the shared validated harness. No IV is
assumed anywhere.

## 2. Data and windows (frozen)

- Spot: `hf_index_options_1m/index/NIFTY.parquet`, pre-open 09:00-09:07 bars removed (landmine #2).
- Options: `hf_index_options_1m/options/NIFTY/{expiry}.parquet`, 261 valid weekly expiries.
  `2023-06-29` corrupt and `2026-06-09` stub are excluded by `chain.build_expiry_index()`.
- **BUILD = 2021-05-24 .. 2025-12-31.** All selection, all ranking, all judgement happens here.
- **FORWARD = 2026-01-01 .. 2026-06-30, HELD OUT.** Reported, never selected on. Not looked
  at until every build cell is finished and written to disk.

## 3. Signal generation (reused verbatim, not re-implemented)

`sweep_signals()` copied unmodified from
`04_RND_LAB/results/EMA_INTRADAY_BUYING_20260729/signal_budget/measure_signal_budget.py`
(with its `load_spot`, `resample`, `clip_entry_window` dependencies from
`stage1_signal_test.py`). 15-min bars, per-day state, entry window 09:20-14:30,
PIT-safe intraday reference (`cummax().shift(2)`).

- **T1 = `sweep_priorday_reclaim`** (primary; measured t=3.10, n=1775 on build)
- **T2 = `sweep_intraday_continue`** (secondary; measured t=2.94, n=5836 on build)

`t` passed to the harness = the SIGNAL BAR's own stamp. The harness fills at the first
option bar strictly after it (`entry_rule="next_bar"`). No pre-shifting, no same-bar fill.

## 4. Grid — EXACTLY the cells the orchestrator specified, no expansion

Per trigger: **DTE {0-1, 2-3, 4-7} x offset {2 ITM, 1 ITM, ATM, 1 OTM} x exit {A, B, C} = 36 cells.**

- offsets in harness moneyness convention: `-2` = 2 ITM, `-1` = 1 ITM, `0` = ATM, `+1` = 1 OTM.
  (Harness limitation #9: the legacy `engine_swing.py` sign is inverted and every published
  `*_ITM2` number in `intraday_options_strategy/buying/REPORT.md` is really OTM. Not copied.)
- exit A `flat1525`: no target/stop/trail; flat at 15:25 same day.
- exit B `stop35_tgt100`: `stop_pct=0.35`, `target_pct=1.00`; else flat 15:25 same day.
- exit C `trail35`: `trail_pct=0.35`; else flat 15:25 same day.
- All three intraday (`max_hold_days=0`), so the DTE gradient is read at CONSTANT holding
  period — that is the clean experiment.
- `expiry_handling="trade_out"` (harness limitation #1): required so the DTE 0-1 bucket's
  0DTE signals are squared off at a real 15:25 print instead of a zero-time-value settlement.
- `allow_opposite_signal_exit=False` everywhere, so the exit is exactly the three specified
  rules and nothing else.
- `lots=1` everywhere, so per-trade % returns are comparable across cells (harness
  limitation #5: lot_size is pinned at 75 for 2021-2026, so absolute rupees are a SCALED
  quantity; `ret_pct_net` is the trustworthy metric).
- Costs: harness default `cost_model="cost_standards"` (STT 0.1% sell-side premium, exch
  0.035%, brokerage Rs.20/order, GST 18%, stamp, SEBI) — binding D-021. Slippage 0.5%/leg
  with dynamic 1x/2x/3x bar-volume tiering, `slippage_min_rs=0.05`. `exclude_zero_volume=True`
  (a zero-volume bar is NOT a fill). `max_entry_lag_min=5`.

**SECONDARY, separately labelled family (multi-day probe, 12 cells, T1 only):** exit C
`trail35` with `max_hold_days=5` and `expiry_handling="settle_intrinsic"`, across
DTE {0-1, 2-3, 4-7} x offset {-2,-1,0,+1}. Reason stated up front: exits A-C as listed are
all intraday, so the listed grid cannot by itself distinguish a multi-day "trend catcher"
from an intraday "pulse". This probe is the minimum needed to answer the Principal's actual
question. It is NOT part of the primary grid, is reported separately, and IS counted in the
honest trials total.

**HONEST TRIALS = 36 (T1) + 36 (T2) + 12 (T1 multi-day probe) = 84 build cells.**
Multiplicity bar for reference: Bonferroni-adjusted 5% two-sided t threshold at 84 trials
is |t| ~ 3.35; the expected maximum |t| of 84 pure-noise cells is ~2.9. Any winner with
build t below ~3.0 must be treated as selection noise, not an edge.

## 5. PASS BAR (all four must hold — pre-registered, verbatim from the orchestrator)

A cell PASSES only if:

1. **P1 net-positive** — `net_total > 0` on BUILD after real costs.
2. **P2 sign does not invert out of sample** — FORWARD (2026 H1) `net_total >= 0`.
3. **P3 not concentrated** — no single trade contributes > 30% of gross profit
   (`top1_profit_share <= 0.30`).
4. **P4 fills credible** — `zero_vol_entry_frac <= 0.02` AND `thin_entry_frac <= 0.20`
   AND `fill_rate >= 0.80`.

Supporting statistics reported for every cell but NOT used as hard gates (per the firm's
power-aware re-screen rule: low t at small n is not evidence of no effect):
per-trade `ret_pct_net` mean and t, gross vs net separately, PF gross and net, win rate,
months-positive on GROSS and on NET separately, max drawdown, exit-reason mix, entry lag.

## 6. VERDICT MAPPING (fixed now)

- **KILLED** — zero cells satisfy P1, or every P1-positive cell fails P2/P3/P4, or the best
  build cell's t is below the noise bar (~3.0) AND its forward net is <= 0.
- **SURVIVES_NEEDS_VERIFY** — at least one cell satisfies P1+P2+P3+P4. Not a certification:
  it goes to red-team / sensitivity / OOS-audit next, never to capital.
- **INCONCLUSIVE_DATA** — a data defect (not an economic result) prevents measurement of the
  grid; must be named specifically.

## 7. Anti-cheat commitments

- No parameter is changed after seeing a result. If a cell disappoints, it is reported as
  it ran. Any deviation forced by a bug gets an appended amendment with a reason.
- Build cells are ALL run and written to disk BEFORE the forward set is executed.
- A negative outcome is a valid, reportable outcome and will be stated plainly, not softened.
- Every number in SUMMARY.md is computed; nothing is estimated or filled in by hand.
  A genuinely undefined metric gets an explicit sentinel plus an explanation.
- Tags: [DATA] measured, [INFERENCE] derived, [OPINION] judgement.

## 8. Engineering deviation declared in advance (affects speed, not results)

To make 84 x ~2000-6000 signals feasible, the harness's 2-entry expiry LRU is replaced by a
process-global store, and each expiry frame is pruned to strikes within +/-300 points of that
expiry's own spot range before caching. The largest strike this grid can ever request is
2 steps = 100 points from an intraday ATM, so the pruned frame provably contains every
strike the grid can select (plus a full step of slack for nearest-listed snapping).
**This is validated, not assumed:** one full config is run through the unmodified harness and
through the patched store, and the two trade tables must match on every column. If they do
not match, the patch is discarded and the grid runs slow. Result recorded in `PATCH_PARITY.txt`.

---
## AMENDMENTS (append-only)

**A1 (2026-07-30, before any grid cell ran) — my parity TEST was wrong, not the patch.**
The first version of `run_parity.py` compared columns with
`xa.astype(str) != xb.astype(str)`. Under pandas' NA-aware string dtype that comparison
PROPAGATES NA, so every missing-vs-missing cell counted as a difference. The test therefore
reported 11 failing columns and "PATCH REJECTED" while the underlying tables were in fact
identical (`status` matched on every row and `max|net_pnl A - net_pnl B| = 0.0`, verified in
`dbg.py`). I fixed the comparator (missing values collapsed to a `<MISSING>` sentinel plus an
explicit missing-pattern check) rather than the store. Recording it here because the honest
sequence was fail -> diagnose -> the test was at fault, and that is exactly the kind of step
that must not be silently rewritten. Corrected result: **A vs B and B vs C both PASS, all 42
columns identical, exact 0.00e+00** (`PATCH_PARITY.txt`).

**A2 (2026-07-30, before any grid cell ran) — cache pruning changed from a price band to an
exact strike set, for memory not for results.** The originally-described "+/-300 point band"
held ~60% of every expiry file and the machine (15.6 GB total, ~3 GB free) segfaulted on it.
Replaced with a pruned set built from the signals themselves: for every signal, the ATM
+/- 4 strike steps (200 pts), unioned per expiry (~19 strikes/expiry). The grid can never
request more than 2 steps from the ATM, so the cached set still provably contains the exact
strike every cell selects, with 2 spare steps for the harness's nearest-listed snap. Proven,
not argued: `PATCH_PARITY.txt` (intraday) and `verify_probe_chunk.py` (multi-day, across a
year boundary) both show exact equality with the unmodified harness.

**A3 (2026-07-30, before any grid cell ran) — a machine limit must never become a data point.**
A smoke run produced one `expiry_read_error:MemoryError` reject, i.e. a failed parquet read
silently masquerading as an untradeable signal. The store now retries such a read after
evicting and collecting, and `run_grid.py` raises rather than reporting any cell whose reject
tally contains a `expiry_read_error:*` entry. Grid runs confirm `mem-retries 0`.
