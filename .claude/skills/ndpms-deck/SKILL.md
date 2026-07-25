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
   "the firm's fund-quality framework").
4. Principal sign-off before any client artifact ships.

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
