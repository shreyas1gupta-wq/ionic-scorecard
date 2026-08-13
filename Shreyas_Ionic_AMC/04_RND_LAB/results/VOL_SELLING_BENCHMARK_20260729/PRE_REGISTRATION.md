# PRE-REGISTRATION — VOL-SELLING BENCHMARK, trend/signal-filtered (2026-07-29)
Written BEFORE running `vol_selling_backtest.py`. Owner: Vikram Shah (FM). Locked per D-035 —
no threshold below is changed after seeing results.

## Structures (both entered weekly, delta-based strikes, fixed 09:20 entry)
- **short_strangle** (naked, 2 legs): sell PE+CE at short_delta=0.18 (BS delta, IV from ATM straddle).
- **iron_condor** (defined-risk, 4 legs): short legs same as above; long wings at wing_delta=0.08,
  clipped to be strictly outside the short strikes.
- Entry day: DTE targeting identical to the firm's `engine_sell.py` convention — target_dte=3,
  min_dte=2, max_dte=5 (data-driven from actual expiry dates, no weekday assumption).
- Management: buy back at 50% of credit captured (target_frac=0.50); stop at 2x credit
  (stop_mult=2.0); else hold to expiry, **cash-settled at underlying intrinsic** (LANDMINE #9 —
  never read an expiry-day option settle print as price).
- Sigma-based strike selection is NOT run this pass (delta-based only, reusing validated
  `engine_sell.py`/`bs_pricing.py` machinery) — logged as a design choice, not a result.

## Costs (Principal-supplied, SHARED_CONTEXT, authoritative for this mandate)
- Rs25/lot/side brokerage = 25/75 = 0.3333 premium points per leg per fill (entry AND exit,
  each leg separately). A strangle = 2 legs → up to 4 fills; a condor = 4 legs → up to 8 fills.
- **Expiry-worthless legs incur NO closing brokerage** (no order is placed to let an OTM option
  lapse) — stated assumption, flagged [INFERENCE].
- Slippage: 0.4% of each leg's own premium per fill (sell fills worse/lower, buy fills worse/
  higher) — mid-point of the index-ATM slippage convention in `frictions.py` (0.4% base for
  "index"), applied per leg regardless of moneyness for simplicity. Stated assumption.
- **GROSS = raw mid-price P&L, zero costs. NET = fill-price P&L (post-slippage) minus brokerage
  rupees.** Reported separately, never blended.

## Margin (Principal ruling 2026-07-29 22:56, supersedes the 15% figure)
- **short_strangle (naked): margin = 10% x (spot x lot_size), applied ONCE to the whole 2-leg
  position** (not doubled per leg) — mirrors the firm's own S1-F precedent, which charged its
  15% rate once to the whole straddle rather than per leg, on the realistic basis that a
  strangle's two legs cannot both be maximally adverse simultaneously (exchange SPAN nets this).
  Flagged [INFERENCE] — the Principal's ruling states a rate, not a netting convention; this is
  the most consistent reading given firm precedent and is stated explicitly here, not decided
  after seeing results.
- **iron_condor (hedged/defined-risk): margin = 5% x (spot x lot_size)**, per the ruling, applied
  once to the whole 4-leg position.
- Sizing: `lots = floor(0.75 x running_equity / margin_per_lot)` — same DEPLOY=0.75 convention as
  S1-F, for direct comparability. Margin is DYNAMIC (recomputed from spot every trade), never flat.
- Capital base Rs10L (matches S1-F reference sizing).

## Filters under test (all computed on D-1, the trading day BEFORE the entry day — fully
PIT-safe; today's entry decision never uses same-day information beyond the 09:20 entry print)
Day-level flag = "did this event fire at least once on D-1's 15-min bars":
1. `sweep_intraday_reclaim` (t=-3.64 as a continuation signal upstream = inverted = a
   non-continuation/mean-reversion tell) — **flagship of this arm.** Tested BOTH directions:
   `enter_if_reclaim` (sell only when D-1 showed a failed intraday sweep — the hypothesis) and
   `skip_if_reclaim` (falsifying control, opposite direction).
2. `sr_round_reject` (t=-0.78 upstream, weak) — `enter_if_round_reject` only (one direction,
   bounding trial count; upstream evidence is too weak to justify testing both directions).
3. `sweep_priorday_continue` (t=+0.53 upstream, a genuine continuation tell for buyers, hence
   logically a WARNING sign for sellers) — tested both `enter_if_pd_continue` (per brief's
   instruction to test conditioning on it) and `skip_if_pd_continue` (the economically-motivated
   direction, since a real continuation day is bad for short gamma).
4. `trend_veto` — reuse S1-F's exact F1/F2 vetoes (RSI(5) daily >=80 or <=20 on D-1 close;
   |D-1 close-to-close return| > 1.5%) as the trend/overbought-oversold filter item 3 asks for.
   Skip the week if either fires.
5. `reclaim_and_trend` — combo of the flagship signal with the trend veto (`enter_if_reclaim`
   AND NOT `trend_veto`), the single most-motivated combination, tested once.
6. `unconditional` — control, always enter. This IS the base "item 1" result.

8 filter arms x 2 structures = **16 configurations**, each run on BUILD (2021-05-24..2025-12-31)
and separately on HELD-OUT FWD (2026-01-01..2026-06-30). = 32 runs. Every one logged to
`TRIALS_LOG.csv` regardless of outcome — no silent discard.

## Kill / promotion criteria (pre-registered, will NOT be adjusted after seeing numbers)
- A filter is judged to **improve risk-adjusted return** over its structure's `unconditional`
  control (same structure, same margin) only if, on BUILD: (a) Sharpe strictly higher AND
  (b) Calmar strictly higher, AND (c) retains n>=30 trades (a filter that prunes n below 30 to
  inflate a per-trade mean is the session's already-demonstrated confluence-stacking trap, and
  is disqualified regardless of headline Sharpe).
- No survivor here is "validated" — every one is a forward-test candidate. The held-out 2026 H1
  (~26 weekly expiries) is reported for every arm that clears the BUILD bar, but its own power is
  too thin to certify anything alone; it is directional evidence only.
- A configuration is flagged as **beating S1-F** only if BUILD Sharpe > 2.15 AND Calmar > 2.83
  AND maxDD-on-margin-capital no worse than -4.44%, on the same 2021-05..2025-12 window used for
  S1-F. Given S1-F's own Sharpe sits above the firm's documented VRP ceiling (0.9-1.2) and is
  DSR/PBO-unaudited, any "win" recorded here is provisional pending the same audit — stated up
  front, not as a post-hoc hedge.
- Concentration: if >30% of a config's NET profit sits in one day/trade, flag FRAGILE regardless
  of headline ratios.

## What will NOT be tuned after this file is written
target_dte/min/max, short_delta/wing_delta, target_frac/stop_mult, cost/slippage rates, margin
rates and netting convention, filter definitions and both-direction test list, capital/deploy,
kill thresholds above. If a run errors out on data (corrupt/stub expiry), it is skipped and
counted, never silently re-parameterized to force a fit.
