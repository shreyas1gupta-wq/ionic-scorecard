# Audit 2026-07-29 — Annexure modules + QA tooling (Anand Reddy HNI_DEEP)

Scope: annexure modules re-check, parked-module leak check, QA-tooling blind-spot analysis,
actual build/gate/visual run. Build used: `PR_SUFFIX=_audit3`, tier HNI_DEEP, 75 slides.

## Finding 1 (SEVERITY: CRITICAL, live, real client) — `annex_valuation_bands.py` narrative
contradicts its own chart

`_derive`/`_pctile` computed Anand Reddy's real weighted trailing P/E at **22.0x, the ~10th
percentile** of the (synthetic) 10-year band — i.e. the book is at the **cheap** end of its own
range. Verified by running the module's own functions against `data/anand_reddy.py` and by
rendering slide 67: the chart itself plots "Today 22.0x · ~10th percentile" at the bottom of the
band. But the callout text on the *same slide* (`render()`, `hni`/`std` branch) is a hardcoded
narrative that always asserts the opposite: "The starting multiple ... sits high" / "priced for a
lot of good news" / "near the top of its usual range". The text is not conditioned on `pct` at
all — it was written for whatever book originally sat near the expensive end (the demo book) and
never made data-driven. For Anand Reddy this is now a **directly false claim next to the
correct chart**, the same bug class as the `house_view_fit.py` fabrication caught 2026-07-28.
**Fix needed:** branch `b1`/`b2` on `pct` (cheap/mid/expensive tercile), not a fixed assumption.
**File:** `modules/annex_valuation_bands.py` lines ~64-75.

## Finding 2 (SEVERITY: HIGH, live, main deck not annexure) — `scheme_overlap_full.py` fund
labels collide

Slide 25 (main Fund Book section) shows the top-10 fund overlap matrix with **two rows/columns
both labeled "Mirae" and two both labeled "HDFC"** — genuinely different funds (Mirae Asset
**Midcap** Fund vs Mirae Asset **ELSS Tax Saver** Fund; HDFC **NIFTY 50 Index** Fund vs HDFC
**Hybrid Equity** Fund) rendering as identical, undifferentiated labels. Root cause in
`_short()` (`modules/scheme_overlap_full.py` lines 10-20): (a) the keyword list is
case-sensitive and checks `"Nifty"` (title-case) against fund names that actually contain
`"NIFTY"` (upper-case) — the match silently fails, so the index fund loses its "N50" suffix and
collides with HDFC Hybrid Equity; (b) the keyword list has no entry for "Midcap"/"Mid" or
"ELSS"/"Tax Saver", so the two Mirae funds get no differentiator regardless of case. Confirmed
live via direct call: `_short()` returns `'Mirae'` for both Mirae funds and `'HDFC'` for both HDFC
funds. A reader cannot tell which specific scheme is high-overlap with which from this slide.
**Fix needed:** case-insensitive match, plus widen the keyword list (Midcap, ELSS, Hybrid, Value,
Focused, Dividend Yield) or fall back to `short_name(f["name"])` when no keyword hits, so two
same-AMC funds never collapse to the same label.

## Finding 3 (SEVERITY: HIGH, live) — `before_after.py` dangling reference to a cut page

