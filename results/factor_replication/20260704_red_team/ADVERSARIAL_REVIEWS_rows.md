# ADVERSARIAL_REVIEWS.md — row drafts (append to 07_RISK_OFFICE/ADVERSARIAL_REVIEWS.md §Review log)
Drafted by Nikhil Bose (E-014), 2026-07-04. Two engagements from the D-029 factor wave.

| Date | Target | Attack chosen | Evidence | Verdict | AP |
|---|---|---|---|---|---|
| 2026-07-04 | **I-016 N500 LowVol50 QUARTERLY (post-Gate-4)** | Turnover-artifact: is the +2.88pp margin over the 12.74% hurdle low-VOL selection or low-TURNOVER cost saving? Built a random-50 invvol basket turnover-matched (~119%/yr) to LowVol, run through the CERTIFIED engine (reproduced 15.62% exactly) | Random turnover-matched invvol basket median net-2x ≈ **15.0%** vs LowVol **15.62%** — selection margin over like-for-like random churn is **~0.6pp**, not +2.88pp. Skill-less random net-2x climbs 9.9%→15.0% purely by trading less (hurdle is full-churn ~200%+ turnover, 3.31pp drag; LowVol 110%, 1.84pp drag). ~2.3 of 2.88pp headline = cost artifact. Regime-carry (Sameer) compounds: only 2005-15 pre-crowding era beats matched-random | **FRAGILE** (bordering FAKE-as-edge; number real, "alpha" interpretation fake) — flip to REAL needs selection to beat turnover-matched-random p75 by >~2pp; diversifier case survives ONLY with stress-month corr proof vs short-vol book | +15 (claim) |
| 2026-07-04 | **I-017 pure N500 momentum-50 monthly (pre-intake, post-hoc control)** | (c) liquidity fiction: flat 22bps tier on a score-weighted book that concentrates into thin names; re-costed at honest ADV-resolved tier. (a) honest-trials count; (b) reconcile 26.4% vs family MQ50 15.4% | Reproduced 26.38/23.10 exactly. **59.8% of book weight in SMALL-ADV names (<Rs25cr/day)**, honest tier 27.1bps not 22. Net-2x: 23.10%→**22.05%** (actual tier)→**20.46%** (35bps floor) — CAGR REAL, not fragile to tier. 26 vs 15 gap = mom-only selection + score-weighting into smallcaps (real construct, not data-path bug). Trial-count: structural control (100/0 blend corner), not a lucky search survivor | **ADVANCE-TO-INTAKE** with 5 pre-registered kills (BINDING: RP-14 capacity w/ participation-impact; honest ADV tier baked in; -50% DD overlay judged risk-adjusted; honest trials carried; regime split). Real return but a -68%-DD unfillable-at-size smallcap-momentum tilt — capacity is the true gate, not CAGR | +15 (claim) |

## Notes for the CIO
- **I-016** is the firm's FIRST double-gate (DSR+PBO) passer, and the batteries are genuinely clean — which is
  precisely why the turnover-artifact is dangerous: no existing gate tests comparator turnover-matching. Recommend
  this becomes standing SOP: **any strategy measured against the random-basket hurdle must also clear a
  TURNOVER-MATCHED random basket, not just the (full-churn) hurdle.** (My attack template → firm SOP, per the
  IC-1 signal-shuffle precedent.)
- **I-017** headline (23.10% net-2x) must NOT travel as a clean "N500 momentum factor" into any IC/investor doc —
  it is a 60%-illiquid-tail, -68%-DD tilt. Advance the RESEARCH, gate the NUMBER.
