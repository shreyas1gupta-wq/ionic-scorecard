# WHY THE EDGE IS 5 POINTS AND NOT 100 — the RR curve against the random-walk null
**2026-07-31 · DESK-100 · 48 rare setups × 8 risk-reward levels · the answer is measured, not argued**

## The Principal's question
*"why are we just making 5-10 points instead of 30-60 points or 100 points? find good setups even if
it trades less, does not trade few months, i do not care."*

## The answer in one paragraph
I had been conflating MOVE SIZE with EDGE SIZE. The moves are not small — NIFTY's daily ATR is
200-250 points, and the setups below average **+97 to +139 points per trade**. What is small is the
EDGE, because the direction is close to a coin flip. For a driftless random walk with a stop at −S
and a target at +R·S, the probability of touching the target first is **exactly 1/(1+R)**. At
RR 1:1.5 that is 40.0%. Across 87 option-buying cells I measured **40-43%**. So the honest statement
is not "the edge is small" — it is that at intraday horizons NIFTY behaves as a near-perfect random
walk, and a 5-6 point cost then turns "no edge" into "a loss".

**The follow-on question is whether a bigger target fixes it. It does not, and this run measures why.**

## The central measurement: the SLOPE of excess hit rate
For every setup and every RR in {1, 1.5, 2, 3, 4, 5, 6, 8}:
`excess(R) = observed_hit_rate(R) − 1/(1+R)`

- A random walk gives excess ≈ 0 at every R.
- **Convexity** means excess is positive AND **RISING** in R — the payoff scales faster than the hit
  rate decays. This is what an option buyer or a wide-target trend trader needs to exist.
- **Pure drift** means excess is positive but **FLAT or FALLING** — you get the first couple of R and
  nothing beyond.

### Result: 19 of 22 setups have a NEGATIVE slope.

| setup | mean excess | **slope** | best RR | exp_R | mean pts | t | /yr |
|---|---|---|---|---|---|---|---|
| GAP_EXTREME_fade_up | +4.38% | **−0.0286** | 8.0 | 0.630 | +139.3 | 1.26 | 3.1 |
| COMPRESSION_5_break | +1.29% | +0.0090 | 6.0 | 0.593 | +97.6 | 1.31 | 2.9 |
| NEAR_52W_HIGH | +5.94% | **−0.0359** | 8.0 | 0.524 | +99.9 | 1.39 | 4.0 |
| DONCHIAN_20_up\|wkEMA | +5.08% | **−0.0374** | 2.0 | 0.493 | +53.1 | 1.46 | 4.3 |
| WEEKLY_EMA_CROSS_UP | +0.22% | −0.0157 | 8.0 | 0.443 | +68.5 | 1.48 | 7.5 |
| VOL_TROUGH_up | +4.35% | −0.0152 | 5.0 | 0.443 | +51.3 | 0.87 | 3.2 |
| DONCHIAN_20_up | +3.74% | **−0.0359** | 2.0 | 0.414 | +47.3 | 1.40 | 5.6 |
| DONCHIAN_50_up | +2.31% | **−0.0419** | 2.0 | 0.403 | +64.0 | 1.79 | 5.0 |

**The cleanest single illustration — DONCHIAN_50_up:**

| RR | 1.5 | 3.0 | 5.0 | 8.0 |
|---|---|---|---|---|
| excess hit rate | **+13.8%** | +3.8% | **−7.1%** | **−9.2%** |

There is a genuine, sizeable edge at RR 1.5-2. It is **gone by RR 5 and negative by RR 8.**

## What this means, stated plainly
**Drift exists. Convexity does not.** The market hands you the first ~2R and then behaves like a coin
flip. You cannot convert a 10-point edge into a 100-point edge by widening the target, because the
hit rate decays faster than the payoff improves.

This is the same fact the earlier MFE/|MAE| = 0.92-1.32 measurement was pointing at, now measured
directly across the whole payoff curve instead of at a single target.

**Practical consequence: stop chasing large targets on the underlying.** The edge lives at RR ~1.5-2.5.
And since a 5-6 point cost against a 2R target of ~150 points is only 3-4%, the arithmetic at RR 2 is
actually fine — the binding problem at RR 2 is not cost, it is that the excess hit rate of +4 to +14%
is not statistically established at these sample sizes (see below).

