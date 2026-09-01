# Audit 2026-07-29 — IPS engine, page-cut hygiene, correlation caps, X-ray/Equity Book sweep

Scope: fresh, skeptical re-check of `pr_template/` per the 5 focus areas requested. No code
edited. Build artifacts in `out/*_audit2.pptx`.

## Severity-ordered findings

### HIGH — `priority_actions.py` row 4 cross-reference is a permanently dead link
`modules/priority_actions.py:113`: `refs = ["tbl:sell_list", "mod:concentration",
"mod:fund_actions", "mod:deployment"]`. The 4th row ("Park net proceeds") pagerefs
`"mod:deployment"`. Only `modules/deployment.py:42` ever calls `deck.anchor("mod:deployment",
s, ...)` — and `deployment.py` is permanently cut (core=False, in no tier's `optional_on`,
confirmed in `tiers.py`/`engine.py`). So this anchor is **never** registered, in any tier, for
any client. `slidekit.py:170-179` (`resolve_links`) handles a dead ref gracefully — it blanks
the "p.NN" text rather than crashing — so this doesn't error, but it means **every real build,
every tier, permanently** ships an empty page-reference stub next to "Park net proceeds" on a
core (always-rendered) client-facing slide. The 2026-07-28 journal entry says it "fixed a
dangling text reference... that pointed to the now-cut deployment.py" — that fix addressed a
different piece of prose; this `refs[]` array was missed. Confirmed live in the just-built
HNI_DEEP/STANDARD/RM_SIMPLE(reg!="simple" only, so STANDARD+HNI_DEEP) decks — row 4 always
renders (dep is core, park-proceeds row always present), so this fires on every real build.
Fix (not applied, per instructions): repoint to an anchor that actually exists (e.g.
`"mod:fund_actions"` again, or drop the pageref for that row) or restore an anchor call
somewhere proceeds are actually discussed.

