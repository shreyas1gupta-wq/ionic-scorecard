---
name: ionic-wealth-complete
description: The ONE comprehensive operating manual for Ionic Wealth's client product suite — NDPMS portfolio-review deck (pr_template), Stock Scorecard 750 (quantamental scoring), MF quality frameworks (QFRA-1/QFRA-2), client intake, QA gates, all Principal rulings, environment, and the full agent roster. Give this file to any team member; nothing else needed besides the GitHub repo.
---

# Ionic Wealth — Complete Operating Manual (v2, 2026-07-31)

Everything a team member needs to produce client deliverables. This is the SINGLE source of truth. The GitHub repo has all code, data, and scripts referenced below.

> **Repo:** https://github.com/shreyas1gupta-wq/ionic-scorecard (private)

---

## QUICK START: Holdings In → PPTX Deck Out

**INPUT:** A client's holdings file (CSV or XLSX extracted from NSDL CAS statement).
Required columns (case-insensitive): `type` (EQ/MF), `name`, `isin` (preferred), `units`, `value_inr`.

**OUTPUT:** A branded Ionic Wealth PPTX portfolio-review deck (75/40/23 slides depending on tier).

### The 6-step pipeline (end to end)

```
STEP 1  Holdings file arrives (CSV/XLSX from CAS)
   ↓
STEP 2  client_intake.py matches each holding to the scored universe
   ↓    → pf_qual_*.json (equity scores) + QFRA verdicts (fund scores)
   ↓    → exceptions.csv (unmatched rows → back to RM, never dropped)
   ↓
STEP 3  Create data/<client>.py (ctx dict) from matched results
   ↓    → Copy data/azby_family.py as template, fill real numbers
   ↓    → Every Sell/Hold call comes from scorecard + analyst research
   ↓    → Every fund verdict comes from QFRA-1 + QFRA-2 frameworks
   ↓
STEP 4  Build the deck
   ↓    cd Shreyas_Ionic_AMC/09_PRODUCT/pr_template
   ↓    set PYTHONIOENCODING=utf-8 && set PYTHONUNBUFFERED=1
   ↓    "C:\...\python.exe" build_<client>.py HNI_DEEP
   ↓
STEP 5  QA gates (ALL mandatory, in order)
   ↓    a) check_geometry.py + check_geometry2.py = 0 findings
   ↓    b) tellscan.py = 0 real findings
   ↓    c) Visual check of changed slides
   ↓    d) Cross-panel number consistency
   ↓
STEP 6  Principal sign-off → publish to 09_PRODUCT/reports/
```

### What if the scored universe is missing for a stock?
The intake script flags unmatched stocks in `exceptions.csv`. For each:
- Run the Stock Scorecard 750 pipeline (Part 2 below) to score it — one Sonnet agent per stock does ~3min deep research
- The analyst's `pf_qual_<SYMBOL>.json` is the output, which feeds directly into the deck's data layer
- Until scored, the stock gets `"No Recommendation"` — never a fabricated score

### What if QFRA data is missing for a fund?
- QFRA-2 covers 40 curated funds; held funds outside it get an honest gap note: "needs a QFRA-2 scoring run"
- A fund with no framework coverage gets `"No View"` — never a fabricated verdict
- The deck renders these honestly (the module handles missing data gracefully)

---

## PART 1: NDPMS PORTFOLIO REVIEW DECK (pr_template)

### What it is
A Python-powered PowerPoint generator that produces institutional-grade portfolio review presentations for NDPMS (Non-Discretionary Portfolio Management Service) clients. Three depth tiers, ~57 slide modules, fully templatized design with navy/gold house style.

### Location
`Shreyas_Ionic_AMC/09_PRODUCT/pr_template/`

### Architecture
```
pr_template/
  engine.py          Module registry + build() orchestrator
  tiers.py           HNI_DEEP / STANDARD / RM_SIMPLE presets
  slidekit.py        PowerPoint primitives (txt, table, callout, pic, etc.)
  charts.py          Matplotlib chart generators (donut, bar, paired_bar, heatmap...)
  chart_ext_b.py     Extended chart lib (beta ladder, concentration curve...)
  art.py             Generative cover/divider flow art
  gallery.py         Render all modules to PNG for visual QA
  tellscan.py        AI-writing-tell scanner (QA gate)
  check_geometry.py  Overlap/bounds geometry checker (QA gate)
  check_geometry2.py Extended geometry checker (QA gate)
  data/
    azby_family.py   Demo client context (schema reference)
    anand_reddy.py   Real client: Anand Reddy (first production deck)
  modules/           ~57 slide modules, each: render(deck, ctx, tier) -> int
  out/               Build output directory
```

### Tiers (what depth to build)

| Tier | Audience | Slides | Register | Notes |
|---|---|---|---|---|
| **HNI_DEEP** | Family office / sophisticated HNI | ~75-82 | Technical, full methodology | All annexure modules ON |
| **STANDARD** | Typical NDPMS client | ~38-40 | Professional, accessible | Selected annexure modules |
| **RM_SIMPLE** | RM-led / newer investor | ~19-23 | Plain language, bigger type | Core story beats only |

### How to build a deck

**Step 0: Environment setup** (one-time)
```bash
# Python path (the `python` alias is BROKEN on this machine)
set PYTHON="C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe"

# Required packages
%PYTHON% -m pip install python-pptx matplotlib Pillow numpy openpyxl
```

**Step 1: Create the client data file**
Copy `data/azby_family.py` (demo schema) to `data/<client_name>.py`. Fill in:
- `_CLIENT` dict: name, code, account_type, profile, horizon, construction, as_of date
- `_EQUITY` list: each stock with symbol, company_name, isin, sector, value_inr, weight_pct, rec (Sell/Trim/Hold), ionic_score, score_3y, score_1y, growth_pct, negative_para, rationale, summary, positive, reverse_dcf, holding_years
- `_FUNDS` list: each MF scheme with name, amc, category, weight_pct, value_inr, cagr3y, bench_cagr3y, down_capture, verdict (Hold/Sell/Switch/Redeem-to-Direct), mdd, worst1y
- `_IPS` dict: on_file flag, alloc_bands, single_stock_cap_pct, single_amc_cap_pct, locked_in_pct, cash_pct, mcap_bands, etc.
- `_TOTALS` dict: grand_inr, eq_pct, mf_pct, cash_pct, n_sell, n_trim, n_hold
- `_GOALS` list, `_FAMILY` dict, `_MEETING_HISTORY` list
- `_TAX` dict: fund_rows, gross, ltcg, stcg, net
- `_DEPLOYMENT` dict: proceeds_inr, tax_leak_inr, net_inr
- A `ctx()` function returning all of the above as a single dict

