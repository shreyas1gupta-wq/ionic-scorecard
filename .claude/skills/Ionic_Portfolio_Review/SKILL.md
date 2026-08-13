---
name: Ionic_Portfolio_Review
description: Operating manual for the Ionic Wealth NDPMS portfolio-review product: the deck engine (pr_template), the five-signal holdings page, Stock Scorecard 750 + the frozen v3 scoring layer, the MF quality frameworks (QFRA-1/QFRA-2), client intake by ISIN, the whole-pipeline QA audit, and every Principal ruling that governs a client-facing slide. The repo already carries the finished stock scores and fund grades, so you CONSUME them rather than re-run them. Start at 09_PRODUCT/HOW_WE_SCORE_STOCKS.md. Self-updating: run check_version.py to see whether this copy is current. Made by Shreyas Gupta on 13 August 2026, 8:11 pm IST. v4.0
---

<!-- SKILL: Ionic_Portfolio_Review | VERSION: v4.0 | SEQUENCE: 4 -->
<!-- Made by Shreyas Gupta on 13 August 2026, 8:11 pm IST. v4.0 -->

# Ionic Portfolio Review

> ### Version v4.0 — Made by Shreyas Gupta on 13 August 2026, 8:11 pm IST. v4.0
>
> **Before you rely on anything below, check that this copy is current.** From this skill's folder:
>
> ```bash
> python check_version.py
> ```
>
> It prints CURRENT or STALE and, if stale, what changed. `python check_version.py --update` replaces
> this file from the delivery branch — then **re-read the skill**, because the old text is still in
> your context. It refuses to overwrite local edits you have not committed.
>
> **Why this matters, from experience:** a skill dropped into `.claude/skills/` is a *copy* and does
> not track the repository. An earlier handover shipped a copy asserting the stock scores were **not**
> in the repo — the opposite of the truth — and nothing told the reader it was out of date. The version
> check is the fix.
>
> **One limitation, tested and real:** the repository is **private**, so the HTTPS fallback cannot read
> it. A copy of this skill sitting on its own, with no clone anywhere, will report `unknown` rather
> than CURRENT or STALE — it has no way to see the delivery branch. Run the check from inside a clone
> and it works (verified: reports `[git origin/master]`). This is a property of a private repo, not a
> bug, and it is the strongest practical argument for working inside the clone rather than keeping a
> loose copy.
>
> **You may not need a copy at all.** Claude Code discovers skills from `.claude/skills/` in whatever
> folder you open, and this skill lives *inside* the repo. Work in a clone and `git pull` is the whole
> update mechanism:
>
> ```bash
> git clone -b master https://github.com/shreyas1gupta-wq/ionic-scorecard.git
> cd ionic-scorecard && claude
> ```
>
> If you also keep a personal copy in `~/.claude/skills/`, delete it — both can be live at once and the
> stale one may win.

# Ionic Wealth â€” Complete Operating Manual (v3, 2026-08-07)

> **What changed in v3** â€” read this before anything else if you knew v2:
> 1. The equity holdings page no longer carries a prose one-liner. It shows **five colour-coded
>    traffic-light dots** per holding. See **PART 1A**.
> 2. The scoring model has a **frozen v3 correction layer** sitting beside the engine
>    (`fix_thin_coverage_v3.py`). It fixes a real bug that inflated recently-listed companies by up to
>    13 points. See **PART 2A**.
> 3. The recommendation ladder changed: **no name at or above 40 is ever a Sell**, and 40-50 confers
>    *eligibility* to trim rather than a Trim instruction. See **PART 2A Â§ladder**.
> 4. There is now a **one-command whole-pipeline audit**: `scripts/audit_full_workflow.py`. Run it
>    before you hand anything to anyone. See **PART 1B**.
> 5. `check_method.py` takes a **data module**, not a .pptx. Two gate rules are **inverted on demo
>    decks**. Both cost me time; PART 1B says exactly how.
>
> **The scores and fund grades are already in the repo** - you consume them, you do not re-run
> the scoring chain. Read PREREQUISITES below for what is and is not committed.

## STANDING RULE â€” ESCALATE TO A HUMAN RATHER THAN GUESS (Principal, 2026-08-05)
**Applies to every decision in this manual, not just the fund frameworks.** His words: *"keep this
rule for everything â€” if large escalations and AI cannot solve and need human, feel free to ask at
the last with your view and counter view and situation explained clearly."*

When a call cannot be resolved on the evidence available â€” conflicting signals, a material holding
with missing or stale data, an override that contradicts the score, a threshold the data cannot
support â€” **do not pick a side silently and do not split the difference.** Escalate, and escalate in
this shape:

1. **The situation**, stated plainly: what is being decided, for which holding, and how much of the
   book it affects.
2. **Our view**, with the evidence behind it.
3. **The counter-view**, argued honestly rather than strawmanned â€” the strongest case against us.
4. **What would settle it**: the specific datum, threshold or ruling needed.

Escalate **at the end**, once everything resolvable has been resolved, so the human is handed one
clear question rather than a running commentary. A page or a call that reaches a client must never
depend on a coin-flip we made quietly.

Discretion is **one-directional** wherever it appears in this manual: an analyst or AI overlay may
veto or soften an action, never manufacture one. That asymmetry is what keeps judgment from becoming
a licence to invent.

## PREREQUISITES â€” WHAT IS IN THE REPO AND WHAT IS NOT

**You get the code AND the finished scores. You do not get the working data behind them.** That split is
deliberate (Principal, 2026-08-07): you should be **consuming** scores, not regenerating them. Verified
against `.gitignore` and `git ls-files`.

| | in the repo? | what it is |
|---|---|---|
| `pr_template/` â€” engine, slidekit, all modules, `lib/five_signals.py` | **YES** | the deck code |
| `09_PRODUCT/scripts/` â€” builders, audits, `pptx_slide_png.py` | **YES** | the tooling |
| `results/pf_qual_*.json` â€” **752 files** | **YES** | the analyst research per stock |
| `data/<client>.py` â€” client context files | **YES** | see the PII warning below |
| **`results/full750_scored_v3.csv`** â† **USE THIS ONE** | **YES** | the frozen v3 stock scores |
| `results/full750_scored.csv` | **YES** | v1 scores, for comparison only |
| `results/portfolio_quant.csv` | **YES** | per-client pillar scores |
| `results/EARNINGS_QUALITY.csv` | **YES** | profit-bridge earnings flags |
| **`05_DATA_OFFICE/data/isin_master.csv`** | **YES** | symbol/ISIN map, 2,404 NSE equities - the ONLY exact join key from a client's CAS to the scored universe |
| **`MF_RECOMMENDATIONS/**/QFRA1_all_categories.csv`** | **YES** | QFRA-1 fund grades |
| **`MF_RECOMMENDATIONS/**/QFRA2_verdicts.csv`, `QFRA2_current_asof_*.csv`** | **YES** | QFRA-2 fund verdicts |
| `datasets/screener_deep/*.parquet` | **no** | raw financials â€” working data |
| `ALPHA_RANKER/data/prices/` | **no** | price panels â€” working data |
| MF working files (`fund_daily.csv`, `bench.csv`, `codes.csv`) | **no** | NAV working data |
| QFRA-2 **engine code** | **no** â€” a **separate repo** | only needed to RE-RUN the fund ranking |

**What this means in practice.** You can build decks, read every stock score and every fund grade, and
run the whole QA suite. You **cannot** re-run the scoring chain (`fix_thin_coverage_v3.py` needs the
screener parquets and the price panel) or any backtest. If you need to regenerate rather than consume,
ask the Principal for the working data.

**Start here, in this order:** read `09_PRODUCT/HOW_WE_SCORE_STOCKS.md` for the scoring workflow in
plain language, then PART 1A below for the deck page, then build the ABXY demo deck to see it end to end.

**âš  CLIENT PII IS IN THIS REPO.** `data/talaulikar_family.py` is a **real client's** holdings, weights
and analyst commentary, and it **is tracked**. The `.gitignore` PII guard covers `pr_kordes/` and
`*Kordes*` but not this file. Do not widen access to the repo without checking with the Principal
first, and do not add another real client file without extending that guard.

**âš  THE GIT REMOTE URL CONTAINS A PLAINTEXT PERSONAL ACCESS TOKEN.** `git remote -v` prints it. Anyone
with the working copy has push access to the repo. Rotate the token before sharing a clone or a
machine image.

---

Everything a team member needs to produce client deliverables, **given the data files above**. This is
the single source of truth for method and process.

## GET THE CODE FIRST

```bash
git clone -b master https://github.com/shreyas1gupta-wq/ionic-scorecard.git
```

**The `-b master` matters.** The repository's default branch is `main`, which holds a single README and
a history unrelated to the real work, so a plain `git clone` gives you nothing and raises no error. If
the default has since been switched to `master`, the flag is simply redundant, never wrong.

**The finished stock scores and fund grades ARE in the repo — you consume them, you do not re-run the
scoring chain.** An earlier version of this manual said the opposite; it predated the data being
committed, and acting on it means redoing work that is already done. What is *not* committed is the raw
working data behind those scores (screener parquets, the price panel), so you can build decks and read
scores but cannot regenerate them. See PREREQUISITES below, and the QFRA-2 exception in PART 3.

Then confirm the data actually joined. From `09_PRODUCT/pr_template/`:

```bash
python check_dots.py
```

It must print `PASS`. If it does not, every signal dot on the holdings page is a hollow grey ring and
the deck is a shell that will still build with exit code 0. See BURN YOU #1.


---

## QUICK START: Holdings In â†’ PPTX Deck Out

**INPUT:** A client's holdings file (CSV or XLSX extracted from NSDL CAS statement).
Required columns (case-insensitive): `type` (EQ/MF), `name`, `isin` (preferred), `units`, `value_inr`.

**OUTPUT:** A branded Ionic Wealth PPTX portfolio-review deck (75/40/23 slides depending on tier).

### The 6-step pipeline (end to end)

