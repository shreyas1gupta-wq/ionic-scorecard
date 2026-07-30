# UNIFIED SIGNAL ALLOCATOR — spec parked for later build (Principal, 2026-07-30 12:15)
**Status: SPEC ONLY. Principal instruction is explicit — "now independently focus on 2 tasks i gave
first then later do this." Do NOT build this until the overshoot/mean-reversion and high-CAGR work is done.**

## The Principal's point, and why it is correct
> "there will be times that you allocated 15% to a particular strategy but there are no signals and
> capital is idle whereas we have other signals we can gain from. So instead of thinking on strategy
> level we can look basis a better strategy signal, regime, weights and other factors -> final signals
> and weights -> trade, instead of each trade separately."

**This exposes a real defect in the portfolio work done today.** Every blending result in
`FINAL_RANKING_20260730/marginal_add.csv` assumed STATIC per-sleeve capital. Consequences:
- CALENDAR_1x1 trades ~1x/month, so a static 15-20% allocation is IDLE ~95% of the time. That is why it
  measured as "immaterial" (+0.22% CAGR at 20% weight). **That verdict is an artifact of static
  allocation, NOT a property of the strategy.** Under pooled capital it could be sized far larger while
  it is the only signal competing.
- SWING_pw10 (~0.9 trades/month) is understated for the same reason.
- SWEEP_E (~32 trades/month) is the only candidate whose static weight is close to fully utilised, so
  the static framework is BIASED IN ITS FAVOUR. **The comparison was not apples-to-apples.**
=> **Any future sleeve comparison must be run on a capital-utilisation-adjusted basis, or through the
allocator below. Do not re-quote the static blending table as a ranking.**

## Target architecture
```
  all strategies emit SIGNALS (not positions)  ->  arbitration layer  ->  one sized trade stream
                                                    |
                     regime state + per-signal weight + risk budget + correlation + capacity
```
1. **Signal bus.** Every strategy publishes {timestamp, instrument, direction, conviction, expected
   edge in points, expected hold, stop distance}. It does NOT decide size. This is the key inversion.
2. **Arbitration / allocation.** At each decision point, rank live signals by expected edge per unit of
   risk, then allocate from ONE pooled capital base subject to: the drawdown-cushion sizing already
   validated (`DYN_SIZING_20260730` — CPPI floor with a min-1-lot floor; note pure 0-lot CPPI is a death
   trap that permanently freezes), the 25% maxDD budget, margin (10% unhedged / 5% same-expiry hedged),
   and per-instrument capacity.
3. **Correlation-aware, at the SIGNAL level.** Two strategies firing the same direction on the same
   instrument at the same moment are ONE bet, not two — must not be double-sized. **Precedent: SWEEP_E
   and SWEEP_D correlate 0.82 because they share an entry signal and differ only in exit. The allocator
   must detect this structurally (same signal source) rather than statistically after the fact.**
4. **Idle-capital rule.** Unallocated capital is explicitly cash, and the report must show utilisation
   over time. If utilisation is chronically <30%, either strategies are too infrequent or the risk
   budget is too tight — both are actionable, and both are invisible under static weights.

## Evaluation rules for the allocator when built
- Benchmark against the STATIC-weight book on identical data. The allocator must beat it on CAGR AND
  maxDD, not just CAGR.
- Report capital utilisation %, and CAGR on DEPLOYED capital vs on TOTAL capital separately — the gap
  is the whole point of the exercise.
- **Overfitting hazard, must be pre-registered:** the arbitration weights are new free parameters. Fit
  them on pre-Oct-2024 only and evaluate post-Oct-2024 and 2026 untouched, or the allocator becomes an
  elaborate curve-fit on the sleeve set.
- Honour the standing evaluation framework (SHARED_CONTEXT §EVALUATION FRAMEWORK): hard kills are
  placebo/lookahead/concentration/maxDD>25%; t-stats set tier, never kill.

## Live constraints to carry in
- Recency: **every existing candidate is negative post-Oct-2024 at 2x costs** (SWEEP_E -Rs339k,
  SWEEP_D -Rs518k, CALENDAR -Rs4k, SWING -Rs329k). An allocator over sleeves that are individually flat
  cannot manufacture edge — it can only allocate better among what works. **So the allocator is worth
  building AFTER at least one sleeve works in 2025-2026, not before.** This is the main reason the
  Principal's sequencing (2 tasks first) is correct.
- Unresolved and blocking a SWING allocation: `PORTFOLIO_MARGINAL_20260729` claims blending SWING cut
  book maxDD -18.4%->-9.5%, but direct measurement in `marginal_add.csv` shows maxDD getting slightly
  WORSE (-19.24% -> -19.32% at 15%, -19.61% at 20%) and worst-month degrading -9.61% -> -11.01%.
  **Reconcile before SWING gets any weight.**