**Step 2: Create the build script**
Copy `build_anand_reddy.py` to `build_<client>.py`. Change the import to your data file:
```python
import data.<client_name> as D
```

**Step 3: Build**
```bash
cd Shreyas_Ionic_AMC/09_PRODUCT/pr_template
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" build_<client>.py HNI_DEEP
```
Output: `out/<ClientName>_HNI_DEEP.pptx`

**Step 4: QA gates (ALL mandatory, in order)**
1. **Visual inspection**: Open the PPTX and visually check changed slides
2. **Geometry check**: `python check_geometry.py out/<deck>.pptx` AND `python check_geometry2.py out/<deck>.pptx` — must be 0 findings
3. **Tell scan**: `python tellscan.py out/<deck>.pptx` — must be 0 real findings (small false-positive rate on ordinary English words like "genuine" is expected)
4. **Cross-panel consistency**: Any two numbers on the same slide that a reader assumes are the same set MUST reconcile
5. **Principal sign-off** before any client artifact ships

**Step 5: PDF (ON REQUEST ONLY)**
```bash
"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" ../scripts/pptx_to_pdf.py out/<deck>.pptx
```
Do NOT auto-convert to PDF after every rebuild — ask the advisor whether they want PPTX, PDF, or both.

**Step 6: Publish**
Copy to `Shreyas_Ionic_AMC/09_PRODUCT/reports/` with client-facing filename: `NDPMS_Portfolio_Review_<ClientName>_<Tier>.pptx`

### Module registry (canonical order)

**Section 0 — Understanding:**
cover, contents_legend, ips_summary (renders only if IPS on file), exec_summary, since_last_review (renders only if meeting_history exists), mandate_method

**Section 1 — Portfolio X-ray:**
snapshot, allocation_house_view, concentration_risk, sector_exposure, mcap_positioning
(CUT: group_concentration — denominator bug fixed but not wired)

**Section 2 — The Equity Book:**
score_method, book_scored, equity_book, sell_list, hold_rationale

**Section 3 — The Fund Book:**
fund_book_scored, funds_equity, funds_hybrid, scheme_overlap_full (top 10 funds by weight), fund_actions
(CUT: fund_category_rules, fund_quality_alloc, fund_overlap)

**Section 4 — Recommendations:**
house_view_fit, tax_impact, priority_actions, growth_projection (mu/sigma from real holdings, not constant)
(CUT: cost — was scheme-TER only with no Regular-drag/PMS overlays)

**Section 5 — Annexure (optional, tier-dependent):**
before_after, quality_vs_price, spotlight_holdings, holdings_detail, sell_cards, scheme_scorecards, annex_score_vs_call, annex_valuation_bands, annex_correlation (top 15 by weight), annex_risk_contribution, annex_beta_ladder, annex_concentration_curve, annex_income_ladder, annex_goal_mapping, appendix, disclaimer
(CUT permanently: opportunity_set, deployment, factor_profile, annex_currency_geo, annex_mcap_migration, annex_liquidity_ladder, annex_returns_quilt, annex_stress_scenarios [DELETED], annex_seasonality, annex_drawdown_history, annex_sip_vs_lumpsum, annex_fee_compounding, annex_tax_lot_aging, glossary)

### Sell page structure (sell_list.py + sell_cards.py)
- **sell_list**: confirmed Sells only (no "Under review" pill client-side), no reason-category column, analyst-authored 2-line case per name, visible p.NN link per row to the rationale card, paginates at 5 rows.
- **sell_cards**: each Sell name gets a full-page rationale card with:
  - `negative_para`: the driver — why we're selling (OPENS the card, leans with the call)
  - `positive` ("The bull we rejected"): the strongest counter-argument, explicitly discounted
  - `reverse_dcf` ("Reverse-DCF: margin of safety"): what the market is pricing in vs our estimate
  - `rationale`: the analyst's full reasoning
  - If `positive` or `reverse_dcf` is empty, it falls back to "On file with the analyst desk." — always populate these from the scored universe's `pf_qual_*.json` or `ANALYST_RECOMMENDATIONS_v2.xlsx`

### Tax chart scope (tax_impact.py)
The tax chart shows **direct-equity sells & trims only** (not fund proceeds). In the data layer:
- `eq_proceeds = sell_val + trim_val` — equity-only, used for `tax["gross"]`
- `proceeds = eq_proceeds + fund_action_val` — combined total, used for `deployment["proceeds_inr"]`
The chart caption says "Direct-equity sells & trims, net of est. tax" — if the gross number includes fund actions, it's a BUG.

### IPS page (ips_summary.py, v2, RESTORED)
Renders ONLY when `ctx["ips"]["on_file"]` is True. Structure:
- 4 mini-tables in the house navy/gold rail-and-pill style (never a plain corporate table)
- **Portfolio level**: equity/debt split, single-scheme/AMC/locked-in/cash caps
- **Equity level**: market-cap bands, thematic/unlisted/international caps
- **Fixed income**: credit-quality bands (AAA/AA/A/below-A) + duration cap
- **Commodities**: gold/silver bands
- "Current" is ALWAYS computed live from ctx via `_lookthrough_mix()` — includes look-through equity/debt split (direct equity + equity-oriented fund categories), materially different from direct-equity-only figures
- "Ideal" shows "TBD" and Fit shows "Pending" for any parameter with no bespoke IPS on file — never a fabricated target

### Cross-panel consistency scan (mandatory QA gate)
Any two numbers on the same slide that a reader will assume are the same set MUST reconcile or be explicitly scoped. Examples:
- Tax table = fund actions vs waterfall = equity plan → different bases, both disclosed
- concentration_risk KPI vs holdings table rows = same basis: % of equity sleeve
- Same-entity names identical across slides (short_name width >=30 for scheme tables)
- A driver/tag must match the narrative beside it and the same call's rationale elsewhere in the deck

