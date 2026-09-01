# Personalization vs. Standardization — the actual fault line (2026-07-29)

Grounded in this session's real bug history (2026-07-27 through 2026-07-29, ~30 fixes across the
pr_template pipeline), not generic advice. Every fix this session lands on ONE of two sides of a
single dividing line — recognizing which side a piece of code is on, on sight, is the whole game.

## The rule: standardize the FORMULA, personalize the DATA, never standardize the OUTPUT

A module is safe exactly when its Python code contains **zero client-specific facts** — every
number, name, and verdict it prints must trace back to a `ctx[...]` lookup. A module is a latent
bug the moment it contains a fact that happens to be true for the demo client (or the first real
client) but isn't derived from `ctx` for every client. This session's entire bug list is one
pattern repeated ~15 times:

| Module | The bug (standardized OUTPUT, should've been a formula over DATA) |
|---|---|
| `house_view_fit.py` | Hardcoded prose ("28% seeds a global sleeve... two positions trimmed") — confirmed FALSE for the real client; not derived from `ctx["deployment"]`/`ctx["totals"]` at all |
| `annex_mcap_migration.py` | `TRIM_PT = 2.0` constant applied regardless of whether any trim actually happened |
| `annex_goal_mapping.py` | A second, independent flat `MU,SIGMA=12,14` — literally the same bug `growth_projection.py` had already been fixed for, re-typed by hand into a sibling module |
| `opportunity_set.py` (pre-cut) | `today = [0.80,0.03,0.12,0.05]` — authored to match the DEMO's assumed gaps, not derived from the real client's mix |
| `annex_stress_scenarios.py` | `TODAY`/`PROP` drawdown arrays hardcoded outright — deleted, not fixable |
| `data/client_b.py` (fund placeholders) | `(f3,f1,b3,b1)=(0,0,0,0)` "no research run" marker fed straight into `cagr3y`/`alpha_ann` as if 0% were a real finding |
| `fund_actions.py`, `tax_impact.py` | Layout math hand-tuned for "~2 non-Hold funds" — broke the instant a real client's constraint produced 7 |

None of these were sloppy code. Every one was **correct for the exact client shape the author had
in front of them** and silently wrong for a different shape. That is the actual risk in this
pipeline — not syntax errors, not crashes (those get caught fast), but **content that is accidentally
standardized when it should have been a formula over real data**. It reads as polished and
confident right up until a client's numbers don't match the assumption baked in.

## Why this is a token-efficiency question, not just a quality one

The whole economic case for this template engine is: **research costs tokens once per client,
rendering costs ~zero tokens forever.** That promise only holds if every module is a pure function
of `ctx`. Every bug above broke that promise in a specific way — it turned a "should be free"
render into a "found by an expensive audit, or worse, by the client" render. Concretely:

- **7 modules had to be re-diagnosed and re-fixed after already reaching a real client's build.**
  Each cost a full research→fix→rebuild→re-gate→re-screenshot cycle — the single most expensive
  loop in this whole pipeline, and one that a correctly-written module never triggers at all.
- **The audits that caught these (3 rounds, ~9 parallel Sonnet agents across 2 days) are
  themselves the token cost of NOT having caught the pattern at write-time.** An audit is what you
  pay when standardization-that-should-have-been-personalization already shipped once.
- **Two of these bugs (`annex_goal_mapping`'s flat rate, `fund_category_rules`/`scheme_overlap_full`
  page-26 mix-up) were literally the SAME class of mistake recurring** — the flat-rate one is the
  clearest: `growth_projection.py` was fixed for exactly this bug one day, and the identical bug
  was found hand-typed into a sibling module the next day. That's a design smell (duplicated
  formula, not shared), not a one-off typo.

## What "personalization" should actually cost tokens on — and what it shouldn't

**Should cost tokens (real, irreducible, per-client):**
- Researching real stock/fund calls (analyst judgment on Sell/Hold/verdict) — this is the firm's
  actual investment work, never automate away the judgment itself.
- Composing an honest fallback SENTENCE when data doesn't exist for a given client (deciding what
  "no foreign sleeve funded yet" should say) — this is design work, done once per fallback branch,
  not once per client.
- The occasional genuinely-novel client shape that needs a NEW module or a NEW ctx field designed
  from scratch (e.g., yesterday's IPS-v2 richer schema, or today's stocks-vs-funds matrix-cap
  split) — real design decisions, correctly Sonnet-tier, correctly token-costing.

**Should NOT cost tokens (but has been, repeatedly, this session):**
- Re-deriving a value a shared formula already computes correctly (the `_derive_mu_sigma()` /
  `_lookthrough_mix()` pattern — write the formula ONCE, import it everywhere it's needed, per
  the firm's own "consolidate reused code" convention — `opportunity_set.py` already does this
  correctly for `_lookthrough_mix()`; `annex_goal_mapping.py` did NOT do this for mu/sigma until
  caught).
