# NDPMS Portfolio-Review Template — v9 Master Spec
**Ionic Wealth NDPMS client review · config-driven slide-module engine · replaces the bespoke v8 build (`build_pr_full.py`, 57 slides).**
Authored 2026-07-25 (DESK-100) from the 5-lens redesign workflow (Product / Fund-method / Equity / Cost-Tax-Deploy / IPS-Compliance) + completeness critic. Governs the automated template and the AZBY Family demo.

> **What "template, not a deck" means.** v8 was one hand-built presentation. v9 is a **library of ~34 slide-modules**, each a `render(prs, ctx, tier)` function in its own file. A build = pick a **tier preset** (which modules, how deep, what language register) → the engine renders the selected modules in canonical order → one deck. Some engagements use 22 slides, some use 60. Every module is *ready*; the config decides what ships.

---

## 1. The three (four) tiers — same content, rendered for the audience

A **tier** is a build-config preset: `{modules_on, register, chart_density, show_horizon_legs}`. The *content and numbers are identical across tiers* — only depth, language, and chart richness change. This is the "same review, 3-4 ways" requirement.

| Tier | Audience | Modules | Register | Charts | Horizon legs |
|---|---|---|---|---|---|
| **HNI_DEEP** | Family office / sophisticated HNI | Core + **all** annexure (per-name sell cards, per-scheme scorecards, overlap heatmap, factor radar, efficient frontier, growth cone, tax bridge) | Technical, full methodology | Rich (every chart) | On (if advisory approves) |
| **STANDARD** | Typical NDPMS client | Full core + selective annexure (top-2 spotlights, opportunity set, growth projection; **no** per-name cards / per-scheme scorecards / overlap heatmap) | Professional, accessible | Standard | Off (blended only) |
| **RM_SIMPLE** | RM-led review / newer investor | **Reduced core** — IPS, exec gap-grid, snapshot, concentration, sell-list (categories only), fund-actions (plain cards), cost, deployment, before/after, priority actions | Plain, larger type, fewer numbers, "gap → fix" | Minimal (donut/bar/dumbbell/waterfall only) | Off |
| *(ADVISOR_LIVE)* | Internal, advisor-present | = HNI_DEEP + horizon legs + Score-vs-Call detail | Technical | Rich | On |

**Register** drives copy: `simple` swaps jargon for plain sentences, expands the "what this means for you" line, and caps each slide to one idea. `hni`/`std` keep the analytical voice. The engine holds two label sets per module (a `LABELS[register]` dict); no numbers change.

**Tier guardrails (from the critic):**
- A light tier that toggles a fact-bearing annexure **off** must suppress every core-slide cross-reference to it ("see annexure p.X" renders only if the target is in this build).
- Exec-summary Sell/Trim/Hold counts must **equal** the book-scored counts (build-time equality check, else fail).
- The Disclaimer is **always on**, exempt from every tier toggle.
- No annexure module may introduce a *new* verdict/number the client hasn't seen in core — annexure is elaboration only.

---

## 2. Canonical module order (the MOD-INDEX)