### CEO-sweep fixes (baked in, do not regress)
- `_reason_category`: buckets scored by keyword-hit COUNT on negative_para first (rationale fallback), with negation scrub (`no ... red flags` never trips forensic) and bare "growth" excluded (stat mentions like "PAT growth +156%" aren't a slowing-growth thesis)
- Commodity-cycle reversal suffix (sell_cards): applies to sector "Metals & Mining" ONLY — conglomerates/utilities in Oil&Gas/Power must not get "metal price" language
- Tax rows: character from holding_years (>=1y = LTCG; REDEEM = "Mixed, lot-by-lot") — the old `action in ("Switch","Exit")` check never matched UPPERCASE codes
- CoPilot CTA is OUT — no product names client-side

### Talaulikar-build lessons (2026-08-02) — bugs fixed, do not regress

**MF / fund name mapping**
- **Never fuzzy-match a fund name to a framework's fund list.** A naive string-similarity pass matched "Kotak Midcap Fund" to "Kotak Multicap Fund" (wrong category) and "ICICI Prudential Liquid Fund" to "ICICI Pru Large & Mid Cap Fund" (nonsensical — liquid vs equity). Always dispatch a Sonnet agent, one fund at a time, reasoning about real scheme identity (same AMC + same mandate) with web search to disambiguate — see `[[feedback-mf-mapping-no-fuzzy]]` memory. "Not found" beats a wrong guess, always.
- **AMC abbreviation table needed.** "ICICI Prudential" == "ICICI Pru" (same AMC — reconcile), but "Aditya Birla Sun Life Flexi Cap" != "Axis Flexi Cap" (different AMC — do NOT reconcile despite similar-sounding "Flexi Cap" suffix). Build and maintain a canonical AMC-alias table so this stops being solved fresh per client.
- **Scheme-rename table needed.** Several AMFI schemes changed names and our mapping missed them on first pass: ICICI Pru Bluechip Fund → ICICI Prudential Large Cap Fund; Kotak Emerging Equity Fund → Kotak Midcap Fund; Bandhan Core Equity Fund (formerly IDFC Core Equity Fund) → Bandhan Large & Mid Cap Fund; DSP Equity Opportunities Fund → DSP Large & Mid Cap Fund. Maintain a living rename lookup so the next client's holdings match on the first pass, not after a manual audit finds the gap.
- **Category-label mismatch between our schema and QFRA's.** Our fund `category` field ("mid") doesn't always match QFRA's own category value ("largemid") for the same real scheme — check both label sets before concluding a fund is "not covered."

**CAS parsing / data corruption**
- **Row-bleed defect found and fixed:** one stock's `name` field was silently concatenated with an entirely different holding's row content (`POLYCAB INDIA LIMITED` had `NIPPON LIFE INDIA ASSET ... NAM-INDIA.NSE ...` glued onto the front) — a real double-mapping bug in the CAS extraction path. **Add a validation pass on every new client's parsed CSV**: any equity/fund `name` field over ~80 chars, or containing more than one ISIN-looking token, is a red flag — fix before it enters `data/<client>.py`.

**Score / verdict field completeness**
- **Setting `rec`/`verdict` and setting `qfra`/`merit` (the actual score+grade) are two separate steps** — it's easy to update one and leave the other blank, producing a Sell/Hold pill with no number behind it on the fund-book-scored table. Any override block that changes a call must set both together, never one alone.
- **Never default a categorical field to one hardcoded value for the whole book.** `mcap_band` silently defaulted to `"Small"` for every stock and `sector` defaulted to blank/"Diversified" for every stock — both went undetected until the mcap/sector slides visibly showed 100% in one bucket. Always compute per-holding from a real classification, never a blanket default.
- **Never render a raw 0 for "unscored."** Distinguish `None` (genuinely outside the scored universe → show blank/"-") from a real score of 0 — audit every module that does `f"{score:.0f}"` for a missing None-guard.

**Ground-truth vs. derived-state confusion**
- **Never treat an earlier in-session variable dump as "the base data."** A dump taken mid-session already reflected a prior fixup-loop's mutation; trusting it as ground truth nearly caused reverting three real equity Sells back to Hold. Before removing what looks like a redundant override, always grep the ORIGINAL dict literal in the source file — never rely on a cached mental model or an earlier printout from the same conversation.

**Stale / hardcoded narrative text**
- **Any hardcoded client-specific-sounding sentence is a landmine.** Found and fixed 6+ in one rebuild: a fabricated ">11% concentration breach" that didn't exist in the real book (`exec_summary.py`), a false "All 98 holdings are scored" claim (`book_scored.py`), an overbroad "never a performance sale" claim (`fund_actions.py`), a hardcoded "positions above the 8% cap" trim narrative when nothing was above the cap (`priority_actions.py`), stale data-quality flags still saying "No Recommendation" / "all shown as No View" after both had changed, and a self-contradictory "retirement gap...can close" sentence sitting next to a 100%-funded number (`annex_goal_mapping.py`).
- **Rule going forward:** every hardcoded narrative sentence in a module must be re-derived from `ctx` at build time. A module docstring or inline comment should flag anything that can't be (rare) as "CLIENT-SPECIFIC — reverify every build." Grep for `>`, "all", "none", "every" + a number across `modules/*.py` before shipping any deck with materially changed data.

**Template scale limits**
- `fund_actions.py`'s card grid and `tax_impact.py`'s fund table were both hand-fit for ~6-10 items and broke (illegible or overflowing) once a real client had 16-17 fund actions in one book. Fixed with adaptive column counts and capped+summarized rows (never silently drop items — show top-N + a disclosed "+N more" row).
- **Rule:** stress-test any module rendering a variable-length list from `ctx` at 2-3x the current largest real client's count before shipping, not just against the size of the original demo book.

**Cross-module total consistency**
- Two modules independently computing "the same" total (`tax_impact.py` vs `priority_actions.py` fund-actions total) used different rounding/summation order and disagreed by Rs 0.1L on an identical figure. **Rule:** any total shown on more than one slide must be computed via one shared path — never reimplemented per-module with its own rounding order.

**QFRA-1 vs QFRA-2 discipline**
- These are different engines (QFRA-1 = short-term capture-ratio, 6 categories; QFRA-2 = long-term curated 40-fund list, 8 categories) — never back-solve one framework's score from the other's raw metrics without validating against known real overlap cases first. A tested back-solve formula inverted the real grade on 2 of 8 validation funds (looked fine short-term, scored D/C on the real long-term framework) — using it uncaught would have shown the client a plausible-looking WRONG number. When a back-solve doesn't validate, disclose the honest coverage gap instead of guessing.
- When only QFRA-1 covers a fund (no QFRA-2 curated entry), the defensible fallback score is a REAL percentile rank on the framework's own primary ranking metric (`HC_total_cap_6M`) computed from the actual dataset — a genuine statistic, not an invented formula.

**Directed/portfolio-reason vs. quality-reason conflation**
- A Sell/Trim driven by a client's cash need (directed liquidity) is a fundamentally different fact than one driven by the scoring framework — conflating the two silently breaks several narratives at once (an inflated "analyst override" register, a false "never a performance sale" claim, a wrong sell-count description). **Fix:** tag it explicitly in the data (`sell_reason_type = "quality" | "liquidity"`) the moment a directed override is applied, so every downstream module reads one authoritative field instead of re-deriving the distinction from score thresholds (tried, and it's error-prone — genuine analytical overrides and liquidity-directed sells can land on the same score band).

