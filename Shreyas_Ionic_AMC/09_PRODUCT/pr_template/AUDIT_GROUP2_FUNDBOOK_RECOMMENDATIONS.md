# Audit Group 2 — Fund Book & Recommendations modules

Scope: 16 assigned modules + 3 parked (cost, fund_overlap, fund_quality_alloc). Full-file reads, no code changes made.

| Module | Classification | Model tier | Top issue (1 line) |
|---|---|---|---|
| fund_book_scored.py | NEEDS_CODE_CHANGES | Sonnet (schema+pagination logic) | `is_demo` defaults `True` — real client with the field unset prints "Illustrative synthetic funds." |
| funds_equity.py | NEEDS_CODE_CHANGES | Sonnet | `dcap = [f["down_capture"] for f in act]` has no None-filter — one fund with no down-capture history crashes the chart |
| funds_hybrid.py | NEEDS_CODE_CHANGES | Sonnet | Dead code `min()/max()` over `hyb` crashes on a client with zero hybrid funds |
| fund_category_rules.py | NEEDS_CODE_CHANGES | Sonnet | Only the `is_demo` default-True tag; rule logic itself is clean and ctx-derived |
| scheme_overlap_full.py | DATA_ONLY | Haiku (once real look-through lands) | Hash-based fabricated overlap number, honestly double-disclosed as illustrative |
| fund_actions.py | NEEDS_CODE_CHANGES | Sonnet | Raw SENTINEL flag codes (`CLOSET_INDEX`, `NEG_ALPHA`...) printed unstranslated — jargon leak |
| house_view_fit.py | NEEDS_CODE_CHANGES | Sonnet (judgment, not template) | Hardcoded "what the plan does" text is FALSE for the real Anand Reddy deck — see Top Findings #1 |
| tax_impact.py | SAFE_AS_IS | Haiku | Well-built; no `is_demo` tag at all (inconsistent with siblings, not harmful) |
| priority_actions.py | NEEDS_CODE_CHANGES | Sonnet | `is_demo` default-True same class as above; otherwise solid, ctx-derived math |
| growth_projection.py | SAFE_AS_IS | Sonnet (formula already correct) | Already fixed per brief; capped, disclosed fallbacks, no further issue found |
| data_notes.py | SAFE_AS_IS | Sonnet | Silent truncation past y=6.6 drops flags with no "+N more" notice |
| deployment.py | SAFE_AS_IS | Sonnet (narrative) | No risk/drawdown claim attached to cash-park — does not repeat the stress_scenarios bias |
| before_after.py | SAFE_AS_IS | Sonnet | Mix-shift only, explicitly "not redeployed"; do not let a risk metric get bolted onto this later |
| opportunity_set.py | NEEDS_CODE_CHANGES | Sonnet | Hardcoded `today = [0.80, 0.03, 0.12, 0.05]` presented as the client's real mix — see Top Findings #2 |
| quality_vs_price.py | SAFE_AS_IS | Haiku | Real per-holding pe/roe, correctly None-filtered |
| appendix.py | SAFE_AS_IS | Haiku | Methodology-only; `is_demo` default-True tag only issue |
| cost.py (parked) | REDUNDANT_CANDIDATE | Haiku | Real computed TER math; stay parked — overlaps fund-action cost framing |
| fund_overlap.py (parked) | NEEDS_CODE_CHANGES (if resurrected) | Sonnet | Should be RESURRECTED via mf-lookthrough, not left cut — see Top Findings #4 |
| fund_quality_alloc.py (parked) | NEEDS_CODE_CHANGES (if resurrected) | Sonnet | Unconditional "Synthetic demo funds." hardcoded in source line — would mislabel a real client |

## TOP FINDINGS (severity order)

