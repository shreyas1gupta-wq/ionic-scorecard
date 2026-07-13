# PRE-MORTEM RISK MEMO — Short Index-Options Book into an RBI + Budget Week

**Desk:** Short-vol paper book (defined-risk spreads + naked strangles, NIFTY/BANKNIFTY)
**Author:** Risk Office (pre-mortem, model-grid MG04) · **Date basis:** written as if 12 months forward, the morning after the worst week the book has ever printed
**Frame:** This is a *pre-mortem*. Assume the loss already happened. The job is to say *what killed it*, *how big the tail plausibly was*, *what triggers I pre-commit to now*, and *what I cannot hedge cheaply*. All figures are [INFERENCE] on a stated notional; scale linearly to actual book. Paper only, no live capital (firm rule).

## Reference book (so numbers are concrete)
Assume deployed margin **₹1.00 cr**, net short premium **₹6–8 L collected**, greeks at entry: **net short vega ≈ ₹40k/vol-pt**, **net short gamma**, delta ≈ flat, theta ≈ **+₹18k/day**. Roughly 60% of risk in defined-risk spreads (capped) and 40% in naked strangles (uncapped, ~15–18-delta legs). This is the book that blew up.

## What killed it (ranked cause chain)
1. **Event-vol double-count, then a gap through the short strikes.** IV was *already* rich into the week, so premium looked fat and the desk sized to the premium, not to the move. RBI surprised (or the Budget carried an off-consensus tax/borrowing line), NIFTY gapped **~4–6% in a session** and kept going intraday. The naked strangle's short leg went from 15-delta to ~55-delta; **short gamma turned the delta against us faster than we could hedge.**
2. **Vol-of-vol / vega on the crush that never came.** The classic short-vol prayer is "IV collapses after the event." It didn't — realized *exceeded* implied, and the term structure inverted (front IV +8 to +15 vol-pts). Short vega ₹40k/pt × +12 pts ≈ **−₹4.8 L** on vega alone, on top of directional loss.
3. **Liquidity evaporation at the exact moment of need.** Bid-ask on the OTM legs blew from ₹1–2 to ₹15–30 wide; the "defined risk" spreads were only defined *at expiry*, not intraday — marking-to-mid understated the real exit cost by **2–4x** (T7b/COST_STANDARDS dynamic-slippage regime). We could not roll or close the naked legs without paying the panic spread.
4. **Correlation-to-one / no true diversification.** Every position was the same trade (short NIFTY vol) wearing different strikes. "Spreads + strangles" felt diversified; under stress the book had **one factor** and it was short-gamma-short-vega. Margin (SPAN + exposure) spiked as scan-range widened, forcing de-risk into the worst prices — a margin-call feedback loop.

## Quantified plausible tail (numeric, stated notional)
| Scenario | Index move | Front IV Δ | Est. book P&L | Note |
|---|---|---|---|---|
| Bad-but-normal | −2.5% / +2.5% | +4 pt | **−₹1.5 to −2.5 L** | inside modeled worst-case |
| Severe (base tail) | −4.5% gap | +10 pt | **−₹6 to −9 L** | naked legs breached; ~1.0–1.5x collected premium lost |
| Worst-week-ever | −6 to −8% + follow-through | +12 to +18 pt | **−₹12 to −18 L** | 12–18% of deployed margin; **1.5–2.5x** premium collected |
| Left-tail / limit-down type | −10%+ | +25 pt, illiquid | **−₹25 L+** | naked strangle is effectively unbounded here; defined-risk legs cap ~₹6L of it |

**Headline:** worst-week loss ≈ **−12% to −18% of margin (base tail)**, with a fat, *non-symmetric* left tail where the naked strangle carries **theoretically unbounded** downside (practically ₹25L+ before we could flatten). Modeled 1-day 99% VaR pre-event probably read **~₹2.5–3 L**; the realized loss was **4–6x VaR** — the standard short-gamma signature (VaR is blind to jumps).

## Pre-committed de-risk triggers (decided NOW, mechanical, no discretion in the moment)
- **T-minus sizing cap:** into any RBI/Budget/Fed week, **cut net short vega by ≥50%** and **cap naked-strangle margin at ≤15%** of book (down from 40%) *before* the event. Pre-registered, not negotiable.
- **Naked → defined:** convert every naked strangle to an **iron condor / add long wings** (buy the 5-delta) by T-1 close. Caps the unhedgeable tail at a known, budgeted debit.
- **Loss trigger 1 (soft):** book MTM **−₹3 L (−3% margin)** intraday → stop adding, hedge delta to flat with futures, halve remaining naked exposure.
- **Loss trigger 2 (hard kill):** book MTM **−₹6 L (−6% margin)** *or* short-leg delta > **30** *or* margin utilization > **80%** → **flatten naked legs immediately at market**, accept the spread; keep only defined-risk. This is the circuit breaker; it fires on price/greek, not on opinion.
- **Vol trigger:** front IV rises **+8 vol-pts intraday** post-event (crush thesis is wrong) → de-risk regardless of P&L.
- **Liquidity trigger:** if OTM bid-ask > **10x** its pre-event width, do **not** average/roll; exit the closest liquid strike and stand down.
- **Event blackout:** no new short-vol entries in the **48h window around the announcement**; theta is not worth the gap risk.

## What CANNOT be hedged at acceptable cost (honest section)
- **The jump/gap itself.** Overnight/announcement gaps happen when the market is closed — no delta hedge fills through a gap. You pay for gap protection *in advance* via long wings, and that premium is a **permanent drag on the short-vol edge** (it eats most of the collected theta in quiet weeks). There is no free convexity.
- **Correlated liquidity + margin spike.** When you most need to hedge, spreads are widest and margin is highest — the hedge is most expensive exactly when required. Buying that insurance continuously makes the strategy uneconomic; accepting it means accepting the tail.
- **Vol-of-vol / term-structure inversion.** Cheap, liquid vega-of-vega hedges don't exist for a retail-scale NIFTY book; a VIX-style hedge is basis-mismatched and itself illiquid intraday here.
- **Model risk on "defined."** Defined-risk is only defined *at expiry*. Intraday, under stress, the max-loss can be touched *before* expiry via margin/liquidity, so the "capped" comfort is partly illusory.
- **The strategy's own DNA.** Short vol is *structurally* short the left tail. You can shrink it (wings, sizing, blackout) but you cannot remove it without deleting the edge. The only complete hedge is **not being in the trade** during the event — which is exactly what the sizing cap and blackout above encode.

## One-line verdict
The book died because it was sized to fat premium instead of to the gap, ran uncapped naked gamma into a scheduled shock, and discovered its "defined" risk and its liquidity were both conditional on the market staying calm. **Pre-commit the sizing cap + naked-to-condor conversion + the −6% hard kill; budget the wing premium as the honest cost of surviving the tail you cannot otherwise hedge.**
