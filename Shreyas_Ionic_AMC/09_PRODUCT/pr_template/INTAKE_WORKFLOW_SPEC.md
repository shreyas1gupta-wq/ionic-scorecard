# NDPMS Intake Workflow — design spec (per Principal ask, 2026-07-27)

Governs a new "Step 0" for the `ndpms-deck` skill: what to ask an advisor when they upload a
holdings file, how tier + customize selection works, and what runs unattended in parallel so
the advisor's wait time is spent on Python assembly, not research.

## 1. The intake question set (asked together, one batch, right after upload)

Distinct from `client_intake.py --profile` (which carries the *structured* personalization
JSON: goals/timelines, holding ages/costs, family structure, meeting_history — filled once,
reused on every future review). These 4 are the lightweight *per-build* questions an advisor
answers every time, because they change build-to-build even for the same client.

**Q1 — Deck depth (always asked, single-select):**
> "Which deck depth does this client need?"
> - **Detailed (60–100 pages)** — full methodology, every annexure chart, holding-level detail. Family office / sophisticated HNI.
> - **Medium (30–60 pages)** — professional review, core annexures only. Typical NDPMS client.
> - **RM Light (15–30 pages)** — plain-language essentials. RM-led / newer investor.

**Q2 — First review or follow-up (single-select):**
> "Is this a first review for this client, or a follow-up?"
> - First review (no prior deck on file)
> - Follow-up — have last review's numbers to compare
>
> If "Follow-up" and `meeting_history` isn't already in the profile, prompt once for the prior
> snapshot (date + key numbers) — this is what lights up `since_last_review`.

**Q3 — Anything to exclude or downplay (multi-select + free text):**
> "Anything to exclude or go light on for this client?"
> - None
> - No tax-slide detail (tax-sensitive)
> - No methodology/scoring detail (keep it simple)
> - Other (type it)

**Q4 — Timeline / output (single-select + optional add-on):**
> "Turnaround and output?"
> - Standard turnaround
> - Needed today — bias toward the tier's core, skip discretionary annexure
> - Also export a PDF alongside the PPTX

That's 4 questions, one screen, before any deck-scope discussion. Q1's answer alone doesn't
build anything yet — it only unlocks §3 below.

## 2. Tier mapping — confirmed against real builds, no `tiers.py` changes needed

| Named tier (Principal) | Page band | Existing preset | Confirmed slide counts |
|---|---|---|---|
| Detailed | 60–100 | `HNI_DEEP` | Demo 61→79 slides (module library grew); **real client (Anand Reddy) build = 82 slides** |
| Medium | 30–60 | `STANDARD` | **40 slides**, stable across the 2026-07-25 and current build (PROGRESS.md log) — mid-band, comfortable headroom both directions |
| RM Light | 15–30 | `RM_SIMPLE` | Demo = 31 slides; **real client build = 23 slides** |

All three map directly onto the existing presets — no new tier machinery required. One
caveat: RM_SIMPLE's demo run (31) sits one slide over the 30-page ceiling; the real client run
(23) came in comfortably under it. The overshoot is pagination-driven (large books push
`sell_list`/`equity_book`/`fund_actions` past 5-rows-per-slide), not module selection — so it's
not a preset bug. Action: if a client's holdings count is unusually large, warn the advisor at
build time that RM Light may print >30 pages and offer Medium instead; don't change
`RM_SIMPLE["optional_on"]` or `skip_core` to chase the ceiling artificially.

## 3. Recommended vs Customize

After Q1, ask one follow-up:
> "Use the [tier]'s recommended slide set, or customize which pages go in?"
> - **Recommended** — ship the tier's current preset as-is (Section 2 above). Zero more questions.
> - **Customize** — see the checklist below.

**Checklist design.** Two different things get checked, depending on tier:
- **Section 5 (Annexure)** — always fully exposed, all ~25 currently-live optional modules
  (i.e. `HNI_DEEP`'s `optional_on` set — the full annexure catalog; parked modules
  `fund_quality_alloc`/`fund_overlap` and Principal-cut modules — seasonality, drawdown-history,
  sip-vs-lumpsum, fee-compounding, tax-lot-aging, glossary — are **not shown**, they're retired,
  not selectable). Every row tagged **(recommended)** if it's in *this build's* tier's
  `optional_on`, unmarked otherwise. Advisor toggles freely; nothing here is core, so any
  combination is safe to ship.
- **Sections 0–4 (core)** — only exposed as a checklist for **RM Light**, where `skip_core`
  actively drops 14 modules by default; the advisor can re-add specific ones (e.g. put
  `score_method` back for a client who wants the "how we score" page even in a light deck).
  For Detailed/Medium, core sections 0–4 render unconditionally (`skip_core` is empty in both
  presets) — nothing to customize there, so the checklist starts straight at Annexure.
- Three modules are **never** shown as checkboxes because they're data-conditional, not a
  choice: `since_last_review` (needs `meeting_history`), `group_concentration` (needs a
  promoter group >20% of equity sleeve), `data_notes` (needs actual data-quality flags). They
  self-gate silently either way.

**Worked example — Medium tier, Customize selected:**

