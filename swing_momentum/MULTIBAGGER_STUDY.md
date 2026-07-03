# MULTIBAGGER ANATOMY — what each year's >=2x winners actually showed
`run_multibagger_study.py` on the survivorship-safe panel, 549 multibagger-years (2007-2025).

## POOLED PROFILE (what the big winners looked like)
| trait | value | implication |
|---|---|---|
| passed our trend-template in-year | **100%** | every multibagger became a Stage-2 leader → the signal CAN catch them all |
| already ABOVE 200DMA at year start | 58% | most are already in uptrends; ~42% emerge mid-year (turnarounds) |
| already uptrend + near-52w-high at start | 54% | over half are PRE-IDENTIFIABLE leaders Jan 1 |
| median prior-12m momentum at start | ~0% (wide) | NOT uniformly high — many launch from bases/turnarounds, not extension |
| median prior 60d volatility (annualised) | **42%** | multibaggers are VOLATILE — a low-vol screen would EXCLUDE them |
| median start price | Rs.94 | mid/small-cap tier (not large-caps) — capacity moat |
| **median INTRA-year max drawdown** | **23%** | **you must ENDURE ~23% heat to hold a multibagger** |

## THE BIGGEST ACTIONABLE FINDING (changes our rules)
**A 15% trailing stop EJECTS you from the median multibagger (which draws down 23% mid-run).**
Tight per-name stops kill the very winners that drive the strategy. The fix that great
momentum traders use:
- **Tight INITIAL stop** (5-8% below the pivot) for entry risk control — cut losers fast.
- **WIDE trailing stop once profitable** (give a winner ~25-35% / trail below 50DMA) so
  multibaggers can run through their normal 23% shakeouts.
- **Control DRAWDOWN at the PORTFOLIO level** (regime gate + cash + position sizing +
  leverage dial), NOT by choking individual winners. This resolves the earlier tension where
  tightening to 15% cut CAGR — it was ejecting multibaggers, not just cutting losers.

## REGIME IS EVERYTHING FOR MULTIBAGGERS (the compounding engine)
Multibaggers cluster massively in GREEN years and vanish in RED:
  2007:79  2009:122  2014:77  2021:54  2017:51  2023:41  ... vs  2008:1  2016:2  2025:2.
→ Deploy AGGRESSIVELY (concentration + leverage) when breadth is strong; sit in CASH in RED.
The "100%+ years" come from being heavily exposed to a target-rich GREEN regime.

## SKILLFUL LEVERAGE + CASH (regime-scaled exposure: 0 in RED, 0.5x->base by breadth in GREEN)
| base leverage | CAGR | MaxDD | Calmar |
|---|---|---|---|
| 1.00 | +12.1% | 21.0% | 0.58 |
| 1.25 | +14.4% | 26.0% | 0.55 |
| 1.50 | +16.6% | 30.8% | 0.54 |
| 2.00 | +20.9% | 40.2% | 0.52 |
**Leverage scales CAGR ~linearly but DD scales too → Calmar ~constant (~0.55).** Leverage
does NOT improve edge quality; it picks your point on the risk line. Skillful = 1.25-1.5x in
STRONG-breadth GREEN (CAGR 14-17%, DD 26-31%), 1.0x normal GREEN, 0 (cash) in RED. 2x = DD 40%,
too much. To genuinely lift Calmar you need a BETTER edge (entry timing, sizing) or an
uncorrelated sleeve — not more leverage.

## RULE CHANGES to fold into the engine
1. Two-stage stop: tight initial (entry), wide trailing (~25-30% / below 50DMA) for runners.
2. Do NOT add low-vol or low-price filters — multibaggers are volatile, mid-priced.
3. Regime-scaled leverage 0 / 1.0 / 1.25-1.5x (cash / green / strong-green by breadth).
4. Conviction sizing + pyramiding into the strongest leaders (next test).
5. Sector strength: NOT yet measured (no sector map in data) → fetch a sector mapping to add
   sector-momentum tilt (multibaggers historically cluster in the year's hot sectors).

## CAVEAT
Sector/quality/chart-pattern (VCP) features need data we lack (sector map; intraday/volume for
VCP). Measured here: momentum, trend-stage, distance-from-high, volatility, price, intra-run
heat, catchability. The 23%-heat and regime-clustering findings are the high-confidence ones.
