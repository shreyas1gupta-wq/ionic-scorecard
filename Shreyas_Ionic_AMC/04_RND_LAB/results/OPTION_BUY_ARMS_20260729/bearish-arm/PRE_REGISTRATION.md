# PRE-REGISTRATION — ARM 2: BEARISH NIFTY OPTION BUYING (buy PE)

**Written and frozen BEFORE any P&L was computed.** Firm order D-035 (epistemic conduct),
D-021 (COST_STANDARDS binding), D-028 (lookahead controls).

Author: quant desk agent (DESK-100), 2026-07-29.
Output folder: this folder. (Orchestrator requested `undefined/OPTION_BUY_ARMS_undefined/bearish-arm/`
— a variable-interpolation bug in the calling script; I used the firm convention
`04_RND_LAB/results/<NAME>_<YYYYMMDD>/`.)

---

## 1. HYPOTHESIS UNDER TEST

H0 (the firm's incumbent belief, from `intraday_options_strategy/buying/REPORT.md`):
*"NIFTY drifts up; every bearish signal failed."* — to be **tested, not assumed**.

H1: at least one measured bearish intraday trigger delivers a **net-positive** P&L when
traded as a long NIFTY weekly PUT on **real 1-min option prices**, after binding
COST_STANDARDS costs and dynamic slippage.

Secondary question the Principal asked explicitly: **does index put skew (richer downside
IV) kill the bearish arm even where the raw spot signal is decent?** To be **quantified
from real option prices**, never asserted.

## 2. NO FORMULA PROXIES (Principal's METHOD LAW this session)

No heuristic "required move" formula is permitted. Every P&L number comes from the shared,
independently validated option-P&L harness reading the real 1-min option parquet files:
`04_RND_LAB/results/OPTION_PL_HARNESS_20260729/opt_pl.py`. Where IV is needed (skew
measurement only) it is **inverted out of real traded option prices**, never assumed.

## 3. DATA + SPLIT (frozen)

- Spot: `intraday_options_strategy/datasets/raw/hf_index_options_1m/index/NIFTY.parquet`,
  filtered to 09:15–15:30 (landmine #2, pre-open auction).
- Options: `.../hf_index_options_1m/options/NIFTY/{expiry}.parquet` via `chain.py`.
- **BUILD: 2021-05-24 .. 2025-12-31.** **FORWARD (HELD OUT): 2026-01-01 .. 2026-06-03.**
- Nothing is selected on the forward set. The forward set is reported once, at the end.

## 4. TRIGGERS (bearish subsets only; generators reused verbatim from
`EMA_INTRADAY_BUYING_20260729/signal_budget/measure_signal_budget.py`, indicators computed
PER DAY so no state leaks across sessions; entry window 09:20–14:30)

| id | trigger | bearish definition | measured signed edge (both dirs, prior work) |
|---|---|---|---|
| T1 | `sweep_priorday_reclaim` | rows with `dir == -1` (sweep **above** prior-day high, then close back **below** it) | +0.0560%, 10.03 pts, t=3.10 — strongest family |
| T2 | `supertrend_15m_ATR10x3` | `dir == -1` flips (bull→bear) | +0.0429%, 8.65 pts, t=2.30 |
| T3 | `supertrend_15m_ATR14x3` | `dir == -1` flips | +0.0431%, 9.65 pts, t=1.80 (thin n) |
| T4 | `sr_week_reject` | `dir == -1` (rejection from prior-week high/low/close level) | +0.0206%, 3.98 pts, t=2.00 |
| T5 | `sr_month_reject` | `dir == -1` (rejection from prior-month level) | +0.0243%, 5.37 pts, t=1.53 |
| T6 | `sweep_intraday_reclaim_FADE` | raw rows with `dir == +1`, **traded at −1** | raw family t = **−3.64** (significantly inverted) → the FADE is the tradeable side (firm standing convention: auto-test the reversal of any strongly-inverted signal) |

T6's direction flip is registered HERE, before any option P&L is computed, and is justified
by a build-set spot statistic measured in prior work — not by any option result.

## 5. GRID (frozen — 6 triggers x 3 DTE windows x 3 strike offsets x 2 exit sets = 108 cells)

- DTE windows: **{0–1, 2–3, 4–7}** (`min_dte`/`max_dte`).
- Strike offsets (harness MONEYNESS convention, `strike = ATM + offset*50*direction`):
  **{−1 = 1 step ITM, 0 = ATM, +1 = 1 step OTM}**. For a PE, direction = −1, so
  offset +1 → strike = ATM − 50 (genuinely OTM for a put). Harness limitation #9: this sign
  is the OPPOSITE of the legacy `engine*.py` files, whose published `ITM` labels were wrong.
- Exit sets (matching arm 1 / the harness template):
  - **E1**: `target_pct=0.50`, `stop_pct=0.30`, intraday, flat `15:25`.
  - **E2**: no target/stop, hold to `15:25` (pure signal test, isolates whether the exit
    logic is doing the work).
- `max_hold_days=0` (intraday), `lots=1` (comparable % returns), `allow_opposite_signal_exit=False`,
  `no_overlap=False`, `expiry_handling="trade_out"` (intraday caller — harness limitation #1:
  the default would strip time value from expiry-day trades), `cost_model="cost_standards"`
  (binding D-021), `slippage_mode="dynamic"`, `exclude_zero_volume=True`, `max_entry_lag_min=5`.
- Entry fills at the **next** 1-min option bar strictly after the signal bar
  (`entry_rule="next_bar"`). No same-bar fills.

**Honest trials count for any later DSR/PBO work: 108.** Nothing outside this grid will be
run and reported as a headline result. If I run anything extra it will be labelled
EXPLORATORY and excluded from the pass/fail decision.

## 6. PASS BAR (all four must hold — pre-registered, not to be relaxed)

A config PASSES only if **all** of:

1. **Net-positive after real costs on the BUILD set** (`net_total > 0`), and the per-trade
   net return t-stat is > 0.
2. **Sign does NOT invert on the held-out 2026 H1 forward set** (forward `net_total >= 0`).
   If a config has <5 forward trades the forward test is **INCONCLUSIVE**, stated as such —
   it does not count as a pass.
3. **No single trade > 30% of gross profit** (`top1_profit_share <= 0.30`).
4. **Zero-volume fill fraction low enough that fills are credible**: `zero_vol_entry_frac
   <= 0.02` AND fill rate >= 0.70. (Zero-volume bars are already rejected by the harness;
   this catches a config surviving only on a handful of implausible prints.)

## 7. KILL CRITERIA (pre-registered)

**ARM 2 IS KILLED if:** zero of the 108 configs is net-positive on the build set, OR every
build-net-positive config either inverts sign on the forward set or fails the concentration
/ fill-credibility gates.

A kill is a valid outcome and will be reported plainly, with the mechanism (directional edge
absent vs. edge present but eaten by premium/skew/theta/costs) separated using:
- **frictionless gross** = `(exit_px_raw − entry_px_raw) * qty` (no slippage, no statutory),
- **gross** (post-slippage, pre-statutory),
- **net**.
If frictionless gross is already negative, the failure is directional/theta, NOT the cost
model. If frictionless gross is positive but net is negative, the failure is cost/skew.

## 8. SKEW MEASUREMENT (pre-registered method, empirical only)

For every trading day in the sample, at a fixed 11:00 IST snapshot, on the nearest weekly
expiry with 2–7 DTE:
- take the 1-step-OTM CE (`ATM+50`) and the 1-step-OTM PE (`ATM−50`) — **equidistant** from
  ATM — using their real 1-min closes;
- invert Black–Scholes (Brent, r=0, q=0, T from calendar days/365) on each **real price** to
  get IV_CE and IV_PE;
- report mean/median **IV_PE − IV_CE** and the premium ratio PE/CE.
Then translate to a decision-relevant number: the extra points of favourable move a put
buyer must earn to break even versus a call buyer at the same moneyness distance, computed
from the **observed premium difference**, not from a formula for "required move".
Additionally, at each bearish signal timestamp, the PE actually bought is compared to the
mirror-offset CE at the same timestamp — an exactly matched premium comparison.

## 9. THINGS THAT WOULD INVALIDATE THIS TEST (declared up front)

- lot_size held at 75 across 2021–26 (harness limitation #5) — **rupee P&L is a scaled
  quantity; `ret_pct_net` is the trustworthy metric.** Reported rupee sums are at 1 lot of 75.
- Exits use 1-min CLOSES only; no intrabar touch (harness limitation #3) — conservative for
  targets, mildly optimistic for stops.
- Option data is sparse; fills needing >5 min are rejected. Reject reasons are reported.
- Expiry `2023-06-29` corrupt, `2026-06-09` stub (skipped by `chain.py`); `2026-05-26` and
  `2026-06-02` lack expiry-day spot.
- OI is unusable as a liquidity gate for 2025+ (harness limitation #7) — volume only.

## 10. NO POST-HOC TUNING

Grid, exits, gates, split and kill criteria above are final as of writing. Any deviation
forced by data reality will be recorded as a dated AMENDMENT below with the reason, never
by silently editing the text above.

## AMENDMENTS

### AMENDMENT-1 — 2026-07-29, made BEFORE any option P&L existed, on a P&L-BLIND criterion

Running only the signal generator (`gen_signals.py`, no option prices touched) showed that
the two pre-registered supertrend triggers have **essentially no bearish population**:

| generator | total flips | bull | **bear** |
|---|---|---|---|
| supertrend 15min ATR10 x3 | 170 | 165 | **5** |
| supertrend 15min ATR14 x3 | 84 | 83 | **1** |
| supertrend 5min ATR10 x3 | 1376 | 993 | **383** |

Cause: indicators are computed PER DAY (correctly, no cross-session leak), so on 15-min bars
the ATR warm-up consumes 10 of the ~21 bars inside the 09:20–14:30 entry window and the
per-day initial trend state is bullish in the large majority of sessions. **T2 and T3 are
therefore UNTESTABLE (n=5, n=1), not failing** — they will be run for completeness and
reported as `INSUFFICIENT_N`, and they cannot pass or fail the arm.

Added: **T2b = `supertrend_5m_ATR10x3` bear flips (n=383)**. This trigger was already in the
same prior spot-level measurement table (`supertrend_5m_ATR10x3`, n=1269 both directions,
+0.0236%, 5min bars, t=2.76), so it is not a new degree of freedom discovered in this data.
The decision to add it rests **solely on the signal count above**, which is computed from
spot only and is blind to every option price and every P&L number.

Revised honest trials count: **7 triggers x 3 DTE x 3 offsets x 2 exit sets = 126.**
Everything else in sections 1–10 is unchanged.

### AMENDMENT-2 — 2026-07-29, from a 285-signal Q1-2023 smoke test (P&L of that smoke test
### was seen, but this amendment does not depend on it and does not change any pass threshold)

The gate-4 leg "fill rate >= 0.70" as literally written is **not measuring what it was meant
to measure.** In the smoke test, 177 of 285 signals were rejected with
`no_expiry_in_dte_window`: with only WEEKLY expiries listed, a "2–3 DTE" window simply does
not exist on most calendar days. That is an expiry-CALENDAR fact, not evidence that a fill
was implausible, yet it would have failed every DTE-restricted cell on a liquidity test.

**Correction:** the fill-rate leg of gate 4 is computed as
`tradeable_fill_rate = filled / (signals − no_expiry_in_dte_window rejects)`.
The raw `fill_rate` and the full reject histogram are still reported for every cell.
`zero_vol_entry_frac <= 0.02` is unchanged.

I am flagging explicitly that this makes gate 4 **easier** to pass than the literal
pre-registered text, and that I saw smoke-test P&L before writing it. It is recorded rather
than silently applied, per D-035, and it changes no P&L threshold: gates 1–3 (net-positive
build, forward sign, 30% concentration) are untouched, and those are what decide the arm.
