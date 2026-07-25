# HANDOFF — "agentic system" LinkedIn story + 1-3 page companion doc + image
Built 2026-07-21. Hand this whole file to a fresh Claude Code session (paste as the first message) — it's written to need zero prior context.

## Goal
Shreyas wants to publish a LinkedIn post (already drafted, below, lint-clean) plus a 1-3 page Word/PDF companion piece and one image/diagram, telling the story of a personal AI-agent system he built: it runs like a small investment research desk AND has a layer of skills whose job is to grow the system's own capability. Purpose: personal-brand impressions/publicity as a builder.

## Hard constraints — do not skip these
1. **Never name the underlying project, firm, or any employer.** Refer to it only generically: "a personal AI system," "a side project," "a system I built." No proper nouns for the firm.
2. **No stock-specific calls, no investment track record / return claims.** This is an engineering/systems story, not a performance claim. If a number appears (28 agents, 81 skills, etc.), it must be a system-design fact, never a P&L or return figure.
3. **State plainly and prominently, at least once per deliverable, that this runs entirely on paper with zero real capital** — no client money, no live trades.
4. **Before Shreyas actually publishes anything**, remind him once to double-check his employer's comms/compliance policy for public posts about investment-related systems — his own notes (`Shreyas_Ionic_AMC/10_BRAND_DESK/VOICE_SAMPLES.md`, line 16) flagged this as PENDING as of 2026-07-15 for him specifically as an "AIF insider." This is not blocking your work — just surface it once at the end, don't nag about it repeatedly.

## Voice and style — must follow
- Read `Shreyas_Ionic_AMC/10_BRAND_DESK/VOICE_SAMPLES.md` in full before writing anything. His real voice: first person, grounded, confident-but-hedged, concrete specifics over hype. Note: his established LinkedIn voice is market-commentary, not project-showcase — there's no exact precedent for this genre, so match his tone/confidence register, not a literal structural template.
- Before presenting ANY final text (post or doc copy) to Shreyas, run it through the repo's own AI-tell linter:
  `"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" "Shreyas_Ionic_AMC\..\.claude\skills\style-lint\scripts\lint.py" <path-to-draft-file>`
  (from repo root `C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500`). Target: 0 findings, 0 em-dashes. Fix anything flagged before showing it. The banned-word/pattern list is at `.claude\skills\style-lint\data\taxonomy.json` if you want to self-check by eye too.
- No em-dashes, no rule-of-three lists, no "delve/leverage/robust/landscape"-class words, no chatbot-ish phrasing ("let's dive in," "here's the thing," "the result?"). Full list in the taxonomy file above.

## Verified facts to use (already confirmed true as of 2026-07-21 — no need to re-derive, but source paths given if you want to pull an exact quote)
- **28 specialized AI agent personas**, each with one narrow job, mirroring a real buy-side org: a CIO-equivalent role with risk veto power, 3 fund-manager-equivalent roles, a quant lead, a technical/chart lead, 5 sector analysts, a compliance officer, a risk manager, a macro strategist, a derivatives structurer, an ops engineer, a data officer, an execution/cost analyst, a "librarian" for institutional knowledge, an attribution analyst, a product lead, an overfit/statistics specialist, a hedging lead, and one agent whose only job is adversarial: try to kill every result before it's trusted. (Source: `.claude/agents/*.md`, 28 files + 2 unrelated utility personas.)
- **81 reusable custom-built skills** (repeatable workflows), roughly: 25 for research/validation (catching lookahead bias, checking for overfitting, cost-realism modeling, adversarial red-teaming), 16 for risk/ops cadence, 12 for team governance and self-improvement, 15 general engineering-discipline skills (planning, TDD, code review), 8 for design/brand, 5 for data/token efficiency. (Source: `.claude/skills/`, 81 folders.)
- **An 8-gate research pipeline** every idea must pass through, in order: intake → triage → cheapest-possible falsification test → full backtest with a statistical validation battery → adversarial red-team review → committee memo → paper-trading period → live (this last gate requires a specific human sign-off, never automatic). (Source: `Shreyas_Ionic_AMC/04_RND_LAB/IDEA_PIPELINE.md`.)
- **THE HEADLINE ANGLE — the "skill of skill" layer.** A cluster of skills whose job is to grow the system's own capability, not do research directly:
  - one skill watches ongoing work for recurring patterns worth turning into a brand-new reusable skill
  - one skill goes and finds/adopts skills other people already built, instead of reinventing them
  - one skill takes an underperforming skill/prompt and rewrites it in a single bounded, evidence-based pass (not just "make it better" — has to show why)
  - one skill onboards an entirely new specialized agent end to end when a real capability gap is found
  A meaningful share of the 81 skills were proposed by this layer, not hand-written from scratch. This is the most differentiated, least-obvious-to-outsiders detail — lead with it in the companion doc.