**1. `house_view_fit.py` PLAN dict — hardcoded content, confirmed FALSE on the real Anand Reddy deck (same bug class as stress_scenarios).**
Lines 11-17: the `PLAN` dict hardcodes both the narrative AND the "Aligned/Gap" verdict per house-view dimension, e.g. `"Foreign equity": ("~28% of net proceeds seeds a global sleeve, a first step; the full ~15% target is phased over cycles.", "Gap")` and `"Gold & silver": ("New gold–silver sleeve (75:25) added from proceeds; still building toward the ~5% target.", "Gap")` and `"Domestic equity": ("...the two >11% positions trimmed toward guideline.", "Aligned")`. This text renders unconditionally in the table's "What the plan does" column for every register (not gated to non-simple). `house_view_fit` is a CORE module in RM_SIMPLE (`tiers.py` line 59), and Anand Reddy's deck was built on RM_SIMPLE. His actual `data/anand_reddy.py` ctx (lines 634-636) shows `"deployment": {"sleeves": [("Liquid / cash", proceeds, "Parked pending client discussion...")]}` — proceeds are 100% parked in cash, NO global sleeve, NO gold-silver sleeve exist. His `totals` also show `"n_trim": 0` (line 617) — zero trims happened, contradicting "the two >11% positions trimmed." **This means the shipped Anand Reddy deck told him money was already being deployed into foreign-equity and gold-silver sleeves and that two oversized positions had been trimmed, none of which is true.** Fix: derive `plan_txt`/`fit` per-dimension from `ctx["deployment"]["sleeves"]`, `ctx["totals"]["n_trim"]`, and `ctx["ips"]["alloc_bands"]` — the module already has a working generic fallback path (lines 48-50) that does this correctly; the 5 named dimensions need the same treatment, not static prose.

**2. `opportunity_set.py` — hardcoded "Today" allocation presented as the client's real mix.**
Lines 24-25: `today = [0.80, 0.03, 0.12, 0.05]` is a fixed constant, never derived from `ctx["totals"]` (which carries real `eq_pct`/`mf_pct`/`cash_pct` and is used correctly for this exact purpose in `before_after.py`). The callout text (lines 36, 42) asserts "Your mix today... leans almost entirely on Indian shares" / "The book today... is concentrated in Indian equity" as if computed from the client's real holdings — for any client whose actual eq/mf/cash split differs from 80/3/12/5, this is a false claim of the same kind as the cut `stress_scenarios` bug (hardcoded numbers dressed as real). The `mu`/`sigma`/`corr` arrays are fine — they are honestly labeled "Illustrative long-run capital-market assumptions" in the source line (line 47) and are genuinely a global CMA, not client data. Fix: replace `today` with `[t["eq_pct"]/100, foreign_pct, debt_pct, gold_pct]` from ctx totals (foreign/gold currently have no ctx field — flag as a data gap if so, don't fabricate).

**3. `fund_actions.py` — raw internal flag codes leak to the client (jargon-leak, violates the standing tellscan rule).**
Line 50: `flags = "  ·  ".join(f["flags"]) if f["flags"] else "structural"` prints the raw SENTINEL codes (`CLOSET_INDEX`, `NEG_ALPHA`, `DOWN_CAP_HI`, etc.) directly. Both `fund_book_scored.py` (its own `FLAB` dict, line 10-13, with a comment "flag chips read as PLAIN WORDS (leak audit 2026-07-26), never engine codes") and `scheme_scorecards.py` (`_FLAB`, duplicated) already translate these to plain words. `fund_actions.py` was missed. Fix: import/reuse the same translation dict (this is also a "consolidate reused code" candidate — `FLAB`/`_FLAB`/`_FLAG_READ` are three near-identical copies across `fund_book_scored.py`, `scheme_scorecards.py`, and `funds_hybrid.py`; belongs in a shared `lib/fund_flags.py`).

