---
name: red-team
description: Launch Nikhil Bose (Red Team) to adversarially attack a strategy, backtest, or claim before capital. Use for /red-team <target>, "attack this", "is this result real?", or before any pipeline gate-5 pass.
---

# /red-team — one focused kill attempt

1. Read the target's evidence (backtest output, memo, or code) + `Shreyas_Ionic_AMC/07_RISK_OFFICE/ADVERSARIAL_REVIEWS.md` (gate checklist + placebo battery) + `04_RND_LAB/CODE_CHECKS.md`.
2. Spawn `red-team-nikhil-bose` (sonnet — D-036, 2026-07-16: WS-4 benchmark measured Sonnet tying/beating Opus on this exact task type at ~1/15th the cost) with the target and this instruction: pick the SINGLE most likely reason the result is fake (priority: lookahead → measurement artifact → costs/liquidity fiction → selection bias → overfitting → tail concealment), prosecute it with evidence, run applicable placebos, and return REAL / FRAGILE / FAKE. Escalate to opus only for a genuinely hard call or a capital-sized/IC-bound decision — not by default.
3. Log the review as a new row in ADVERSARIAL_REVIEWS.md (+AP if a kill). If FAKE → move the idea to KILLED_IDEAS with a resurrection condition (D-012). If FRAGILE → state exactly what proof flips it.
4. D-008: one focused attack, not a bureaucratic checklist recital. Fast, lethal, evidence-first.
5. Same-family-judge caution (D-036): if this same red-team verdict will also be graded/scored by an Opus-family step downstream (e.g. IC synthesis), don't treat agreement between them as independent confirmation — self-preference bias between same-family judge/gradee was measured at +0.5-1.0/10 in the WS-4 study.