- **Runs across two separate coordinating sessions** (think: two people who never talk directly, coordinating entirely through a shared, versioned set of files) — a real distributed-coordination problem, not just "an AI wrote some code."
- **Self-audit finding (authentic, not boastful):** running a full bug audit on the system this week found real gaps even in the heavily-engineered parts — e.g., a risk-limit check that computed the correct number but never actually enforced it, and a bias-detection script that couldn't catch the exact pattern it was built for once the input was shaped slightly differently. Nothing catastrophic (paper-only, zero real capital), but a clean "the guardrail existing and the guardrail working are different claims" beat. Good for the doc's closing/reflection section.
- Dozens of research ideas have been formally killed with logged reasons and explicit conditions under which they could be revisited — evidence of real discipline, not just enthusiasm. (Source: `Shreyas_Ionic_AMC/04_RND_LAB/KILLED_IDEAS.md`.)

## Deliverable 1 — LinkedIn post: DONE, just sanity-check
Already written and lint-clean (0 findings, 315 words). Use as-is unless Shreyas asks for changes:

---
Three weeks ago I started building an AI system that runs like a small investment research desk. It's grown into something I didn't expect: a system that also decides what it needs to get better at, on its own.

Twenty-eight AI agents, each with one job. A CIO who can veto anything on risk grounds. A quant lead who owns statistical validity. Sector analysts. A compliance officer. One agent whose only role is to try to kill every result before it gets trusted.

Every idea moves through the same gate: cheap test first, full backtest only if that survives, then an adversarial review built to find the one reason it might be fake, before anything gets written down as a decision.

The agents weren't what got me. It was watching the system start managing its own toolkit. One skill just watches the work and flags patterns worth turning into a new reusable skill. Another goes and finds skills other people already built instead of reinventing them. A third takes a skill that isn't performing and rewrites it in one bounded, evidence-based pass, not by vibes. Eighty-one of these skills exist now, and a good number were proposed by the system itself, not by me.

Running a full audit on the whole thing this week turned up real gaps too. A risk check that computed the right limit but never enforced it. A bias detector that missed the exact pattern it was built to catch, under a slightly different input shape. Nothing that touches real money, this runs entirely on paper, but a reminder that "we built a guardrail" and "the guardrail works" are two very different claims.

Still working out what all of this is actually good for. But building something that argues with itself before it lets me trust a result has changed how I think about research discipline, full stop.
---

## Deliverable 2 — 1-3 page companion document (Word .docx, PDF also fine)
Use the `docx` skill (Anthropic skill, triggers on any .docx request). Suggested arc:
- **Page 1:** hook (can reuse the post's opening two lines) + one clean diagram (see Deliverable 3) + 3-4 stat callouts as a simple row (28 agents / 81 skills / 8 gates / 2 coordinating sessions) — visual, not a wall of text.
- **Page 2:** the "skill of skill" layer in more depth — this is the differentiated content, give it room. Can use a simple labeled loop or numbered flow (watch → propose → author → refine) if it helps rather than another paragraph block.
- **Page 3 (optional, only if it earns its place):** the self-audit finding as a short "what I got wrong" sidebar, then a brief personal reflection close. Cut this page if 2 pages already tell the story well — do not pad to hit 3.
Keep visual design clean and professional; do not reuse any firm-specific branding/colors/logo (there is no firm name in this public-facing piece — see hard constraint 1). A neutral, modern, personal-brand-appropriate look is right.

## Deliverable 3 — one image/diagram
Pick ONE, whichever tells the story with less clutter (your call, but justify it in one line when you present it):
(a) a simplified org chart (Principal → oversight roles → specialist roles), or
(b) the 8-gate pipeline as a left-to-right flow, or
(c) the "skill of skill" loop (watch → propose → author → refine → back into the system) — arguably the most novel visual since it's the least generic.
Repo already has `design`, `design-system`, `slides`, and `banner-design` skills that can build a clean HTML-based diagram/graphic — use one rather than hand-drawing SVG paths. Keep it to one idea, well-executed, not a busy infographic.

## Where to save output
`Shreyas_Ionic_AMC/10_BRAND_DESK/drafts/` (matches the existing draft→approved convention in this repo). Do not mark anything "published" — Shreyas reviews and posts manually per his own house rule (system delivers content, never auto-posts).

## Budget note
Shreyas is low on tokens for the remainder of this week — work efficiently: reuse the verified facts above rather than re-deriving them, batch file reads, and check in with a finished draft rather than iterating live with him unless he asks for changes.
