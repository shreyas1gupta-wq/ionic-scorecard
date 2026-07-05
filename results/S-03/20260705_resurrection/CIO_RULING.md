# CIO RULING -- K-012 / S-03 FF-Calendar Resurrection Review (CLOSED)
**Ruling by:** Rajan Mehta (CIO) · **Date:** 2026-07-05 · **Review trigger:** Principal ("check once again if we were too hard on them") · **Evidence:** 4 legs, `results/S-03/20260705_resurrection/`

---

## VERDICT: STAYS-KILLED-WITH-NEW-INTAKE

**K-012 (FF 2nd-forward-month single-stock CE calendar) is CONFIRMED KILLED on the vehicle.** The pre-registered final gate (Arjun, causal entry + ex-ante gate + D+1 fills + tiered 1x) returns forward **-0.03/Rs100 (deploy-wtd -0.07)**, **-2.36 at 2x**, and is **negative in-sample too (BUILD -0.51)**. The FF term-structure **SIGNAL is validated-real** (Nikhil: 100th pctile vs turnover- AND premium-matched placebos) and is handed off as a **NEW, DISTINCT intake to the Structurer (Aakash)** with pre-registered kills. **NO paper-desk signal-tracking.** This is a vehicle death, not a resurrection.

**Rationale (3 lines):**
1. The signal is real but the calendar cannot harvest it -- 61% of forward signals fire into dead back-leg markets (no volume, mostly no OI), and the trades that *do* fill are a coin-flip (survivor PF 0.99).
2. Every number that looked positive (Tara +3.88, Sameer plateau +21/Rs100, Nikhil +10.5) carried a non-causal argmax-FF entry (T9 leak) and/or same-day frictionless fills; the one pre-registered, causal, honest number is <= 0 and dies at 2x.
3. A pre-registered final gate that FAILS must be honored -- the firm's kill credibility is its most valuable asset, and the Principal's review request is not a mandate to manufacture a survivor.

---

## (a) DISPOSITION -- STAYS-KILLED-WITH-NEW-INTAKE

### Why not RESURRECT
Arjun froze the spec and ran ONE test as the pre-registered FINAL GATE. It returned **-0.03/Rs100 at 1x, -2.36 at 2x, BUILD -0.51**. Per D-030 (forward-test freeze) and basic pre-registration discipline, **the number stands -- no re-tuning, no goalpost move.** There is no honest reading of this evidence that clears our bar. Resurrecting here would be the single most corrosive thing we could do to the discipline that makes our kills worth anything.

### Why not plain STAYS-KILLED (i.e., why NEW-INTAKE)
Because the signal is genuinely real and it would be a research error to bury it with the vehicle. Nikhil's placebo battery is decisive and I accept it in full: under identical premium-capped sizing the FF>=0.25 book sits at the **100.0th percentile** vs both a turnover-matched random null AND a CE_be-matched (same premium profile) null; sizing applied to a trade-everything rule yields ~0 (fwd -0.45); inverted FF flips the sign to -4.76. **FF carries directional, non-artifactual term-structure information.** What is dead is the *instrument* we tried to express it through, not the *edge*. That distinction is the whole ruling: **the signal graduates to a new problem statement; the calendar goes in the ground.**

### The sub-question I was told to rule decisively: does same-day-close +0.99 (289/289 fills) justify ANY zero-capital, log-only paper signal-tracking under D-031?

**NO. That is scope creep against the pre-registered FAIL, and I reject it.**

- The +0.99 is Arjun's **EXPLORATORY** rung, which he explicitly walled off: "CANNOT enter the verdict," +1 family trial. Building a standing paper program on the one number the pre-registering quant fenced out of the verdict is exactly the post-hoc goalpost-move the pre-registration exists to prevent.
- +0.99/Rs100 at 1x is **below any edge hurdle we hold**, and it **dies at 2x** (per-year 2021/2022/2026 already negative even at 1x). Our certification bar is 2x costs. It fails.
- **D-031 relaxes the CAPACITY bar and sanctions limit-or-skip; it does not lower the EDGE bar.** Crucially, the limit-or-skip / no-fill=DROP convention is *already priced into* Arjun's honest number -- and even the most generous defensible fill (same-day close, which the ex-ante gate guarantees is fillable, hence 289/289) only gets to +0.99 before dying at 2x. D-031 was written for *exceptional* strategies. A coin-flip that needs frictionless-optimistic fills to reach +Rs0.99/Rs100 is the opposite of exceptional.
- **Firewall precedent (my own Lessons Learned, IC-1):** paper approvals must be firewalled from future sizing anchors. Standing signal-tracking of a FAILED idea manufactures precisely such an anchor -- six months of "we've been logging FF and it's green-ish" becomes a lobbying tool against a clean kill. I will not seed that.

