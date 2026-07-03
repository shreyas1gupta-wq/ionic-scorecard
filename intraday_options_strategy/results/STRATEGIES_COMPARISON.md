# STRATEGY COMPARISON — what beats the baseline (real m=0.80, 2% slip, gap-through stops)

Session 5c (2026-06-15). All at the live-calibrated m=0.80, conservative costs.
Fund Sharpe = annualised over the full calendar (idle days = 0).

## Single-sleeve results
| Sleeve | structure | n | WR | PF | avg/lot | worst/lot | Sharpe | OOS |
|---|---|---|---|---|---|---|---|---|
| **S3 naked straddle** | short ATM C+P, 25% stop, exit 14:30 | 222 | 64% | 2.10 | +1125 | -5897 | **1.79** | **2.01** |
| S5 iron fly | + long wings ±5 strikes | 222 | 71% | 1.48 | +594 | -9205 | 0.93 | 0.71 |
| S6 iron condor | short ±3, long ±8 | 195 | 77% | 1.03 | +10 | -5180 | 0.05 | -0.02 |
| S4 trend rider | long ATM on ORB break | 227 | 36% | 0.45 | -828 | -6509 | -1.70 | -1.16 |

## Why "more structures" did NOT beat the simple stopped straddle
- **Iron fly / condor:** the long wings cost more premium than the tail protection
  is worth WHEN you can stop out intraday at 1-min granularity. Wings only earn
  their cost if you hold unmonitored / overnight (not our case). Condor's OTM
  shorts collect too little to clear costs.
- **Trend rider (S4):** long premium structurally bleeds theta → negative
  standalone. It IS ~uncorrelated with short-vol (rho ~ -0.05) but the negative
  carry outweighs the weak diversification → vol-parity blends LOWER the
  portfolio Sharpe, not raise it. (combo S3+S4 OOS 0.82 < S3 alone 2.01.)

## Principled improvement sweep on S3 (gap gate, exit time) — IS vs OOS
Tighter gap gate (0.4%→0.2%) and earlier exit (14:30→13:00) BOTH reduce Sharpe:
they remove profitable trades and don't cut the worst day (-5897 is invariant →
the big loss is an intraday trend on a non-gappy morning). **Baseline is already
near-optimal; no curve-fit-free tightening helps.**

## Honest synthesis
The only robust retail edge here is **short intraday volatility (0DTE)**, and it
is essentially ONE trade — all short-vol variants are 0.5-0.8 correlated. The
"ensemble of uncorrelated sleeves" ideal is capped because no OTHER profitable,
uncorrelated edge survived (long/directional = no edge; weekly short-vol = no
edge intraday). So the best system is the **single well-tuned S3**, Sharpe ~1.8-2.0
at real pricing — already above the 1.5 bar, but it carries an irreducible
intraday-trend tail that entry filters cannot remove.

## ✅ DELTA-HEDGED short gamma — BUILT & TESTED, it WORKS (the real improvement)
`engine_v2.simulate_delta_hedged` + `run_delta_hedge.py`. Short 0DTE ATM
straddle, hedge net delta with Nifty futures (~1-min index), rebalance when
residual delta > band, hold to 14:30 (hedge bounds risk → no premium stop).
Real m=0.80, 2% opt slip, 0.5pt futures slip, brokerage per rebalance.

| config | WR | PF | avg/lot | Sharpe | IS | OOS | maxDD/lot | reb/day |
|---|---|---|---|---|---|---|---|---|
| naked (stop) | 64% | 2.10 | +1125 | 1.79 | 1.62 | 2.01 | 15,839 | - |
| hedged band 0.10 | 69% | 3.46 | +884 | 2.39 | 3.02 | 2.19 | 10,551 | 21 |
| hedged band 0.15 | 75% | 4.35 | +1107 | 2.79 | 3.33 | 2.68 | 10,949 | 12 |
| **hedged band 0.25** | **79%** | **4.65** | **+1254** | **2.98** | 3.59 | **2.74** | 11,350 | 5.4 |

**Result: delta-hedging lifts OOS Sharpe ~2.0 → ~2.7 (full ~1.8 → ~3.0), PF
2.1 → 4.65, and cuts maxDD ~28%.** The hedge adds +464/lot on average — on
trend days the long-futures hedge (straddle goes short-delta as spot rises)
captures the move that the straddle loses, isolating the clean short-gamma /
positive-VRP P&L. band 0.25 is best: only ~5 rebalances/day → low cost.
Caveats: (1) single-worst-day is bigger than naked (no premium stop; discrete
rebalance + gamma) but maxDD is LOWER overall; (2) per-1-lot hedge delta is
fractional — real deployment runs >= a few straddle lots so whole-futures-lot
granularity is fine; (3) index used as futures proxy (basis/bid-ask ignored
beyond 0.5pt slip); (4) hedge P&L being net-positive partly reflects Nifty's
up-drift over 2015-2026 — re-confirm on the paper month.

**This is now the lead strategy: delta-hedged 0DTE short straddle, OOS Sharpe ~2.7.**