```
STEP 1  Holdings file arrives (CSV/XLSX from CAS)
   â†“
STEP 2  client_intake.py matches each holding to the scored universe
   â†“    â†’ pf_qual_*.json (equity scores) + QFRA verdicts (fund scores)
   â†“    â†’ exceptions.csv (unmatched rows â†’ back to RM, never dropped)
   â†“
STEP 3  Create data/<client>.py (ctx dict) from matched results
   â†“    â†’ Copy data/azby_family.py as template, fill real numbers
   â†“    â†’ Every Sell/Hold call comes from scorecard + analyst research
   â†“    â†’ Every fund verdict comes from QFRA-1 + QFRA-2 frameworks
   â†“
STEP 4  Build the deck
   â†“    cd Shreyas_Ionic_AMC/09_PRODUCT/pr_template
   â†“    set PYTHONIOENCODING=utf-8 && set PYTHONUNBUFFERED=1
   â†“    "C:\...\python.exe" build_<client>.py HNI_DEEP
   â†“
STEP 5  QA gates (ALL mandatory) â€” just run the whole-pipeline audit:
   â†“    python ../scripts/audit_full_workflow.py
   â†“    It runs every gate on every deck x every tier and writes WORKFLOW_AUDIT.md.
   â†“    Then do the ONE thing it cannot do: LOOK at the changed slides (PART 1B).
   â†“
STEP 6  Principal sign-off â†’ publish to 09_PRODUCT/reports/
```

**The scoring chain that must run BEFORE step 2**, in this order (each writes what the next reads):
```
earnings_quality_decomp.py   â†’ results/EARNINGS_QUALITY.csv    (profit-bridge flags)
fix_thin_coverage_v3.py      â†’ results/full750_scored_v3.csv   (the frozen correction layer)
audit_v3_freeze.py           â†’ results/V3_FREEZE_AUDIT.md      (21 invariants; must be 21/21)
```
All three live in `04_RND_LAB/STOCK_SCORECARD_750/`. `fix_thin_coverage_v3.py` **aborts** if it cannot
reproduce the engine's own composites exactly â€” that assertion is the guard against it drifting from
the engine it corrects. If it aborts, stop; do not edit the assertion.

### What if the scored universe is missing for a stock?
The intake script flags unmatched stocks in `exceptions.csv`. For each:
- Run the Stock Scorecard 750 pipeline (Part 2 below) to score it â€” one Sonnet agent per stock does ~3min deep research
- The analyst's `pf_qual_<SYMBOL>.json` is the output, which feeds directly into the deck's data layer
- Until scored, the stock gets `"No Recommendation"` â€” never a fabricated score

### What if QFRA data is missing for a fund?
- QFRA-2 covers 40 curated funds; held funds outside it get an honest gap note: "needs a QFRA-2 scoring run"
- A fund with no framework coverage gets `"No View"` â€” never a fabricated verdict
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

Actual slide counts as at 2026-08-07 (real client book / demo showcase):

| Tier | Audience | Slides | Register | Notes |
|---|---|---|---|---|
| **HNI_DEEP** | Family office / sophisticated HNI | **103 / 67** | Technical, full methodology | All annexure modules ON |
| **STANDARD** | Typical NDPMS client | **48 / 38** | Professional, accessible | Selected annexure modules |
| **RM_SIMPLE** | RM-led / newer investor | **30 / 20** | Plain language, bigger type | Story beats + the five-signal page |

A real client book runs longer than the demo because `sell_cards` and `scheme_scorecards` paginate per
name (Talaulikar: 21 sell cards, 19 scheme scorecards). Do not treat the demo count as the target.

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

**Step 4: QA gates (ALL mandatory)**
```bash
%PYTHON% ../scripts/audit_full_workflow.py        # everything, every tier -> WORKFLOW_AUDIT.md
%PYTHON% ../scripts/pptx_slide_png.py out/<deck>.pptx 25,26    # then LOOK at what changed
```
The audit covers geometry Ã—2, tellscan, check_method per data module, and the scoring chain. What it
cannot do is **see** the page â€” do that yourself, always, on every slide you touched. See **PART 1B**
for the four ways these gates mislead (`check_method` takes a data module; `SYNTHETIC_DEMO_LEAK` is
inverted on demos; `'genuine'` and the disclaimer colophon are standing false positives).

Also still yours to check by eye, because no gate does it:
**cross-panel consistency** â€” any two numbers on the same slide that a reader assumes are the same set
MUST reconcile or be explicitly scoped. Then **Principal sign-off** before anything ships.

**Step 5: PDF (ON REQUEST ONLY)**
```bash
"C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" ../scripts/pptx_to_pdf.py out/<deck>.pptx
```
Do NOT auto-convert to PDF after every rebuild â€” ask the advisor whether they want PPTX, PDF, or both.

**Step 6: Publish**
Copy to `Shreyas_Ionic_AMC/09_PRODUCT/reports/` with client-facing filename: `NDPMS_Portfolio_Review_<ClientName>_<Tier>.pptx`

### Module registry (canonical order)

**Section 0 â€” Understanding:**
cover, contents_legend, ips_summary (renders only if IPS on file), exec_summary, since_last_review (renders only if meeting_history exists), mandate_method