- Rediscovering the same layout-fragility bug per module (fixed-y callouts colliding with a
  variable-height table above them — happened in `tax_impact.py`, and the pattern likely exists
  in more of the ~57 modules that haven't been stress-tested against an atypical row count yet).
- Rebuilding+re-screenshotting the WHOLE 75-slide deck to verify a 1-module fix — still the
  default workflow this session, and still the single most repeated expensive step across ~30
  rebuild iterations in 3 days (see TOKEN_TIME_OPTIMIZATION.md Rec #2/#3, still open).

## Concrete recommendations (ranked by leverage, not effort)

### 1. A "no bare literals in client-facing text" write-time discipline (HIGHEST leverage)
Before writing a module, every number/name/percentage/asset-class-list that appears in a client-
facing string must be traceable to a `ctx[...]` read in the same function. If it's a genuine
constant (a disclosed CMA assumption, a regulatory rate), it must carry an explicit
`[ILLUSTRATIVE]` tag or a `Not a claim about this client's holdings` disclosure — the deck already
has this convention (8 of the annexure modules do this correctly, disclosed and fine); the bug is
ALWAYS a hardcoded fact presented as if derived, never a disclosed constant. This is a discipline,
not a tool — but it is exactly the discipline that would have prevented every bug in the table
above at write-time, for zero tokens, instead of at audit-time for a full Sonnet-agent pass.

### 2. A cheap static-analysis pre-flight, not another LLM audit (HIGH leverage, LOW cost)
Most of the bugs above are mechanically detectable without an agent at all: a module containing a
numeric literal (not `0`, `1`, `100`, or an obvious loop index) inside an f-string or `deck.txt`/
`deck.callout` call, where that literal is NOT read from a variable traced to `ctx`, is a
candidate. This is a ~50-line AST-based Python script (`ast.parse` each `modules/*.py`, walk
`Constant` nodes inside string-formatting calls, flag ones not fed by a `ctx[...]`-derived name)
— cheaper than the audit-agent pattern used the last 2 days, runs in seconds, and catches this
EXACT bug class before a single token is spent on research or an agent dispatch. Recommend
building this as `lint_hardcoded_content.py` alongside `check_geometry.py`/`tellscan.py` — a
fourth deterministic gate, not a fourth LLM pass.

### 3. One shared formula module, not N independent ones (MEDIUM-HIGH leverage)
`_derive_mu_sigma()` and `_lookthrough_mix()` already prove the right pattern (write once in the
module that owns the concept, `from modules.X import _fn` everywhere else that needs it) but it's
ad hoc — each was discovered as a fix, not designed as policy. Recommend a `modules/_shared.py` (or
promote to `lib/` per the firm's existing convention) housing every cross-module formula
(expected-return/vol, look-through allocation, single-scheme/AMC concentration, SENTINEL-flag
translation — `FLAB`/`_FLAB`/`_FLAG_READ` are three near-duplicate dicts across `fund_book_scored.py`/
`scheme_scorecards.py`/`funds_hybrid.py` today, already flagged in yesterday's audit, not yet
consolidated) so a fix to the formula is a fix everywhere, not a fix-then-audit-to-find-the-copies.

### 4. Fuzz the module library against synthetic edge-case client shapes, before a real client hits them
Every layout/crash bug this session (`annex_concentration_curve.py`'s <5-holding IndexError,
`funds_hybrid.py`'s empty-list crash, `fund_actions.py`/`tax_impact.py`'s row-count-scaling
collapse) was found AFTER it reached a real client's specific shape. A cheap, standing fix: keep
2-3 synthetic `data/_fuzz_*.py` ctx builders (zero direct-equity/fund-only client; 30-fund/40-
holding mega-client; single-sector/single-fund thin client) and run every tier build against them
as a pre-flight whenever a module changes — a few seconds of deterministic script time that would
have caught essentially every crash-class bug in this document before it needed an audit to find.

### 5. Still-open recommendations from 2026-07-27's review, now higher-priority given 2 more days of
evidence: **diff-based visual QA** (Rec #3 there) and **per-module render caching** (Rec #2) — the
~30 rebuild-and-rescan cycles across the last 3 days are the largest single time/token sink in
this pipeline, and every one of them re-renders and re-reviews slides that didn't change. This is
no longer a nice-to-have; it is now the largest remaining lever, full stop.

## The one-sentence version

**Every bug this session was a fact that should have been a formula — write the formula, feed it
real data, and the personalization is free forever; skip that discipline, and every atypical
client pays for it with a fresh audit.**
