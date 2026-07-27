---
name: ndpms-deck
description: Build/modify the Ionic Wealth NDPMS portfolio-review deck from the pr_template engine — tiers (HNI_DEEP/STANDARD/RM_SIMPLE), modules, charts, QA gates and every Principal ruling that governs client-facing slides. Use for "build the client deck", "update the review ppt", template/module edits, or any NDPMS presentation ask.
---

# NDPMS Deck Engine (pr_template) — operating playbook (consolidated 2026-07-26)

**Home:** `Shreyas_Ionic_AMC/09_PRODUCT/pr_template/`. Config-driven module library:
`engine.py` (module registry + build), `tiers.py` (HNI_DEEP / STANDARD / RM_SIMPLE presets),
`slidekit.py` (Deck primitives), `modules/*.py` (~57 slide modules), `charts.py` → shared
`09_PRODUCT/scripts/chart_lib*.py`, `art.py` (generative cover/divider art), `data/azby_family.py`
(demo ctx; schema in its docstring). Build: `PR_SUFFIX=_vN python build_azby.py [TIER]` +
`build_master.py`. Outputs `out/`. If a deck errors with PermissionError it is OPEN in the
Principal's PowerPoint — bump PR_SUFFIX, never fight the lock.

## THE QA LAW (non-negotiable, in order)
1. `render_preview.py <deck> <outdir>` (python-pptx→PIL, real fonts) and **LOOK at changed slides** —
   geometry checkers catch overlaps, not ugliness. No deck change ships unseen.
2. `check_geometry.py` AND `check_geometry2.py` (box + rendered-extent, z-order-aware) = 0 findings.
3. Tell-scan: 0 em-dashes/double-hyphens/hollow intensifiers, 0 "Buy" as a recommendation,
   0 internal jargon (SENTINEL/QFRA/MERIT — client words: "watch-outs", "fund score /100", "grade",
   "the firm's fund-quality framework"), and 0 **data-QA vocabulary** (CEO sweep 2026-07-26):
   "stale", "does not reconcile", "data feed", "data cut", "data/quant snapshot", snake_case field
   names (fcf_yield/bs_flag/redflags), source names (screener.in), org names (Data Office), product
   CTAs (CoPilot). slidekit.txt() carries a render-time scrub net for these, but the DATA files
   (pf_qual narration) must be clean too — the scrub can't rescue whole sentences of QA talk.
4. **Cross-panel consistency scan** (CEO sweep class of bugs): any two numbers on the same slide
   that a reader will assume are the same set MUST reconcile or be explicitly scoped
   (tax table=fund actions vs waterfall=equity plan; group-concentration KPI vs table rows =
   same basis: % of equity sleeve). Same-entity names identical across slides (short_name width
   ≥30 for scheme tables). A driver/tag must match the narrative beside it and the same call's
   rationale elsewhere in the deck.
5. Principal sign-off before any client artifact ships.

## FULL PIPELINE (real client, Apr/Oct cadence; auto-build wired in OPERATING_CALENDAR)
1. **Intake** `09_PRODUCT/scripts/client_intake.py --holdings <CAS-extract.csv|xlsx> --profile
   <profile.json> --out <client_dir>` → client_ctx.json + exceptions.csv (unmatched rows go to
   the RM, never dropped/fabricated). Profile JSON (template via --emit-template) carries the 4
   personalization blocks: goals/timelines, holding ages & costs, family structure, meeting
   history. NSDL CAS PDF parser slots in when a sample statement arrives.
2. **Fund calls** `09_PRODUCT/scripts/fund_ctx_adapter.py` — QFRA-2 (QFRA2_current.csv, 40
   curated funds only: held funds outside it = honest gap "needs a QFRA-2 scoring run") +
   QFRA-1 (mf_capture_recomm.compute_category on MF Dashboard.xlsx; returns (df, anchor);
   FN=6M down-capture, HC=6M total capture); merged by the dual-framework rule (Sell needs
   BOTH non-Hold; disagreement → Hold, flagged).
3. **Build** `PR_SUFFIX=_vN python build_azby.py [TIER]`; `since_last_review` module renders
   only when profile has meeting_history.
4. **Gates** (QA LAW above). 5. **PDF** `09_PRODUCT/scripts/pptx_to_pdf.py <deck.pptx>` —
   LibreOffice 26.2.5 user-local at %LOCALAPPDATA%\Apps\LibreOffice (msiexec /a extract, no
   admin; version-discovery downloader in 99_OPS if it ever needs a reinstall).
6. **Publish** to `09_PRODUCT/reports/` with client-facing names (current CEO set:
   NDPMS_Portfolio_Review_ABXY_HNI.pptx/.pdf + ..._RM_Lite.pptx/.pdf), DRAFT until sign-off.

## PRINCIPAL RULINGS BAKED INTO THE TEMPLATE (do not regress)
- **Vocabulary:** Sell/Trim/Hold only, never Buy; no buy recommendations anywhere (opportunity-set
  mix = "Illustrative"; proceeds PARK in cash; transition/deployment slides live in the ANNEXURE).
- **Asymmetric override bars (final 2026-07-26):** Sell on a >40 scorer = 90%+ exceptional case
  (amber EXCEPTIONAL tag on the sell page); Hold on a sub-40 scorer = 60%+ documented case.
  Default below 40 is Sell; 40-50 = watch zone with a stated reason. Book sanity: the 750 universe
  runs ~33% quant Sells — a book far below that is override leakage.