**4. `fund_overlap.py` (parked) should be resurrected via the new `mf-lookthrough` skill — the more decision-relevant overlap module is cut while the weaker, fabricated one is live.**
`fund_overlap.py`'s "stocks held both directly and via funds" double-pay table is exactly what the `mf-lookthrough` skill (`(SKILL.md description: "the double-pay table (stocks held both directly and inside funds)")` now computes, but no monthly-portfolio-disclosure data has actually been ingested yet (no `monthly_portfolio*` file found in the repo), so parking it was correct at cut-time. What's inconsistent: `scheme_overlap_full.py` — whose own `_ov()` function (lines 21-34) fabricates its overlap score from a **hash of the fund-name pair** (`h = abs(hash(...)) % 14`), not any real computation — was moved INTO the main deck (Section 3, "The Fund Book", per the 2026-07-27 Principal ruling) as "supporting evidence for the action call," while `fund_overlap.py`, which the same commit's docstring calls "the decision-relevant one," stays cut. Recommend: wire `fund_overlap.py` to real `mf-lookthrough` output once that data lands, and reconsider whether a hash-fabricated chart belongs positioned as "supporting evidence" in the main deck at all (it is disclosed as illustrative in small print, but its prominence now outweighs that disclosure).

**5. Systemic: `ctx.get("is_demo", True)` default is backwards and appears in 19 modules firm-wide (7 in this group's scope: fund_book_scored, funds_equity, funds_hybrid, fund_category_rules, fund_actions, house_view_fit, priority_actions, appendix, cost, fund_quality_alloc).**
Only `data/anand_reddy.py` explicitly sets `"is_demo": False` (line 595, with the comment "real client — modules must not print illustrative/synthetic text"). `client_intake.py` (the automated real-client pipeline) does not set `is_demo` anywhere. If a future real client's `client_ctx.json` omits the key, every one of these 19 modules will silently default to `True` and print "Illustrative synthetic funds" / "AZBY demo" disclaimers on a real client's deck. Fix belongs in `client_intake.py` (always emit `is_demo: False` explicitly) as the single point of truth, not in each module — but each module's `True` default should also flip to `False` as defense-in-depth, since a missing key should never silently mean "treat as demo."

**6. `fund_quality_alloc.py` (parked) — unconditional demo label, would mislabel a real client if ever resurrected.**
Line 66: `"...Quality = fund score. Synthetic demo funds."` is a hardcoded string suffix, not gated on `ctx.get("is_demo")` at all (unlike every other module's conditional `demo_tag`). Must be fixed before any resurrection.

**7. `funds_hybrid.py` — crash risk on a client with zero hybrid funds (dead code).**
Lines 183-184 compute `worst = min(hyb, key=...)` and `best = max(hyb, key=...)` but neither variable is referenced again anywhere in the function. `min()`/`max()` raise `ValueError` on an empty sequence — a first-review client who simply doesn't hold hybrid funds (common) will crash the whole module. Delete the two dead lines; no functional loss.

**8. `funds_equity.py` — down-capture chart has no None-guard.**
Line 60: `dcap = [f["down_capture"] for f in act]` is passed straight into `CH.paired_bar` with no filtering. Per root CLAUDE.md's DATA LANDMINES, `down_capture` is frequently `None` for real clients (thin fund NAV history firm-wide). One such fund in the active-fund list will pass `None` into a numeric chart, which will error. Fix: filter `act` to `down_capture is not None` before charting, same pattern already used correctly for `bfunds`/`cagr3y` two lines above (line 39).

**9. `data_notes.py` — silent truncation, no "+N more" indicator.**
Line 80-81: `if y + h > 6.6: break` silently drops any flags beyond page capacity with no indication to the reader or the RM that content was cut. Low severity (guards against overflow correctly) but worth a one-line "N more flags on file, see RM" fallback for a data-heavy real client.

## Parked-module verdict (cost.py, fund_overlap.py, fund_quality_alloc.py)
- **cost.py**: keep parked. Computation is real and correct (`ctx["cost"]["rows"]`, weighted TER), not a bug — it was cut for scope reasons (no Regular-drag/PMS overlay), and that gap is now covered qualitatively by fund-action cost-hygiene framing. Redundant as a standalone slide today.
- **fund_overlap.py**: candidate for resurrection, not deletion — it is the more decision-relevant of the two overlap modules and now has a real computation path (`mf-lookthrough` skill) once portfolio-disclosure data is ingested. Do not resurrect until that data exists (would otherwise repeat the hash-fabrication problem).
- **fund_quality_alloc.py**: keep parked; fix finding #6 first if it's ever revived. The quadrant concept (quality × allocation-gap) is sound and not duplicated elsewhere in the current core deck.