### MEDIUM — `tiers.py` optional_on entry contradicts its own adjacent comment
`tiers.py:12` literally includes `"scheme_overlap_full"` in `HNI_DEEP["optional_on"]` (so it
DOES render — correct, matches the 2026-07-29 restore and `engine.py`'s comment). But
`tiers.py:35-47`, a few lines below in the **same set literal**, carries a comment block dated
"Principal cut 2026-07-28 (permanent, ALL tiers...)" describing `scheme_overlap_full` as if it
were removed from this exact set — stale from the earlier (later reversed) cut, never cleaned
up after the restore. Functionally harmless today (the string is still in the set, so the page
renders as intended), but a live self-contradiction inside one file: a future edit "cleaning up"
per the comment would silently re-break the restore. Recommend deleting/updating that stale
paragraph.

### LOW — `engine.py` DIVIDER_TOC section-3 mini-TOC still lists the cut module, omits the
restored one
`engine.py:132`: `3: [..., ("fund_category_rules", "Category & structure rules"), ...]` — 5
slots, still naming the now-permanently-cut `fund_category_rules` (harmless at runtime —
`_toc_for` filters it out via `optional_on` membership, confirmed by code read) but not
naming the restored `scheme_overlap_full`, which now renders in that same section. Net effect:
the section-3 divider's mini-table-of-contents silently drops a page that actually exists
(no crash, just an incomplete on-slide index). Cosmetic, worth a line swap next edit.

### LOW — `scheme_overlap_full.py` omits scope disclosure entirely in the uncapped case
`modules/scheme_overlap_full.py:56-57`: `if capped: deck.scope_tag(...)`. Unlike its sibling
`annex_correlation.py` (`annex_correlation.py:59-61`, which ALWAYS shows a scope string —
"Top N" even when N == the full count), `scheme_overlap_full.py` shows **no** scope/MF-sleeve
disclosure at all when a client has ≤10 funds. Not exercised by Client B today (25 funds,
always capped), but inconsistent with the sibling module's design and will silently under-
disclose for a smaller future client. Both TOP_N constants (15 / 10) themselves are correctly
wired and grammatically fine in the capped case ("Top 15 of 27...", "Top 10 of 25 funds by
weight · MF sleeve only").

### LOW — `ips_summary.py` dead branch (cosmetic, no user-visible effect)
`modules/ips_summary.py:141` returns 0 whenever `not ips.get("on_file", False)` — so by the
time execution reaches line 149's `elif not ips.get("on_file", True):`, `on_file` is
provably `True`, making that elif unreachable. Harmless (falls through to `tag=""`, the
correct outcome) but confusing dead code for a future editor; the "IPS NOT ON FILE" tag text
it contains can never actually display.

### LOW — `ips_summary._lookthrough_mix()` under-counts total AUM by "No View" funds
`_current_values()`'s equity+hybrid_debt+cash sum comes to **99.985%**, not 100%, for Anand
Reddy — verified by direct call. Cause: `_lookthrough_mix()` iterates `ctx["funds"]`, but
funds under the house's 7-month "No View" rule (here: JioBlackRock Flexi Cap, Rs 2,826,
0.0175% of AUM) live in `ctx["data_notes"]["no_view"]`, a separate list never touched by
`ips_summary.py`. `ctx["totals"]["mf_pct"]` (used elsewhere in the deck) explicitly folds
`no_view_val` back in; the IPS page's look-through split does not. Immaterial at this client's
scale (won't flip any Aligned/Gap pill) but the "Current" percentages on the IPS page technically
don't foot to the real total book — worth a one-line fix (fold No-View funds' weight into
`fund_other_w`/cash by category, or explicitly disclose the gap) if this module is ever
resurrected for a client with a larger No-View sleeve.

## Verdicts by numbered area

**1. IPS rebuild + shared logic — PROBLEM (see HIGH+2 LOW above), but currently dormant for
the real client.** (a) Category coverage is airtight: every value that actually appears in
`ctx["funds"]["category"]` for Client B (`mid, small, large, flexi, multi, elss,
dividend_yield, focused, value, passive, thematic_mnc, hybrid, conservative_hybrid, gilt,
debt_short, overnight`) is covered by `_EQUITY_FUND_CATS`/`_HYBRID_FUND_CATS`/
`_DEBT_FUND_CATS` — confirmed programmatically (`cats - union == set()`). The only leak is
the No-View-fund omission above, and it isn't a category-coverage bug (JioBlackRock's
"Flexi Cap" category string is a red herring — it's simply never in `ctx["funds"]` at all, by
design, not miscategorized). (b) Self-gate is airtight — `return 0` happens before any
`deck.content()` call, so there is no partial render path; confirmed by the STANDARD/HNI_DEEP/
RM_SIMPLE build logs all showing `ips_summary  x0` for Client B. **Important calibration for
the rest of this section: because Client B's real `ips["on_file"] = False` (data/
client_b.py:688 — "first review, no IPS on file"), the IPS page currently renders NOTHING
in his real deck.** The `_lookthrough_mix()`/`_current_values()` bugs above are real code bugs,
live in the module, but not currently visible in any Client B PPTX — they'd surface the
moment `on_file` flips to True at a real review. (c) Given that, yes — `_current_values()`
correctly reflects CURRENT real holdings including all 7 Sell-flagged funds (the code applies
no verdict/rec filter at all when summing weights — Sell names haven't actually been sold yet,
so counting them in "Current" is the right behavior, not staleness). Confirmed no verdict-based
filtering exists in `_current_values()` or `_lookthrough_mix()`.

