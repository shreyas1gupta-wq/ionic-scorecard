# PRE-REGISTRATION — CONVEX_STRUCTURES_20260729 (Kabir Anand)
Written BEFORE any backtest in this folder is run. Binding per D-035 / retained gates.

## Scope
Ratio backspreads (1x2 CE/PE), calendars/diagonals (weekly-vs-weekly, weekly-vs-"monthly"),
and a broken-wing/skewed directional structure, on NIFTY weekly index options. Build
2021-05..2025-12, forward 2026-01..2026-06 HELD OUT (report only, no selection on it).

## Data-feasibility finding (discovered during setup, BEFORE any P&L run — logged here per protocol)
Inspected all 261 valid expiry files' first-available-trading-day. Every expiry file (weekly
*and* the last-weekly-of-month "monthly" tag) starts trading data only ~8-10 calendar days
before its own expiry, EXCEPT 6 expiries (2024-02-29, 2024-08-29, 2024-11-28, 2025-02-27,
2025-05-29, 2026-05-26) which have 39-44 trading days / ~58-60 calendar days of history.
CONSEQUENCE: a "sell weekly / buy monthly" calendar entered more than ~10 days before the
monthly leg's own expiry will find the far leg's price series EMPTY on the entry date, for
all but those 6 instances. This is either (a) a genuine NIFTY far-month liquidity gap most of
the time, or (b) a capture artifact of this dataset — cannot fully distinguish from here. Either
way it is TREATED as an execution/data gate: entry is SKIPPED when the far leg has no data on
the entry date, and the resulting sample size + skip rate is reported prominently, not hidden.
This is checked BEFORE claiming any calendar mechanistically differs from K-012.

## Structures and trial grid (every cell below enters the trials ledger regardless of outcome)
**A. Ratio backspread (1x2):** sell 1 near strike, buy 2 further strikes (net long optionality
by construction -> satisfies net-hedge-positive count discipline). CE and PE. Widths tested:
1, 2, 4 strikes (50/100/200 pts). Unconditional weekly cadence + signal-gated
(sweep_priorday_reclaim, sweep_intraday_continue). Exit: 1 trading day before expiry (default)
vs hold-to-expiry-cash-settled-at-intrinsic (sensitivity).
**B. Calendar/diagonal:** sell near-week ATM, buy far leg. Far = near+1 week, near+2 weeks,
and "monthly" (last expiry of month). Unconditional + signal-gated diagonal (far strike offset
by signal direction). Exit 1 trading day before NEAR leg's expiry, or stop at -75% of debit.
**C. Broken-wing (protected risk reversal):** long 1 OTM call + short 1 OTM put + long 1
further OTM put (tail protection on the short put) -- 2 long/1 short, net-hedge-positive.
Unconditional bullish lean (tests NIFTY's known structural upward drift with NO signal) +
signal-gated (direction flips call/put roles per sweep_priorday_reclaim / sweep_intraday_continue).
**Trap-zone frequency:** measured unconditionally on the FULL spot history (not just traded
instances) for each width, plus on actual trades taken. This is a distributional fact about
the market, reported regardless of which structure "wins".

## Costs (mandate-authoritative, SHARED_CONTEXT)
Rs25/lot/side commission (lot=75) + 0.375pt/side ATM slippage (midpoint of mandate's
0.25-0.5pt range; 0.25 and 0.5 also sensitivity-tested). Friction = total lot-units traded
(sum of |qty| across legs) x Rs25 x 2 sides + slippage. Reported as Rs and as % of GROSS
for every structure, prominently, per the NS-1 lesson (55-84% cost/gross killed that arm).

## Margin (Principal ruling 22:56, dynamic, spot-scaled)
All three structures are defined-risk by construction (bounded max loss via the offsetting
long leg) -> 5% of notional. Notional = spot_at_entry x lot_size x lots (position-sizing
unit, not multiplied by leg count -- [INFERENCE], the ruling does not disambiguate multi-leg
notional basis). Where a naked-equivalent comparison is meaningful we also report it at 10%,
labeled explicitly. Equity curve: start Rs10L (S1-F sizing convention), lots sized as
floor(0.75 x equity / margin_per_lot), single position at a time (no overlap), compounding.

## Pre-registered KILL criteria (fixed before any result is seen)
1. Friction >= 50% of gross P&L on average for a cell -> KILL that cell (extends the NS-1
   "cost eats the collection" lesson to convex buying structures).
2. NW t-stat on net pts/trade < 2.0 -> cell does not clear significance; reported but not
   claimed as a finding.
3. A cell whose Sortino/Calmar is driven by a near-zero downside deviation from a small-n
   short-tail-selling artifact (Kabir's standing lesson) -> flagged and DISQUALIFIED from
   being called a "winner" regardless of headline ratio.
4. Any structure identified as mechanistically identical to K-012's failure mode (far leg
   dead >50% of intended entry attempts) -> same verdict as K-012: vehicle dead, signal
   (if any) may still be valid, do not claim the vehicle.
5. A KILL is a valid result. No cell gets softened; no survivor gets inflated.

## Comparison bar
S1-F: 12.57% CAGR / -4.44% maxDD / Calmar 2.83 / Sharpe 2.15 / n=204 / win 74% (already flagged
firm-side as sitting above the honest VRP ceiling with an OOS-hygiene bill still owed -- not
an easy bar). Also compare qualitatively to the killed EMA-intraday-buying arm (zero convexity,
MFE/|MAE| ~1.0) and to K-012 / NS-1 for mechanism, not just headline numbers.
