---
name: ndpms-deck
description: Build/modify the Ionic Wealth NDPMS portfolio-review deck from the pr_template engine — tiers (HNI_DEEP/STANDARD/RM_SIMPLE), modules, charts, QA gates and every Principal ruling that governs client-facing slides. Use for "build the client deck", "update the review ppt", template/module edits, or any NDPMS presentation ask.
---

# NDPMS Deck Engine (pr_template) — operating playbook (consolidated 2026-07-27)

**Home:** `Shreyas_Ionic_AMC/09_PRODUCT/pr_template/`. Config-driven module library:
`engine.py` (module registry + build), `tiers.py` (HNI_DEEP / STANDARD / RM_SIMPLE presets),
`slidekit.py` (Deck primitives), `modules/*.py` (~57 slide modules), `charts.py` → shared
`09_PRODUCT/scripts/chart_lib*.py`, `art.py` (generative cover/divider art), `data/azby_family.py`
(demo ctx; schema in its docstring). Build: `PR_SUFFIX=_vN python build_azby.py [TIER]` +
`build_master.py`. Outputs `out/`. If a deck errors with PermissionError it is OPEN in the
Principal's PowerPoint — bump PR_SUFFIX, never fight the lock.
**Optimization reference:** `TOKEN_TIME_OPTIMIZATION.md` — what's now permanently fixed vs still
a recurring cost, prioritized build-pipeline efficiency recommendations (per-module render cache,
diff-based visual QA, model-tier assignment). Read before a large multi-iteration rebuild session.

## THE QA LAW (non-negotiable, in order)
1. `render_preview.py <deck> <outdir>` (python-pptx→PIL, real fonts) and **LOOK at changed slides** —
   geometry checkers catch overlaps, not ugliness. No deck change ships unseen.
