---
name: hire
description: Onboard a NEW team member end-to-end — persona file, roster row, model assignment, CLAUDE.md entry, evolution log. Use for /hire <role>, "hire a new analyst/agent", "add someone to the team".
---

# /hire — new team member onboarding (D-016 gamified-team protocol)

1. Gate check first: a brand-NEW role (not previously on the roster) needs Principal approval before building; a refill of an existing role is CIO/FM authority alone. If new-role and unapproved, stop and ask.
2. Create the persona file `.claude/agents/<role-slug>-<name>.md` matching the existing format (see `data-officer-kavya-reddy.md`): frontmatter (`name`, `description` with trigger phrases, `model:` tier), then Identity/Charter (role scope, what they own), firm protocol summary (P-01..P-12 essentials: never guess, tag [DATA]/[INFERENCE]/[OPINION], checkpoint, token-aware), memo format for their output type, an empty `## Lessons Learned` section, and a compensation line (virtual base + AlphaPoints per TEAM_ROSTER.md).
3. Add a roster row to `00_GOVERNANCE/TEAM_ROSTER.md` (next sequential E-###, name, role, a sensible virtual base vs comparable roles, AP Balance 0, Status Active).
4. Add a row to `00_GOVERNANCE/MODEL_ASSIGNMENTS.md` (employee, tier Judgment/Analysis/Mechanical, primary + backup model, frontmatter `model:` value matching the persona file).
5. Add a row to the root `CLAUDE.md` "THE TEAM" table (agent id, role, summon-when) and append a hire entry to `00_GOVERNANCE/EVOLUTION_LOG.md` (date, employee, trigger = hire, what changed, files touched). Journal one line.
