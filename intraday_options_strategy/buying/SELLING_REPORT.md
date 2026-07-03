# NIFTY Option-SELLING Strategy — Findings
**Date:** 2026-07-02 | `intraday_options_strategy/buying/` (engine_sell.py, refine_sell.py, sell_ce_20dma.py)

Fixed 1 lot, real 1-min prices, retail costs. Build 2021-2025 / untouched forward 2026 H1.

## Scoreboard
| Strategy | Build | Forward 2026 H1 | Verdict |
|---|---|---|---|
| **Short strangle** (naked, Δ0.18) | PF 1.70, Sharpe 1.66, +63% | −7.5% (1 tail loss) | REAL VRP edge, but naked tail + heavy margin — wrong for low capital |
| Iron condor Δ0.16 + IV/trend filter | PF 1.20, Sharpe 0.40, +4.7% | −1.8% (7 tr) | Defined-risk, modest, forward inconclusive |
| Iron condor Δ0.16 strict filter | PF 1.41, Sharpe 0.66, +6.1% | +0.8% (2 tr) | Too few trades to trust |
| Iron condor Δ0.12 | PF 0.74 (loses) | neg | Too far OTM — wings eat the credit |
| Iron fly (ATM) | PF 0.78, −64% | ~0 | Bad — too much ATM gamma |
| Sell CE, spot>20DMA (user) | PF 1.03, Sharpe 0.10, DD −21% | +3.9%, Sharpe 1.20 | Marginal; naked up-tail (−₹29k worst) |
| Sell CE, spot<20DMA (user) | PF 1.02, DD −24% | −2.1% | Marginal/negative |

## Key insights
1. **The VRP edge is REAL** — but it lives in selling BOTH sides, delta-neutral (strangle PF 1.70).
   Selling one side only (naked CE) is ~breakeven with a brutal directional tail.
2. **Defined-risk (iron condor) caps the loss but the protective wings eat most of the edge**
   → modest PF 1.2–1.4. That's the price of safety for low capital.
3. **IV-richness + trend-avoidance filters genuinely help** (condor PF 1.07→1.41 on build;
   less-bad forward). Only sell when vol is elevated AND price isn't strongly trending.
4. **2026 H1 was a hard short-vol regime** — hurt everything except calm/filtered subsets.
   Negative skew (small wins, rare big loss) is short-vol's nature.
5. User's "sell CE by 20DMA": the ABOVE-20DMA leg was positive in BOTH build (+5.3%) and
   forward (+3.9%) — the consistent leg — but −21% DD and −₹29k naked tail make it unsafe as-is.

## Best low-capital-safe candidate
Iron condor, Δ0.16 shorts / Δ0.08 wings, IV-rank≥0.5 + |price/20DMA−1|≤4%, manage@50%:
build PF 1.20, Sharpe 0.40, defined risk ~₹10k/trade, ~20 trades/yr. Modest but the most
robust defined-risk structure. Forward inconclusive (needs paper/live confirmation).

## Recommended next step
Convert the user's CE-selling idea to DEFINED-RISK: sell 1% OTM CE + buy further-OTM CE
(bear call spread) to kill the −₹29k tail, add the IV+trend filter, and optionally add the
put side (→ full iron condor). This marries the user's regime idea with the tail protection
that low capital requires.

## CORRECTION (cost-honest): the Sharpe>2 multi-strat was GROSS on the overnight sleeve
Multi-strat v1/v2 modeled the overnight-drift & gap-fade sleeves WITHOUT transaction costs.
Re-run standalone with realistic round-trip costs (overnight_gapfade.py):
- Overnight drift: gross build Sharpe 1.92 -> at 5bps round-trip **Sharpe 0.63, forward -1.70**.
  The +0.08%/night edge is SMALLER than the daily round-trip cost. DEAD net. The multi-strat
  Sharpe-2 leaned on this gross sleeve = OVERSTATED.
- Gap-fade: survives costs (6bps -> build Sharpe 1.79, +12% CAGR, -4% DD) because the +0.6%
  move dwarfs cost; BUT ~25 trades/yr and 2026-H1 forward was ~flat (few gap-downs) = inconclusive.
- Honest verdict: cost-surviving + forward-positive pieces = CE-sell+2.5xstop (fwd Sharpe 1.48),
  IV-filtered weekly strangle (fwd 0.98), gap-fade (build only). Realistic blend ~Sharpe 1.0-1.5,
  NOT 2+. Sharpe 2 existed only gross-of-costs. corr(overnight, gapfade) = -0.39.
Files: overnight_gapfade.py, overnight_gapfade.png