**Front matter (CORE)**
1. `cover` — Cover *(v8 #1, unchanged)*
2. `contents_legend` — Contents & How-to-Read + one-time vocab strip (Sell/Trim/Hold, not a solicitation) + score-positioning legend + per-build "annexure included this cycle" tag
3. `ips_summary` — **Investment Policy Statement** *(NEW, F1)* — risk-tier badge, objectives, constraints, strategic allocation bands (the target the exec grid diffs against). **Advisory-owned content** via `client_ips.yaml`; renders "IPS NOT ON FILE" if absent.
4. `exec_summary` — **Executive Summary: category gap→action grid** *(v8 #3 redesigned, F2/F8)* — keep the stat band; replace prose with a 5-row `Category | Gap vs IPS | Action | Slide-ref` grid; every row must resolve to a non-empty action + slide number.
5. `mandate_method` — **Our Understanding: Mandate, Construction & Benchmark** *(v8 #4, F9/F10)* — advisory-authored "our understanding" prose; **core-satellite definition** boilerplate; **benchmark** resolved to a typed record (named index / blended composite / qualitative stance / absolute hurdle), never the bare alias "Asset X house view"; NDPMS execution note (client authorises before execution). Score-position band attaches here.

**Section 01 — Portfolio X-ray (CORE)**
6. `snapshot` *(v8 #6)*
7. `allocation_house_view` *(v8 #7)* — benchmark bands advisory-owned
8. `concentration_risk` *(v8 #8)*
9. `sector_exposure` *(v8 #9, F12)* — **CMP-DATASCOPE tag** + over/under vs house-view bands
10. `mcap_positioning` *(v8 #10, F12)* — scope tag + SEBI cutoffs + mid/small VIEW line

**Section 02 — Equity (CORE)**
11. `score_method` — **How we score every stock** *(NEW, F13)* — two horizons (3Y fundamentals-tilted / 1Y technical-tilted) blended 60/40 over 7 pillars in 3 client buckets (Quality&Growth / Value / Trend&Flow); safety gates cap at 40; forward tilt; **the dominant "THE HUMAN READ" block** (score is the input, not the verdict); thresholds (<40 either horizon = Sell; 40-50 on >2.5% = Trim; ≥50 = Hold).
12. `book_scored` — **The whole book, scored — with analyst read** *(v8 #12, F13)* — distribution strip (Hold/Trim/Sell counts, no book-level weighted score — frozen rule); table with a **new one-line analyst-read column**; Score-vs-Call callout listing every analyst override; scope tag "direct equity only".
13. `equity_book` *(v8 #13)*
14. `sell_list` — **The names we would sell** *(v8 #16, F3)* — table with a fixed **reason-taxonomy category** (Forensic/governance flag | Balance-sheet gate | Quality below peers | Weak long-term growth | Rich valuation | Weak trend) + exact binding trigger + a `Detail→` ref to the annexure card; ordering rule: forensic/gate reasons rank above valuation/trend; scope tag.
15. `hold_rationale` — **What stays, and why** *(v8 #17, F3/F13)* — grouped by conviction; each name = score + one-line read + **thesis-break trigger**.

**Section 03 — Funds (CORE)** — *all fund scoring consumes the frozen QFRA 2.0 engine (`qfra2-rerun` skill); the deck never re-implements the formulas.*
16. `fund_book_scored` — **The fund book, scored** *(v8 #19, F4/F12)* — scope banner "MF sleeve only"; row = Scheme | Category | Plan | Wt | QFRA/100 | MERIT grade | SENTINEL flags (chips) | Verdict (Hold/Trim/Switch/Redeem-to-Direct/Exit — never Buy).
17. `funds_equity` — **Equity funds: Upside · Downside · Consistency** *(NEW, F14)* — up_capture / down_capture / rolling-3Y hit-rate; asymmetry = up−down; alpha_t, info_ratio, r² (CLOSET_INDEX if >0.95); "why beating the benchmark isn't enough" callout; capture scatter chart.
18. `funds_hybrid` — **Hybrid funds: RAR · Max Drawdown · Worst Year** *(NEW, F15)* — Sortino + Calmar; max_dd (DEEP_DD if worst-quartile); **worst 1-yr rolling return as the headline**; down_capture (is it cushioning?); drawdown curve + rolling-return band charts.
19. `fund_category_rules` — **Category & Structure: preference rules** *(v8 #21, F14)* — Rule 1 Flexi>Multi (SEBI 25/25/25 floor kills agility at same fee); Rule 2 Factor/Passive>Active-LC (thin net-of-fee alpha, closet-indexing); each rule = RULE→WHY→which held schemes violate→action; AMC-concentration strip.
20. `fund_quality_alloc` — **Fund quality × allocation — the overlay** *(NEW, F16 canonical home)* — 2D quadrant: X=alloc gap vs house view, Y=fund quality, bubble=weight; prescriptions per quadrant (over+low = Trim-then-Exit; over+high = Trim to target; under+high = retain/redeploy target; under+low = Switch vehicle).
21. `fund_overlap` — **Where you're duplicating exposure** *(v8 #22 REDEFINED, F17)* — Panel A fund-vs-fund duplication; Panel B **fund-vs-direct double-pay** (names held both directly and via funds); headline stat "X% of AUM re-buys stocks you already hold directly, at Y bps". *(Full pairwise heatmap → annexure.)*
22. `fund_actions` — **Fund actions — rationale cards** *(v8 #23, F4)* — one card per action; anatomy = Action | Scheme | firing SENTINEL flags | 2-3 metric deltas vs category exemplar | structural reason (mandate rigidity / plan-cost / capacity / closet-index) | "measured against exemplar [X]"; count-agnostic; **no performance-only exits**.

**Section 04 — Recommendations (CORE ends at #26)**
23. `house_view_fit` *(v8 #25)*
24. `cost` — **What you're paying today (the fee stack)** *(NEW, split from v8 #26, F5)* — 3 KPI tiles (total fee load ₹/bps | Regular-plan drag avoidable | PMS/advisory fee); fee register (worst-to-best, top-8 on core, full in annexure); **PMS fee shown separately from fund TER**; single soft CoPilot hook line (compliance-gated). Fee stack chart.
25. `tax_impact` — **Tax impact of this plan** *(NEW, split from v8 #26, F7)* — fund-action tax table; direct-equity **tax-gap panel** (needs demat trade file); tax-drag-on-deployment strip (illustrative haircut → feeds deployment net-of-tax base); confirm-with-tax-adviser footnote. Tax bridge chart.
26. `deployment` — **Where the money moves — and why** *(v8 #27, F6)* — waterfall with an explicit "less: est. tax leakage" step; **sequencing rationale panel** (execute clear-Sells first / stage by liquidity / cash-until-deployed); **per-sleeve one-line rationale**; non-solicitation framing (liquidity logic, not a market call).
27. `before_after` *(v8 #28)*
28. `priority_actions` *(v8 #29)* — **← F18 MANDATORY-CORE CUT LINE**

**Section 05 — Annexure (OPTIONAL, per-tier)**
29. `opportunity_set` — efficient frontier *(v8 #30)*
30. `quality_vs_price` — value map *(v8 #31)*
31. `factor_profile` — factor radar *(v8 #32)*
32. `growth_projection` — projection cone *(v8 #33)*
33. `spotlight_holdings` — top-N holdings, config N=0-5 *(v8 #14/#15, de-hardcoded)*
34. `holdings_detail` — per-holding, toggle *(v8 #35-51)*
35. `sell_cards` — **per-name sell rationale cards** *(NEW, F3)* — full analyst rationale + **"THE BULL WE REJECTED"** (positive_para) + reverse-DCF margin-of-safety + **"WHAT WOULD CHANGE OUR MIND"** reversal condition + forensic-checklist status + PIT stamp
36. `scheme_overlap_full` — **Scheme Overlap & Redundancy** heatmap *(NEW, F17)* — weighted common-holdings `OVERLAP(A,B)=Σ min(w_iA,w_iB)`; active-share vs passive; look-through top-10
37. `scheme_scorecards` — **per-scheme scorecard** *(NEW, F4)* — full QFRA battery + SENTINEL ledger + narrative exit rationale + rolling/drawdown mini-charts
38. `appendix` *(v8 #53-56)*
39. `disclaimer` — **ALWAYS ON, tier-exempt** *(v8 #57)*

---

## 3. Visual library

**Reuse (chart_lib.py, Ionic brand indigo `#1B27A3` / orange `#F2A93C`):** donut · hbar · paired_bar · waterfall · dumbbell · radar · heatmap · treemap · histogram · bubble · lollipop · stacked100 · small_multiples_bars · efficient_frontier · value_map · projection_cone · bar3d.

**New (add to chart_lib.py):**
| fn | Module | What |
|---|---|---|
| `capture_scatter(up, down, wt, labels)` | funds_equity | up-capture (x) vs down-capture (y), 45° symmetry line, ideal NW quadrant shaded; a fund below the line captures more up than down |
| `drawdown_curve(nav_series)` | funds_hybrid / scorecards | underwater plot, max-DD marked in rust |
| `rolling_return_band(nav, window=252)` | funds_hybrid / scorecards | rolling-1Y return line + p10–p90 band, worst-year marked gold |
| `fee_stack(rows)` | cost | horizontal stack: fund TER (direct) + Regular-plan drag (avoidable, rust) + PMS fee, in bps |
| `tax_bridge(gross, ltcg, stcg, net)` | tax_impact / deployment | waterfall: gross proceeds → less LTCG → less STCG → net deployable |
| `quality_alloc_quadrant(gap, quality, wt, labels)` | fund_quality_alloc | 4-quadrant scatter, quadrant labels, bubble=weight |
| `over_under_bar(cats, gap_pct)` | exec/sector/overlay | diverging bar, under-allocated left / over right, house-view zero line |

---

## 4. Data contracts (what the engine reads)

**client_data** (per engagement): holdings (symbol, value_inr, plan Reg/Direct, purchase date/cost if available); scheme list (ISIN/AMFI, category, plan, weight); `client_ips.yaml` (advisory-authored — objectives, risk tier, allocation bands, constraints); `benchmark_config.yaml`; `mandate_understanding.md`.

**firm_data** (shared, versioned): scored universe (`portfolio_quant.csv` + `pf_qual_*.json`); frozen scoring-method table (7 pillars, both horizons, gates); QFRA outputs (`QFRA2_current.csv` + `panel_<cat>.csv` + `features.py`) via the `qfra2-rerun` skill; `risk_profile_grid.yaml` (5-tier standard); `core_satellite_definition` boilerplate; statutory tax-rate table (Compliance-signed, Budget-versioned); SEBI mcap cutoffs; house-view sector/allocation bands; fund look-through holdings (PIT-dated, for scope tags + overlap).

**Advisory / cross-desk owned (rendered only when supplied, else flagged on-slide):** IPS wording + risk-profile bands (Portfolio Reviews, F11) · benchmark definition + core-satellite wording (advisory, F9/F10) · deployment-destination rationale (CIO/FM, F6) · statutory tax rates + CoPilot-CTA + naming a switch-target exemplar (Compliance) · PMS/advisory fee schedule (from signed IMA) · MF look-through feed (Data Office, F12).

---

## 5. Open items routed to advisory / other desks (do NOT fabricate on a real client deck)
- **F9** benchmark: is "Asset X house view" a named index, a blended composite, a qualitative stance, or an APMI-tagged Investment Approach benchmark (SEBI Dec-2022 circular)? → advisory.
- **F10** core-satellite: ratify the boilerplate definition (illustrative draft in the engine, tagged [OPINION]).
- **F11** risk-profile grid: ratify the 5-tier bands (illustrative draft in engine, tagged [OPINION]).
- **F6** deployment rationale: CIO/FM to author "why this destination"; else the slide shows the split without reasoning.
- **F7** tax: caveat-only until a demat trade file is supplied; statutory rates need Compliance sign-off.
- **F5** CoPilot soft-CTA framing on a Sell/Trim/Hold deck; **F4** may a client deck name the QFRA final-2 exemplar as a switch target — both default to the conservative option until Compliance rules.

---

## 6. AZBY Family — the demo (self-contained, fully synthetic)

**Purpose:** prove the template renders end-to-end across tiers with the new modules. **All AZBY content is [ILLUSTRATIVE — synthetic demo data, not a real client]**; because it is fictional the demo *may* carry authored IPS / house-view / deployment text (tagged illustrative) that a real client deck would route to advisory.

- **Client:** "AZBY Family" NDPMS, Aggressive / Long-term / Core-satellite, ~₹6.8 Cr.
- **Direct equity (~38 names):** real tickers from our 230-scored universe so **scores are real** — includes genuine Sells (RELIANCE, TATAPOWER, JIOFIN, DEEPAKNTR, POONAWALLA, BHEL, TATATECH, ANANDRATHI, COCHINSHIP, HINDCOPPER…) and Holds; deliberate concentration (2 names >11%); a few micro clutter positions.
- **Mutual funds (8-10)** with **synthetic NAV series engineered to trigger the flags** — the "LIC-type underperformers we can Sell":
  - *LIC MF Large Cap (Regular)* → CLOSET_INDEX (r²>0.95) + NEG_ALPHA → **Switch to a passive/factor LC**
  - *LIC MF Flexi Cap* → weak up-capture, poor 3Y hit-rate → **Switch**
  - *LIC MF Multi Cap* → mandate-rigidity → **Switch to Flexi** (structural, not performance)
  - *ICICI Pru Multi-Asset (Regular)* → plan/cost → **Redeem to Direct**
  - *Bandhan/other Small Cap (sub-scale ₹3L)* → DEEP_DD + capacity + over-alloc quadrant → **Exit**
  - *LIC MF Balanced Advantage (hybrid)* → down_capture near equity, poor Sortino/worst-year → **Trim/Switch**
  - + 2-3 genuine **Holds** (a quality flexi, an index fund, a decent hybrid) so the deck isn't all-Sell.
- **IPS:** illustrative AZBY IPS (risk tier Aggressive, equity 65-85% band, foreign-equity target, gold sleeve, single-name ≤8-10% guideline) → drives the exec gap-grid.
- **Transition/deployment plan:** Sell proceeds → net-of-illustrative-tax → low-vol/value core, foreign-equity step, gold-silver sleeve; sequenced by liquidity; cash-until-deployed.

**Build outputs:** `AZBY_Family_HNI.pptx` · `AZBY_Family_STANDARD.pptx` · `AZBY_Family_RM_SIMPLE.pptx` (+ PDFs), from the one engine + one dataset, tier flag only.

---

## 7. Engine architecture
```
09_PRODUCT/pr_template/
  TEMPLATE_V9_SPEC.md          ← this file
  engine.py                    ← registry + build(ctx, tier); ordered MODULES list
  tiers.py                     ← TIER presets (modules_on, register, chart_density)
  slidekit.py                  ← pptx primitives (title, KPI band, table, chart-embed, scope-tag, score-band, callout) in Ionic style
  modules/<id>.py              ← one render(prs, ctx, tier) per module (parallel-safe: separate files)
  data/azby_family.py          ← synthetic AZBY dataset builder
  build_azby.py                ← CLI: build all three tiers
chart_lib.py (existing)        ← extended with the 7 new charts
```
Registry entry: `Module(id, section, core: bool, tiers: set, order: int, render: callable)`. `build(ctx, tier)` = for m in MODULES sorted by order: if `m.core or tier in m.tiers`: `m.render(prs, ctx, tier)`. Page numbers resolved at build time (never hand-patched). Build-time asserts: exec counts == book counts; no dangling annexure cross-ref; weights sum 100 before/after.

---
*Source: 5-lens redesign workflow (wf_0961e270-b0e) + critic, 2026-07-25. Feedback items F1-F18 all mapped (§2 tags). Advisory-owned slots in §5 never auto-filled on a real client deck.*