## NON-EXPIRY-DAY expansion (Session 5e) — DTE=1 works, DTE>=2 doesn't
Tested delta-hedged short straddle by days-to-expiry (every day, nearest weekly):
| DTE | WR | PF | avg/lot | Sharpe | why |
|---|---|---|---|---|---|
| 0 (expiry) | 77% | 4.55 | +1215 | 3.15 (OOS 2.72) | max gamma, ~0 vega |
| **1 (pre-exp)** | **75%** | **3.15** | +651 | **2.59 (OOS 2.64)** | still high gamma, low vega |
| 2 | 68% | 1.61 | +311 | 0.76 | vega tail appears (-26k day) |
| 3-4 | 62% | 1.13 | +67 | 0.26 | dead |
| 5-7 | 51% | 0.70 | -204 | -1.13 | pure short vega, loses |

**Mechanism:** a non-expiry straddle is short VEGA; delta-hedging removes
direction but NOT vega, so an IV spike (any selloff) hits it — the further from
expiry, the more vega, the fatter the tail. The edge survives ONLY at DTE 0-1
(near-zero vega, high gamma). "Non-expiry days work" is FALSE in general; only
the day-before-expiry (DTE=1) qualifies.

**COMBINED DTE0+DTE1 NIFTY book** (both delta-hedged, 1 lot each):
fund Sharpe **3.13, OOS 3.61** (higher than either sleeve alone), ~75 deploy
days/yr, maxDD/lot 13,885, **corr(DTE0,DTE1) = -0.02** → near-uncorrelated, so
adding DTE1 both doubles deployment AND diversifies. `run_dte01.py`.
(DTE0 OOS 2.61, DTE1 OOS 2.51 individually.)

> BUGFIX (Session 5f): the delta-hedge engine previously closed the residual
> futures hedge at exit for FREE (P&L was marked to close correctly — no
> overnight position — but the unwind slippage + 1 brokerage order were not
> charged). Now charged in `simulate_delta_hedged` + `run_today_live.py`. Effect
> was small: combined OOS Sharpe 3.78 → 3.61. All delta-hedge figures here are
> post-fix.

## OPTION BUYING (long premium) — tested, REJECTED (Session 5g, run_buying.py)
Low capital + bounded MDD (premium only), but NEGATIVE CAGR — buyers pay the
VRP we harvest. m=0.80, 2% slip:
| buy strategy | WR | CAGR | MDD | Sharpe |
|---|---|---|---|---|
| long 0DTE straddle | 24% | -3.6% | 23.7% | -2.27 |
| S4 trend rider (long ATM) | 36% | -0.9% | 7.1% | -1.42 |
| long OTM momentum (best) | 34% | -1.2% | 9.7% | -1.21 |
The long 0DTE straddle's -3.6% mirrors the short straddle's gain → zero-sum
proof the edge is on the SELL side. No intraday Nifty buying strategy clears
the bar; not a tuning failure, it's market structure (theta+spread+VRP).

## CAPITAL EFFICIENCY — return on MARGIN posted (run_capital_eff.py, 3x buffer)
| structure | capital/lot | CAGR/cap | MDD | Sharpe |
|---|---|---|---|---|
| naked 0DTE straddle | Rs.390k | +7% | 2.7% | 1.43 |
| delta-hedged 0DTE | Rs.390k | +8% | 1.9% | 2.29 |
| iron fly 0DTE | **Rs.32k** | **+25%** | 17.8% | 0.74 |
FRONTIER: can't max all of {low capital, very-high CAGR, MDD<25%, Sharpe>1.5}.
Iron fly = low-capital/high-CAGR-on-capital/MDD<25% but Sharpe 0.74. Delta-hedged
straddle = high Sharpe/low MDD but capital-heavy. **Proposed build to get BOTH:
DELTA-HEDGED IRON FLY** (defined-risk low capital + hedge lifts Sharpe) — needs
delta-hedged multileg engine.

## Capital-efficiency roadmap (validated + proposed)
- ✅ NIFTY DTE0 + DTE1 → ~75 days/yr, OOS Sharpe ~3.8 (this file).
- → Replicate the DTE0-1 book on SENSEX (BSE, Thu expiry) for ~2 more days/wk —
  different underlying, low correlation → stacks. Wire via the Angel/Kotak
  fetcher (live data; historical SENSEX option backtest needs BSE bhavcopy).
- ✗ Non-expiry (DTE>=2) and naked weekly straddles REJECTED (vega tail).

## (superseded) earlier "next step" note: DELTA-HEDGED short gamma
The trend-day loss is mostly DIRECTIONAL (delta) once spot leaves the strike.
Professionally, short straddles are run delta-hedged: trade Nifty futures against
the accumulating delta to neutralise direction and keep the pure short-gamma/
theta P&L. This specifically attacks the tail S3 can't filter. Backtestable with
the 1-min index path as the hedge instrument (futures ~ index + small basis/cost).
Expected effect: lower worst-day & vol → higher Sharpe and much lower DD, at the
cost of more hedge trades (cost drag, esp. high-gamma near expiry). This is the
recommended next build; it is a real improvement, not a structure reshuffle.

## Decisions locked
- Lot size 65 (Angel master), not 75 — fix config before sizing.
- Defined-risk wings parked (only help if unmonitored). Keep S3 + strict stop.
- Iron-fly/condor code retained (engine_v2.simulate_multileg) for the delta-hedge
  build and for markets where overnight risk applies.