**House-style consistency**
- Currency-symbol drift (₹ vs the house "Rs") survived undetected in a few modules. Add a house-style grep (currency symbol, internal jargon words, "No Recommendation" vs "No View") to the standard pre-ship pass, not just the 3 automated QA gates.

**Process / workflow**
- Parallel read-only audit agents — one per deck section, each cross-checking rendered PPTX text against `ctx` and module source — surfaced real, citable bugs efficiently and should be the standard pre-ship review pattern for any client rebuild with material data changes, not just the 3 automated QA gates.
- **Freeze the target before auditing.** One audit agent caught the source files changing mid-audit (slide count flickering 95→92→95) and had to pin a frozen snapshot to get reliable results. Don't dispatch audit agents against files still being actively edited — copy the target PPTX + data file to a frozen snapshot first.
- Under real time pressure ("2 min", "30 sec max"), the fix is not to skip verification — it's to keep the CHEAPEST verification (grep the raw source literal) even while moving fast. A rushed assumption about "base state" during a compressed window is exactly when a regression slips through.

### Slidekit primitives (prevent regressions)
- `clip_sentences`: whole sentences, decimal-safe
- `clip_clause`: sentence/semicolon-only periods, paren-balanced
- `short_name`: word-drop, no mid-word chops (min width 30 for scheme tables)
- `callout_h`: text-hugging panel heights
- `scope_tag`: drops whole segments when capped
- `resolve_links()`: internal clickable cross-refs at save time
- Render-time detell in `txt()`: em-dash to comma, "genuine" to "clear", arrow/math symbols to words (Bahnschrift lacks the glyphs)
- Chart law: NEVER `ax.legend()` — use direct labels, `caption_above()`, or `chip_legend()`; NAVY = primary series; `halo()` behind text on fills

### Tell scan buckets (tellscan.py)
AI-writing tells: em-dash, "genuinely"/"robust"/"holistic"/etc.
Internal jargon: SENTINEL, QFRA, MERIT, pf_qual, AZBY, "quant-only, analyst view", "Ratified Sell", "One-time review", "House decision"
Client words to use instead: "watch-outs", "fund score /100", "grade", "the firm's fund-quality framework"
Data-QA vocabulary: "stale", "does not reconcile", "data feed", "data cut", Data Office, CoPilot
Source/analyst citations: screener.in, INDmoney, Groww, Paytm Money, Advisorkhoj, analyst names
Raw snake_case field names
"synthetic/demo/illustrative" language mislabeling REAL client data

---

## PART 2: STOCK SCORECARD 750 (Quantamental Scoring)

### What it is
A 0-100 quantamental scoring engine for stock holdings. Dual-horizon (3-Year fundamental-tilted, 1-Year technical-tilted), never blended into one number at the analyst level. Recommendation vocabulary: **Sell or Hold ONLY, never Buy** — this reviews existing holdings.

### Location
`Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/`

### Dual-horizon scoring (7 pillars)

| Pillar | 3Y Weight | 1Y Weight | Formula |
|---|---|---|---|
| Quality | 20% | 16% | mean(pctile(ROE, sector-neutral), pctile(ROCE, sector-neutral)) |
| Growth | 20% | 16% | 3Y: 3yr revenue CAGR; 1Y: 1yr/TTM revenue growth — universe-wide pctile |
| Value | 18% | 16% | 0.25*pctile(-PE,univ) + 0.35*pctile(-PE,sector*tier) + 0.20*pctile(-PB,sector*tier) + 0.20*pctile(FCFyield,sector*tier) |
| Stage/Technical | 14% | 26% | Mechanical: mean(pctile(return,univ), pctile(return,sector)) gated by DMA; 1Y has +/-5pt RSI nudge. If technical-agent ran: replaces 3Y mechanical score |
| Sector & Macro | 11% | 13% | pctile(sector-mean return) + regime-cyclicality fit adjustment |
| Ownership Flow | 9% | 8% | pctile(mean FIIs_qoq+DIIs_qoq), trailing 6-of-8Q (3Y) / 1-2Q (1Y) |
| Accumulation | 8% | 5% | pctile(OBV slope), 6-12mo (3Y) / 1-3mo (1Y) |

All inputs winsorized 2%/98% before percentile ranking.

### Overlay gates (multiplicative, after weighted composite)
- **Balance-Sheet Safety**: D/E>2.5 OR IntCov<1.5 = RED, caps at 40. D/E>1.5 OR IntCov<3 = AMBER, x0.85. **Financial sectors EXEMPT** from D/E trigger (leverage is their business model).
- **Liquidity**: median 60d turnover below size-tier bar (5cr/1cr/25L for Large/Mid/Small) = RED, caps at 40.

### Penalty/Boost
Penalty = -min(10, 2^(redflag_count)-1). Red flags: IntCov<1.5, D/E>2.5 (non-financial only), negative 1yr revenue growth, >15pp deceleration, analyst expected growth <10%.
Boost = +3 if zero flags AND Quality+Value both >60th pctile. Full +10 reserved for qualitative confirmation.

### Recommendation logic
Per horizon: gate RED = Sell. Score missing = No Recommendation. Score >=40 = Hold, <40 = Sell.
**Overall = Sell if EITHER horizon says Sell** (conservative).
Analyst's `your_recommendation` OVERRIDES quant when research exists.