- **Sell page:** confirmed Sells only (no "Under review" pill client-side), no reason-category
  column, analyst-authored 2-line case per name (`data/client_cases.json` overlay; fallback =
  negative para, NEVER the trigger — triggers can read bullish), visible p.NN link per row to the
  rationale card, paginates at 5 rows.
- **Commentary leans WITH the call** — a Sell never leads with praise; positives only as the
  explicitly-rejected bull (rule also in agentic-fund-manager Steps 2-3).
- **Score method = gist only**: never reveal the 60/40 blend, pillar weights or thresholds beyond
  "below 40 / 40-50 watch / 50+"; balance-sheet gate described as context-aware (industry norms,
  sovereign/group backing).
- **Demo-data honesty:** a demo Sell/Trim may wear a real fund/stock name ONLY if the real record
  supports it (Bandhan rule — verify vs MF Dashboard first; PGIM = verified weak example).
  Synthetic numbers must be plausible (no 56% CAGR bars).
- **Group concentration:** checked EVERY build; slide renders only when a promoter group >20% of
  the equity sleeve (`modules/group_concentration.py`).
- **MF pages:** two framework-aligned charts (3y record vs index; participation-in-falls vs the
  QFRA-1 category cutoff) — bars, never the banned capture scatter; fund Sell needs BOTH frameworks
  non-Hold; fund cards: LIC BAF class = scale/record framing, never a cushioning smear.
- **Cost slide:** scheme TER only — no Regular-drag / PMS "extra you pay" overlays.
- **Cut pages stay cut:** fund_overlap (folded into fund_actions as the index-sleeve replacement
  suggestion; AMC-concentration strip STAYS), seasonality, drawdown-history, staged-deployment,
  fee-compounding, tax-lot-aging, glossary.
- **Cover/dividers:** generative flow-art (`art.py`), two-tone "Portfolio Review" headline, text
  logo lockup on navy (never the white-box PNG on dark slides), divider mini-TOC + ghost numeral.
- Tax-inertia (fund units >5y = raised switch bar, structural-only; stocks exempt); commodity
  names carry the 10-15yr cycle read; "what would flip a Hold" type meta-text is banned.

## CEO-SWEEP FIXES BAKED IN (2026-07-26 — do not regress)
- `_reason_category` (azby_family): buckets scored by keyword-hit COUNT on negative_para first
  (rationale fallback), with a negation scrub (`no ... red flags` never trips forensic) and bare
  "growth" excluded (stat mentions like "PAT growth +156%" aren't a slowing-growth thesis).
- Commodity-cycle reversal suffix (sell_cards) applies to sector "Metals & Mining" ONLY —
  conglomerates/utilities in Oil&Gas/Power baskets must not get "metal price" language.
- tax rows: character from holding_years (>=1y → LTCG; REDEEM → "Mixed, lot-by-lot") — the old
  `action in ("Switch","Exit")` check never matched UPPERCASE codes, printing all-STCG.
- CoPilot CTA is OUT (spec F5 conservative default): cost slide carries a neutral "NEXT STEP"
  line, no product names client-side.
- Every fund is measured vs its OWN SEBI category benchmark (never one common index):
  large=N100, largemid=N250, **mid=NIFTY Midcap 150 TRI**, flexi=N500, multi=Multicap
  50:25:25, small=Smallcap 250, hybrid=N50 Hybrid Composite 65:35 (data layer:
  `data/azby_family.py` BENCH dict; `bench_label` carried per fund/scheme). MDD/worst-1yr
  are labeled COMMON 3-YEAR WINDOW everywhere (since-inception drawdowns across different
  launch dates are not a fair comparison — Principal ruling 2026-07-26).

## PENDING (Principal 2026-07-26, next time — do NOT implement without re-confirming)
`funds_equity.py`'s paired-bar chart currently shows each fund's own-benchmark CAGR
correctly in the underlying data, but the chart's visual legend just says "Its category
benchmark" generically — a reader can't tell WHICH benchmark applies to WHICH fund bar
from the graph alone (only the scope-tag/source text names it). Principal wants a
category-wise benchmark MAP visible directly in the graph (e.g., a per-bar label/tick
annotation, or a small legend table naming fund→benchmark) — not this build, add next time.

## SLIDEKIT PRIMITIVES THAT PREVENT REGRESSIONS
`clip_sentences` (whole sentences, decimal-safe), `clip_clause` (sentence/semicolon-only periods,
paren-balanced), `short_name` (word-drop, no mid-word chops), `callout_h` (text-hugging panel
heights), `scope_tag` (drops whole segments), anchors/hotspots/pagerefs (`resolve_links()` at save
— internal clickable cross-refs), render-time detell in `txt()` (em-dash→comma, genuine→clear,
→/≤/≥ → words since Bahnschrift lacks the glyphs). Chart law: **never `ax.legend()`** — direct
labels, `caption_above()`, or `chip_legend()`; NAVY = the one primary series; `halo()` behind
text that can land on fills.

## DATA FLOW
Equity calls/rationale come from `04_RND_LAB/STOCK_SCORECARD_750/results/pf_qual_*.json` +
`portfolio_quant.csv` (recheck audit trails live in `recheck_*` fields there). Fund calls come
from the Ionic MF desk frameworks (qfra1-rerun / qfra2-rerun skills) — the deck never invents MF
methodology. New client: copy `data/azby_family.py`, swap holdings/IPS.