## The random-day placebo: nothing clears, but this is a POWER statement
17 setups qualified (best exp_R > 0.05). **Zero clear p < 0.05.**

| setup | RR | real exp_R | placebo mean | placebo p95 | p |
|---|---|---|---|---|---|
| DONCHIAN_20_up\|wkEMA | 2.0 | +0.493 | +0.154 | +0.553 | 0.087 |
| DONCHIAN_50_up | 2.0 | +0.403 | +0.145 | +0.507 | 0.123 |
| DONCHIAN_20_up | 2.0 | +0.414 | +0.150 | +0.543 | 0.153 |
| DONCHIAN_50_up\|wkEMA | 2.0 | +0.356 | +0.124 | +0.546 | 0.170 |
| GAP_EXTREME_fade_up\|wkEMA | 3.0 | +0.504 | +0.183 | +0.798 | 0.183 |
| GAP_EXTREME_fade_up | 8.0 | +0.630 | +0.300 | +1.057 | 0.237 |

**Read this carefully rather than as a kill.** n is only 28-62 per setup — these are deliberately rare
setups — so the placebo distribution is enormously wide (p95 up to +1.06 R). Random days can easily
produce exp_R of +1.0 at n=30. So "no edge vs random day" here reflects a *lack of power*, not a
demonstrated absence of effect. This is exactly the case the Principal's standing rule covers: do not
reject a signal for low t at small n, because power ≠ no-effect.

What it does establish: **no rare daily setup is DEMONSTRATED yet.** The four Donchian variants
clustering at p = 0.087-0.170 with exp_R 0.36-0.49 at RR 2 are the honest shortlist — consistently
the same direction, consistently at RR 2, and consistently the best-populated cells.

## Scope note — these are no longer tradeable under the current mandate
Every setup here holds up to **25 trading days**. The Principal has since restricted the book to
**intraday only, no overnight**. So none of these is directly tradeable now. They stand as the
DIAGNOSIS of why intraday targets cannot be stretched, and the Donchian/compression family remains
the shortlist if the no-overnight constraint is ever relaxed.

## Setups that failed outright (useful as negatives)
`DONCHIAN_20_dn` mean excess **−11.08%**, exp_R −0.186 — downside breakouts are actively bad on this
sample, the mirror of the candle-formation finding that only bullish patterns paid on a +186% index.
`VOL_TROUGH_dn` excess −3.98%, `GAP_EXTREME_go_dn` −7.74%, `STREAK_DOWN_3|wkEMA` −9.41%.
**Weekly candle formations as TRIGGERS** — the half of an earlier ask that CANDLE_MTF left undone —
were included here: `WEEKLY_ENGULF_BEAR` exp_R −0.015, `WEEKLY_HAMMER` +0.165, `WEEKLY_ENGULF_BULL`
and `WEEKLY_EMA_CROSS_UP` +0.443. None clears its placebo. **That debt is now discharged: weekly
formations as triggers do not work either.**

## Controls applied
- All exits through `lib/pathsafe` — target as a resting limit, **stop resolves ADVERSELY**, both
  intra-bar bounds returned, unreliable cells flagged (`DONCHIAN_20_dn` at RR 1.5/3.0 flagged \*AMB\*).
- **ONE POSITION AT A TIME**, so the 10× overlap inflation caught earlier today cannot recur.
- Stop fixed at 1.0 × daily ATR14 so noise cannot take a trade out; targets scale from it.
- Cost charged ONCE per trade (correct for futures), era-correct at 4.47/5.97 index points + 0.5
  slippage.
- Era split at 2024-10-01; 2026 held out. **Held-out columns are mostly empty because these setups
  fire 3-7 times a YEAR** — that is an honest power limit, not an omission.
- 176 (setup × RR) cells scored; Bonferroni-ish bar t ≈ 7.4. Nothing comes close, consistent with the
  power discussion above.

## Files
`big_move.py` · `rr_curves.csv` (176 cells) · `convexity.csv` (slope per setup) · `placebo.csv` ·
`meta.json` · `run_log.txt`