### Ionic Score (client-facing, one number)
`base = 0.60 * final_3y_adj + 0.40 * final_1y_adj`
Forward adjustment:
- Growth leg (analyst's forward 3-5yr estimate): <5% = -15 | 5-10% = -5 | 10-15% = 0 | 15-20% = +5 | 20-25% = +10 | >=25% = +15 | +20 exceptional (>=25% AND ROE>=20% AND dilution<2%)
- Conviction leg: analyst Sell = -6 | analyst Hold where quant said Sell = +6 | agreement = 0
- Clamped +/-20. Two caps: (a) expected growth <10% = net adjustment <=0; (b) analyst Sell = net adjustment <=0.
- `ionic_score = clamp(base + adj, 0, 100)`

### Client recommendation logic (two-gate, with portfolio weights)
- **Gate A (quality):** analyst Sell = Sell. Else ionic_score <40 = Sell.
- **Gate B (concentration):** ionic_score 40-50 AND weight >2.5% = Trim.
- Concentration guidance: 5-10% = okay if growth strong; >10% = "little bad", Trim expected; >20% = extreme, strong Trim.
- Trim targets set by FM judgment, not formula.

### Asymmetric override bars
- Sell on a >40 scorer: needs 90%+ exceptional case (amber EXCEPTIONAL tag)
- Hold on a <40 scorer: needs 60%+ documented case
- Default below 40 is Sell. The 750 universe runs ~33% quant Sells — a book far below that = override leakage.

### Research pipeline (Sonnet, one agent per stock)
Each stock gets ~3min deep research: business model, earnings-quality check, sector-cycle context, reverse-DCF valuation judgment, forward growth estimate. Persona-routed by sector. Escalation only for genuine analytical disagreement (price staleness is expected, NEVER escalated).

### Technical agent (separate, one per stock)
Reads real price parquet, monthly resample, judgment on multi-year swing structure, MA-stack, volume character. Produces `chart_long_term_technical_pattern_score` (0-100) + choppiness penalty (0 to -15).

### Output formats

**Analyst Excel** (`build_analyst_excel.py`): 3 sheets — Analyst Full Detail (46 columns, full schema), Field Guide (self-documenting column definitions), Research Reader (per-stock long-form blocks).

**Client Excel** (`build_client_excel.py`): 3 sheets — At a Glance (dashboard), Recommendations (Stock/Ticker/ISIN/Sector/%/Ionic Score/Rec/Trim-to/Rationale), Portfolio Before-vs-After (weights, sector, mcap, concentration before and after).

### Running the scorecard
```bash
# 1. Scrape data (per SCRAPING_SOP.md)
# 2. Compute quant scores
%PYTHON% 09_PRODUCT/scripts/compute_client_scores.py

# 3. Run analyst research (sector-persona agents via the agent roster)
# 4. Run technical agent pass
# 5. Build client Excel
%PYTHON% 09_PRODUCT/scripts/build_client_excel.py <quant_csv> <qual_json_dir> <out.xlsx>

# 6. Build analyst Excel
%PYTHON% 09_PRODUCT/scripts/build_analyst_excel.py <quant_csv> <qual_json_dir> <out.xlsx>
```

### Shared code library
`04_RND_LAB/STOCK_SCORECARD_750/lib/scorecard_common.py`: winsorize, percentile_rank, filter_pit, atomic_write, SECTOR_CYCLICALITY, fundamental-ratio derivation (ROE/ROCE/D-E/P-E/P-B/reverse-DCF), technical indicators (RSI/returns/SMA/vol via gs_quant.timeseries + OBV).

### Regime system (6 categories)
1. Global Risk-On/Easy Liquidity
2. Global Risk-Off/Tightening
3. India Domestic Expansion
4. India Domestic Slowdown/Stress
5. Value/Cyclical Rotation
6. Growth/Quality Leadership

Current call: Primary = Value/Cyclical Rotation (mild), Secondary = India Domestic Slowdown/Stress (mild), blended 70/30.

---

## PART 3: MF QUALITY FRAMEWORKS (QFRA-1 / QFRA-2)

### QFRA-1 (Short-term capture framework)
Source: `MF Dashboard.xlsx` via `mf_capture_recomm.compute_category`.
Method: 6-month down-capture ratio vs the fund's own SEBI category benchmark. FN=6M down-capture, HC=6M total capture.
Category cutoffs: Large/Multi = 90%, Mid = 80%.
A fund that takes LESS of the benchmark's falls than the cutoff passes.

### QFRA-2 (Long-term SIP framework)
Source: `QFRA2_current.csv` (40 curated funds only).
Method: Long-term scoring framework, proprietary to the Ionic MF desk.
Coverage: focused + value/contra categories that QFRA-1's dashboard has no sheet for.

### Dual-framework fund Sell rule
**A fund Sell goes to the client ONLY when BOTH frameworks independently say Sell.**
- A BUY/high-score on EITHER side VETOES the Sell
- One says Sell + the other Hold = default HOLD
- Both Hold = Hold
- Structural actions (Redeem-to-Direct, mandate switch) are exempt — they're plan facts, not performance calls
- Coverage gap: QFRA-2 covers focused + value/contra not in QFRA-1; single-framework Sells there need explicit FM sign-off

### Fund benchmarks (every fund vs its OWN SEBI category benchmark)
Large = Nifty 100 TRI, LargeMid = Nifty 250 TRI, Mid = Nifty Midcap 150 TRI, Flexi = Nifty 500 TRI, Multi = Multicap 50:25:25, Small = Smallcap 250 TRI, Hybrid = N50 Hybrid Composite 65:35 TRI.
MDD/worst-1yr labeled COMMON 3-YEAR WINDOW everywhere.

### Factor-fund rule
Factor ETF/index fund held directly defaults to Hold, UNLESS it is a Nifty 200 Momentum 30 fund (documented regime-dependent failure mode = Sell). Plain non-factor index funds can still be Sold on consolidation/cost grounds.

### "Redeem-to-Direct" display
Internal verdict code stays `Redeem-to-Direct`. Client-facing display = "Switch" (via VDISP mapping in each module).

---

## PART 4: CLIENT INTAKE WORKFLOW

### Design principle
**"Standardize the FORMULA, personalize the DATA, never standardize the OUTPUT."**
Every module is a pure function of the `ctx` dict — numbers/names/verdicts all trace to `ctx[...]` lookups. The template is standardized; the data layer is per-client; the rendered deck is unique to that client's book.

### Full pipeline (real client, Apr/Oct cadence)

**Step 0: Advisor intake (same turn as holdings upload)**
The INSTANT a holdings file arrives, do TWO things in parallel:

**(a) Launch parallel-compute** (zero advisor interaction needed):
`client_intake.py` match → `pf_qual_*.json` lookups per matched stock → `fund_ctx_adapter.py` QFRA-1/QFRA-2 verdicts per matched fund → sector/mcap/concentration/cost aggregates → all written to `client_ctx.json` + `exceptions.csv` on disk.

**(b) Ask the advisor up to 4 questions** (while compute runs):

**Q1 — Deck depth:**
| Option | Slides | Description |
|---|---|---|
| **Detailed (HNI_DEEP)** | 60-100pg | Full methodology, all annexure modules, family-office grade |
| **Medium (STANDARD)** | 30-60pg | Professional, accessible, selected annexure |
| **RM Light (RM_SIMPLE)** | 15-30pg | Plain language, bigger type, story beats only |
Warn: RM Light can occasionally print >30pg on a large book (pagination, not a preset bug) — offer Medium instead of forcing the ceiling.

**Q2 — First review or follow-up?** (unlocks `since_last_review` module if meeting_history supplied)

**Q3 — Anything to exclude/downplay?** (tax detail, methodology detail, specific sections)

**Q4 — Turnaround / PDF need?** (PDF conversion is ON REQUEST ONLY, never auto)

**Then ONE follow-up after Q1 is answered:**
**Recommended** (ship the tier's current preset from `tiers.py` as-is) or **Customize** (show a checklist of the tier's optional modules, each tagged **(recommended)** when it's in that tier's `optional_on`; for RM_SIMPLE only, also show its `skip_core` modules as re-addable). Modules that are PARKED/CUT are never listed — they're retired, not a choice. Full spec: `INTAKE_WORKFLOW_SPEC.md`.

Do NOT wait on (b) to start (a) — they're independent; by the time the advisor answers, the expensive research is already on disk.

**Step 1: Intake**
```bash
%PYTHON% 09_PRODUCT/scripts/client_intake.py --holdings <CAS.csv|xlsx> --profile <profile.json> --out <client_dir>
```
Profile JSON template (emit via `--emit-template`):
- client: name, code, account_type, profile, horizon, construction
- goals: [{name, target_inr, by_year, note}]
- holdings_meta: per-symbol acquisition info (holding_years, cost_inr)
- family: {members, structure_note}
- meeting_history: [{date, summary, actions: [{action, owner, status}]}]

Matching: ISIN first, then normalized-name prefix. Unmatched rows go to `exceptions.csv` for the RM — NOTHING silently dropped or fabricated.

**Step 2: Fund calls**
`fund_ctx_adapter.py`: QFRA-2 (curated CSV, 40 funds) + QFRA-1 (MF Dashboard.xlsx); merged by dual-framework rule. Held funds outside QFRA-2 = honest gap "needs a QFRA-2 scoring run".

**Step 3: Build**
```bash
set PR_SUFFIX=_v1
%PYTHON% build_<client>.py HNI_DEEP
```
If build errors with **PermissionError** — the PPTX is OPEN in PowerPoint. Bump `PR_SUFFIX` (e.g. `_v2`), never fight the lock.

**Step 4: QA gates** (see Part 1)

**Step 5: PDF on request** (see Part 1)

**Step 6: Publish** to `09_PRODUCT/reports/`

### Holdings source format (CAS extract)
Columns (case-insensitive): type (EQ/MF), name, isin (preferred), units, value_inr.
A raw NSDL CAS PDF parser is planned when a sample statement arrives.

---

## PART 5: PRINCIPAL RULINGS (ALL, DO NOT REGRESS)

### Vocabulary & scope
- **Sell/Trim/Hold only, NEVER Buy.** No buy recommendations anywhere. Proceeds park in cash.
- **opportunity_set.py and deployment.py are CUT entirely** — this deck only sells/holds.
- **Cost slide CUT** — was scheme-TER-only with no Regular-drag/PMS overlays.
- Commentary leans WITH the call. A Sell never leads with praise; positives only as the rejected bull.
- Score method = gist only: never reveal the 60/40 blend, pillar weights, or thresholds beyond "below 40 / 40-50 watch / 50+".

### Design & presentation
- Cover/dividers: generative flow-art, two-tone headline, text logo lockup on navy, divider mini-TOC + ghost numeral.
- Correlation/overlap matrices capped: annex_correlation top 15 by weight, scheme_overlap_full top 10 by weight. Both disclose cap via scope_tag.
- Growth-projection mu/sigma derived from THIS book's real holdings, never a flat 12%/14% constant.
- **PDF on request only** — never auto-convert after every rebuild.
- **Deliverables are HUMAN-format**: Word/PowerPoint with tables/charts, or clean in-chat tables. Never bare .md pointers.

### Fund rules
- Tax inertia: fund units >5y get raised switch bar. Stocks exempt (single-name risk dominates).
- Fund Sell needs BOTH frameworks (QFRA-1 AND QFRA-2) independently at Sell.
- Every fund measured vs its own SEBI category benchmark (never one common index).
- MDD/worst-1yr labeled COMMON 3-YEAR WINDOW.
- Factor-fund default = Hold (except Momentum 30 = Sell).
- LIC BAF class = scale/record framing, never a cushioning smear.

### Equity rules
- Asymmetric override bars: Sell on >40 = 90% exceptional; Hold on <40 = 60% documented.
- Balance-sheet gate is context-aware (industry norms, sovereign backing, promoter group).
- Commodity-cycle names get explicit cycle-position read.
- Demo-data: real name in demo only if real record supports it.

### Scheme overlap heatmap (scheme_overlap_full.py)
- Fund-vs-fund overlap matrix capped to **top 10 by weight** (permanent)
- Label generation uses **case-insensitive 22-keyword matching** (LARGE/FLEXI/MULTI-ASSET/MULTI/SMALL/MIDCAP/MID CAP/BALANCED/HYBRID/ELSS/VALUE/FOCUSED/DIVIDEND/NIFTY/INDEX/OVERNIGHT/LIQUID/GILT/SHORT/ULTRA SHORT/ARBITRAGE/EQUITY SAVINGS) to prevent label collisions between same-AMC funds

### Redeem-to-Direct display collision risk
Internal verdict code stays `Redeem-to-Direct`; client-facing display = "Switch" via VDISP mapping. Known open risk: this visually collides with the pre-existing "Switch" verdict (move to a different fund). Both show identical "Switch" pill. Revisit if a client ever holds both action types and it reads as confusing.

### Internal jargon control
Client vocab: "watch-outs", "fund score /100", "grade", "the firm's fund-quality framework".
NEVER in client materials: SENTINEL, QFRA, MERIT, pf_qual, engine version numbers, agent names, technical jargon.

### "What would flip a Hold" type meta-text is BANNED.

### Pending (next time, do NOT implement without re-confirming)
`funds_equity.py`'s paired-bar chart currently shows each fund's own-benchmark CAGR correctly, but the visual legend just says "Its category benchmark" generically — a reader can't tell WHICH benchmark applies to WHICH fund. Principal wants a category-wise benchmark MAP visible directly in the graph.

---

## PART 6: ENVIRONMENT & COMMANDS

### Python
```
Path: C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe
Alias "python" is BROKEN — always use the full path.
Always set: PYTHONIOENCODING=utf-8  PYTHONUNBUFFERED=1  (console is cp1252)
```

### Corporate proxy
~0.7MB/s. Sequential `requests.Session()` only (threads stall).
`truststore.inject_into_ssl()` before any HTTPS call.

### PowerShell 5.1
No `&&` operator. Write Python to .py files and execute (here-strings break raw strings).

### PDF conversion (`pptx_to_pdf.py`, auto-backend)
Three backends tried in order (best-available wins):
1. **PowerPoint COM** (desktop, pixel-perfect) — needs `comtypes` pip package + MS Office. `pip install comtypes` once.
2. **LibreOffice** (user-local `%LOCALAPPDATA%\Apps\LibreOffice`, msiexec /a extract, no admin)
3. **Slide-to-PNG** (pure Python, works on web/sandbox/no-Office) — rasterises at 150 DPI, text not selectable but layout faithful
Force a backend: `--backend pptx|libre|png`. Default = auto-detect.

### Angel SmartAPI (data only, NO real trades ever)
API key: 8crMtPbu, client: S59047501. Rate limit AB1021: use >=1.2s/req, retry passes.
Angel purges expired option contracts from master — daily capture task handles this.

### NSE data
`nsearchives.nseindia.com` bhavcopy zips + corporate-board-meetings/event-calendar APIs succeed after cookie warm-up. Other `/api` endpoints (FII/DII, constituents) still 403 from corporate network.

### Key data locations
```
datasets/                                       Raw market data
04_RND_LAB/STOCK_SCORECARD_750/results/         Scored universe (pf_qual_*.json, portfolio_quant.csv)
04_RND_LAB/STOCK_SCORECARD_750/book/            Per-stock analyst pages
09_PRODUCT/pr_template/data/                    Client context files for the deck
09_PRODUCT/pr_template/out/                     Built decks
09_PRODUCT/reports/                             Published deliverables
09_PRODUCT/scripts/                             Builder scripts (Excel, PDF, intake, analytics)
```

---

## PART 7: DATA LANDMINES (violating these = fake backtests)

1. **HF timezone bug**: daily timestamps 18:30 UTC = next-day IST. Fix: `dt.tz_convert('Asia/Kolkata').dt.date`.
2. **Pre-open auction bug**: 1-min "open" at 09:00 is auction price; real open = first bar >=09:15.
3. **Earnings lookahead**: use PIT dataset `datasets/earnings_pit/unified_quarterly_pit.parquet` with `available_date`. NEVER quarter-end dates.
4. **Option data dual schema**: HF 1-min tz-aware vs bhavcopy daily with `settle` col and 0.00-price untraded strikes. Use `04_RND_LAB/lib/guards.py` schema helpers.
5. `india_fundamentals_mc/Train.parquet` `annual_report` col is corrupt at source — read other cols only.
6. **Survivorship**: use `NIFTY500_TICKER_2005_2025_Final.xlsx` (42 PIT snapshots) for universe membership.
7. **Circuit/volume fills**: no fill on circuit-locked bars; slippage 2-3x on thin-volume days.
8. **Angel getCandleData ONE_DAY timestamps**: bars stamped 00:00 IST. A `fromdate` with intraday time silently DROPS the first day.
9. **F&O bhavcopy expiry-day SETTLE_PR**: the UNDERLYING's final settlement, NOT the option price. Never read expiry-day option settles.

---

## PART 8: AGENT ROSTER

### Investment Committee
| Agent | Role | Summon when |
|---|---|---|
| cio-rajan-mehta | CIO, 20+yr, capital protection & tail risk | Final decisions, risk vetoes, portfolio-level calls |
| fm-vikram-shah | FM — Derivatives & short-vol, 15+yr | Idea prioritization, capital allocation, IC convening |
| fm-equities-devika-menon | FM — Equities & Momentum, 15+yr | Equity/momentum allocation, Track-2, factor sleeves |
| fm-fundamental-sanjay-kulkarni | FM — Fundamental Quality & Value, 18+yr | Long-only fundamental portfolio, value/quality sleeves |

### Research desk
| Agent | Role | Coverage |
|---|---|---|
| equity-head-ananya-iyer | Head of Equity Research, 10+yr | Coordinating analyst desk, deep-dives |
| analyst-financials-meera-krishnan | Financials analyst | Banks/NBFC/Insurance/CapMarkets |
| analyst-it-karan-malhotra | IT analyst | IT/Internet/New-age |
| analyst-pharma-sneha-patil | Pharma analyst | Pharma/Healthcare/Chemicals |
| analyst-industrials-rohan-deshmukh | Industrials analyst | Industrials/Defence/Power/Infra |
| analyst-consumer-priya-nair | Consumer analyst | Consumer/Auto/Retail |

### Quant & risk
| Agent | Role | Summon when |
|---|---|---|
| quant-head-arjun-rao | Head of Quant (IIT/MIT), 10+yr | Backtest design, stats validity, signal research |
| technical-head-dhruv-kapoor | Technical, Minervini-school, 15+yr | Chart setups, entries/exits, stage analysis |
| risk-manager-ritika-sharma | Portfolio Risk Manager, 10+yr | VaR/stress/exposure/limits |
| overfit-analyst-sameer-bhat | Overfit Analyst, 10+yr | Param surfaces, perturbation, DSR/PBO, Gate-4 |
| red-team-nikhil-bose | Devil's Advocate | MUST review before any strategy passes audit gate |

### Specialists
| Agent | Role | Summon when |
|---|---|---|
| macro-strategist-cyrus-daruwalla | Macro Strategist, 15+yr | Macro calendar, regime reads, event-window warnings |
| structurer-aakash-jain | Derivatives Structurer, 12+yr | Vehicle/strike/margin design |
| hedge-expert-kabir-anand | Hedging & Tail Risk, 14+yr | Hedge programmes, options overlays, tail sizing |
| execution-tca-tara-singh | Execution & TCA | Cost modeling, fill realism, slippage |
| attribution-analyst-neel-basu | Attribution Analyst, 8+yr | P&L decomposition, monthly attribution |

### Operations
| Agent | Role | Summon when |
|---|---|---|
| ceo-meher-kapadia | CEO, 20+yr | Firm-wide coordination, cadence, budget, HR |
| product-head-tanvi-desai | Head of Product, 12+yr | Investor letter, dashboards, deck UX |
| data-officer-kavya-reddy | Data Management | Ingestion, verification, catalog |
| ops-engineer-manoj-pillai | Ops Engineer, 10+yr | Pipelines, scheduled jobs, repairs |
| ml-expert-ishaan-gupta | ML/Data Science | Feature engg, models, validation |
| rnd-head-aditya-verma | Head of R&D | New edge hypotheses, research loop |
| librarian-lakshmi-narayanan | Knowledge Curator | KNOWLEDGE_BASE, paper summaries, prior-art |
| compliance-farhan-qureshi | Compliance, 12+yr SEBI | Standing-order audits, regulatory watch |

---

## PART 9: HARD RULES (NEVER BYPASS)

1. **NO real-money trades, EVER.** Angel account is fund-less/data-only. Everything is research/paper until the Principal explicitly approves a live step.
2. **EPISTEMIC CONDUCT (D-035):** never fabricate; estimates labeled; no silent assumptions; tag [DATA]/[INFERENCE]/[OPINION]; verify before claiming done.
3. **MAX 3 PARALLEL AGENTS** (D-023).
4. **Approvals (D-025):** prompts/standards/data-sources = CEO+CIO joint. LIVE capital + RISK_LIMITS = Principal ONLY.
5. **Forward-test freeze (D-030):** once a strategy is in forward test, spec+code+params are FROZEN (pin git hash). Any change = new version with restarted clock.
6. **Cost/slippage assumptions:** use ONLY `06_TRADING_DESK/COST_STANDARDS.md`. Approved (D-021).
7. **Lookahead controls:** T1-T10 taxonomy in `07_RISK_OFFICE/LOOKAHEAD_CONTROLS.md`. No Gate-4 pass without a LOOKAHEAD AUDIT PASS.
8. **Token discipline:** cheapest model that does the job (haiku=mechanical, sonnet=analysis/coding, opus=IC/final capital judgment). Checkpoint before token limits.

---

## PART 10: FIRM STRUCTURE

```
Shreyas_Ionic_AMC/
  00_GOVERNANCE/       Charter, TEAM_ROSTER, TOKEN_POLICY, MODEL_ASSIGNMENTS, EVOLUTION_LOG
  01_COMMAND_CENTER/   SESSION_JOURNAL, CURRENT_STATE, DECISIONS_LOG
  02_PROMPT_LIBRARY/   drafts/ -> approved/
  03_RESEARCH_DESK/    IC_MEMO_TEMPLATE, memos/
  04_RND_LAB/          IDEA_PIPELINE, KILLED_IDEAS, KNOWLEDGE_BASE, STOCK_SCORECARD_750/
  05_DATA_OFFICE/      DATA_CATALOG, DATA_QUALITY_RULES
  06_TRADING_DESK/     COST_STANDARDS, STRATEGY_REGISTER, PAPER_LEDGER
  07_RISK_OFFICE/      RISK_LIMITS, ADVERSARIAL_REVIEWS, LOOKAHEAD_CONTROLS
  08_BOARD_ROOM/       BOARD_CHARTER, minutes/, month_end/
  09_PRODUCT/          pr_template/ (NDPMS deck), reports/, scripts/
  10_BRAND_DESK/       Personal brand publishing (LinkedIn, Substack)
  90_PRINCIPALS_DESK/  Principal's non-firm tasks (firewalled)
  99_OPS/              EOD_ROUTINE, BACKUP_POLICY
```

### Session protocol
1. **Session start:** read `01_COMMAND_CENTER/CURRENT_STATE.md` + last ~2 journal entries
2. **Session end / milestone:** append to `SESSION_JOURNAL.md` AND update `CURRENT_STATE.md`
3. Long tasks: checkpoint progress to files so the other account or a restart can resume

### Two-desk model
- **DESK-20** (desktop app, $20/mo): CIO office — R&D, ideas, analysis, light work. Max 2 parallel agents.
- **DESK-100** (VS Code, $100/mo): Execution floor — backtests, bulk data, batch workflows, EOD auto-runs. Max 3 parallel agents.

---

## PART 11: AGENTIC FUND MANAGER WORKFLOW

### Full NDPMS client review (Sell/Trim/Hold with targets)

**Step 1 — Mechanical layer** (script, ~0 tokens):
Compute ionic_score, portfolio weights, sector weights, mcap bands. Flag candidates:
- Gate A: analyst Sell or ionic_score <40 = Sell-candidate
- Gate B: ionic_score 40-50 AND weight >2.5% = Trim-candidate
- Concentration: >10% = Trim advice expected; >20% = extreme
- Single-GROUP concentration: if any promoter group >20% of equity sleeve, flag for group-concentration slide

**Step 2 — FM judgment pass** (one Sonnet agent):
FM sets final action + Trim targets + client reasons. Overrides are logged. Commentary leans with the call. Nothing invented — shaky facts go back to analyst layer.

**Step 3 — Verification gate** (MANDATORY):
Script-verify: weights sum to 100.00 (+/-0.05), after-weights reconcile, every Sell/Trim has reason, every Trim has target < current, vocabulary correct, sentiment matches call, no internal jargon.

**Step 4 — Build + ship gate**:
Build Ionic Wealth Excel via `build_client_excel.py`. No deliverable ships without Principal sign-off.

---

## QUICK REFERENCE: COMMON COMMANDS

```bash
# Set up environment
set PYTHON="C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe"
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

# Build NDPMS deck
cd Shreyas_Ionic_AMC/09_PRODUCT/pr_template
%PYTHON% build_<client>.py HNI_DEEP

# Run QA gates
%PYTHON% check_geometry.py out/<deck>.pptx
%PYTHON% check_geometry2.py out/<deck>.pptx
%PYTHON% tellscan.py out/<deck>.pptx

# Convert to PDF (on request only)
%PYTHON% ../scripts/pptx_to_pdf.py out/<deck>.pptx

# Build client Excel (stock scorecard)
%PYTHON% 09_PRODUCT/scripts/build_client_excel.py <quant_csv> <qual_json_dir> <out.xlsx>

# Build analyst Excel
%PYTHON% 09_PRODUCT/scripts/build_analyst_excel.py <quant_csv> <qual_json_dir> <out.xlsx>

# Client intake
%PYTHON% 09_PRODUCT/scripts/client_intake.py --holdings <file> --profile <profile.json> --out <dir>

# Portfolio analytics
%PYTHON% 09_PRODUCT/scripts/compute_portfolio_analytics.py
```
