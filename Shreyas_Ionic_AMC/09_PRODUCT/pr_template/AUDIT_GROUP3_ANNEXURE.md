# Audit Group 3 — Annexure Modules (2026-07-28)

Scope: 15 assigned modules (all live in HNI_DEEP's `optional_on`, confirmed in `tiers.py`) + 7
permanently-parked modules. `annex_stress_scenarios.py` and `growth_projection.py` were
re-checked in passing since they anchor this audit's bug classes.

## Module table

| Module | Classification | Model-tier | Top issue |
|---|---|---|---|
| spotlight_holdings.py | SAFE_AS_IS | Haiku | None found — real ctx data, honest fallback chain (client_case→detailed→analyst_read→summary). |
| holdings_detail.py | SAFE_AS_IS | Haiku | None found — real data, single global sort (CEO-sweep fix already in place). |
| sell_cards.py | SAFE_AS_IS | Sonnet | None found — real ctx + honest "On file with the analyst desk" fallback. |
| scheme_scorecards.py | SAFE_AS_IS | Sonnet | None found — explicit None-safe `_fmt` helpers throughout; best-guarded module in the batch. |
| annex_score_vs_call.py | SAFE_AS_IS | Sonnet | None found — self-returns 0 slides when no override exists; real data only. |
| annex_valuation_bands.py | NEEDS_CODE_CHANGES | Sonnet | Crashes (ZeroDivisionError) if zero holdings have a usable PE; P10-P90 band is honestly `[ILLUSTRATIVE]`-tagged (fine). |
| annex_returns_quilt.py | SAFE_AS_IS | Haiku | Fully hardcoded RETS array, but fully and repeatedly disclosed `[ILLUSTRATIVE]` — correct pattern. |
| annex_correlation.py | NEEDS_CODE_CHANGES | Sonnet | Crashes if fewer than 2 direct-equity holdings (empty `pairs` → div/0); jitter-based matrix is disclosed. |
| annex_risk_contribution.py | NEEDS_CODE_CHANGES | Sonnet | Crashes if `ctx["equity"]` is empty (all-fund client); VOL_SYM dict is disclosed `[ILLUSTRATIVE]`. |
| annex_beta_ladder.py | NEEDS_CODE_CHANGES | Sonnet | Same empty-equity crash (book_beta ÷ 0); hash-jittered betas disclosed `[ILLUSTRATIVE]` (same pattern as scheme_overlap_full). |
| annex_concentration_curve.py | NEEDS_CODE_CHANGES | Sonnet | IndexError if book has <10 (even <5) direct holdings — see Top Findings. |
| annex_liquidity_ladder.py | NEEDS_CODE_CHANGES | Sonnet | IndexError if fewer than 2 direct-equity holdings (`big[0]`/`big[1]`); LIQ_TIER dict disclosed. |
| annex_mcap_migration.py | NEEDS_CODE_CHANGES | Sonnet | **Undisclosed hardcoded `TRIM_PT=2.0` feeds the "after" bars as if computed — see Top Findings.** |
| annex_income_ladder.py | NEEDS_CODE_CHANGES | Sonnet | IndexError if fewer than 2 direct-equity holdings (`labels[0]`/`labels[1]`); YLD dict disclosed. |
| annex_goal_mapping.py | NEEDS_CODE_CHANGES | Sonnet | Flat `MU,SIGMA=12.0,14.0` — the exact anti-pattern the Principal already banned in growth_projection.py. |
| annex_seasonality.py (parked) | SAFE_AS_IS | Haiku | Disclosed synthetic RNG data, fixed seed; fine to stay parked. |
| annex_drawdown_history.py (parked) | SAFE_AS_IS | Haiku | Disclosed approximate historical episodes; no client data shown; fine. |
| annex_sip_vs_lumpsum.py (parked) | SAFE_AS_IS | Sonnet | Disclosed synthetic price path; fine. |
| annex_fee_compounding.py (parked) | SAFE_AS_IS | Haiku | Disclosed constant fee scenarios; fine. |
| annex_tax_lot_aging.py (parked) | SAFE_AS_IS | Sonnet | Disclosed synthetic lot schedule; fine. |
| factor_profile.py (parked) | SAFE_AS_IS | Sonnet | Real ctx-derived tilts, disclosed as "approximated" in source line; correctly cut for being a proxy, not a bug. |
| annex_currency_geo.py (parked) | SAFE_AS_IS | Sonnet | GEO revenue-split dict disclosed `[ILLUSTRATIVE]`; fine. |

## TOP FINDINGS (severity order)

**1. `annex_mcap_migration.py` (lines 15, 35) — undisclosed hardcoded constant driving the "after" chart, same bug class as the already-fixed `annex_stress_scenarios.py`.**
`TRIM_PT = 2.0` is a flat, hand-picked percentage-point assumption ("the two >11% names trimmed
toward the single-name cap") applied unconditionally in `_mix()`: `after[Large] = band["Large"]
- sells["Large"] - TRIM_PT + add_large`. It is never derived from the client's actual over-cap
names/amounts, and — unlike every other synthetic number in this file's siblings — it carries
**no `[ILLUSTRATIVE]` tag or disclosure anywhere on the slide**; the scope_tag instead reads
"after = Sells + the two >11% trims executed... redeployed per plan," presented as fact. Fix:
derive the real trim amount from `ctx["ips"]["single_name_cap_pct"]` vs each over-cap holding's
actual weight (the data needed already exists — `annex_concentration_curve.py` computes `over`
this way), or explicitly tag TRIM_PT as `[ILLUSTRATIVE]` if it must stay a placeholder.

**2. `annex_mcap_migration.py` — "after" redeployment is shown as executed, not as the disclosed framework it actually is.**
`add_large`/`add_foreign` come from `ctx["deployment"]["sleeves"]`, but `deployment.py` itself
carries the explicit footer "framework, not a recommendation... sleeves are illustrative and
nothing executes without your authorisation." `annex_mcap_migration.py` drops that caveat
entirely and instead says the redeployment is "executed" / "per plan," so the same numbers read
as committed fact one page over from where they're honestly framed as speculative. This is a
cross-panel consistency violation (QA LAW §4) as well as an under-disclosure issue. Fix: either
carry the same "framework, not executed" language into this module's scope_tag/source, or gate
the "after" bars visually (dashed/lighter) to signal they assume an unexecuted plan.

**3. `annex_goal_mapping.py` (line 14) — the exact flat-rate bug the Principal already banned, resurfacing in a sibling module.**
`MU, SIGMA = 12.0, 14.0` is used to discount every goal to present value and size the projection
cone — the identical anti-pattern `growth_projection.py` was rewritten to eliminate 2026-07-27
("never revert to a fixed assumed rate," permanent ruling). Because `annex_goal_mapping.py`
renders in the same HNI_DEEP annexure, a reader can see two different expected-return
assumptions for the same book in the same deck (holdings-derived ~X% in growth_projection vs
flat 12% here) — a cross-panel reconciliation failure, and it also drives a real number
(funded-today %) shown with confidence. The goal amounts/dates are correctly `[ILLUSTRATIVE]`-
tagged already (fine, pending real family goals); the return-rate hardcode is the separate,
higher-severity defect. Fix: import and reuse `growth_projection._derive_mu_sigma(ctx)` here
(also satisfies the firm's "consolidate reused code" convention) instead of a second constant.

**4. Systemic crash risk: five modules assume the direct-equity sleeve has ≥2 (often ≥10) holdings, with no guard.**
A first-review NDPMS client can plausibly be fund-heavy with a thin or empty direct-equity
sleeve. Confirmed unconditional index/zero-division bugs on real client data (not edge-of-edge
cases):
- `annex_concentration_curve.py` line 30: `c5, c10, c20 = cum[4], cum[9], cum[19] if n >= 20 else
  cum[-1]` — the ternary (due to Python precedence) only guards `c20`; `cum[4]`/`cum[9]` raise
  `IndexError` outright on a book with fewer than 10 (or 5) direct holdings.
- `annex_income_ladder.py` line 53 (`labels[0]`, `labels[1]`) and `annex_liquidity_ladder.py`
  line 55 (`big[0]`, `big[1]`) both `IndexError` with fewer than 2 direct-equity holdings.
- `annex_correlation.py` (`avg = sum(...)/len(pairs)`), `annex_risk_contribution.py`
  (`e["weight_pct"]/tot_w`), and `annex_beta_ladder.py` (`book_beta = .../wsum`) all
  `ZeroDivisionError` if `ctx["equity"]` is empty (an all-mutual-fund client).
- `annex_valuation_bands.py` (`wpe = sum(...)/cov`) `ZeroDivisionError`s if no holding has a
  usable trailing PE (all extreme/negative/missing).
Fix pattern: guard each with `if n < K: return 0` (module already returns an int slide-count,
so this is the established idiom — see `annex_score_vs_call.py`'s `if not any(...): return 0`).

**5. `annex_stress_scenarios.py` still contains the exact fixed-vs-real bug in code, just switched off.**
Confirmed in `engine.py` (core=False) and `tiers.py` (explicitly excluded 2026-07-28, with the
Principal's own note quoted almost verbatim from this brief: hardcoded `TODAY`/`PROP` arrays,
"structurally biased regardless... this deck only ever sells into cash, never buys into new
positions"). The file itself was **not edited** — only unwired. Because it renders cleanly and
looks plausible, it is one accidental `optional_on` edit away from resurrection. Recommend
**deleting the file outright** rather than parking it (unlike the 7 parked modules below, which
are honestly disclosed and have a plausible future use) — it is both permanently dead and a
live landmine.

## Lower-severity / disclosed-illustrative findings (informational only)
`annex_valuation_bands.py` (P10–P90 band), `annex_returns_quilt.py` (RETS array),
`annex_correlation.py` (jitter matrix), `annex_risk_contribution.py` (VOL_SYM), `annex_beta_ladder.py`
(BETA + md5 jitter), `annex_liquidity_ladder.py` (LIQ_TIER), `annex_income_ladder.py` (YLD),
`annex_currency_geo.py` (GEO) all use hardcoded or jittered numbers — but every one carries an
explicit `[ILLUSTRATIVE]` scope_tag and source-line disclosure, the same honest pattern as
`scheme_overlap_full.py`. No action required; listed here only so future edits don't strip the
disclosure while "cleaning up" the code.

## Redundancy notes
- `spotlight_holdings.py` vs `holdings_detail.py`: intentional complementary pair (narrative
  cards for top-N vs flat scored table for all) — same pattern as `scheme_scorecards.py` vs
  `fund_book_scored.py` (cross-group). Not redundant, keep both.
- `annex_mcap_migration.py` overlaps with **`before_after.py`** (cross-group, Annexure) — both
  render a "before vs after the plan" comparison (asset-mix donuts vs cap-band bars). Worth a
  joint review to see if one should absorb the other, or if before_after's donut is enough and
  mcap_migration is the redundant, buggier one (see Finding 1).
- `annex_concentration_curve.py` partially overlaps **`concentration_risk.py`** (cross-group,
  main deck) — same "top-heavy" theme, different chart form (Lorenz curve vs treemap). Low
  redundancy, different reading.
- `annex_score_vs_call.py` partially overlaps **`book_scored.py`** (cross-group) — score-vs-call
  is a narrower, override-only lens; not fully redundant.
- `scheme_scorecards.py` vs **`fund_book_scored.py`** (cross-group) — same complementary
  summary/detail pattern as spotlight/holdings_detail; flag for the fund-book audit group to
  confirm, not a finding here.

## Summary
2 undisclosed/borderline hardcode-and-bias bugs found (both in `annex_mcap_migration.py`), 1
cross-module methodology inconsistency (`annex_goal_mapping.py`'s stale flat-rate assumption),
6 crash-risk modules on a thin-equity or fund-only first-review book, and 1 dead-code hygiene
recommendation (`annex_stress_scenarios.py` deletion). The disclosed-illustrative modules
(8 of 15) are all correctly handled and need no change.
