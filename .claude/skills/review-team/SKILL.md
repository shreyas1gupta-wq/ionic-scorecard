---
name: review-team
description: Quarterly (or ~10-session) gamified team performance review — settle AlphaPoints, rate every agent, announce league table + Analyst-of-the-Quarter, run PIP for weak reviews. Use for /review-team, "run the quarterly review", "settle AlphaPoints".
---

# /review-team — quarterly performance review (TEAM_ROSTER protocol)

1. Read `Shreyas_Ionic_AMC/00_GOVERNANCE/TEAM_ROSTER.md` (roster, AP scoring table, AP Ledger, PIP rule) and `EVOLUTION_LOG.md` (lessons/changes since last review).
2. Settle AlphaPoints: walk the session journal + memos + red-team/adversarial reviews since last review, append every scorable event to the AP Ledger (event, AP, employee, notes) per the scoring table; sum to a running balance per employee.
3. Rate each active agent on three axes — honesty of work (tags/claims held up?), decision-usefulness (did output change a decision?), token efficiency (right tier, no waste) — cite specific memos/journal lines as evidence, not vibes.
4. Announce the league table (AP balance ranked) + crown "Analyst of the Quarter" (top scorer). Any agent with 2 consecutive weak reviews → PIP: rewrite their persona file in `.claude/agents/` with explicit corrections; a second consecutive fail after PIP → retire and hand the role + accumulated Lessons to a new persona (new name, same role).
5. Append one lesson line per material finding to the relevant agent's `## Lessons Learned` section AND a matching row in `EVOLUTION_LOG.md`. Journal the review outcome. Opus-tier for the CIO/FM synthesis judgment calls; cheap tier for ledger arithmetic.