```
CUSTOMIZE — Medium tier (STANDARD preset, 40-slide default)
Core sections 0-4 (Understanding / Portfolio X-ray / Equity Book / Fund Book /
What We Would Do) render in full — not customizable at this tier.

Annexure — check to include, uncheck to drop:
  [x] deployment            Transition framework        (recommended)
  [x] before_after           Before/after allocation      (recommended)
  [x] opportunity_set        Illustrative opportunity set (recommended)
  [ ] quality_vs_price       Quality-vs-price scatter
  [ ] factor_profile         Factor exposure profile
  [x] growth_projection      Growth projection            (recommended)
  [x] spotlight_holdings     Holding spotlights (2)        (recommended)
  [ ] holdings_detail        Every holding, scored (long)
  [ ] sell_cards             Full sell rationale cards
  [ ] scheme_overlap_full    Full scheme overlap detail
  [ ] scheme_scorecards      Per-scheme scorecards
  [ ] annex_score_vs_call    Score vs call scatter
  [ ] annex_valuation_bands  Valuation-band illustration
  [ ] annex_returns_quilt    Returns quilt
  [ ] annex_correlation      Correlation matrix
  [ ] annex_risk_contribution Risk-contribution chart
  [ ] annex_stress_scenarios Stress-scenario table
  [ ] annex_beta_ladder      Beta ladder
  [ ] annex_concentration_curve Concentration curve
  [ ] annex_liquidity_ladder Liquidity ladder
  [ ] annex_currency_geo     Currency/geography split
  [ ] annex_mcap_migration   Market-cap migration
  [ ] annex_income_ladder    Income ladder
  [ ] annex_goal_mapping     Goal-mapping page
  [x] appendix               Appendix                    (recommended)
```
(19 additional annexure modules unchecked by default; advisor can add any subset — each added
module is +1 slide typically, some paginate.) This is implementable either as one
`AskUserQuestion` multi-select block (grouped, with the `(recommended)` suffix baked into each
option's label) or as a plain grouped list Claude prints in chat with checkbox notation, whichever
the interaction surface supports at build time.

## 4. Parallel-compute — what happens BEFORE the advisor answers anything

Fire this the instant a holdings file lands, in the *same turn* as asking the 4 questions
(§1) — it needs nothing from the advisor's answers, only the file:

1. `client_intake.py --holdings <file> --out <client_dir>` (with `--emit-template` if no
   profile.json exists yet) → `client_ctx.json` (matched rows) + `exceptions.csv` (unmatched —
   routed to RM, never dropped or fabricated).
2. For every matched equity symbol/ISIN: read `04_RND_LAB/STOCK_SCORECARD_750/results/pf_qual_
   <TICKER>.json` — pull the existing Sell/Hold verdict + score + rationale. Pure file reads,
   ~0 compute.
3. Matched symbols with **no** `pf_qual_*.json` on file → flag as "out-of-universe / needs a
   one-time scoring run" in a queue; do not fabricate a score (epistemic-conduct rule).
4. `fund_ctx_adapter.py` against QFRA-2 (`QFRA2_current.csv`, 40 curated funds) and QFRA-1
   (`mf_capture_recomm.compute_category`) for every held fund → dual-framework merged verdict
   per the Sell-needs-both rule. Funds outside QFRA-2 → flagged "needs a QFRA-2 scoring run"
   (the existing honest-gap rule, not a new one).
5. Compute the module-agnostic aggregates that don't depend on tier or customization at all:
   sector exposure %, mcap positioning, group-concentration check (>20% trigger), cost/TER
   roll-up. These feed `snapshot`/`sector_exposure`/`mcap_positioning`/`cost` regardless of
   which tier eventually gets picked.
6. Write everything above to `<client_dir>/client_ctx.json` (already the schema `build_azby.py`
   consumes) so it survives independent of chat/session state.

By the time the advisor has answered Q1–Q4 and the tier/customize question, steps 1–6 are
already on disk. What's left — `engine.build(ctx, tier_name)` with the module list resolved
from tier defaults ∪ customize deltas — is pure Python, no research, no tokens: assembly only.

## 5. Ready-to-paste SKILL.md section

Insert as a new numbered step **before** the current "1. Intake" line in the `## FULL PIPELINE`
section (renumber existing 1–6 to 2–7):

```markdown
0. **Advisor intake (new — file upload to tier/scope decision).** The instant a holdings file
   is uploaded, in the SAME turn: (a) launch the parallel-compute pass — `client_intake.py`
   match → `pf_qual_*.json` lookups per matched stock → `fund_ctx_adapter.py` QFRA-1/QFRA-2
   verdicts per matched fund → sector/mcap/concentration/cost aggregates — all written to
   `client_ctx.json`/`exceptions.csv` on disk, and (b) ask the advisor 4 short questions: deck
   depth (Detailed 60-100pg = HNI_DEEP / Medium 30-60pg = STANDARD / RM Light 15-30pg =
   RM_SIMPLE), first-review-vs-follow-up (unlocks `since_last_review` if meeting_history is
   supplied), anything to exclude/downplay (tax detail, methodology detail), and turnaround/PDF
   need. Do not wait on (b) to start (a) — they're independent.
   Once deck depth is answered, ask ONE follow-up: Recommended (ship the tier's current preset
   from `tiers.py` as-is) or Customize. Customize shows the ~25 live optional (Annexure)
   modules as a checklist, each tagged **(recommended)** when it's in that tier's `optional_on`;
   for RM_SIMPLE only, also show its 14 `skip_core` modules as re-addable. Parked modules
   (`fund_quality_alloc`, `fund_overlap`) and Principal-cut modules (seasonality,
   drawdown-history, sip-vs-lumpsum, fee-compounding, tax-lot-aging, glossary) are never listed
   — they're retired, not a customize option. By the time this question is answered, step (a)'s
   output is already on disk — the rest of the pipeline is assembly, not research.
```

---
*Design only — no code or SKILL.md edits made. Real anchors used: STANDARD = 40 slides
(PROGRESS.md build log), HNI_DEEP real-client = 82 slides and RM_SIMPLE real-client = 23 slides
(SESSION_JOURNAL.md, 2026-07-27 Anand Reddy entries).*