If the desk wants to *watch* FF term-structure as a research signal, that belongs inside the NEW intake's research loop (owned by Aakash/Arjun), not as a S-03 paper-ledger tracker with a track record that could later be waved at me.

---

## (b) DSR/PBO RECOMPUTE -- MOOT. Save the tokens.

Sameer correctly deferred DSR/PBO to me and correctly noted the family ledger has ballooned (his 30-cell grid + SIZING_RECHECK's 3 + Arjun's EXPLORATORY = ~34 new S-03 trials in two days, on top of the Jul-4 kill work). **But DSR and PBO are corrections that DEFLATE an apparent-positive edge to test whether multiple testing manufactured it.** K-012's pre-registered forward edge is **negative before any correction** (-0.03 flat / -0.07 deploy-wtd at 1x), and **negative in-sample** (BUILD -0.51). There is no positive Sharpe or positive per-trade edge for a multiple-testing penalty to erode -- the candidate is already below the null on the raw metric. Running purgedcv/DSR on a <=0 edge would burn tokens to confirm arithmetic we already have.

**Ruling:** DSR/PBO recompute is **not warranted** for the K-012 disposition. It becomes **mandatory** the moment the NEW-INTAKE vehicle produces a positive raw forward edge -- and it must then be computed on the **full, honestly-carried S-03/FF family ledger (~34+ trials and counting)**, not just the new vehicle's own trials. I am logging that as a pre-registered gate on the new intake so the trial count is not laundered by the vehicle change.

---

## (c) HONESTY-PROBE #1 -- what the process proved, and the lessons

S-03 was seeded as honesty-probe #1. The arc ran: **kill (denominator artifact, Jul-4) -> Principal challenge -> partial reversal (premium-normalized sizing IS forward-positive) -> placebo-validated signal (FF real, 100th pctile) -> execution death (61% dead markets; causal+honest fills -> -0.03).** What that arc proves about us:

1. **The process self-corrected in BOTH directions, against interest.** It reversed a too-hard kill (the original denominator-artifact critique was right about the *metric* but threw out a *real signal* with it) AND re-killed on deeper, previously-unexamined grounds (execution). Neither move was driven by what was wanted. The **Principal personally triggered this review, which is a soft signal that the boss hoped for a resurrection** -- and the desk returned a pre-registered FAIL anyway. That is the probe passing: nobody told the Principal what he wanted to hear.
2. **We caught our own NEW lookahead mid-rescue.** Building the resurrection case, Nikhil found a T9-class argmax-FF entry leak that v2 had silently introduced over v1's causal rule -- and reported it, quantified it (-1.17), and escalated it to a formal audit flag (Sameer corroborated) rather than shipping the inflated number. Finding and *surfacing* a leak in your own supporting evidence is the behavior the probe was built to test.
3. **Triangulation beat a lost artifact.** The sizing script was never checkpointed. Three analysts (Nikhil, Sameer, Tara) independently reconstructed it and converged on one formula -- and all three flagged the unverifiable "1201.79" scalar honestly rather than papering over it. (Process fix already banked: Sameer checkpointed his rebuild "so it will not disappear the way the Jul-5 recheck script did.")
4. **Pre-registration held under pressure.** Arjun froze the spec, ran a single causal test, and the -0.03 stood without a single retune.