**2. Cut-module hygiene — PROBLEM (the HIGH finding above).** `annex_stress_scenarios.py`:
file confirmed deleted, string absent from `engine.py`/`tiers.py`. `fund_category_rules.py`,
`deployment.py`, `opportunity_set.py`, `annex_mcap_migration.py`, `annex_liquidity_ladder.py`,
`annex_returns_quilt.py`: all core=False in `engine.py` and absent from every tier's
`optional_on` (confirmed HNI_DEEP/STANDARD/RM_SIMPLE) — none reachable. `scheme_overlap_full.py`
correctly reachable (in HNI_DEEP's `optional_on`, matching the "restored" journal entry) despite
the stale contradicting comment (MEDIUM above). `build_client_b.py`'s only `skip_core`
addition is `"cost"` (already globally core=False — acknowledged-redundant, harmless, as its own
comment says). No skip_core entry references a cut module unexpectedly. The
`priority_actions.py` → `deployment.py` cross-reference is the one genuinely still-broken
dead link (HIGH above) — `deck.pageref`'s dead-link fallback does get exercised, and does so
cleanly (blanks the box, no crash), but the reference itself should have been retargeted or
removed when `deployment.py` was cut.

**3. Correlation/overlap caps — CLEAN (with 1 LOW inconsistency).** `TOP_N=15`
(`annex_correlation.py:10`) and `TOP_N=10` (`scheme_overlap_full.py:39`) are both correctly
wired and exercised (Client B: 27 direct-equity holdings → "Top 15 of 27"; 25 funds → "Top
10 of 25 funds by weight · MF sleeve only") — both grammatically correct in the capped case.
No downstream module hardcodes the old "top-8" cap or an uncapped assumption (grepped all
modules/engine.py/tiers.py). The one gap is `scheme_overlap_full.py` silently omitting any
scope disclosure in the (currently unreached) uncapped case, per LOW above.

**4. Portfolio X-ray / Equity Book sweep — CLEAN.** Full grep of `ctx["ips"]` and
`ctx["deployment"]` across every module in `modules/`: readers are `annex_concentration_curve.py`,
`concentration_risk.py`, `exec_summary.py`, `ips_summary.py`, `mandate_method.py`,
`priority_actions.py`, `snapshot.py` (ips) and `annex_mcap_migration.py`, `before_after.py`,
`deployment.py`, `priority_actions.py` (deployment). None of `snapshot.py`,
`allocation_house_view.py`, `sector_exposure.py`, `mcap_positioning.py`, `book_scored.py`,
`equity_book.py`, `sell_list.py`, `hold_rationale.py` touch either key except `snapshot.py`
(reads only the stable `single_name_cap_pct` scalar, unchanged by the v2 rebuild). Every actual
consumer reads `single_name_cap_pct` (unchanged top-level key, present with or without
`on_file`) or, in `house_view_fit.py`'s case, `ctx["deployment"]["sleeves"]` (a real data key,
distinct from the cut slide module) with an honest "no sleeve funded yet" fallback already
verified correct against the current single "Liquid / cash" sleeve. No schema-break regressions
found.

## Build/gate results, all 3 tiers (`PR_SUFFIX=_audit2`)

| Tier | Slides | Crashes | check_geometry.py | check_geometry2.py | tellscan.py |
|---|---|---|---|---|---|
| HNI_DEEP | 75 | 0 | 0 findings | 0 findings | 4 findings — 2× `+0.0%` (slide 59, SBI Gilt real near-zero alpha), `MERIT` (slide 22), `genuine` (slide 46) — all 3 previously-accepted false positives, none new |
| STANDARD | 38 | 0 | 0 findings | 0 findings | 1 finding — `MERIT` (slide 22), accepted |
| RM_SIMPLE | 21 | 0 | 0 findings | 0 findings | 0 findings |

All three tiers build cleanly with `ips_summary x0`/`since_last_review x0` for Client B
(correct self-gate behavior, no partial renders, no exceptions). HNI_DEEP slide count (75)
matches the 2026-07-29 journal entry exactly. No tier shows a module-load `[skip]` line or
traceback. `tellscan.py` on `data/client_b.py` itself shows many hits, but all are inside
comments/the `_scrub_client_text` regex definition (which exists specifically to strip these
strings before they reach any slide) — the rendered-PPTX tellscan results above confirm the
scrub is actually working; this is expected noise, not a live leak.
