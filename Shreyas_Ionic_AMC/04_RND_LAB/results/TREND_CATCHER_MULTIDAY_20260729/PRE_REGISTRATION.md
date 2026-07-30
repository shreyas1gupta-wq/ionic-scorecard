# PRE-REGISTRATION — Multi-day "Trend Catcher" Long Options
**Owner:** Arjun Rao (Head of Quant). **Filed:** 2026-07-29, BEFORE any cell was run.
**Rule:** nothing below changes after seeing results. Any deviation is logged in SUMMARY.md as a deviation, not silently applied.

## 1. Objective
Test whether multi-day (8-35 DTE) long CE/PE trend-following options solve the MAGNITUDE
problem that killed every intraday option-buying arm today, and if so, whether they then
fail on PREDICTABILITY (the genuinely open question) or on PROFIT CONCENTRATION (the
documented failure mode of this family: a prior firm multi-day variant had 99.5% of profit
in 4/22 trades and 0% win rate OOS).

## 2. Data (verified 2026-07-29)
- Spot 1-min: `intraday_options_strategy/datasets/raw/hf_index_options_1m/index/NIFTY.parquet`,
  477,738 bars, 2021-05-24 09:07 .. 2026-06-03 15:30 (1,242 trading days). Filter time>=09:15
  for real open (pre-open auction landmine).
- Options 1-min: `.../hf_index_options_1m/options/NIFTY/{expiry}.parquet`, 261 valid weekly
  expiries 2021-05-27..2026-06-02 (corrupt 2023-06-29 and stub 2026-06-09 excluded per `chain.py`).
- Reused as-is: `intraday_options_strategy/buying/chain.py` (`nearest_expiry`, `load_expiry`,
  `load_index`), `engine.py::_costs` + `STEP=50` (Rs25/lot/side cost model, approved D-021 family).
- DTE-bucket coverage check (62 monthly samples, 2021-2026): bucket (8-12 DTE) has an
  available contract on 45/62 sample days (73%); (15-22) on 60/62 (97%); (25-35) on 61/62
  (98%). The (8-12) bucket will show a real, reportable skip rate — not hidden.

## 3. Signals (daily bars built from 1-min spot; ALL indicator math uses only prior-day-closed
information; signal fires on day D's CLOSE, entry is the NEXT session, never same-bar)
Directions: bullish -> long CE, bearish -> long PE. Warmup buffer: first 60 trading days of
loaded spot history (>= 2021-08-17) are reserved for indicator warmup and are NOT eligible
entry dates for the BUILD window, to avoid partial-EMA/rolling-window artifacts.

- **(a) ema_cross**: 50-day EMA of daily close = the trend line (single line, not a dual
  fast/slow cross — the dual-EMA variant is already effectively covered by breakout20's
  20-day horizon, so testing a second EMA pair here would just be a redundant extra axis).
  Bullish: close crosses above EMA50 (close>ema50 today, close<=ema50 yesterday). Bearish:
  mirror image, cross below.
- **(b) breakout20**: close > `rolling(20).max().shift(1)` of prior daily highs -> bullish;
  close < `rolling(20).min().shift(1)` of prior daily lows -> bearish. `.shift(1)` guarantees
  today's own bar never contaminates its own breakout level.
- **(c) sweep_priorweek_reclaim** (daily analogue of the session's strongest intraday trigger,
  10.03pt/t=3.10): weekly swing levels = high/low of the immediately PRIOR completed
  Mon-Fri week (W-FRI period, lagged by exactly one period, never the current week-to-date).
  Bearish: today's HIGH > prior week's high but today's CLOSE < prior week's high (sweep +
  rejection). Bullish: today's LOW < prior week's low but today's CLOSE > prior week's low.

## 4. Instrument / grid
- **Expression:** long CE (bullish) / long PE (bearish) only, single leg (no spreads — keeps
  this arm's economics comparable 1:1 to the intraday kills, which were single-leg).
- **DTE buckets** (via `chain.nearest_expiry(entry_day, min_dte, max_dte)`, no rolling — see
  §6): (8,12), (15,22), (25,35).
- **Strike:** ATM = `round(spot/50)*50`. For CE, ITM1=ATM-50, OTM1=ATM+50. For PE (mirrored
  moneyness), ITM1=ATM+50, OTM1=ATM-50.
- **Entry:** next session, 09:20 fill = option's first 1-min bar >= 09:20, OPEN price,
  +0.5% slippage (same convention as `engine_swing.py`).
- **Costs:** `engine.py::_costs` (Rs25/lot/side flat + STT/exch/GST/SEBI/stamp on real
  premium turnover) — the approved D-021 family cost model used everywhere else this session.
- **Sizing:** capital Rs3,00,000, risk_per_trade 3% of capital -> lots, same convention as
  `engine_swing.py` defaults (rupee P&L is thus indicative/comparable-to-precedent, not a
  claim about optimal sizing; per-trade `ret_pct` is the primary, size-agnostic metric per
  the firm's IC-1 per-trade-first convention).

## 5. Exit menu (five hold/exit rules; **stop -40% is ALWAYS active on top of every rule**,
checked every 1-min bar from entry, same priority style as `engine_swing.simulate()`)
1. **reversal** — exit at the next OPPOSITE-direction trigger's mapped entry bar (same
   signal family); if no future opposite trigger exists in the loaded data, ride to the
   option's own expiry.
2. **N5 / N10 / N20** — exit at 15:15 on the Nth subsequent TRADING day (from the spot daily
   calendar), capped at the option's own expiry if that arrives first ("expiry_cap").
