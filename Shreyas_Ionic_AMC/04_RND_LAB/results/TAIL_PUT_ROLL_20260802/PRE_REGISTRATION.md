# PRE-REGISTRATION — TAIL_PUT_ROLL_20260802
Long NIFTY 10%-OTM put, 6-month tenor. ROLL (close+refresh every ~3 months) vs NO-ROLL (hold to own
6M expiry). Isolated single-leg comparison -- NOT embedded in a multi-asset portfolio (that's
`MULTIASSET_HEDGE_20260717`, which already found the ROLL version genuinely additive at 25%
notional on a diversified base). This test asks the narrower question the Principal actually
asked: holding the roll-cadence decision constant, which is the better STANDALONE way to run this
specific put.

## Structure
Entry: strike = nearest listed strike to spot x 0.90 (search nearby offsets if untraded, log any
divergence from true 10% same as MIDCAP_OTM_PUT's honest-fill-vs-target disclosure convention).
Expiry = nearest listed expiry to 180 calendar days out.
- **NO_ROLL**: hold to the put's OWN expiry, cash-settle at INTRINSIC from real spot close (never
  SETTLE_PR, landmine #9). Enter the next cycle the following trading day. ~20 cycles over
  2016-2026.
- **ROLL_3M**: close the put at ~90 days after entry (market CLOSE, CONTRACTS>0 gated, since this
  is NOT its own expiry), immediately open a fresh 10%-OTM/180-day put at the new prevailing spot.
  ~40 cycles over 2016-2026.
Cost: 1.77 pts round trip (single leg, COST_STANDARDS-derived, matches all prior arms in this
session).

## This is a HEDGE, not an alpha search -- the read criteria are different
A hedge is EXPECTED to lose money on average (insurance premium). The right questions are:
1. Annualized cost of carry (how much does each variant bleed per year, on average).
2. Payoff during REAL NIFTY drawdown windows (identified empirically from the spot series, not
   assumed) -- does the structure earn its keep when it matters.
3. Which roll cadence is cheaper to carry AND/OR pays off better in a real crash.
There is no "kill" bar here in the alpha-search sense; the deliverable is an honest cost/payoff
comparison for a CIO/hedge-sizing decision, per hedge-expert-kabir-anand's usual framework
(net-hedge-positive discipline: does it help study on the drawdown it's meant to protect against).
