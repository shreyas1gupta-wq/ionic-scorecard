# Model-tier assignment for the NDPMS deck pipeline (2026-07-28)

Every future deck is client-facing (Ionic Wealth letterhead) — zero tolerance for errors. That
does NOT mean "use Opus everywhere." It means: use the cheapest tier that cannot produce a wrong
or half-baked result for that specific step, and gate anything genuinely judgment-heavy behind a
Sonnet/Opus pass + the QA LAW (render_preview look, geometry x2, tellscan, cross-panel, sign-off)
regardless of which model did the work. Per D-036 (this firm's own benchmark): Sonnet ties or
beats Opus on review-type work at ~1/10-1/15th cost — Opus is reserved for genuine high-ambiguity
judgment, not a default quality dial.

## Haiku-appropriate (mechanical, deterministic-adjacent, high parallelism safe)

| Step | Why Haiku is safe |
|---|---|
| Running `check_geometry.py`/`check_geometry2.py`/`tellscan.py` and reporting pass/fail + a punch list | Pure script output summarization — zero interpretation needed, the script already decided |
| Running `pptx_to_pdf.py`, checking exit code/file size | Mechanical pipeline step |
| `client_intake.py --holdings <file>` matching + `pf_qual_*.json` lookups per matched symbol | File I/O + exact-match joins, schema is fixed |
| `fund_ctx_adapter.py` QFRA-1/QFRA-2 joins for a new client | Same — deterministic join against curated CSVs |
| Wiring already-researched real fields into a client's `data/<client>.py` ctx file, ONCE a clear mapping/spec is given (e.g. "put full750_scored.csv's pe_current into equity[i].pe for these 19 symbols") | Mechanical field substitution against an explicit spec — the judgment (which source, which fallback) was already made by a human/Sonnet pass; Haiku just executes the mapping |
| Re-running `build_<client>.py` across tiers and reporting manifest slide counts / [ERR] lines | Script output transcription |
| Flagging which of a client's holdings are OUT of the 750-scorecard/QFRA universe (a lookup, not a judgment) | Set-membership check |
| Rendering `render_preview.py` PNGs and doing a first-pass mechanical scan for obviously blank/broken slides (all-white, giant red X, empty chart) | Visual pattern match, not content judgment |

**Parallelism note:** these are genuinely safe to fan out with many Haiku agents (e.g. one per
client in a bulk-refresh run) since each is independent and mechanically checkable — but the
firm's D-023 rule caps ANY session at 3 concurrent agents regardless of model tier. If bulk usage
(e.g. refreshing 20 clients' decks in one run) is a real near-term need, that cap should be
revisited explicitly with the Principal/CIO (D-025 joint-approval class), not silently raised.

## Sonnet-appropriate (real judgment, but bounded/checkable)

| Step | Why Sonnet, not Haiku |
|---|---|
| Module hardening — deciding what an honest fallback sentence should say when data is missing (e.g. "no allocation targets on file yet" vs crashing) | Requires composing new, client-safe prose that reads naturally, not just substitution |
| Root-causing a geometry-checker or tellscan finding to its actual source line | Needs to trace data flow through a module, not just read an error string |
| Cross-panel consistency checks ("do these two numbers on different slides actually reconcile") | Requires holding two pieces of context in mind and comparing meaning, not just string-matching |
| This session's full-library audit (3 agents, ~47 modules) | Hunting for a SUBTLE bias pattern (sell-only mix always looking better) requires understanding the mechanism, not pattern-matching a known bad string |
| Scrubbing internal-audit-trail prose into client-safe rationale (the `_scrub_client_text` class of fix) | Judgment on what to keep vs cut from a real analyst's sentence |
| Deciding fund/stock Sell-Hold calls from real quant + qualitative inputs (analyst-agent work) | Genuine analytical judgment, this firm's actual investment work |
| Building/upgrading skill documentation, tier configs, new pipeline steps (like this session's `tellscan.py`, the intake-workflow spec) | Design work with real tradeoffs |

## Opus-appropriate (high-ambiguity, capital/reputation-facing, rare)

| Step | Why Opus |
|---|---|
| Final client-safe copy sign-off — "does this still lean with the call, would the Principal wince reading this to the client" | The one place a wrong call is expensive (client-facing, firm reputation) and the judgment is genuinely hard to bound with a checklist |
| Adjudicating a genuinely novel escalation (e.g. a holding with conflicting quant/qualitative signals, no precedent in the frozen methodology) | Same D-036 logic as elsewhere in this firm: reserve Opus for CIO/IC-class judgment, not routine review |
| Designing a NEW systemic rule (like today's factor-fund Sell/Hold policy) where getting it wrong propagates to every future client | High blast-radius, worth the higher cost once, not per-build |

**What this deliberately does NOT include:** routine QA-gate running, mechanical data-wiring,
PDF conversion, or slide-count reporting. If Opus is being used for any of those today, that's
the single highest-value model-tier reassignment available — same logic as D-036's Red-Team move.

## Concrete example: this session, correctly tiered in hindsight

- Data-availability inventory + real-field extraction (2 research agents, earlier session) →
  correctly Sonnet (real research judgment on data quality/coverage).
- Module-hardening code changes (1 agent) → correctly Sonnet (composing fallback prose).
- This audit (3 agents, current) → correctly Sonnet (bias-pattern hunting).
- Running the QA gates and reporting slide counts after each of ~13 rebuild iterations → **this
  was done by the main thread directly via Bash, not delegated** — in a bulk/multi-client context
  this exact step (run script, report numbers) is the clearest Haiku-delegation opportunity on
  the table and wasn't exploited this session because it's cheap enough inline for one client;
  it becomes worth delegating specifically when running the SAME mechanical step across many
  clients in parallel.
