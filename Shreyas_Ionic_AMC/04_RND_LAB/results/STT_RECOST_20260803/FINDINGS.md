# BUDGET-2026 STT HIKE — the futures cost floor DOUBLES, and four of our survivors die
**2026-08-03 · DESK-100 · evidence pack for a COST_STANDARDS amendment (D-021 needs Principal sign-off)**

## Confirmed, two independent sources
Union Budget 2026, **effective 1 April 2026**:

| levy | old | new | change | side |
|---|---|---|---|---|
| **Futures, on sale value** | 0.02% | **0.05%** | **+150%** | seller |
| Options, on premium | 0.10% | **0.15%** | +50% | seller |
| Options, on exercise | 0.125% | 0.15% | +20% | purchaser |

Stated rationale: curb F&O speculation. Revenue target ₹63,700cr FY26 / ₹73,700cr FY27 against
~₹48,000cr collected to Jan-2026.

## Why this is the single most consequential number in the book
**STT is not a line item in our futures cost — it IS the futures cost.** The decomposition reconciles
exactly: the firm's model steps 4.47 → 5.97 index points at Oct-2024, and that step came from STT
0.0125% → 0.020%. A ΔSTT of 0.0075% moving the total by 1.50 points implies 0.02% = 4.00 points, i.e.
a reference spot near 20,000 (0.0002 × 20,000 = 4.0). So the **non-STT residual is 1.97 points** and
the STT term scales linearly with spot.

| spot | STT old | STT new | RT old | **RT new** | Δ | ratio |
|---|---|---|---|---|---|---|
| 20,000 | 4.00 | 10.00 | 6.47 | **12.47** | +6.00 | 1.93× |
| 24,000 | 4.80 | 12.00 | 7.27 | **14.47** | +7.20 | **1.99×** |
| 26,000 | 5.20 | 13.00 | 7.67 | **15.47** | +7.80 | 2.02× |

**The gross edge required just to break even on a NIFTY futures round trip goes from 7.27 to 14.47
index points.** The entire session's central result was that measured gross edges cluster at 2–5
points. That band was already below the old floor; it is now **3.6× below the new one.**

## The asymmetry is the actionable part

| vehicle | old | new | ratio |
|---|---|---|---|
| NIFTY futures (% of notional) | 0.0303% | **0.0603%** | **1.99×** |
| NIFTY options (100-pt premium) | 1.869 pts | 1.919 pts | **1.027×** |
| **MCX GOLDM (% of notional)** | 0.0246% | **0.0246%** | **1.00×** |

Options are hit ~3% because STT applies to the **premium**, not the notional. MCX commodities are not
hit at all — they pay CTT, not STT.

> **This REVERSES my own earlier conclusion.** I reported that gold carried no cost advantage
> (0.0246% vs 0.0228%). From April 2026 gold is **2.45× CHEAPER** than NIFTY futures, having been
> 1.23× more expensive. Gold is now the cheapest liquid intraday vehicle available to this book.
> (Caveat retained: gold's own best measured gross edge was 0.0149% against its 0.0246% cost, so it
> still does not work standalone — what changed is the venue ranking, not gold's standalone verdict.)

## Four survivors DIE. The ones that live all have a large per-trade edge.

| cell | vehicle | net old | net new | verdict |
|---|---|---|---|---|
| THREE_SOLDIERS 3-session | FUT | +45.52 | **+38.32** | survives (but ~60% beta) |
| WTI crude-crash short | FUT | +27.60 | **+20.40** | survives |
| Ratio calendar 1×1 rolled | OPT | +28.48 | **+28.41** | survives |
| MARUBOZU_BULL 2-session | FUT | +29.76 | +22.56 | survives (likely beta, placebo p=0.200) |
| HAMMER 2-session | FUT | +25.52 | +18.32 | survives (likely beta, p=0.242) |
| BOX4 first-60min break | FUT | +20.42 | +13.22 | survives (zero 2026 held-out) |
| THREE_SOLDIERS 1-session | FUT | +18.52 | **+11.32** | survives, but **−39%** |
| S1-F 0DTE short straddle | OPT | +9.71 | **+9.655** | survives, barely touched |
| Overshoot sell 0-1DTE | OPT | +0.30 | +0.27 | marginal |
| **Sweep prior-day reclaim (15m)** | FUT | +6.669 | **−0.531** | **DIES** |
| **ICHIMOKU_TK 15min** | FUT | +2.442 | **−4.758** | **DIES** |
| **VORTEX 60min** | FUT | +2.394 | **−4.806** | **DIES** |
| **1DTE flow-imbalance FADE** | FUT | +2.80 | **−4.40** | **DIES** |

**ICHIMOKU_TK was the one TradingView cell to clear a placebo** — I reported it as the first indicator
to pass that bar since VIX-RV divergence. It is dead from April 2026.
**The VORTEX open item resolves itself:** its placebo was never run, but at −4.81 net the question is
moot. Closing it as cost-killed rather than as an untested unknown.

## Three things this retrospectively validates
1. **"Frequency is not what makes a strategy scalable — edge-to-drawdown ratio is."** The STT hike is
   a tax on frequency and on small edges. The 3-session hold loses 16% of its edge; the 1-session hold
   loses 39%; the sub-3-point cells lose all of it. Same direction as the lot-scaling finding, arrived
   at from a completely different cause.
2. **The selling book is where the money is.** Options are essentially untouched (1.027×) while
   futures double. The VRP at t=32 was already the strongest measurement in the book; it is now also
   the cheapest to harvest.
3. **Large targets are hurt far less than small ones.** At RR 1:1.5 with a 1-ATR (~250pt) stop the new
   cost is 3.86% of the target. The problem was never large-target trades — it was that the *hit rate*
   at large RR collapses (excess-hit-rate slope negative on 19 of 22 setups).

## Timing note on our own 2026 held-out figures
Effective 1 April 2026. Our held-out windows mostly span Jan–May/Jun 2026, so **Jan–Mar used the
correct old rate and April onward is under-costed** in every quoted futures figure. The affected
portion is small in trade count but the direction is uniformly optimistic.

## Governance
This is an **evidence pack, not an amendment.** `06_TRADING_DESK/COST_STANDARDS.md` is APPROVED under
D-021 and amendable only via post-mortem evidence plus Principal sign-off. Recommended amendment:
futures STT → 0.05% with the non-STT residual held at 1.97 points and the STT term computed from
contemporaneous spot rather than a fixed point value; options STT → 0.15% of premium; an explicit MCX
row noting CTT-not-STT. Until signed, all quoted futures results should carry a "pre-April-2026 cost
basis" flag.

## Files
`recost.py` · `futures_cost_by_spot.csv` · `options_cost_by_premium.csv` · `recost_survivors.csv` ·
`meta.json` · `run_log.txt`

## Sources
HDFC Securities Union Budget 2026 note · HDFC Bank · ICICI Direct · ClearTax · 1Finance · Finnovate