Confirmed on rendered slide 35: the callout text still reads "...the staging framework sits on
the previous page" — referring to `deployment.py`, which was cut permanently (`core=False`,
absent from every tier's `optional_on`) on 2026-07-29. `before_after.py` itself is now the
**first** slide in the Annexure section 5 sequence (right after the divider), so "the previous
page" is false — there is no staging-framework page anywhere in the deck. This is the exact same
bug class already caught and fixed once in `priority_actions.py` the same day ("dangling text
reference... pointed to the now-cut deployment.py annexure page") but was missed in
`before_after.py`, its direct neighbor in the old canonical order. Task's premise ("re-confirm it
shows ONLY the sell effect") checks out — the donuts and math are correct, sell-only, no implied
redeployment — but the prose line needs the same fix priority_actions.py got.
**File:** `modules/before_after.py` line 63.

## Finding 4 (SEVERITY: MEDIUM, live, cosmetic-but-visible) — goal-mapping chart label overlap

Slide 73 (`annex_goal_mapping.py`): the "Today ₹1.61 Cr" marker label and the "Education 2031 ·
Rs 1.5 Cr" goal-line label sit almost exactly on top of each other and are illegible where they
cross (confirmed by pixel crop). Root cause: Education's target (Rs 1.5 Cr) is very close to
today's corpus (Rs 1.61 Cr) for this client, so the goal reference line renders right at x=0,
colliding with the "Today" annotation. This lives entirely **inside the matplotlib PNG** produced
by `charts.projection_cone` — see Finding 6 below on why neither geometry checker can or will
catch this class of bug.

## Finding 5 (SEVERITY: LOW / design-smell, not currently manifesting) — same static-narrative
anti-pattern in `annex_beta_ladder.py`

`render()`'s body text unconditionally states "close to the market" regardless of the computed
`book_beta`. For Anand Reddy `book_beta=1.06`, so the claim happens to be true today — not a live
bug — but it is the identical pattern as Finding 1 (assertion not conditioned on the number it
describes) and will silently go wrong for a future client whose book beta drifts materially above
1.2-1.3. Worth a defensive branch (e.g. "above/below/near market") while fixing Finding 1, same
root cause, cheap to fix together.

## Area-by-area verdicts

1. **Annexure re-check:** PROBLEM. `annex_valuation_bands.py` (Finding 1, critical),
   `annex_goal_mapping.py` (Finding 4, medium, chart-internal), `annex_beta_ladder.py`
   (Finding 5, latent). CLEAN: `annex_score_vs_call.py` (already uses the
   table-return-value-for-callout-position pattern correctly — see Finding 7),
   `annex_risk_contribution.py`, `annex_concentration_curve.py`, `annex_income_ladder.py`
   (crash-guards from 2026-07-28 verified correct), `growth_projection.py` (`MU_CAP=18.0`
   confirmed applied, formula sane, `ips.horizon_yrs` read defensively via `.get`),
   `spotlight_holdings.py`, `holdings_detail.py`, `sell_cards.py`, `appendix.py`,
   `quality_vs_price.py`. `annex_concentration_curve.py` reads `ctx["ips"]["single_name_cap_pct"]`
   with a direct (non-`.get`) index — safe today because the field is always populated
   (house-standard 8% default, confirmed in `data/anand_reddy.py` even with `on_file=False`),
   but inconsistent with the `.get`-guarded style used in `annex_mcap_migration.py`/
   `annex_currency_geo.py`/`growth_projection.py` for the same ctx branch — minor robustness note,
   not a bug today.

2. **Parked-module leak check:** CLEAN. `group_concentration.py`'s denominator fix
   re-derived and verified correct: `post_sale_eq_total = eq_total - sold_total` (shrinks by
   ALL equity sells book-wide, not just the group's own), and `after` correctly excludes sold
   group members from the numerator — the fix is mathematically sound. `fund_quality_alloc.py`'s
   `ctx.get("is_demo", False)` gate is correctly placed (`False` default, matches the firm-wide
   2026-07-28 fix). `grep -n` across `engine.py`/`tiers.py`/`build_anand_reddy.py` confirms
   neither module appears in any tier's `optional_on`, both stay `core=False` — genuinely
   unreachable in any current build.

3. **QA-tooling blind spot (see write-up below).**

4. **Build/gates/visual:** ACTUALLY RUN. See results below.

## QA tooling: the blind spot, and a scoped fix

Read `check_geometry.py`, `check_geometry2.py`, `tellscan.py` in full. Both geometry checkers
build their collision universe from **`shape.has_text_frame`** (plain textboxes) and
**`shape.shape_type == 13`** (pictures) only, per-slide. `slidekit.Deck.table()` does **not**
create a native PPTX table/GraphicFrame — it draws each cell as an individual textbox via
`self.txt()` (confirmed in `slidekit.py`), so table cells technically *are* visible to both
checkers as `has_text_frame` shapes. The real blind spot is narrower and more insidious: **every
collision check in both scripts gates on `len(text) >= 12/13` characters** to avoid false
positives on short labels — and the overwhelming majority of table cell text (a symbol, a percent,
a score, a pill word) is under that length, so it is silently excluded from collision detection.
There is no notion in either script of "these N textboxes together are one table with one
aggregate bottom edge" — which is exactly what let the tax_impact.py bug (dynamic table end-y vs.
a fixed-position callout box added later in the same `render()`) through both gates: the
individual cell strings were all short, the table's *aggregate* extent was never computed or
compared against anything.

Confirmed this is a real, currently-live gap by finding a second class of bug neither script can
ever catch by construction: chart-internal label collisions (Finding 4 above) happen inside a
matplotlib PNG that both checkers only ever treat as one opaque picture rectangle — pixel content
inside it is invisible to a shape-tree walker regardless of any fix to the table problem.

**Concrete, scoped recommendation (small change, not a rewrite):** in `slidekit.py`'s `table()`
method, tag every textbox it creates via `self.txt()` for that table with a recognizable
`shape.name` (e.g. `tb.name = f"tblcell_{id(rows)}"` or simply `"tblcell"` — python-pptx shapes
expose a settable `.name`). Then in `check_geometry.py`/`check_geometry2.py`, add one small block:
group shapes per slide by `name.startswith("tblcell")`, compute the **union bounding box** of each
group (this reproduces exactly what `deck.table()`'s existing return value `ty` already knows,
but derived independently from the rendered shapes rather than trusted from the caller), then run
that single aggregate box through the *existing* collision/bounds logic against every other shape
on the slide — with **no length gate**, since it is one aggregate object, not a short string. This
generalizes the tax_impact.py-class fix (already applied ad hoc in that one module, and already
used correctly via the `ty` return value in `annex_score_vs_call.py` and `group_concentration.py`)
into a structural, automatic check for every table on every slide, for an estimated ~15-20 lines
across the three files, no architecture change.

## Actual build / gate / visual results

- Build: `PR_SUFFIX=_audit3`, `build_anand_reddy.py HNI_DEEP` → **75 slides**, no crashes.
- `check_geometry.py`: **0 findings.**
- `check_geometry2.py`: **0 findings.**
- `tellscan.py` (rendered pptx): **4 findings, all previously-accepted false positives** —
  "genuine" (slide 46, ordinary English in `_REVERSAL["Balance-sheet strain"]`), "MERIT" (slide
  22), and `+0.0%` x2 (slide 56, SBI Gilt's real, disclosed, near-zero computed net alpha — same
  fund/number the 2026-07-29 journal entry already accepted). No new tellscan regressions.
- Visual QA, slides actually opened: **slide 25** (scheme_overlap_full, Finding 2), **slide 31**
  (growth_projection — mu 13.6%/sigma 11.0%/7yr, clean render, no collisions), **slide 67**
  (annex_valuation_bands, Finding 1), **slide 68** (annex_correlation — Top-15-of-27 cap correctly
  applied, clean), **slide 73** (annex_goal_mapping — Finding 4; mu/sigma display as
  "14%"/"11%" vs growth_projection's "13.6%"/"11.0%", same underlying `_derive_mu_sigma()` value,
  just coarser rounding on this page — consistent, not a bug), **slide 35** (before_after,
  Finding 3, sell-only mix confirmed correct apart from the dangling text).

## Priority order for a fix pass

1. Finding 1 (`annex_valuation_bands.py`) — false claim on a live client slide, fix before this
   ships past DRAFT.
2. Finding 2 (`scheme_overlap_full.py`) — main-deck ambiguous labels, not annexure.
3. Finding 3 (`before_after.py`) — one-line text fix.
4. Finding 4 (goal-mapping chart label collision) — cosmetic but visible; low effort chart fix
   (nudge or suppress the near-zero-offset goal label when it overlaps "Today").
5. Finding 5 (beta-ladder latent pattern) — fix alongside Finding 1, same anti-pattern.
6. QA-tooling recommendation — do before the next multi-fund-action client, since it is exactly
   the class of bug (table extent vs. later shape) that has now bitten this deck twice
   (tax_impact.py, confirmed) and structurally can recur anywhere `deck.table()` is followed by a
   fixed-position shape in the same `render()`.
