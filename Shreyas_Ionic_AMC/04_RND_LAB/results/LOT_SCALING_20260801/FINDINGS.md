# MDD-AWARE LOT SCALING — the plan works, but most of what it compounds is BETA
**2026-08-01 · DESK-100 · 5 sizing policies × 3 arms × 2,000 bootstrap paths each**

## The plan as stated
*"strategies with 10-30 point avg mean profit and 10-30 trade per month totaling 300-1000 point and
300×65=20000+ in which we can buy 1-2 more lot and next month scale... scaling in a mdd aware and
buffer way to avoid wipeouts."*

## Reality check on the inputs
8 cells in the book DO meet "10-30 pts avg AND 10-30 trades/month". **ZERO reach 300 pts/month.**

| cell | trades/mo | mean pts | pts/month | ₹/month on 1 lot |
|---|---|---|---|---|
| SOLDIERS 1-session (in-spec) | 13.0 | +18.52 | **241** | **₹15,650** |
| SOLDIERS 3-session (best) | 5.5 | +45.52 | 250 | ₹16,250 |

So the per-lot base is **₹15,650/month, not ₹20,000+**. The bottom of the stated range is roughly
right; the top of it does not exist in anything we have measured.

## The decisive result: sequencing risk, 2,000 block-bootstrapped orderings
Same months, resampled order (stationary block bootstrap, block=3 months, so volatility clustering
is preserved — iid trade shuffling would flatter every policy by destroying exactly the clustering
that causes wipeouts).

| arm | policy | median ret | p5 ret | **P(ruin)** | **P(>25% DD)** | med maxDD |
|---|---|---|---|---|---|---|
| SOLDIERS 1-sess | FIXED 1 LOT | 214% | +159% | 0.0% | **0.0%** | −4.4% |
| SOLDIERS 1-sess | naive monthly +1 | 6678% | +4714% | 0.1% | **35.4%** | −20.4% |
| SOLDIERS 1-sess | margin-only | 8011% | +5566% | 2.7% | **62.5%** | −32.0% |
| SOLDIERS 1-sess | **MDD buffer 60%** | 7778% | +5439% | 0.7% | **50.0%** | −25.0% |
| SOLDIERS 1-sess | CPPI floor | 230% | −21.6% | 0.0% | 24.1% | −20.1% |
| SOLDIERS 3-sess | naive monthly +1 | 7268% | +5596% | 0.0% | **10.0%** | −12.6% |
| SOLDIERS 3-sess | **CPPI floor** | **7810%** | −2.3% | **0.0%** | **11.9%** | −14.1% |
| **RANDOM LONG (beta)** | naive monthly +1 | **3801%** | **−69.4%** | **17.8%** | **91.8%** | **−51.5%** |
| **RANDOM LONG (beta)** | margin-only | 4323% | **−207.7%** | **32.7%** | 92.3% | −57.0% |

## Three findings, in order of importance

### 1. Over half the compounding is leveraged beta, not signal
A **random long** with the same stop, trail and hold, scaled by the same monthly rule, compounds to a
median **3801%**. The real signal reaches 6678%. So the signal genuinely adds — but the majority of
the compounded outcome comes from being leveraged long an index that rose 186% across the sample.
This is consistent with the earlier beta placebo (random long earns +29.25 pts, exp_R 0.432; only
THREE_SOLDIERS added incrementally at +18.7 pts over matched-random, p=0.000).
**Consequence: a bear decade inverts the larger half of this result.** There is no bear segment in
the data long enough to test it.

### 2. The wipeout risk you want to avoid is real, and it lives in the beta
On the beta control, monthly lot-adding gives **P(ruin) = 17.8%** and margin-only gives **32.7%** —
roughly one path in three destroyed. p5 return of −207% means the ruin guard fired (equity would have
gone negative). The real signal's own ruin probability is low (0.1-2.7%) precisely *because* its edge
is larger; but the strategy is ~60% beta, so its true ruin probability sits between the two arms, not
at the flattering end.
**Mechanism: monthly lot-adding is positive feedback.** You add size after good months, so you are
maximally sized entering the bad one. The mean per-trade edge is untouched by sizing; what sizing
changes is the order-dependence of the outcome.

### 3. Your MDD-aware buffer helps ruin but does NOT protect the 25% ceiling
The buffer implemented literally — never hold more lots than a repeat of the worst observed
per-lot drawdown can absorb at 60% of equity — cuts P(ruin) from 2.7% to **0.7%**. Good. But
**P(>25% DD) is still 50.0%** with a median maxDD of exactly −25.0%. It manages ruin, not the ceiling.
**CPPI floor is the only policy that respects the ceiling**, and on the 3-session hold it costs
almost nothing: median **7810%** with **0.0% ruin and 11.9% ceiling breach**, versus naive's 10.0%
breach at 7268%. On the 1-session hold CPPI is far too restrictive (median lots = 0 — the cushion
rarely supports even one lot), which is a genuine flaw in applying it to a high-frequency, small-edge
arm.

## The counter-intuitive practical answer
**The 3-session hold scales far better than the 1-session hold, even though the 1-session is the one
that matches your trades-per-month spec.**

| | 1-session (13/mo, +18.52) | 3-session (5.5/mo, +45.52) |
|---|---|---|
| P(>25% DD) under naive scaling | 35.4% | **10.0%** |
| P(>25% DD) under CPPI | 24.1% | **11.9%** |
| median ret under CPPI | 230% | **7810%** |

Larger edge per trade relative to its own drawdown means more lots can be carried safely. Frequency
is not what makes a strategy scalable — **edge-to-drawdown ratio is.** Chasing 10-30 trades/month
actively works against the scaling plan.

## What is NOT real in this table, stated plainly
The 6,000-8,000% figures are **arithmetic, not a forecast**. Three reasons:
1. `MAX_LOTS=40` binds almost immediately in most policies (median lots = 40), so these are
   "maximum permitted leverage held for 11 years" paths, i.e. an upper bound by construction.
2. 40 lots × 65 × ~24,000 = **₹6.24 crore notional**, and this strategy has never had a capacity
   check. Liquidity in NIFTY futures probably supports it; slippage at that size has not been
   measured, and `COST_STANDARDS` slippage was calibrated for far smaller clips.
3. The sample is a +186% bull market and over half the result is beta.

## Recommendation
- Run **1 lot** until the signal has forward evidence. Fixed-1 gives 214% with **0.0%** ceiling
  breach and a −4.4% median drawdown; that is the only row here with no tail.
- If scaling, use **the 3-session hold with a CPPI drawdown floor**, not the higher-frequency arm and
  not naive monthly addition.
- Treat the position as **leveraged index exposure with a signal overlay**, and size it against the
  firm's equity-beta budget rather than as market-neutral alpha.
- Before any real scaling: a capacity/slippage check at target lot count, and an explicit decision
  about carrying 60%-beta leverage into an untested bear regime.

## Method notes
Margin computed from the **contemporaneous** index level (10% of spot × 65 per the Principal's
ruling) — using today's spot for 2015 trades would badly understate early leverage. Costs already
inside the per-trade P&L (era-correct 4.47/5.97 + 0.5 slippage). One position at a time. Hard ruin
floor at 50% of starting equity with trading halted — that guard exists because an earlier sizing run
without it produced maxDD −266%/−409% and CAGR 8.2e10% by letting equity go negative.

## Files
`lot_scaling.py` · `historical_paths.csv` · `bootstrap_paths.csv` · `meta.json` · `run_log.txt`