3. **trail35** — once position value > entry debit (in profit), trail stop at 35% off the
   running peak; if never triggered, ride to the option's own expiry.
- **No profit target.** This arm's thesis is convexity capture (let winners run); adding an
  arbitrary take-profit would cap exactly the tail this arm exists to test.
- **No rolling across expiries.** A trade uses ONE contract, selected once at entry from
  the DTE bucket. If a hold rule (reversal / N20) would want to keep going past that
  contract's own expiry, the position is capped there instead ("expiry_cap"/"expiry_intrinsic"
  reason, logged and reported separately per cell — this interaction, DTE bucket effectively
  gating realizable hold length, is treated as a FINDING, not hidden). Rationale: rolling
  requires a second cost-and-peg-reset mechanism whose own bugs would eat the token/time
  budget without changing the core magnitude-vs-predictability question this arm exists to
  answer; the no-roll constraint is disclosed everywhere it binds.
- **Landmine #9 compliance:** any position still open on its option's expiry day is cash-settled
  at INTRINSIC = max(direction*(spot_close_1525 - strike), 0), from the underlying 1-min spot
  close near 15:25-15:29 that day. The option's own expiry-day 1-min quotes are NEVER read as
  the exit price once expiry day is reached.

## 6. Trade construction (sequential, one open position per signal family at a time)
Walk each signal family's chronological trigger stream. Open a trade on the first eligible
trigger >= the current "next available" date. Simulate its exit per §5. Set "next available"
= exit date's following trading day. Repeat. This models a single directional book (no
pyramiding, no overlapping bets), consistent with how this would actually be traded.

## 7. Staged design (cap the grid — do NOT run the full 3 signal x 3 DTE x 3 strike x 5 hold
= 135-cell cross product; that violates the "grid <=3x3" gate and manufactures noise per
today's confluence-stacking finding)

**Stage A — signal screen** (3 cells): each of the 3 signals, DTE=(15,22) [middle bucket],
strike=ATM, hold=trail35, over BUILD 2021-08-17..2025-12-31.
**Pre-registered PASS bar to advance to Stage B:** NET per-trade `ret_pct`, Newey-West t
>= 2.0, net PF > 1.2, n >= 30 trades. **If NO signal clears this bar, STOP — report a clean
kill of the whole arm.** This is a valid, valuable result, not a failure to soften.

**Stage B — DTE x strike grid** (9 cells, ONLY if a signal survived A): the winning signal x
3 DTE buckets x 3 strikes, hold=trail35 (fixed, unchanged from A), same BUILD window.
Selects the (DTE,strike) cell with the best NET NW-t among cells with n>=30; if none reach
n>=30 that is itself reported loudly as small-sample fragility, not silently worked around.

**Stage C — hold-rule robustness** (4 cells, diagnostic only): the Stage-B winning
(signal,DTE,strike), the 4 hold rules NOT yet run (reversal, N5, N10, N20), same BUILD
window. **This stage does NOT re-select a new "final" config** — it only reports whether
trail35 is a plateau (robust) or a cliff (fragile) versus the alternatives. The final
candidate taken to forward test is fixed as Stage B's winner with trail35, decided BEFORE
Stage C is run, to prevent any post-hoc "best of 5 hold rules" cherry-pick.

**Total build-phase trials: 16 cells.** Every cell's full trade CSV is written to disk.

## 8. Forward test (ONE untouched touch)
The single final candidate (locked at the end of Stage B, per §7) is run exactly once on
2026-01-01..2026-06-03 (entries in this window only). Whatever it shows is reported
verbatim — a forward kill is an acceptable, expected, reportable outcome.

## 9. Honesty battery (every surviving cell)
- Gross AND net P&L; monthly win-rate on BOTH.
- CAGR / MaxDD / Calmar / Sharpe / PF (net), Newey-West t, n.
- **Profit concentration: top-1 and top-4 trade share of total net profit** (the specific,
  named check against the 99.5%-in-4-trades failure mode). >30% in the top trade or a small
  cluster -> FRAGILE regardless of headline CAGR, per charter.
- Degenerate detectors: `04_RND_LAB/lib/guards.py::degenerate_flags` (Sharpe>4, CAGR/MaxDD
  mismatch, equity R^2>0.98, win>75%&W/L<0.5, symbol/period concentration) plus manual
  top-1/top-4 concentration check above.
- DSR using the honest trials count (16 build cells) via the standard Bailey/Lopez-de-Prado
  deflated-Sharpe formula. PBO: flagged as LOW-POWERED given expected small per-cell n
  (daily-trigger frequency, not intraday) — reported with that caveat, not suppressed.
- Regime slices where the sample allows: 2021-22 / 2022 / 2023 / 2024 / 2025 / 2026H1.

## 10. Comparator
S1-F (NIFTY weekly 0DTE short straddle, certified live): 12.57% CAGR / -4.44% MDD /
Calmar 2.83 / Sharpe 2.15 / PF 2.21 / n=204 / win 74%. Any candidate here is measured against
this, on BOTH CAGR/Calmar and on trade count / capital-idle-time honesty (this arm will trade
far less often; idle-capital calm is a structural fact, not an artifact, and will be flagged
as such wherever it inflates Calmar).

## 11. Verdict rule
REAL only if: passes Stage A/B bars, DSR>0.95 (honest 16-trial count), top-4-trade profit
share <=30%, forward 2026H1 net PF>1.0 and win-rate not collapsed vs build. Otherwise
FRAGILE (some bars cleared, some not — state which) or FAKE/KILL (magnitude solved but
concentration or forward collapse reproduces the known failure mode).