2. `check_geometry.py` AND `check_geometry2.py` (box + rendered-extent, z-order-aware) = 0 findings.
3. **`tellscan.py <deck.pptx>` = 0 findings** (standing script, 2026-07-27 — replaces the old
   ad hoc per-session re-derivation of this scan from memory). Buckets: AI writing tells
   (em-dash, "genuinely"/"robust"/"holistic"/etc.), 0 "Buy" as a recommendation, internal jargon
   (SENTINEL/QFRA/MERIT/pf_qual/AZBY/"quant-only, analyst view"/"Ratified Sell"/"One-time
   review"/"House decision" — client words: "watch-outs", "fund score /100", "grade", "the
   firm's fund-quality framework"), data-QA vocabulary ("stale", "does not reconcile", "data
   feed", "data cut", "data/quant snapshot", Data Office, CoPilot), source/analyst citations
   (screener.in, INDmoney, Groww, Paytm Money, Advisorkhoj, analyst names), raw snake_case field
   names, and "synthetic/demo/illustrative" language mislabeling REAL client data (only the
   annexure/opportunity_set pages that are genuinely synthetic proxies may say so). Also run
   `tellscan.py data/<client>.py` on the raw ctx source — slidekit.txt()'s render-time scrub
   can't rescue whole sentences of internal audit trail, so the DATA file must be clean at the
   source, not just patched at render time. A small false-positive rate is expected and fine
   (ordinary English "genuine"/"on merit" reads as a hit) — eyeball flagged lines like any other
   gate, don't chase the script to zero-tolerance on real words.
4. **Cross-panel consistency scan** (CEO sweep class of bugs): any two numbers on the same slide
   that a reader will assume are the same set MUST reconcile or be explicitly scoped
   (tax table=fund actions vs waterfall=equity plan; concentration_risk KPI vs holdings table
   rows = same basis: % of equity sleeve). Same-entity names identical across slides (short_name width
   ≥30 for scheme tables). A driver/tag must match the narrative beside it and the same call's
   rationale elsewhere in the deck.
5. Principal sign-off before any client artifact ships.

## FULL PIPELINE (real client, Apr/Oct cadence; auto-build wired in OPERATING_CALENDAR)
0. **Advisor intake (new — file upload to tier/scope decision, Principal 2026-07-27).** The
   instant a holdings file is uploaded, in the SAME turn: (a) launch the parallel-compute pass —
   `client_intake.py` match → `pf_qual_*.json` lookups per matched stock → `fund_ctx_adapter.py`
   QFRA-1/QFRA-2 verdicts per matched fund → sector/mcap/concentration/cost aggregates — all
   written to `client_ctx.json`/`exceptions.csv` on disk, and (b) ask the advisor up to 4 short
   questions: deck depth (**Detailed 60-100pg = HNI_DEEP** / **Medium 30-60pg = STANDARD** /
   **RM Light 15-30pg = RM_SIMPLE** — confirmed against real builds: HNI_DEEP real-client=82
   slides, STANDARD=40, RM_SIMPLE real-client=23; warn the advisor RM Light can occasionally
   print >30pg on a large book — pagination, not a preset bug, offer Medium instead of forcing
   the ceiling), first-review-vs-follow-up (unlocks `since_last_review` if meeting_history is
   supplied), anything to exclude/downplay (tax detail, methodology detail), and turnaround/PDF
   need. Do not wait on (b) to start (a) — they're independent; by the time the advisor answers,
   the expensive research is already on disk and only Python assembly (near-zero token cost)
   remains.
   Once deck depth is answered, ask ONE follow-up: **Recommended** (ship the tier's current
   preset from `tiers.py` as-is) or **Customize**. Customize shows the tier's live optional
   (Annexure) modules as a checklist, each tagged **(recommended)** when it's in that tier's
   `optional_on`; for RM_SIMPLE only, also show its `skip_core` modules as re-addable. Modules
   that are PARKED/CUT (see "Cut pages stay cut" below) are never listed as a customize option —
   they're retired, not a choice. Full design + a worked Medium-tier checklist example:
   `INTAKE_WORKFLOW_SPEC.md`.
1. **Intake** `09_PRODUCT/scripts/client_intake.py --holdings <CAS-extract.csv|xlsx> --profile
   <profile.json> --out <client_dir>` → client_ctx.json + exceptions.csv (unmatched rows go to
   the RM, never dropped/fabricated). Profile JSON (template via --emit-template) carries the 4
   personalization blocks: goals/timelines, holding ages & costs, family structure, meeting
   history. NSDL CAS PDF parser slots in when a sample statement arrives.
2. **Fund calls** `09_PRODUCT/scripts/fund_ctx_adapter.py` — QFRA-2 (QFRA2_current.csv, 40
   curated funds only: held funds outside it = honest gap "needs a QFRA-2 scoring run") +
   QFRA-1 (mf_capture_recomm.compute_category on MF Dashboard.xlsx; returns (df, anchor);
   FN=6M down-capture, HC=6M total capture); merged by the dual-framework rule (Sell needs
   BOTH frameworks independently at Sell — a BUY/high-score on either side VETOES the Sell;
   disagreement → Hold, flagged. The old "both non-Hold" wording is wrong, never use it —
   it's literally satisfied by BUY+Sell). Sell-derivation rule is UNVALIDATED/unbacktested —
   see NEXT_WEEK_QUEUE.md item 1 before treating any new Sell as standing method.
3. **Build** `PR_SUFFIX=_vN python build_azby.py [TIER]`; `since_last_review` module renders
   only when profile has meeting_history.
4. **Gates** (QA LAW above). 5. **PDF — ON REQUEST ONLY (Principal 2026-07-28, permanent):** do
   NOT auto-run `pptx_to_pdf.py` after every rebuild; ask at the end of the turn whether the
   advisor wants PPTX, PDF, or both, and only convert if PDF is wanted. `09_PRODUCT/scripts/
   pptx_to_pdf.py <deck.pptx>` — LibreOffice 26.2.5 user-local at %LOCALAPPDATA%\Apps\LibreOffice
   (msiexec /a extract, no admin; version-discovery downloader in 99_OPS if it ever needs a
   reinstall).
6. **Publish** to `09_PRODUCT/reports/` with client-facing names (current CEO set:
   NDPMS_Portfolio_Review_ABXY_HNI.pptx/.pdf + ..._RM_Lite.pptx/.pdf), DRAFT until sign-off.

## PRINCIPAL RULINGS BAKED INTO THE TEMPLATE (do not regress)
- **Vocabulary:** Sell/Trim/Hold only, never Buy; no buy recommendations anywhere; proceeds PARK
  in cash. **2026-07-29 (permanent, all tiers):** `opportunity_set.py` and `deployment.py` are
  CUT entirely, not just annexure-parked — this deck only ever sells/holds, never recommends
  buying with freed cash, so any page implying a redeployment/"after" mix (including the old
  "Illustrative" opportunity-set mix) is out of scope and inherently biased (a cash-heavier
  "after" always looks safer by construction). Same reasoning cut `annex_mcap_migration.py`,
  `annex_liquidity_ladder.py`, and `annex_returns_quilt.py` the same day — see SESSION_JOURNAL
  2026-07-29 for the full list and each one's specific tell.
- **Correlation/overlap matrices are capped, never shown in full (2026-07-29, permanent):** a
  fund-vs-fund or holding-vs-holding matrix stops being readable well before a 30-item book.
  `annex_correlation.py` (direct-equity) caps to the **top 15** by weight; `scheme_overlap_full.py`
  (fund-vs-fund) caps to the **top 10** by weight — the Principal's explicit stocks-vs-funds
  split. Both disclose the cap via `scope_tag` when the real count exceeds it ("Top N of M...").
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
- **MF pages:** two framework-aligned charts (3y record vs index; participation-in-falls vs the
  QFRA-1 category cutoff) — bars, never the banned capture scatter; fund Sell needs BOTH frameworks
  non-Hold; fund cards: LIC BAF class = scale/record framing, never a cushioning smear.
- **Cost slide:** CUT entirely (Principal 2026-07-27, permanent) — was scheme-TER-only with no
  Regular-drag/PMS overlays before the cut; `modules/cost.py` stays in the library, renders
  nowhere by default (`engine.py` core=False).
- **IPS page RESTORED, v2 (Principal 2026-07-28, permanent, reverses the 2026-07-27 cut):**
  `ips_summary.py` rebuilt with richer parameter coverage (portfolio/equity/fixed-income/
  commodities level — single-scheme/AMC/locked-in/cash caps, market-cap bands, thematic/
  unlisted/international-equity caps, fixed-income credit-quality bands + duration cap, gold/
  silver bands), sectioned as 4 mini-tables in the house navy/gold rail-and-pill style, never a
  plain corporate table. "Current" is ALWAYS computed live from ctx (never client-authored) —
  including a look-through Equity/Debt split (`_lookthrough_mix()`, direct equity + equity-
  oriented fund categories) that is materially different from the direct-equity-only figure used
  elsewhere in the deck for a fund-heavy client. Ideal shows "TBD" and Fit shows "Pending"
  (never a fabricated target) for any parameter with no bespoke IPS on file yet — the page still
  shows the client's real position on every parameter so a first review has a baseline. The old
  cut was about the THIN pre-v2 version reading as broken with no bespoke IPS, not the concept.
- **`opportunity_set.py`'s "Illustrative" mix is IPS-driven, not a fixed constant (2026-07-28):**
  "Today" reuses `ips_summary._lookthrough_mix()`; "Illustrative" derives from the client's own
  `ips["alloc_bands"]`/`foreign_target_pct`/`gold_band_pct` targets when `ips["on_file"]` is
  True, falling back to a generic diversification example only when no bespoke IPS exists.
- **Cut pages stay cut:** fund_overlap (folded into fund_actions as the index-sleeve replacement
  suggestion; AMC-concentration strip STAYS), seasonality, drawdown-history, staged-deployment,
  fee-compounding, tax-lot-aging, glossary, **group_concentration** (promoter-group concentration
  slide — denominator bug + promoter-map coverage gap fixed 2026-07-28 ahead of any future
  resurrection, per audit recommendation, but still not wired into any tier), **cost**, and
  **factor_profile** ("index/factor fund analysis" — its factor tilts are an
  approximated/illustrative proxy, not a real regression; one of the "pages we're not sure of"),
  and **annex_currency_geo** ("geography analysis"). All modules stay in the library
  (`engine.py` core=False / never in any tier's `optional_on`), rendered nowhere by default —
  same convention as fund_overlap/fund_quality_alloc.
- **Repositioned into the main deck, not the annexure (2026-07-27, permanent):**
  `scheme_overlap_full` ("fund overlap") moved from Annexure into Section 3 The Fund Book,
  positioned right before `fund_actions` (supporting evidence for the action call, not back
  matter); `growth_projection` moved from Annexure into Section 4 Recommendations, positioned
  right after `priority_actions` ("if you follow our recommendations, here's where this could
  go"). Both modules' own `deck.content(...)` section tags were updated to match — a module's
  displayed section header must always agree with its `engine.MODULES` canonical entry.
- **Growth-projection assumption (2026-07-27, permanent):** the projection cone's expected
  return/volatility (`mu`/`sigma`) is no longer a flat 12%/14% constant. `_derive_mu_sigma()` in
  `modules/growth_projection.py` computes both from THIS book's real holdings — equity sleeve:
  holdings-weighted `growth_pct` (analyst-ratified forward EPS growth) plus a disclosed
  dividend-yield proxy; fund sleeve: holdings-weighted real `cagr3y`; blended by the book's
  eq/mf split. Volatility uses a documented composition proxy (large-cap share, top-10
  concentration) since no per-holding return series exists in ctx yet (fund NAV history caps at
  18 monthly points firm-wide — see root CLAUDE.md DATA LANDMINES). Pure Python, zero LLM cost,
  identical formula every build — never revert to a fixed assumed rate.
- **Factor-fund Sell/Hold rule (2026-07-27, permanent):** a factor ETF/index fund held directly
  defaults to **Hold**, not a blanket "consolidate all passive/factor exposure" Sell — UNLESS it
  is specifically a **Nifty 200 Momentum 30** factor fund, which stays **Sell** (momentum carries
  a documented regime-dependent failure mode the house already gates elsewhere — see
  ALPHA_RANKER valuation-band rule in memory). Plain, non-factor index funds (e.g. a vanilla
  Nifty 50 index fund) are unaffected and can still be Sold on ordinary
  consolidation/cost-hygiene grounds. Applies to every future client, not a one-off.
- **"Redeem-to-Direct" displays as "Switch" (2026-07-27, permanent):** the internal verdict
  code/color-style key stays `Redeem-to-Direct` (unchanged, used for `REC_STYLE` lookups and
  `_ORDER`/`_KIND` dicts) — only the CLIENT-FACING display text changes, via each module's
  `VDISP` mapping (`funds_equity.py`, `funds_hybrid.py`, `fund_book_scored.py`) and any inline
  prose that named it. Known open risk, flagged not silently resolved: this collides visually
  with the pre-existing, semantically different `Switch` verdict (move to a different/better
  fund in the same category) — both now show an identical "Switch" pill even though one means
  "same fund, cheaper plan" and the other means "different fund." Revisit if a client ever holds
  both action types in one deck and it reads as confusing; no fund in the Anand Reddy book
  triggered this collision.
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
