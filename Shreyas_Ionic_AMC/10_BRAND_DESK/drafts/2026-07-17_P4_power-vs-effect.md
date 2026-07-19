# DRAFT — Buffer candidate
- **Pillar:** P4 (practical learnings / the craft of research).
- **Target slot:** TBD — ad-hoc add to the buffer, not yet assigned to a Sunday slot.
- **Compliance:** Self-checked against BRAND_CHARTER.md §7 — no stock-specific call, no Ionic/AMC internals, no P&L/positions/PII, doesn't name "Shreyas_Ionic_AMC." This is a self-check, not a formal `/compliance-audit` or red-team pass — run one before finalizing, per §11 step 3-4.
- **Pre-registration:** none — no falsifiable market claim.
- **Status:** DRAFT — needs Shreyas's voice pass + his own real (sanitized) example at `[SHREYAS ADDS]` + proofread.
- **Chart:** `2026-07-17_P4_power-vs-effect_chart.png` (matplotlib, dataviz-skill palette, illustrative — not real backtest output).
- **Provenance note:** originally requested as a "team + architecture + workflow" showcase post. That genre directly conflicts with §5 Prime Directive (rejected 3x on 2026-07-15 as "content strategy"/meta) and §7 rule #5 (never name/reveal the AMC structure). Redirected to a compliant P4 substance post instead — same underlying research substance (a real methodological lesson), none of the internals. Flagged to Shreyas in-chat; he can override if he actually wants the showcase version.

---

## Draft text (LinkedIn)

I nearly killed a promising idea a few weeks ago because its significance test came back weak. Small sample, so the honest thing to do was drop it — that's what I believed, anyway.

Then I sat with it longer. A weak t-stat on 30-40 observations isn't telling you "there's no effect." It's telling you "I don't have the resolution yet to separate a real effect from noise." Those are two completely different statements, and it's easy to collapse them into one when a p-value comes back looking unglamorous.

[SHREYAS ADDS: your own real example here — sanitize numbers/params — the moment you almost dropped something on a thin sample, and what made you look again.]

What I've landed on: statistical power is a reason to keep watching, not a reason to kill. The tests that SHOULD kill an idea regardless of sample size are the ones that don't need more data to fail — a result that only survives with the future leaking into the past, or one that dies the moment you shuffle the dates. Those catch fakeness at n=1. Power just needs time.

Small samples are the normal condition of early research, not the exception. Worth remembering before the next thin-data idea gets buried too early.

Views are my own, shared for discussion — not investment advice.

---
# Post-fill checklist: /style-lint; sanitize example (no real strategy/params/PII); Shreyas voice pass; formal compliance pass; his proofread; posts manually.