**NOTE â€” sections 2 and 3 were SWAPPED on 2026-08-06** (FM comment #11): the **Fund Book is now
section 2** and the **Equity Book section 3**. `sec_no` is a hardcoded literal in each module, so a
renumber means editing ~10 module files plus `engine.py`'s MODULES/DIVIDER_TOC/titles and
`contents_legend.py`'s `_SECTIONS`. Do not renumber casually.

**Section 1 â€” Portfolio X-ray:**
snapshot (incl. look-through allocation), core_satellite, concentration_risk, sector_exposure,
mcap_positioning, ips_seven_aspects
(CUT: group_concentration â€” denominator bug fixed but not wired Â· allocation_house_view â€” retired
2026-08-06 per FM #7, file kept unwired, not deleted)

**Section 2 â€” The Fund Book:**
fund_book_scored, mf_methodology, funds_equity, funds_hybrid, funds_debt, scheme_correlation,
scheme_overlap_full (annexure), fund_actions
(CUT: fund_category_rules, fund_quality_alloc, fund_overlap)

**Section 3 â€” The Equity Book:**
score_method, **book_scored** â† the five-signal dots page (PART 1A), equity_book, sell_list,
hold_rationale

**Section 4 â€” Recommendations:**
house_view_fit, tax_impact, priority_actions, growth_projection (mu/sigma from real holdings, not constant)
(CUT: cost â€” was scheme-TER only with no Regular-drag/PMS overlays)

**Section 5 â€” Annexure (optional, tier-dependent):**
before_after, quality_vs_price, spotlight_holdings, holdings_detail, sell_cards, scheme_scorecards, annex_score_vs_call, annex_valuation_bands, annex_correlation (top 15 by weight), annex_risk_contribution, annex_beta_ladder, annex_concentration_curve, annex_income_ladder, annex_goal_mapping, appendix, disclaimer
(CUT permanently: opportunity_set, deployment, factor_profile, annex_currency_geo, annex_mcap_migration, annex_liquidity_ladder, annex_returns_quilt, annex_stress_scenarios [DELETED], annex_seasonality, annex_drawdown_history, annex_sip_vs_lumpsum, annex_fee_compounding, annex_tax_lot_aging, glossary)

### Sell page structure (sell_list.py + sell_cards.py)
- **sell_list**: confirmed Sells only (no "Under review" pill client-side), no reason-category column, analyst-authored 2-line case per name, visible p.NN link per row to the rationale card, paginates at 5 rows.
- **sell_cards**: each Sell name gets a full-page rationale card with:
  - `negative_para`: the driver â€” why we're selling (OPENS the card, leans with the call)
  - `positive` ("The bull we rejected"): the strongest counter-argument, explicitly discounted
  - `reverse_dcf` ("Reverse-DCF: margin of safety"): what the market is pricing in vs our estimate
  - `rationale`: the analyst's full reasoning
  - If `positive` or `reverse_dcf` is empty, it falls back to "On file with the analyst desk." â€” always populate these from the scored universe's `pf_qual_*.json` or `ANALYST_RECOMMENDATIONS_v2.xlsx`

### Tax chart scope (tax_impact.py)
The tax chart shows **direct-equity sells & trims only** (not fund proceeds). In the data layer:
- `eq_proceeds = sell_val + trim_val` â€” equity-only, used for `tax["gross"]`
- `proceeds = eq_proceeds + fund_action_val` â€” combined total, used for `deployment["proceeds_inr"]`
The chart caption says "Direct-equity sells & trims, net of est. tax" â€” if the gross number includes fund actions, it's a BUG.

### IPS page (ips_summary.py, v2, RESTORED)
Renders ONLY when `ctx["ips"]["on_file"]` is True. Structure:
- 4 mini-tables in the house navy/gold rail-and-pill style (never a plain corporate table)
- **Portfolio level**: equity/debt split, single-scheme/AMC/locked-in/cash caps
- **Equity level**: market-cap bands, thematic/unlisted/international caps
- **Fixed income**: credit-quality bands (AAA/AA/A/below-A) + duration cap
- **Commodities**: gold/silver bands
- "Current" is ALWAYS computed live from ctx via `_lookthrough_mix()` â€” includes look-through equity/debt split (direct equity + equity-oriented fund categories), materially different from direct-equity-only figures
- "Ideal" shows "TBD" and Fit shows "Pending" for any parameter with no bespoke IPS on file â€” never a fabricated target

### Cross-panel consistency scan (mandatory QA gate)
Any two numbers on the same slide that a reader will assume are the same set MUST reconcile or be explicitly scoped. Examples:
- Tax table = fund actions vs waterfall = equity plan â†’ different bases, both disclosed
- concentration_risk KPI vs holdings table rows = same basis: % of equity sleeve
- Same-entity names identical across slides (short_name width >=30 for scheme tables)
- A driver/tag must match the narrative beside it and the same call's rationale elsewhere in the deck

### CEO-sweep fixes (baked in, do not regress)
- `_reason_category`: buckets scored by keyword-hit COUNT on negative_para first (rationale fallback), with negation scrub (`no ... red flags` never trips forensic) and bare "growth" excluded (stat mentions like "PAT growth +156%" aren't a slowing-growth thesis)
- Commodity-cycle reversal suffix (sell_cards): applies to sector "Metals & Mining" ONLY â€” conglomerates/utilities in Oil&Gas/Power must not get "metal price" language
- Tax rows: character from holding_years (>=1y = LTCG; REDEEM = "Mixed, lot-by-lot") â€” the old `action in ("Switch","Exit")` check never matched UPPERCASE codes
- CoPilot CTA is OUT â€” no product names client-side

### Five-signal / v3 build lessons (2026-08-07) â€” bugs fixed, do not regress

**`NaN` is TRUTHY, and `.astype(str)` turns it into `"nan"`.** This cost me three separate bugs in one
day, in three different files. `float('nan') or ""` returns **NaN**, not `""`. And an empty string
round-trips through CSV as NaN, so `df[col].astype(str) != ""` counts every blank row as populated â€”
it reported all 751 names as trim-eligible and printed `Hold âˆ’198`. Always `fillna("")` **before**
`astype(str)`, and use `pd.isna()` rather than truthiness.

**Never write the same threshold twice.** Bands, floors, words and colours live only in
`lib/five_signals.py`. When I duplicated the band logic into a chart script, the two drifted within an
hour.

**A distribution and the values ranked against it must be built the same way.** `_composite_dist()`
was cached with `forward=True` while `signals()` computed `forward=False` â€” every name ranked against a
quantity that was not its own, producing a 267/250/123/104 barbell where quartiles belonged.

**Duplicate basenames break name-imports.** `lib/core_satellite.py` and `modules/core_satellite.py`
both exist, and the engine puts both directories on `sys.path` â€” so `import core_satellite` resolves by
path order and can import *itself*. Load by absolute path via `importlib.util.spec_from_file_location`.
Same pattern used by `book_scored.py` for `lib/five_signals.py`.

**Field-name scrubbing must be a rule, not a list.** The render-time detell named fields one at a time
(`fcf_yield` was listed, `available_date` was not) â€” and `available_date` reached client slides in two
analyst paragraphs and every ABXY deck. Analyst prose comes from 752 independent research passes and
cannot be policed name by name. `slidekit.txt()` now converts **any** snake_case token to spaced words,
because English prose never contains `word_word`. Closes the class, not the instance.

**Matplotlib `Circle` is an ellipse unless the aspect is equal.** Patches take radii in **data** units;
in a non-square axes a "circle" came out 20:1 flat. Size markers in **points** (`ax.plot(..., 'o',
markersize=...)`), which is immune to the data aspect.

**Vertical budgets are tight; measure before adding.** `source()` is a shared 0.24in band at 6.66 and
`score_band()` sits at 6.90 â€” roughly two lines at 7pt. A subtitle placed 0.36 data-units above a title
printed *on* it, because 1 unit was 0.34in and an 11pt line is taller than that. Text overflow passes
the eye and fails `check_geometry`; trust the gate.

**Recompute derived state, do not carry a residual.** Penalty/boost was being recovered as
`final âˆ’ gate(composite)`. That captured v1's red-flag battery, which read the *old* TTM growth figures
â€” so switching to March-to-March would have paired new pillars with stale penalties. Two of the four
red flags read revenue growth directly.

**Count what you print.** The scope tag read "largest 11 of 98" over an 8-row RM page; three separate
`MAXROWS` references had to move together, including one that placed an extra invisible hotspot over
the legend and one that undercounted the annexure overflow by one.

### Talaulikar-build lessons (2026-08-02) â€” bugs fixed, do not regress

**MF / fund name mapping â€” now codified in `09_PRODUCT/pr_template/lib/mf_mapping.py`**
- **Never fuzzy-match a fund name to a framework's fund list.** A naive string-similarity pass matched "Kotak Midcap Fund" to "Kotak Multicap Fund" (wrong category) and "ICICI Prudential Liquid Fund" to "ICICI Pru Large & Mid Cap Fund" (nonsensical â€” liquid vs equity). Always dispatch a Sonnet agent, one fund at a time, reasoning about real scheme identity (same AMC + same mandate) with web search to disambiguate â€” see `[[feedback-mf-mapping-no-fuzzy]]` memory. "Not found" beats a wrong guess, always. `lib/mf_mapping.py`'s docstring states this rule as a hard constraint the module itself must never violate.
- **AMC alias table implemented** (`AMC_ALIASES` + `canonical_amc()`): "ICICI Prudential" == "ICICI Pru" (same AMC â€” reconcile). A companion `AMC_FALSE_FRIENDS` list documents verified NON-equivalences ("Aditya Birla Sun Life" != "Axis" despite both running a "Flexi Cap Fund") so a future similarity pass doesn't re-make the same mistake. Extend both tables as new AMCs/edge-cases turn up â€” never delete an entry without re-verifying it's wrong.
- **Scheme-rename table implemented** (`SCHEME_RENAMES` + `resolve_scheme_rename()`): ICICI Pru Bluechip Fund â†’ ICICI Prudential Large Cap Fund; Kotak Emerging Equity Fund â†’ Kotak Midcap Fund; Bandhan Core Equity Fund (formerly IDFC Core Equity Fund) â†’ Bandhan Large & Mid Cap Fund; DSP Equity Opportunities Fund â†’ DSP Large & Mid Cap Fund. `client_intake.py` now calls `resolve_scheme_rename()` on every MF row automatically, so the next client's holdings match our frameworks on the first pass.
- **Category-label mismatch between our schema and QFRA's.** Our fund `category` field ("mid") doesn't always match QFRA's own category value ("largemid") for the same real scheme â€” check both label sets before concluding a fund is "not covered." (Not yet automated â€” still a manual check per client build.)

**CAS parsing / data corruption â€” now codified in `lib/mf_mapping.py`'s `validate_holdings_row()`/`validate_holdings()`**
- **Row-bleed defect found and fixed:** one stock's `name` field was silently concatenated with an entirely different holding's row content (`POLYCAB INDIA LIMITED` had `NIPPON LIFE INDIA ASSET ... NAM-INDIA.NSE ...` glued onto the front) â€” a real double-mapping bug in the CAS extraction path. `client_intake.py` now runs `validate_holdings()` on every parsed row automatically and writes any flagged rows to `row_warnings.json` in the intake output dir â€” never silently trusted or dropped. Checks: any `name` field over 80 chars, or containing an ISIN token that doesn't match the row's own `isin` field.

**Score / verdict field completeness**
- **Setting `rec`/`verdict` and setting `qfra`/`merit` (the actual score+grade) are two separate steps** â€” it's easy to update one and leave the other blank, producing a Sell/Hold pill with no number behind it on the fund-book-scored table. Any override block that changes a call must set both together, never one alone.
- **Never default a categorical field to one hardcoded value for the whole book.** `mcap_band` silently defaulted to `"Small"` for every stock and `sector` defaulted to blank/"Diversified" for every stock â€” both went undetected until the mcap/sector slides visibly showed 100% in one bucket. Always compute per-holding from a real classification, never a blanket default.
- **Never render a raw 0 for "unscored."** Distinguish `None` (genuinely outside the scored universe â†’ show blank/"-") from a real score of 0 â€” audit every module that does `f"{score:.0f}"` for a missing None-guard.

**Ground-truth vs. derived-state confusion**
- **Never treat an earlier in-session variable dump as "the base data."** A dump taken mid-session already reflected a prior fixup-loop's mutation; trusting it as ground truth nearly caused reverting three real equity Sells back to Hold. Before removing what looks like a redundant override, always grep the ORIGINAL dict literal in the source file â€” never rely on a cached mental model or an earlier printout from the same conversation.

**Stale / hardcoded narrative text**
- **Any hardcoded client-specific-sounding sentence is a landmine.** Found and fixed 6+ in one rebuild: a fabricated ">11% concentration breach" that didn't exist in the real book (`exec_summary.py`), a false "All 98 holdings are scored" claim (`book_scored.py`), an overbroad "never a performance sale" claim (`fund_actions.py`), a hardcoded "positions above the 8% cap" trim narrative when nothing was above the cap (`priority_actions.py`), stale data-quality flags still saying "No Recommendation" / "all shown as No View" after both had changed, and a self-contradictory "retirement gap...can close" sentence sitting next to a 100%-funded number (`annex_goal_mapping.py`).
- **Rule going forward:** every hardcoded narrative sentence in a module must be re-derived from `ctx` at build time. A module docstring or inline comment should flag anything that can't be (rare) as "CLIENT-SPECIFIC â€” reverify every build." Grep for `>`, "all", "none", "every" + a number across `modules/*.py` before shipping any deck with materially changed data.

**Template scale limits**
- `fund_actions.py`'s card grid and `tax_impact.py`'s fund table were both hand-fit for ~6-10 items and broke (illegible or overflowing) once a real client had 16-17 fund actions in one book. Fixed with adaptive column counts and capped+summarized rows (never silently drop items â€” show top-N + a disclosed "+N more" row).
- **Rule:** stress-test any module rendering a variable-length list from `ctx` at 2-3x the current largest real client's count before shipping, not just against the size of the original demo book.

**A module exception leaves a HALF-DRAWN page that passes every gate (2026-08-03)**
- `engine.build()` catches a module exception, logs `[ERR ] <module>: ...`, and moves on. Anything the module already drew before raising STAYS ON THE SLIDE. So a mid-render crash produces a page that looks plausible, is silently missing content, and passes both geometry gates and tellscan â€” because everything present on it is well-formed.
- Real instance: `ips_summary.py`'s `_fit()` unpacked `lo, tgt, hi = band` unconditionally, but bands come in two shapes by design (3-tuple min/target/max for allocation and commodity bands, 2-tuple min/max for equity market-cap and credit bands â€” `_band_txt()` had always handled both). Any 2-tuple raised `not enough values to unpack`, which killed the IPS page **after** its left column was drawn: the entire right half (equity-level parameters + commodities) and the constraints strip vanished. The page still passed 0/0/0. It was caught only by looking at the render and asking why half the page was empty. Note `azby_family.py` â€” the file every client data file is copied from â€” carries the 2-tuple shape, so this hit the house demo too.
- **Rule: always grep the build log for `[ERR ]` before trusting a deck.** A clean geometry/tellscan run does NOT mean every module rendered. And if a page looks oddly empty, that is a defect to investigate, not whitespace to accept.

**Automated QA gates have a real coverage gap â€” visual render-and-look is not optional**
- `check_geometry.py`/`check_geometry2.py` inspect python-pptx's SHAPE geometry, not actual rendered pixels. A real overlap slipped through them completely: `tax_impact.py`'s row-height math budgeted the table's vertical space assuming NO header row (`deck.table()`'s `header=True` default silently consumes an extra ~0.33in that the calling module never accounted for). The bug was invisible to both automated gates and only surfaced when the fund-action count grew enough (17 fund actions) to push the real table bottom past a fixed callout box below it â€” caught only by converting the deck to PDF (`pptx_to_pdf.py`, PowerPoint COM backend) and visually inspecting a sample of slides.
- **Rule, now standing:** before calling any client deck "done," convert to PDF and visually inspect a representative sample (cover, exec summary, a data-heavy table slide, a chart slide, a sell/scorecard card, the last slide) â€” not just run the 3 automated gates. The 3 gates catch text-content and declared-geometry problems; they do NOT catch every real visual layout defect.

**Cross-module total consistency**
- Two modules independently computing "the same" total (`tax_impact.py` vs `priority_actions.py` fund-actions total) used different rounding/summation order and disagreed by Rs 0.1L on an identical figure. **Rule:** any total shown on more than one slide must be computed via one shared path â€” never reimplemented per-module with its own rounding order.

**QFRA-1 vs QFRA-2 discipline**
- These are different engines (QFRA-1 = short-term capture-ratio, 6 categories; QFRA-2 = long-term curated 40-fund list, 8 categories) â€” never back-solve one framework's score from the other's raw metrics without validating against known real overlap cases first. A tested back-solve formula inverted the real grade on 2 of 8 validation funds (looked fine short-term, scored D/C on the real long-term framework) â€” using it uncaught would have shown the client a plausible-looking WRONG number. When a back-solve doesn't validate, disclose the honest coverage gap instead of guessing.
- When only QFRA-1 covers a fund (no QFRA-2 curated entry), the defensible fallback score is a REAL percentile rank on the framework's own primary ranking metric (`HC_total_cap_6M`) computed from the actual dataset â€” a genuine statistic, not an invented formula.

**Directed/portfolio-reason vs. quality-reason conflation**
- A Sell/Trim driven by a client's cash need (directed liquidity) is a fundamentally different fact than one driven by the scoring framework â€” conflating the two silently breaks several narratives at once (an inflated "analyst override" register, a false "never a performance sale" claim, a wrong sell-count description). **Fix:** tag it explicitly in the data (`sell_reason_type = "quality" | "liquidity"`) the moment a directed override is applied, so every downstream module reads one authoritative field instead of re-deriving the distinction from score thresholds (tried, and it's error-prone â€” genuine analytical overrides and liquidity-directed sells can land on the same score band).

**House-style consistency â€” now folded into `tellscan.py`'s standing gate**
- Currency-symbol drift (â‚¹ vs the house "Rs") survived undetected in a few modules. `tellscan.py`'s `GLYPH_HYGIENE` bucket now also catches `â‚¹`; its `INTERNAL_JARGON` bucket now also catches the retired "No Recommendation" label (current label is "No View"). No separate script needed â€” the existing 3-gate QA pass catches both automatically going forward.

**Process / workflow**
- Parallel read-only audit agents â€” one per deck section, each cross-checking rendered PPTX text against `ctx` and module source â€” surfaced real, citable bugs efficiently and should be the standard pre-ship review pattern for any client rebuild with material data changes, not just the 3 automated QA gates.
- **Freeze the target before auditing.** One audit agent caught the source files changing mid-audit (slide count flickering 95â†’92â†’95) and had to pin a frozen snapshot to get reliable results. Don't dispatch audit agents against files still being actively edited â€” copy the target PPTX + data file to a frozen snapshot first.
- Under real time pressure ("2 min", "30 sec max"), the fix is not to skip verification â€” it's to keep the CHEAPEST verification (grep the raw source literal) even while moving fast. A rushed assumption about "base state" during a compressed window is exactly when a regression slips through.

### Slidekit primitives (prevent regressions)
- `clip_sentences`: whole sentences, decimal-safe
- `clip_clause`: sentence/semicolon-only periods, paren-balanced
- `short_name`: word-drop, no mid-word chops (min width 30 for scheme tables)
- `callout_h`: text-hugging panel heights
- `scope_tag`: drops whole segments when capped
- `resolve_links()`: internal clickable cross-refs at save time
- Render-time detell in `txt()`: em-dash to comma, "genuine" to "clear", arrow/math symbols to words (Bahnschrift lacks the glyphs)
- Chart law: NEVER `ax.legend()` â€” use direct labels, `caption_above()`, or `chip_legend()`; NAVY = primary series; `halo()` behind text on fills

### Tell scan buckets (tellscan.py)
AI-writing tells: em-dash, "genuinely"/"robust"/"holistic"/etc.
Internal jargon: SENTINEL, QFRA, MERIT, pf_qual, AZBY, "quant-only, analyst view", "Ratified Sell", "One-time review", "House decision"
Client words to use instead: "watch-outs", "fund score /100", "grade", "the firm's fund-quality framework"
Data-QA vocabulary: "stale", "does not reconcile", "data feed", "data cut", Data Office, CoPilot
Source/analyst citations: screener.in, INDmoney, Groww, Paytm Money, Advisorkhoj, analyst names
Raw snake_case field names
"synthetic/demo/illustrative" language mislabeling REAL client data

---

## PART 1A: THE FIVE-SIGNAL HOLDINGS PAGE (`book_scored.py`) â€” NEW in v3

The equity holdings page used to print a clipped one-line analyst read per holding. It now prints
**five traffic-light dots**. Everything about them lives in **`pr_template/lib/five_signals.py`** â€”
the clubbing, the band floors, the words, the colours, the universe join. **Never restate a threshold
anywhere else.** Three copies of a number is three chances to disagree about what green means.

### The seven pillars clubbed into five

| Signal | Built from | 3Y wt | 1Y wt |
|---|---|---|---|
| Quality | `quality_score` (ROE/ROCE, sector-neutral) | 20% | 16% |
| Growth | `growth_3y_score` â€” **trailing revenue CAGR only** | 20% | 16% |
| Value | `value_score` (P/E univ + P/E sectorÂ·tier + P/B + FCF yield) | 18% | 16% |
| Technical | mean(`stage_3y`, `accumulation_3y`) | 22% | 31% |
| Sector & Flows | mean(`ownership_flow_3y`, `sector_macro_3y`) | 20% | 21% |

Frozen pillar weights, regrouped. Both columns sum to 100. All seven pillars are represented; none is
dropped. **No forward data reaches a dot** â€” the analyst's expected-EPS figure belongs to the score's
forward adjustment (PART 2A), not to the Growth dot. Mixing them was tried twice and was wrong both
times: the estimate is EPS, the pillar is revenue, and averaging them yields a number that is neither.

### Bands, words, colours

| Floor | Word | Dot |
|---|---|---|
| â‰¥75 | Top 25% | dark green `#1E9E6A` |
| â‰¥50 | Upper | light green `#76C7A6` |
| â‰¥25 | Lower | yellow `#F2A93C` |
| <25 | Bottom 25% | red `#E0402F` |
| â€” | Not scored | hollow grey ring |

Three of four are exact slidekit colours; the light green is a tint of HOLD because the palette has no
mid-green. The words are deliberately **relative** ("Top 25%", not "Strong"): the page carries no
explanatory footnote, so the label is the only thing stopping a reader hearing an absolute grade. A
percentile says "better than most of the 750", never "good outright" â€” in an expensive market the
greenest Value dot is still expensive.

### EVERY signal is re-ranked against the universe â€” do not remove this

The legend claims quartiles, which is only true if each column is uniform. **None of the five is**,
because every one is a blend: Quality is the mean of 2 ranks, Value a weighted mix of 4, Technical and
Sector & Flows the mean of 2 each. A blend of ranks is not itself a rank â€” it clusters mid-scale.
Measured before the fix, Value came out **32/32/19/13**. After re-ranking each signal against the
universe's own distribution of that same signal, all five sit at **24-26% per band** and the legend is
literally true.

`_composite_dist()` is **keyed by the `forward` flag**. If the distribution is built one way and the
values another, every name is ranked against a quantity that is not its own â€” that happened once and
produced a 267/250/123/104 barbell.

### The join, and the two traps in it

Deck data files (`data/*.py`) carry `ionic_score` but **no per-pillar scores** â€” they were written when
the page was one prose line. `five_signals.enrich()` joins the pillars in by symbol at build time from
the scoring output. Without it the page ships as a wall of hollow rings: technically honest, useless,
and it looks finished.

1. **Column-name landmine.** The ownership pillar is `ownership_flow_3y_score` in the client output
   (`portfolio_quant.csv`) but `ownership_3y_score` in the universe file (`full750_scored.csv`).
   Reading one name renders "not scored" on every real client deck while looking perfect on the
   universe file. `_ALIASES` reads either.
2. **Worktree trap.** `_nifty_root()` walks up to the `NIFTY 500` directory. Resolving paths relative
   to `__file__` alone lands inside a git worktree where `results/` does not exist, and live data
   silently reports as MISSING.

### Tier behaviour

| tier | rows | dot | notes |
|---|---|---|---|
| HNI_DEEP / STANDARD | 11 | 0.15in | full page |
| RM_SIMPLE | **8** | **0.19in** | taller pitch, 9pt legend |

`book_scored` **is** in RM_SIMPLE (changed 2026-08-07). It had been excluded on 2026-07-26 as
methodology-heavy; that no longer describes a page of five dots, which reads faster than the scatter
beside it. If you change the row cap, the **scope tag count must change with it** â€” it read "largest 11
of 98" over an 8-row page until that was wired.

### Known limitation, state it if asked

A dot carries no label, so colour is the whole message. Light green (~0.52 luminance) and yellow
(~0.50) are nearly identical, and red (~0.24) is *darker* than both â€” so a **mono print** or a
**red-green deficiency (~8% of men)** collapses the ramp. No tuning fixes that while keeping true
traffic-light hues. `DOT_SIZE_RAMP` (graduated diameter) survives both and is built, off by default.

---

## PART 1B: THE QA GATES â€” what each one actually does, and how they lie

**Run `python ../scripts/audit_full_workflow.py` from `pr_template/`.** It executes the scoring chain,
the Excel, 3 decks Ã— 3 tiers, all three geometry/tell gates on each, and `check_method` per data
module, then writes `09_PRODUCT/WORKFLOW_AUDIT.md`. Current state: **41 of 42 pass**; the single
failure is client-data adjudication, not code.

| gate | takes | catches |
|---|---|---|
| `check_geometry.py` | a **.pptx** | overlap, off-slide, text taller than its box |
| `check_geometry2.py` | a **.pptx** | spill past the right/bottom bounds |
| `tellscan.py` | a **.pptx** | AI tells, internal jargon, raw field names, demo-label leaks |
| `check_method.py` | **a data module** (`data/x.py`) | sell-bar/override, churn split, STCG priority, debt grandfathering |
| `check_freshness.py` | â€” | stale data sources; needs `--ack "<name>: <reason>"` |
| `audit_v3_freeze.py` | â€” | 21 scoring invariants |
| `pptx_slide_png.py <deck> <n>` | a **.pptx** + slide nums | **exports slides to PNG so you can LOOK** |

### Four ways these gates mislead â€” all learned the hard way

1. **`check_method.py` takes a DATA MODULE, not a .pptx.** Hand it a deck and it dies with
   `AttributeError: 'NoneType' object has no attribute 'loader'`, which reads like a broken gate.
2. **`SYNTHETIC_DEMO_LEAK` is INVERTED on demo decks.** The rule exists to catch "illustrative /
   synthetic / demo" wording on a *real* client's data. On the ABXY showcase that wording is mandatory
   â€” 22 correct labels were being counted as failures and **masking the 2 findings that were real**.
   The audit keys this to `is_demo`: hard on client decks, benign on demos.
3. **`'genuine'` is a standing false positive.** "Genuine deleveraging" is ordinary English.
4. **The disclaimer colophon always trips `check_geometry2`.** It sits at 6.90-7.20 by design on a dark
   terminal page; the gate exempts by y-position, not by role.

### The gates cannot see the page. You must.

Every automated gate reads XML. None of them can see a chip whose label overflows once PowerPoint lays
out the text, a colour that vanishes against its background, or two shapes that collide only at render.
**Export the changed slides and read them.** Real bugs found this way *after* all gates passed 0:
a legend printed through the source line; a subtitle printed on top of its own title; dots rendered as
flat 20:1 ellipses. `pptx_slide_png.py` exists because this box has no poppler, so the "visual check"
step had no way to run for months.

---

## PART 2: STOCK SCORECARD 750 (Quantamental Scoring)

### What it is
A 0-100 quantamental scoring engine for stock holdings. Dual-horizon (3-Year fundamental-tilted, 1-Year technical-tilted), never blended into one number at the analyst level. Recommendation vocabulary: **Sell or Hold ONLY, never Buy** â€” this reviews existing holdings.

### Location
`Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/`

### Dual-horizon scoring (7 pillars)

| Pillar | 3Y Weight | 1Y Weight | Formula |
|---|---|---|---|
| Quality | 20% | 16% | mean(pctile(ROE, sector-neutral), pctile(ROCE, sector-neutral)) |
| Growth | 20% | 16% | 3Y: 3yr revenue CAGR; 1Y: 1yr revenue growth â€” universe-wide pctile. **v3: MARCH-TO-MARCH full fiscal years, never a TTM window** â€” see PART 2A |
| Value | 18% | 16% | 0.25*pctile(-PE,univ) + 0.35*pctile(-PE,sector*tier) + 0.20*pctile(-PB,sector*tier) + 0.20*pctile(FCFyield,sector*tier) |
| Stage/Technical | 14% | 26% | Mechanical: mean(pctile(return,univ), pctile(return,sector)) gated by DMA; 1Y has +/-5pt RSI nudge. If technical-agent ran: replaces 3Y mechanical score |
| Sector & Macro | 11% | 13% | pctile(sector-mean return) + regime-cyclicality fit adjustment |
| Ownership Flow | 9% | 8% | pctile(mean FIIs_qoq+DIIs_qoq), trailing 6-of-8Q (3Y) / 1-2Q (1Y) |
| Accumulation | 8% | 5% | pctile(OBV slope), 6-12mo (3Y) / 1-3mo (1Y) |

All inputs winsorized 2%/98% before percentile ranking.

### Overlay gates (multiplicative, after weighted composite)
> **v3 SUPERSEDES BOTH OF THESE â€” see PART 2A Â§Gates in v3.** The liquidity cap is now **50**, the D/E
> exemption is widened to power/realty/telecom/construction, and **financials are exempt from the WHOLE
> balance-sheet gate**, not just the D/E trigger. The wording below is the v1 engine's behaviour, kept
> because the engine still runs it.

- **Balance-Sheet Safety**: D/E>2.5 OR IntCov<1.5 = RED, caps at 40. D/E>1.5 OR IntCov<3 = AMBER, x0.85. **Financial sectors EXEMPT** from D/E trigger (leverage is their business model).
- **Liquidity**: median 60d turnover below size-tier bar (5cr/1cr/25L for Large/Mid/Small) = RED, caps at 40.

### Penalty/Boost
Penalty = -min(10, 2^(redflag_count)-1). Red flags: IntCov<1.5, D/E>2.5 (non-financial only), negative 1yr revenue growth, >15pp deceleration, analyst expected growth <10%.
Boost = +3 if zero flags AND Quality+Value both >60th pctile. Full +10 reserved for qualitative confirmation.

### Recommendation logic
> **v3 SUPERSEDES THE "EITHER HORIZON" RULE.** It called Sell on **88 of its 246 Sells** where the
> BLENDED score was above 40 â€” BANKBARODA at 54.1, HINDALCO 52.5, JSWSTEEL 51.8, AXISBANK 47.4. The
> call is now taken on the **blended composite only**, and **no name at or above 40 is ever a Sell**.
> See PART 2A Â§THE LADDER. Sells fell 246 â†’ 198.

Per horizon (v1 engine, still what `full750_scored.csv` contains): gate RED = Sell. Score missing = No
Recommendation. Score >=40 = Hold, <40 = Sell. Overall = Sell if EITHER horizon says Sell.
Analyst's `your_recommendation` OVERRIDES quant when research exists.

### Ionic Score (client-facing, one number)
`base = 0.60 * final_3y_adj + 0.40 * final_1y_adj`
Forward adjustment:
- Growth leg (analyst's forward 3-5yr estimate): <5% = -15 | 5-10% = -5 | 10-15% = 0 | 15-20% = +5 | 20-25% = +10 | >=25% = +15 | +20 exceptional (>=25% AND ROE>=20% AND dilution<2%)
- Conviction leg: analyst Sell = -6 | analyst Hold where quant said Sell = +6 | agreement = 0
- Clamped +/-20. Two caps: (a) expected growth <10% = net adjustment <=0; (b) analyst Sell = net adjustment <=0.
- `ionic_score = clamp(base + adj, 0, 100)`

### Client recommendation logic (two-gate, with portfolio weights)
**As at v3 (2026-08-07) â€” this is the live rule:**
- **Gate A (quality/analyst), BOUNDED BY THE SCORE:** below 40 â†’ Sell. At 40-50 an analyst Sell â†’
  **Trim**. Above 50 an analyst Sell is **OVERRULED** â€” Hold, full stop.
- **Gate B (concentration):** ionic_score 40-50 AND weight >2.5% â†’ **eligible** to Trim.
- **40-50 is eligibility, not an instruction.** Trimming depends on position weight, which exists only
  inside a client book â€” a universe row can never say "Trim". `recommendation_v3` has two values,
  Sell and Hold; the reason lives in `trim_eligible_v3`.
- Concentration guidance: 5-10% = okay if growth strong; >10% = "little bad", Trim expected; >20% = extreme, strong Trim.
- Trim targets set by FM judgment, not formula.

### Asymmetric override bars
- Sell on a >40 scorer: **no longer possible above 50** (v3 ladder). At 40-50 it becomes a Trim and
  still needs the documented case + `exceptional_override` set, or `check_method` fails the build.
- Hold on a <40 scorer: needs 60%+ documented case. This is the **analyst Sellâ†’Hold rescue** and it is
  deliberately preserved â€” 14 names are held on analyst conviction in the current run.
- Default below 40 is Sell. The 750 universe runs ~33% quant Sells â€” **a book far below that = override
  leakage.** v3 currently runs **26%**, which is below that bar: the Gate A ceiling, the widened D/E
  exemption and the EPS-only growth leg each reduce Sells and they compound. Watch it on every book.

### Research pipeline (Sonnet, one agent per stock)
Each stock gets ~3min deep research: business model, earnings-quality check, sector-cycle context, reverse-DCF valuation judgment, forward growth estimate. Persona-routed by sector. Escalation only for genuine analytical disagreement (price staleness is expected, NEVER escalated).

### Technical agent (separate, one per stock)
Reads real price parquet, monthly resample, judgment on multi-year swing structure, MA-stack, volume character. Produces `chart_long_term_technical_pattern_score` (0-100) + choppiness penalty (0 to -15).

### Output formats

**Analyst Excel** (`build_analyst_excel.py`): 3 sheets â€” Analyst Full Detail (46 columns, full schema), Field Guide (self-documenting column definitions), Research Reader (per-stock long-form blocks).

**Client Excel** (`build_client_excel.py`): 3 sheets â€” At a Glance (dashboard), Recommendations (Stock/Ticker/ISIN/Sector/%/Ionic Score/Rec/Trim-to/Rationale), Portfolio Before-vs-After (weights, sector, mcap, concentration before and after).

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

## PART 2A: THE FROZEN v3 SCORING LAYER â€” NEW in v3, read before touching any score

`fix_thin_coverage_v3.py` sits **on top of** the engine and writes `full750_scored_v3.csv` beside v1.
**The engine itself is untouched.** Adoption into the engine is a Principal call and has not happened.

### The bug it fixes

`weighted_mean()` in `score_n100_quant.py` **skips a missing pillar and renormalises over the
survivors** â€” so the missing pillar's weight is *handed* to whatever remains. For a company listed
months ago the survivors are precisely the price pillars, and a post-listing run-up makes those strong;
the fundamental pillars that would temper it are the missing ones. Measured: **67 thin names
re-allocating a mean 37% of the composite**, worst inflation **+13.3 points** (TMCV). AGL scored a
**58.8 Hold off one pillar of seven**.

It is not only new listings. **106 names** (mostly banks) lack `growth_3y` because the screener carries
`Financing Profit` instead of `Sales+`. HOMEFIRST scored **39.6 â€” fractionally under the Sell bar â€”
with ROCE, interest coverage and 3Y revenue CAGR all blank**; the analyst caught it by hand and said so
in the research file. v3 scores it **64.1**.

### The fix, in the order it runs

```
0  REPLICATION CHECK   reproduce the engine's own composites; assert max|diff| < 0.05. Currently
                       0.0000. ABORTS if it fails â€” every number downstream would be fiction.
1  GROWTH ARTEFACTS    revenue CAGR that is infinite or >200% is a base-year artefact, not growth
                       â†’ pillar set missing  (6 names, incl. JIOFIN)
2  HISTORY CLASS       ret_24m present â†’ full (667) | ret_12m only â†’ 1-2y (45) | neither â†’ <1y (39)
3  IMPUTATION, in priority order
     a) 1-YEAR SIBLING   stage_3yâ†stage_1y, growth_3yâ†growth_1y, ownership/accumulation likewise
     b) LISTING-PRICE    <1y names: technical = return since listing, ranked against the universe
                         over the SAME window (longest of 12/9/6/3 months the name supports)
     c) NEUTRAL 50       anything still unobservable
                         â†’ 137 names touched, 38 via listing price
4  MARCH-TO-MARCH      growth from full fiscal-year columns, never a TTM window (716 of 751)
5  PENALTY/BOOST        RECOMPUTED, not inherited â€” two of four red flags read revenue growth
6  GATES                balance sheet + liquidity (below)
7  CAP                  clamp to [5, 95], asserted to move ZERO recommendations
8  FORWARD ADJUSTMENT   growth leg + conviction leg (below)
9  THE CALL             ladder (below)
```

### Why each imputation rule, with the backtest that chose it

Tested on **515 fully-covered names** whose true score is known, deleting exactly the pillars thin
names really lack:

| scheme | bias | MAE | rank corr | verdict |
|---|---|---|---|---|
| skip-and-renormalise (the bug) | +2.95 | 10.08 | 0.601 | â€” |
| value 50 / growth 25 / quality 25 | **+3.07** | **11.83** | **0.445** | **REJECTED â€” worse than the bug** |
| neutral-fill 50 | +1.84 | 6.95 | 0.601 | used for the residual |
| **1-year sibling** | **+0.05** | **2.72** | **0.932** | **adopted â€” biggest win** |
| **listing-price technical** | +1.84 | 6.17 | **0.701** at 3 months | **adopted** |

The 50/25/25 redistribution loses because it concentrates freed weight on value, and value is
*uncorrelated* with the pillars that went missing â€” it amplifies noise instead of adding information.
Under genuine uncertainty, shrinking to the middle beats betting the weight on one surviving pillar.
**Do not re-propose it.** The schema-gap case (banks) was tested separately and substitution still wins
(MAE 4.97â†’3.38, corr 0.843â†’0.898; the two growth pillars correlate 0.645).

### March-to-March, not TTM

666 names sat on `ttm(Mar 2026)` but **76 on `ttm(Jun 2026)`**. Because the Growth pillar is a
**cross-sectional percentile**, those 76 were ranked against the rest **over a different period** â€” not
a freshness trade-off but an invalid comparison. COHANCE read âˆ’13.0% on the engine's window against
**+89.4%** March-to-March; FACT +30.4% against âˆ’19.8%. Forty names differed by >5pp, twelve by >20pp.

### The forward adjustment

```
growth_leg   banded on the ANALYST'S EXPECTED EPS GROWTH ALONE (100% EPS, 0% revenue â€” as v1)
             <5% âˆ’15 | 5-10% âˆ’5 | 10-15% 0 | 15-20% +5 | 20-25% +10 | â‰¥25% +15
             REVENUE RESCUE: expected FORWARD revenue >15% AND expected EPS <10% â†’ floor the âˆ’15 at âˆ’5
                             DORMANT: expected_next_3y_revenue_growth_pct is not captured yet, so it
                             fires on 0 names. It reads the field; adding it activates the rule.
             +20 EXCEPTIONAL tier DORMANT â€” needs share dilution <2%, absent from the dataset. Enabled
                             two-of-three it fired on 27 names, which over-grants.
conviction   analyst Sell âˆ’6 | analyst rescues a quant Sell +6 | agreement 0
clamp Â±20, then: expected growth <10% â†’ net adj â‰¤ 0 ; analyst Sell â†’ net adj â‰¤ 0
Ionic = clamp(base + adjustment, 5, 95)   where base = 0.60Ã—3Y + 0.40Ã—1Y
```

**Why the 60:40 EPS-to-revenue weighting is NOT implemented.** The Principal specified it, twice. It
cannot be built honestly: there is **no expected-revenue figure anywhere in the stack**, so it was
substituted with *trailing* revenue â€” which inverts the leg for exactly the names it matters to. BDL:
the analyst expects **+15% EPS**, trailing revenue was **âˆ’27%** on FY26 delivery delays, and the blend
gave **âˆ’1.8% â†’ the maximum âˆ’15 penalty** on a company the analyst is positive about. In v1 the same name
scored **+5**. Of 93 names then taking âˆ’15, **75 had negative trailing revenue and 20 carried an analyst
estimate of 10%+**. One field per research file (`expected_next_3y_revenue_growth_pct`) unblocks it.

**Where the adjustment lived in v1:** in `compute_client_scores.py` (the CLIENT pipeline, frozen v6.2),
never in the universe file. 30 of 59 holdings on the shipped Talaulikar deck carried one, between âˆ’11
and +15, and the deck's scores reconcile to `pf_mech_flags.json` 59/59. v1's `growth_leg(g)` took the
analyst's expected figure **alone** â€” 100% EPS, no revenue leg at any weight.

### THE LADDER â€” the 40 bar is absolute

```
below 40      Sell
40 and above  Hold        â† an analyst Sell does NOT sell a name here
    40 - 50   trim-ELIGIBLE (weight >2.5% decides, at book level) and/or on the analyst's view
    above 50  analyst Sell is OVERRULED entirely
```

**40-50 is not a Trim band.** It confers *eligibility*, not an instruction â€” and eligibility cannot be
resolved in a universe file at all, because trimming depends on **position weight**, which only exists
inside a client book. Naming a universe row "Trim" asserts a portfolio decision from data containing no
portfolio. `recommendation_v3` therefore has exactly **two values: Sell and Hold**; the reason sits in
`trim_eligible_v3`.

Gate A's ceiling is the substantive change. It had been selling **BAJAJ-AUTO at 67** on a valuation
argument the **Value pillar had already weighed and priced as reasonable** â€” of the 23 such Sells, 9 sat
in Upper or Top-25% Value. The analyst view is not discarded: it still costs 6 points via the conviction
leg and marks the name trim-eligible.

### Gates in v3

| gate | rule |
|---|---|
| Balance sheet | D/E >2.5 or int-cover <1.5 â†’ RED, caps at 40 Â· D/E >1.5 or int-cover <3 â†’ AMBER, Ã—0.85 |
| **Financials** | exempt from the **WHOLE** gate, D/E *and* coverage |
| Power / Realty / Telecom / Construction | exempt from the **D/E trigger only**; coverage still applies |
| Liquidity | below the size-tier turnover bar â†’ caps at **50** (was 40) |

**Do not apply interest coverage to financials.** The frozen doc says "exempt from the D/E trigger",
which reads as coverage-still-applies. It is wrong, and the code was right: interest expense is a
lender's **cost of funds**, not debt service, and an insurer barely has any. Applying it flagged
**NIACL RED at coverage âˆ’399 with ZERO debt**, CANHLIFE âˆ’11.8, NIVABUPA âˆ’3.7, plus five capital-market
firms at 2.0-2.9Ã— â€” eleven healthy names penalised by a ratio that does not describe them.

On sectors: solar **generation** sits in Power (exempt); solar **equipment** makers (EMMVEE, WEBELSOLAR,
UTLSOLAR) are Capital Goods, where leverage is not structural and the gate should bite. Exempting on the
word "solar" lets the wrong half through.

### Earnings quality â€” the profit bridge

The old rule (PAT +50% while Sales <10%) is **wrong and has been removed**. Operating leverage produces
that pattern routinely: of the 29 names it flagged, **17 (59%) were margin-driven**, not one-offs.
Replaced with a decomposition of the year-on-year PBT change:

```
volume effect = (Salesâ‚ âˆ’ Salesâ‚€) Ã— OPMâ‚€     revenue genuinely grew
margin effect =  Salesâ‚ Ã— (OPMâ‚ âˆ’ OPMâ‚€)      LEGITIMATE operating leverage
other income  =  OIâ‚ âˆ’ OIâ‚€                   NON-OPERATING â€” the one to watch
finance/dep   = âˆ’(Î”Interest) âˆ’ (Î”Depreciation)
```

The bridge **closes to 0.6%** (median residual â‚¹1.0cr against a â‚¹169.5cr median PBT change) across 662
names â€” proof it is complete, not approximate. Flags: `oi_driven_growth` (>50% of the PBT increase from
other income) 75 Â· `oi_level_high` (OI >25% of PBT) 140 Â· `oi_spike` (>2Ã— its own 3y median and >15% of
PBT) 81. Financials exempt â€” treasury income *is* their operating business.

A worked check on the bridge's accuracy: it computed **â‚¹1,196cr** of other income for BAJAJ-AUTO; the
analyst, working independently, wrote **â‚¹1,195cr**. It did *not* fire a flag â€” 19.1% of PBT sits under
the 25% threshold and margin contributed more. That is threshold behaviour, not a bug, and it is
precisely why the analyst layer exists.

### Does v3 predict better? Honestly: not established

PIT decile test, 2016-2025, quarterly formation, three horizons
(`results/BT_V1_VS_V3_DECILES.md`). At **1Y**:

| arm | rank IC | hit rate | D10âˆ’D1 |
|---|---|---|---|
| v1 | +0.026 | 59% | **+5.50%** |
| v3-mechanical | +0.022 | 56% | +3.36% |
| v3 + forward growth leg | âˆ’0.007 | 56% | **+0.13%** |

Ordering is **v1 > v3-mech > v3-fwd at every horizon**, and nothing is monotone in a single quarter
(0/32). Three conclusions, in order of confidence: **(1)** the forward growth leg carries no ranking
power â€” it cuts the 1Y spread to nil; **(2)** the mechanical fixes cost a little discrimination in
exchange for not rewarding missing data, which is the right trade; **(3)** the base model's edge is weak
but positive at 1Y and lives at the tails.

Two things the harness **cannot** test, and no claim should be made about either: the **conviction leg**
(no point-in-time history of analyst opinion; proxying it with the score is circular) and the
**listing-price technical** (`score_asof` needs 260 sessions, so sub-1-year names never enter the
universe). v3-fwd proxied the forward leg with *trailing* growth, so it tests the *mechanism*, not
analyst foresight.

### 13 logged challenges â€” read `09_PRODUCT/FIVE_SIGNAL_AND_V3_SCORING_SPEC.md` Â§6b

Three block adoption: **C6** `compute_client_scores.py` has none of the v3 rules, so adopting v3 makes
every deck disagree with the universe Â· **C7** LT's 45.5 is stale (built on a superseded analyst Hold;
recomputes to 33.5, a clean Sell) Â· **C8** the deck reads v1 sources while the Excel reads v3.
Methodological: **C1** the growth and conviction legs correlate +0.24 and **95 names are charged by
both** for what is substantially one opinion (analyst Sells forecast 9.1% median growth vs 13.5% for
Holds) Â· **C2** Sell rate 26% against the frozen ~33% expectation.

---

## PART 3: MF QUALITY FRAMEWORKS (QFRA-1 / QFRA-2)

### QFRA-1 (Short-term capture framework)
Source: `MF Dashboard.xlsx` via `mf_capture_recomm.compute_category`.
Method: 6-month down-capture ratio vs the fund's own SEBI category benchmark. FN=6M down-capture, HC=6M total capture.
**Category cutoffs (live workbook `<cat>2!LO1` values â€” all six, do not guess the missing ones):
large 0.90 Â· mid 0.80 Â· multi 0.90 Â· flexi 1.00 Â· small 1.00 Â· largemid 1.00.**
A fund that takes LESS of the benchmark's falls than the cutoff passes. BUY = top-3 on HC ranked over
ALL funds in the category (excluded funds still consume ranks â€” deliberate). Full method: `/qfra1-rerun`.

### QFRA-2 (Long-term selection engine)

> **âš  QFRA-2 IS NOT IN THIS REPO.** Verified 2026-08-07: neither `QFRA2_current.csv` nor
> `Mf_qfra2/mr_x_framework/src/final_model.py` exists anywhere under the `NIFTY 500` tree. The QFRA-2
> engine, its NAV files and `Mf_qfra2/data/verified_navs_<cat>.csv` live in a **separate QFRA-2
> repository** â€” ask the Principal or the MF desk for access before starting any fund work. Everything
> below describes that engine correctly; you simply cannot run it from this checkout alone.
> This is the one place the manual's "nothing else needed besides the GitHub repo" claim does not hold.

Source: `QFRA2_current.csv`. Engine: the frozen QFRA 2.0 model (`Mf_qfra2/mr_x_framework/src/final_model.py`).
**What it is:** a *selection* engine. Per category it ranks the eligible funds and publishes the **top-2
(from a top-5 shortlist)** most likely to beat the category TRI over 3â€“5 years. Verdicts are **`ACTIVE`**
or **`INDEX CORE (+ satellites)`** â€” **there is NO Sell verdict.** Re-run 6-monthly.

**Coverage â€” read this before declaring a gap (verified 2026-08-04):** `QFRA2_current.csv` holds
**8 categories Ã— top-5 = 40 ROWS**. That is a publication slice, **NOT** the coverage universe.
The engine actually ranks **99 Direct-plan funds** (post-3y-gate): large 8 Â· largemid 5 Â· mid 8 Â·
flexi 6 Â· multi 5 Â· small 6 Â· focused 30 Â· value 31. Before writing "no QFRA-2 coverage" for a held
fund, check `Mf_qfra2/data/verified_navs_<cat>.csv` **and** resolve renames via
`pr_template/lib/mf_mapping.py` `SCHEME_RENAMES` (e.g. ICICI Pru Bluechip â†’ ICICI Pru Large Cap;
Kotak Emerging Equity â†’ Kotak Midcap). Treating absence from the 40 rows as absence of coverage is
what put 6 substituted scores into a shipped client deck.

**Two traps in the score:**
1. **QFRA Score is a within-category RANK percentile, not an absolute quality score.** 80/100 = rank 2
   of 5 (Large & Mid); 88/100 = rank 4 of 33 (Focused). Never compare scores across categories, and
   never read a number as "how good is this fund" in absolute terms.
2. **Deployment scope (CEO):** 6 categories â€” Large (index-core), Large & Mid, Mid (momentum sleeve),
   Flexi, Multi, Small. **Focused and Value/Contra are EXCLUDED from deployment** (the engine still
   publishes them; Value's final-2 are closed Sundaram series with no continuous NAV). **Index-core
   routing is Large Cap and Mid Cap** â€” Large & Mid Cap is `ACTIVE`, High conviction.

Grade = **CALIBRE** (7 pillars: Conviction Â· Alpha Â· Leadership Â· Integrity Â· Benchmark Â· Resilience Â·
Edge), Grade Aâ€“D. "MERIT" is the superseded working name â€” the CSV column is still `merit_grade`, a code
artefact only. **Client-facing word is "grade", never CALIBRE or MERIT** (both are internal jargon;
tellscan flags them).

### Fund Sell rule â€” "ORIGINATE AND VETO" (Principal ruling 2026-08-04; supersedes the old dual-framework wording)

Implemented in `09_PRODUCT/scripts/fund_ctx_adapter.py:merge_calls()`.

| Leg | Role |
|---|---|
| **QFRA-1** | **ORIGINATES.** The only framework with a Sell verdict, and the only one with a replayed backtest. |
| **QFRA-2** | **VETOES ONLY.** A **CALIBRE A or B grade blocks the Sell** â†’ Hold. C/D do not veto. It can NEVER originate a Sell. |

- A QFRA-1 Sell + a QFRA-2 **A/B** grade = **Hold**, and the disagreement is raised as a
  **CONTRADICTION** that must appear in the FM review pack. It is never resolved silently.
  `build_fund_entries()` returns a **3-tuple** `(entries, gaps, contradictions)` for exactly this.
- A QFRA-1 Sell + **no** QFRA-2 coverage = Sell, but flagged `SINGLE-FRAMEWORK SELL` â†’ FM sign-off
  (this covers everything in Focused/Value, which have no QFRA-1 sheet).
- Structural actions (Redeem-to-Direct, mandate switch, liquid/debt/index consolidation) are exempt â€”
  plan facts, not performance calls; they need no framework Sell at all.
- **No client Buy is ever issued.** Vocabulary is Sell / Trim / Hold.
- **RETIRED 2026-08-04:** the old QFRA-2 sell proxy `loser_flags > 0 OR qfra_score < 40`. It fired on
  the engine's OWN rank-2 A-grade High-conviction pick (Franklin India Equity Advantage), because
  SENTINEL is a shortlist-refinement screen, not a verdict on a holding â€” and `qfra_score < 40` sold a
  fixed fraction of every category by construction. Never reinstate either leg.
- **Never write "both non-Hold"** â€” that phrasing is literally satisfied by one side BUY + the other Sell.

**Two honesty caveats you must carry into any client wording (measured 2026-08-04):**
- **The legs are NOT independent.** QFRA-1's ranking metric (6M total capture = up-capture Ã·
  down-capture) *is* QFRA-2's `_cap6`, which carries **w=0.30** in QFRA-2's final blend; 3y
  down-capture adds more. The capture family is **40.5â€“47.5% of the QFRA-2 score** â€” a range, because
  the down-capture leg's share floats with whether a live factor cache is present. Agreement is
  partly one signal agreeing with itself. Say "both of our fund frameworks are at Sell", **never**
  "two independent frameworks agree".
- **QFRA-1's backtest is strong on BUY and weak on SELL.** 906 formations, 2012â€“2024, all six category
  sheets: BUY median **+2.59%**, hit **66%** (robust to trimming) â€” but SELL hit **49.3%** pooled at
  Apr/Oct, and **below 50% in all six anchor pairs**, median âˆ’0.57%, plain mean âˆ’0.13%. Smallcap is the
  exception (median âˆ’1.05%, trimmed âˆ’1.72%, hit 44% â€” rarely right, very right when it is). So a
  QFRA-1 Sell must stand on **the analyst's stated reason**, with the capture statistic as support.
  Never tell anyone "the backtest says sell". Evidence:
  `04_RND_LAB/STOCK_SCORECARD_750/results/anchor_pair_study/ANCHOR_PAIR_STUDY.md` Â§extension.

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
Every module is a pure function of the `ctx` dict â€” numbers/names/verdicts all trace to `ctx[...]` lookups. The template is standardized; the data layer is per-client; the rendered deck is unique to that client's book.

### Full pipeline (real client, Apr/Oct cadence)

**Step 0: Advisor intake (same turn as holdings upload)**
The INSTANT a holdings file arrives, do TWO things in parallel:

**(a) Launch parallel-compute** (zero advisor interaction needed):
`client_intake.py` match â†’ `pf_qual_*.json` lookups per matched stock â†’ `fund_ctx_adapter.py` QFRA-1/QFRA-2 verdicts per matched fund â†’ sector/mcap/concentration/cost aggregates â†’ all written to `client_ctx.json` + `exceptions.csv` on disk.

**(b) Ask the advisor up to 4 questions** (while compute runs):

**Q1 â€” Deck depth:**
| Option | Slides | Description |
|---|---|---|
| **Detailed (HNI_DEEP)** | 60-100pg | Full methodology, all annexure modules, family-office grade |
| **Medium (STANDARD)** | 30-60pg | Professional, accessible, selected annexure |
| **RM Light (RM_SIMPLE)** | 15-30pg | Plain language, bigger type, story beats only |
Warn: RM Light can occasionally print >30pg on a large book (pagination, not a preset bug) â€” offer Medium instead of forcing the ceiling.

**Q2 â€” First review or follow-up?** (unlocks `since_last_review` module if meeting_history supplied)

**Q3 â€” Anything to exclude/downplay?** (tax detail, methodology detail, specific sections)

**Q4 â€” Turnaround / PDF need?** (PDF conversion is ON REQUEST ONLY, never auto)

**Then ONE follow-up after Q1 is answered:**
**Recommended** (ship the tier's current preset from `tiers.py` as-is) or **Customize** (show a checklist of the tier's optional modules, each tagged **(recommended)** when it's in that tier's `optional_on`; for RM_SIMPLE only, also show its `skip_core` modules as re-addable). Modules that are PARKED/CUT are never listed â€” they're retired, not a choice. Full spec: `INTAKE_WORKFLOW_SPEC.md`.

Do NOT wait on (b) to start (a) â€” they're independent; by the time the advisor answers, the expensive research is already on disk.

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

Matching: ISIN first, then normalized-name prefix. Unmatched rows go to `exceptions.csv` for the RM â€” NOTHING silently dropped or fabricated.

**Step 2: Fund calls**
`fund_ctx_adapter.py`: QFRA-2 (curated CSV, 40 funds) + QFRA-1 (MF Dashboard.xlsx); merged by dual-framework rule. Held funds outside QFRA-2 = honest gap "needs a QFRA-2 scoring run".

**Step 3: Build**
```bash
set PR_SUFFIX=_v1
%PYTHON% build_<client>.py HNI_DEEP
```
If build errors with **PermissionError** â€” the PPTX is OPEN in PowerPoint. Bump `PR_SUFFIX` (e.g. `_v2`), never fight the lock.

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
- **opportunity_set.py and deployment.py are CUT entirely** â€” this deck only sells/holds.
- **Cost slide CUT** â€” was scheme-TER-only with no Regular-drag/PMS overlays.
- Commentary leans WITH the call. A Sell never leads with praise; positives only as the rejected bull.
- Score method = gist only: never reveal the 60/40 blend, pillar weights, or thresholds beyond "below 40 / 40-50 watch / 50+".

### Design & presentation
- Cover/dividers: generative flow-art, two-tone headline, text logo lockup on navy, divider mini-TOC + ghost numeral.
- Correlation/overlap matrices capped: annex_correlation top 15 by weight, scheme_overlap_full top 10 by weight. Both disclose cap via scope_tag.
- Growth-projection mu/sigma derived from THIS book's real holdings, never a flat 12%/14% constant.
- **PDF on request only** â€” never auto-convert after every rebuild.
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
`funds_equity.py`'s paired-bar chart currently shows each fund's own-benchmark CAGR correctly, but the visual legend just says "Its category benchmark" generically â€” a reader can't tell WHICH benchmark applies to WHICH fund. Principal wants a category-wise benchmark MAP visible directly in the graph.

---

## PART 6: ENVIRONMENT & COMMANDS

### Python
```
Path: C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe
Alias "python" is BROKEN â€” always use the full path.
Always set: PYTHONIOENCODING=utf-8  PYTHONUNBUFFERED=1  (console is cp1252)
```

### Corporate proxy
~0.7MB/s. Sequential `requests.Session()` only (threads stall).
`truststore.inject_into_ssl()` before any HTTPS call.

### PowerShell 5.1
No `&&` operator. Write Python to .py files and execute (here-strings break raw strings).

### PDF conversion (`pptx_to_pdf.py`, auto-backend)
Three backends tried in order (best-available wins):
1. **PowerPoint COM** (desktop, pixel-perfect) â€” needs `comtypes` pip package + MS Office. `pip install comtypes` once.
2. **LibreOffice** (user-local `%LOCALAPPDATA%\Apps\LibreOffice`, msiexec /a extract, no admin)
3. **Slide-to-PNG** (pure Python, works on web/sandbox/no-Office) â€” rasterises at 150 DPI, text not selectable but layout faithful
Force a backend: `--backend pptx|libre|png`. Default = auto-detect.

### Angel SmartAPI (data only, NO real trades ever)
Credentials are NOT stored in this doc â€” ask the CEO/Ops desk for the current API key and
client ID if your work needs live Angel data. Rate limit AB1021: use >=1.2s/req, retry passes.
Angel purges expired option contracts from master â€” daily capture task handles this.
**Not needed for NDPMS deck / portfolio-review work** â€” that pipeline runs on CAS statements
and the scored universe; edge cases (a stock/fund with no data) go to screener.in/yfinance,
never Angel SmartAPI.

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
5. `india_fundamentals_mc/Train.parquet` `annual_report` col is corrupt at source â€” read other cols only.
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
| fm-vikram-shah | FM â€” Derivatives & short-vol, 15+yr | Idea prioritization, capital allocation, IC convening |
| fm-equities-devika-menon | FM â€” Equities & Momentum, 15+yr | Equity/momentum allocation, Track-2, factor sleeves |
| fm-fundamental-sanjay-kulkarni | FM â€” Fundamental Quality & Value, 18+yr | Long-only fundamental portfolio, value/quality sleeves |

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
- **DESK-20** (desktop app, $20/mo): CIO office â€” R&D, ideas, analysis, light work. Max 2 parallel agents.
- **DESK-100** (VS Code, $100/mo): Execution floor â€” backtests, bulk data, batch workflows, EOD auto-runs. Max 3 parallel agents.

---

## PART 11: AGENTIC FUND MANAGER WORKFLOW

### Full NDPMS client review (Sell/Trim/Hold with targets)

**Step 1 â€” Mechanical layer** (script, ~0 tokens):
Compute ionic_score, portfolio weights, sector weights, mcap bands. Flag candidates:
- Gate A: analyst Sell or ionic_score <40 = Sell-candidate
- Gate B: ionic_score 40-50 AND weight >2.5% = Trim-candidate
- Concentration: >10% = Trim advice expected; >20% = extreme
- Single-GROUP concentration: if any promoter group >20% of equity sleeve, flag for group-concentration slide

**Step 2 â€” FM judgment pass** (one Sonnet agent):
FM sets final action + Trim targets + client reasons. Overrides are logged. Commentary leans with the call. Nothing invented â€” shaky facts go back to analyst layer.

**Step 3 â€” Verification gate** (MANDATORY):
Script-verify: weights sum to 100.00 (+/-0.05), after-weights reconcile, every Sell/Trim has reason, every Trim has target < current, vocabulary correct, sentiment matches call, no internal jargon.

**Step 4 â€” Build + ship gate**:
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

# ONE COMMAND for every gate on every deck x every tier  -> 09_PRODUCT/WORKFLOW_AUDIT.md
%PYTHON% ../scripts/audit_full_workflow.py

# then LOOK at the slides you changed (no gate can see the page)
%PYTHON% ../scripts/pptx_slide_png.py out/<deck>.pptx 25,26      # or 25-28

# individual gates, if you need one in isolation
%PYTHON% check_geometry.py out/<deck>.pptx
%PYTHON% check_geometry2.py out/<deck>.pptx
%PYTHON% tellscan.py out/<deck>.pptx
%PYTHON% check_method.py data/<client>.py         # A DATA MODULE, not a .pptx
%PYTHON% check_freshness.py --ack "<source>: <reason>"

# THE SCORING CHAIN â€” run in this order, before any client build
cd Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750
%PYTHON% earnings_quality_decomp.py       # -> results/EARNINGS_QUALITY.csv
%PYTHON% fix_thin_coverage_v3.py          # -> results/full750_scored_v3.csv  (ABORTS if it cannot
                                          #    reproduce the engine â€” do not edit that assertion)
%PYTHON% audit_v3_freeze.py               # 21 invariants; must be 21/21

# the 750 research Excel (five signals + v3 scores + forward data + earnings flags)
%PYTHON% 09_PRODUCT/scripts/build_scores_excel.py

# re-run a backtest ONLY if a scoring rule changed
%PYTHON% bt_v1_vs_v3_deciles.py           # PIT decile test, quarterly/1Y/3Y
%PYTHON% test_imputation_schemes.py       # which missing-pillar scheme wins
%PYTHON% test_listing_price_signal.py     # does return-since-listing beat neutral-fill
%PYTHON% test_growth_schema_gap.py        # the banks case (growth_3y absent by schema)

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

---

## WHERE THINGS LIVE (v3 additions)

| File | Role |
|---|---|
| `pr_template/lib/five_signals.py` | **single source of truth** for the five signals â€” clubbing, floors, words, colours, re-ranking, universe join |
| `pr_template/modules/book_scored.py` | the five-signal holdings page |
| `pr_template/slidekit.py` | `dot` + `chip` table cell types; `oval(line=)`; the snake_case detell catch-all |
| `scripts/audit_full_workflow.py` | whole-pipeline audit â†’ `WORKFLOW_AUDIT.md` |
| `scripts/pptx_slide_png.py` | slide â†’ PNG (the only way to run the visual gate on this box) |
| `scripts/build_scores_excel.py` | the 750 research Excel |
| `STOCK_SCORECARD_750/fix_thin_coverage_v3.py` | the frozen v3 correction layer |
| `STOCK_SCORECARD_750/earnings_quality_decomp.py` | profit-bridge earnings quality |
| `STOCK_SCORECARD_750/audit_v3_freeze.py` | 21 scoring invariants |
| `09_PRODUCT/FIVE_SIGNAL_AND_V3_SCORING_SPEC.md` | the frozen spec + all 13 logged challenges |
| `STOCK_SCORECARD_750/results/*.md` | every backtest and diagnostic note behind the rules |

**Removed at freeze** â€” `chart_signal_options.py`, `chart_dot_formats.py` (one-off design-option
renders) and `fix_thin_coverage_v2.py` (the interim corrector). If a doc or journal entry mentions
them, that is history, not a missing file.

**`results/full750_scored.csv` is NOT a superseded v1 duplicate.** It is the engine output, the input
`fix_thin_coverage_v3.py` reads, and the file `lib/five_signals.py` joins the universe from. Both it
and `full750_scored_v3.csv` must be present.

---

## KEEPING THIS FILE AND THE DATA CURRENT ON GITHUB

`Shreyas_Ionic_AMC/99_OPS/sync_handover.py` commits and pushes the **handover manifest** â€” this skill,
`README.md`, `HOW_WE_SCORE_STOCKS.md`, the frozen spec, the stock scores, fund grades, the ISIN master,
and the command-centre state files. A `Stop` hook in `.claude/settings.json` runs it at the end of every
turn, so editing this file here updates GitHub with no one remembering to. It is a no-op when none of
those paths changed.

```bash
python Shreyas_Ionic_AMC/99_OPS/sync_handover.py --dry-run
```

Source code is **not** auto-synced â€” that stays a deliberate commit, because an auto-commit of every
dirty file would push half-written code the moment a turn ended.

**Read the delivery warning it prints.** Pushing is not the same as being readable by a recipient. This
repo's default branch (`main`) is a one-file stub whose history is unrelated to the real trunk, so it
can never fast-forward and a plain `git clone` gets nothing. `master` is the real delivery branch, so hand people the
branch explicitly:

```bash
git clone -b master https://github.com/shreyas1gupta-wq/ionic-scorecard.git
```

That gap is exactly how a handover on 2026-08-13 produced a deck with all 24 score cells reading
"pending" and 55 hollow signal rings, while 11 of its 12 names sat in the committed universe file with
real scores.

---

## IF YOU ARE NEW: THE SIX THINGS MOST LIKELY TO BURN YOU

1. **A deck can build perfectly and still be wrong.** Nothing in this pipeline raises an error when
   *data* is missing â€” a failed universe join renders every signal dot as a hollow grey "not scored"
   ring on an otherwise flawless page, exit code 0, no warning. **After your first build, confirm the
   dots have colour.** One command:
   ```
   python -c "import sys; sys.path.insert(0,'lib'); import five_signals as F; print(len(F.load_universe()))"
   ```
   Run it from `pr_template/`. It must print a number in the hundreds. `0` means the join failed and
   every dot on the page is meaningless. (This exact bug shipped once: the repo-root walk matched a
   folder named literally `NIFTY 500`, so it worked on the Principal's machine and silently returned
   nothing from a normal `git clone`. Fixed â€” but the *class* of failure is the thing to remember.)
2. **`check_method.py` takes a data module, not a .pptx.** The error looks like a broken gate.
3. **`NaN` is truthy and `str(NaN)` is `"nan"`.** `fillna("")` before `astype(str)`, always.
4. **Two gate rules are inverted on demo decks** â€” `SYNTHETIC_DEMO_LEAK` is *correct* on ABXY.
5. **The gates cannot see the page.** Export the slides and read them, every time.
6. **Never restate a threshold.** Bands live in `five_signals.py`; scoring rules in
   `fix_thin_coverage_v3.py`. A duplicated number drifts within the hour.
