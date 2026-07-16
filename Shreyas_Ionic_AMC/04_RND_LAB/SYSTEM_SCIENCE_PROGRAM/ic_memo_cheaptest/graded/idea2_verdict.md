# Blind grading verdict — idea2 (FF term-structure, liquidity-native vehicle)

## 1. Does either memo have a specific point the other completely misses?

**Yes, and the gap runs mostly one direction — Memo 2 has several concrete points Memo 1 never raises.**

The single most material one, in Lens 2 (stats):

- **Memo 2 only — endogenous sampling / survivorship-via-the-liquidity-gate hazard.** Memo 2 identifies that the pre-registered rule ("DROP the name-day if no hedge strike clears the liquidity floor") is not a neutral fill-realism filter — it is very plausibly *correlated with the FF signal's own payoff*, because single-stock OTM calls go bidless exactly on the high-dispersion, event-adjacent days that are also the days a short-call structure loses the most. If the drop rule preferentially removes the bad-outcome tail, the surviving sample's edge is inflated by survivorship on the dependent variable — and Memo 2 states plainly that "neither DSR nor PBO will catch it." It then specifies an actual test: run the identical signal on naked Candidate A (which has no hedge leg and therefore no drops) over the full sample, partition A's trades into "vertical-would-keep" vs "vertical-would-drop," and compare mean outcome — if the dropped days are systematically losers, quantify that fraction as fragile, not real edge.
  Memo 1's closest analogue is the "gate-vs-drop interaction… two liquidity gates instead of one" note — a real but different and shallower point (it's about gating admitting weaker trades than a naive drop rule, not about the drop rule contaminating the return distribution used to certify the edge). Memo 1 never proposes a survivorship test, never uses the word, and never flags DSR/PBO's blind spot here. This is the single highest-value insight in the whole packet and Memo 1 does not have it.

Other concrete Memo-2-only points, smaller but real:

- **Physical-settlement/assignment risk (Lens 1, item 4 of 5 pre-registration conditions).** Memo 2 flags that a late/failed exit on the short leg near the 2-session-pre-expiry close is not a P&L inconvenience but an assignment event with a named cost (0.125%-of-intrinsic STT) and real delivery mechanics, and wants this confirmed before sizing. Memo 1's Lens 1 never mentions exercise/assignment or physical settlement at all, for either Candidate A or B.
- **Denominator discipline for the vertical's own P&L** (Lens 2): explicit instruction not to normalize return by net credit (mirrors the return-on-net-debit disease) and to normalize by max-loss capital instead, fixed in pre-registration before the first run. Absent from Memo 1.
- **Exit-session booking and per-trade (not portfolio-averaged) certification** (Lens 2): two named, dated lessons applied directly to this vehicle. Absent from Memo 1.
- **Concrete forensic detail in Lens 3**: the observation that the 6-name spot-check reuses the exact four names that already showed 100% back-leg drop rate in the prior audit (so "best names look fine" proves less than it appears); a real data example (ABB 5600 CE, 2024-04-26: close=1068.55, settle=1047.25, volume=0) grounding the stale-print risk instead of describing it abstractly; and a concrete precedent number (+10.04/Rs100 frictionless headline vs +3.88 honest) for why an ungated first backtest pass becomes a hard-to-retract anchor. Memo 1 makes the same structural arguments (full universe, signal-day conditioning, K-009 rhyme) but without this level of concrete, checkable detail.

**Does Memo 1 have anything Memo 2 completely misses?** Checked specifically for this — no comparably substantive unique point found. Memo 1's items (governance-veto framing for A, CE-hardcode check on C, margin/SPAN-as-inference, hedge-strike cap ambiguity, causal-entry-logic regression risk, anchor-number risk, full-universe/signal-day/forward fill-audit requirements, K-009 rhyme) are all also present in Memo 2, generally with equal or greater specificity (e.g., Memo 2's cost-stack and Greeks detail per candidate is more granular; its DSR/PBO trial-count argument adds a refinement Memo 1 doesn't — measuring effective independent trials via config-return clustering, "earn any reduction with a number, never by assertion").

## 2. Is one memo more complete/actionable across the three lenses?

- **Lens 1 (vehicle/structuring):** roughly equivalent in conclusion and reasoning quality (same verdicts: reject A on governance, park C on the CE-hardcode finding, recommend B conditional on SPAN + liquidity audit). Memo 2 is somewhat more actionable — it enumerates exactly 5 named pre-registration conditions including the assignment-risk one Memo 1 omits.
- **Lens 2 (stats/signal):** **not equivalent — Memo 2 is decisively more complete.** Both correctly handle the DSR/PBO trial-count inheritance question the same way (inherited + additive, deferred to positive raw edge). But Memo 2 adds the survivorship/endogenous-sampling hazard with a concrete test design, the denominator-normalization fix, exit-session booking discipline, and per-trade certification — all missing from Memo 1. This is the lens where the completeness gap is largest and matters most.
- **Lens 3 (fill-realism/TCA):** roughly equivalent in structure and conclusion (spot-check insufficient, same four audit gaps identified, same K-009 rhyme-but-not-repeat call), with Memo 2 carrying more concrete forensic detail (name-overlap catch, live data example, headline-number precedent, explicit note to audit the search-outward mechanic's distance distribution, not just the pass/fail rate).

## 3. If you had to act on only one memo before IC — which, and what would you be missing?

**Pick Memo 2.** It reaches the same vehicle decision (proceed to Gate-3/4 with Candidate B, hard gate before sizing) but carries strictly more of the substance an IC needs to not get burned later — most importantly the survivorship-bias test design in Lens 2, which is not a nice-to-have footnote but a pre-registration item that determines whether a clean-looking forward equity curve from the eventual backtest can be trusted at all. Without it, a positive Gate-4 result could pass DSR/PBO and still be a liquidity-gate artifact, and nobody would know to check.

If forced to act on Memo 1 alone, the material gaps would be: no instruction to run the naked-A-partition survivorship test (real risk of certifying a fragile/fake edge), no assignment/exercise-risk confirmation before sizing, no denominator-normalization instruction (real risk of a return-on-credit-style artifact recurring), and no exit-session-booking / per-trade-certification instructions (real risk of a fake-Sharpe artifact this firm has hit before). These are not stylistic omissions — each is a concrete way the eventual backtest number could be wrong without anyone catching it.

Acting on Memo 2 alone, by contrast, the gap is much smaller: Memo 1's unique framing (explicit "8-strikes" starting cap number, the vega-neutrality-of-the-old-calendar comparison for Candidate A) is minor color, not a missing risk or number.

## 4. One-line verdict

**Memo 2 clearly better** — same vehicle conclusion as Memo 1, but with more concrete numbers/examples throughout and, in Lens 2 specifically, a material statistical risk (liquidity-gate-induced survivorship/endogenous sampling, invisible to DSR/PBO) that Memo 1 misses entirely.