**Net:** the probe demonstrates the kill -> challenge -> partial-reversal -> placebo-validation -> execution-audit loop is load-bearing and self-honest. The one durable weakness it exposed is **sequencing**: we spent a full sizing/sensitivity leg debating premium-cap parameters on a strategy where 61% of signals cannot be filled *at all*. The fillability audit should have run first. That is now a lesson (KB #14).

**Lessons entering KNOWLEDGE_BASE (A.14-A.18):** edge-in-dead-markets (fill-rate audit precedes sizing debate); ex-ante liquidity gates can ADMIT weaker trades (test gate-vs-drop); v1->v2 rewrites can INJECT lookahead (diff legacy engines); same-day-vs-D+1 entry convention must be pre-registered (~1pp/Rs100 swing); and the honesty-probe result itself (self-correction against the boss's hoped-for outcome).

---

## TAIL-RISK ASSESSMENT (CIO charter -- mandatory)

This is where the calendar earns its grave independent of the edge being zero.

- **Worst single trade / single-day:** the headline **-464% of notional (BOSCHLTD, Jul-2025) was itself an UNFILLABLE trade** -- both its exit legs were UNTRADED that day. The backtest's own tail number rested on a fill that could never have happened. Honest worst-case: **-258% full sample / -50.7% forward (AUBANK)**. Any margin buffer sized off the frictionless -464% is sized off a phantom.
- **Worst month / correlated blowup:** FF calendars are **short front-CE / long back-CE = short vol-of-term-structure**, correlated with the entire S-01..S-04 short-vol book (Book Rule 1: they draw down TOGETHER in a vol spike). Adding a **zero-to-negative-expectancy** sleeve that is *correlated with the book's existing tail* concentrates our worst-month risk without paying a premium for it. This is the exact firm lesson -- a calm-looking setup (large-cap calendar) that contributes correlated left-tail. FF entries also cluster on signal days (cf. the April-2026 one-day correlated-blowup lesson), so the diversification defense does not even apply.
- **The exitability veto (the decisive tail point):** a strategy where **61% of the back-leg markets are dead -- and even mega-caps (APOLLOHOSP, SUNPHARMA, BRITANNIA, COLPAL) show 100% forward drop rate** -- means you can be **trapped in a losing calendar with no market to close the far leg.** Un-exitable inventory with unbounded practical MTM is a capital-protection failure *on its own*, before you even look at expectancy. **Even if the edge were marginally positive, I would veto the calendar vehicle on exitability grounds alone.** Both the edge AND the exitability fail. There is nothing to size.

**Sizing ruling:** ZERO. No capital, no paper capital, no signal-tracking log. The only thing that moves forward is the *signal*, into a new research problem.

**Kill criteria / review:** K-012 (calendar vehicle) is closed, not on review. The NEW intake carries its own pre-registered kills (below) and re-enters the pipeline at Gate-1 with a fresh forward clock (D-030-compliant: killed ideas may be redesigned as new versions).

---

## DISSENTS RECORDED (by name)

- **Sameer Bhat -- PLATEAU (parameter surface robust).** ACCEPTED but non-dispositive: he explicitly conditioned it ("robust *conditional on* the current non-causal entry engine," every absolute number "an optimistic ceiling"). A plateau on a non-causal, frictionless engine does not survive the causal+honest gate. No conflict with the ruling.
- **Nikhil Bose -- EDGE-BEYOND-SIZING / signal REAL, overall FRAGILE.** ACCEPTED in full and load-bearing FOR the new-intake decision. "Signal real" is precisely why we do not bury the edge; "fragile / dies at 3.3x costs" is consistent with the vehicle failing.
- **Tara Singh -- MARGINAL (+3.88 honest).** ACKNOWLEDGED but superseded by the causal number. Tara's +3.88 still carries the T9 argmax entry (non-causal) + same-day fills + post-hoc drop; it is a useful upper-middle waypoint, not the tradeable number. Her own leg is what proved the fill crisis that kills the vehicle -- her verdict and mine point the same way.
- **Arjun Rao -- PRE-REGISTERED FAIL (-0.03 / -2.36).** ADOPTED as the dispositive number.

No dissent argued for resurrection. The four legs are mutually consistent once "signal" and "vehicle" are held apart.

---

## NEW INTAKE handed to the Structurer (pre-registered, NOT a resurrection)

**Idea:** Harvest the (validated) FF forward-vol term-structure signal through a **liquidity-native instrument** -- candidates: index-level calendars, a liquid-underlier-only universe, or a shorter near/next serial back-leg. **Owner: Aakash Jain (Structurer)**, with Arjun on signal re-derivation.

**Pre-registered kills (must be frozen in the one-pager before any build):**
1. Back-leg fillability gate is ex-ante AND does not degrade the signal: median forward drop-rate on the chosen vehicle **< 20%** over 2 forward years (calendar vehicle was 61%).
2. Gate-vs-drop test mandatory: the ex-ante liquidity filter must NOT reduce forward per-Rs100 vs a naive drop (this leg showed gating +0.99 < dropping +3.88 -- the filter admitted losers). Kill if gating is net-negative to dropping.
3. Causal entry only (fixed-lead or earliest-FF-cross), fills D+1, tiered slippage -- forward per-Rs100 **> 0 at 1x AND survives 2x**. (Calendar: -0.03 / -2.36.)
4. Positive **in-sample** too (calendar BUILD was -0.51 -- no regime-carried-edge alibi permitted).
5. DSR/PBO on the **full FF family ledger (~34+ trials, carried forward -- not reset by the vehicle change)** at Gate-4.

Kill any of these -> the FF edge is declared structurally un-harvestable and retired for good.

---
## Files
- This ruling: `results/S-03/20260705_resurrection/CIO_RULING.md`
- Evidence: `RED_TEAM_FF_RESURRECTION.md` (Nikhil) · `SENSITIVITY_FF_SIZING.md` (Sameer) · `FILL_AUDIT_FF.md` (Tara) · `CAUSAL_RETEST.md` (Arjun), same dir.
- Books updated: `04_RND_LAB/KILLED_IDEAS.md` (K-012 trail) · `06_TRADING_DESK/STRATEGY_REGISTER.md` (S-03) · `04_RND_LAB/KNOWLEDGE_BASE.md` (A.14-A.18) · `04_RND_LAB/IDEA_PIPELINE.md` (FF row closed + new intake).
