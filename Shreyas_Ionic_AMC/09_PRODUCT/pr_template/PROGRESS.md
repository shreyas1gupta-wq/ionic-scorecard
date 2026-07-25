# PR Template v9 — ✅ COMPLETE (2026-07-25)

**Status: DONE.** All 38 modules render; AZBY demo built across 3 tiers, validated (no blank/off-canvas slides, SEBI-clean vocabulary, tier system proven).
- `out/AZBY_Family_HNI_DEEP.pptx` — 61 slides (2.0 MB)
- `out/AZBY_Family_STANDARD.pptx` — 40 slides (1.4 MB)
- `out/AZBY_Family_RM_SIMPLE.pptx` — 31 slides (0.6 MB)
- **`out/AZBY_MASTER_LIBRARY.pptx` — 89 slides (3.4 MB): ALL 38 template slides + the 24-chart gallery + a style/component reference (palette, pills, score bars, callouts, table/KPI kit). One file, everything.** Build: `python build_master.py`.
**Run:** `cd pr_template && PYTHONIOENCODING=utf-8 <python> build_azby.py [TIER ...]` (client decks) or `build_master.py` (master library). Real client: swap `data/azby_family.py` ctx for the client's holdings + a `client_ips.yaml`; keep advisory-owned slots (§5 of SPEC) empty until advisory fills them. PDF export needs LibreOffice/PowerPoint (not installed here).

---
# (build log below)
# PR Template v9 — build PROGRESS

**Goal:** turn the bespoke v8 NDPMS deck into a config-driven, 3-tier template engine (HNI_DEEP / STANDARD / RM_SIMPLE), extend the chart library, and ship a working synthetic AZBY Family demo across tiers. Spec = `TEMPLATE_V9_SPEC.md`.

## DONE
- [x] Scouted v8 (57 slides), chart_lib (17 charts), ionic_style, skill contract.
- [x] 5-lens redesign workflow + critic → 34-module catalog, MF/hybrid methodology, 29-core order, all F1-F18 mapped. (wf_0961e270-b0e; digest in scratchpad/v9_lens_digest.txt + v9_critic.txt.)
- [x] `TEMPLATE_V9_SPEC.md` authored (module order, tiers, visual library, data contracts, advisory slots, AZBY demo def).

## DONE (foundation, all tested)
- [x] chart_lib_ext.py — 7 new charts (capture_scatter, drawdown_curve, rolling_return_band, fee_stack, tax_bridge, quality_alloc_quadrant, over_under_bar). Smoke-tested OK.
- [x] data/azby_family.py — synthetic AZBY book: 38 real-ticker stocks (real scores, 8 Sell/30 Hold), 9 synthetic-NAV funds incl. LIC underperformers (up/down capture story: LIC Flexi 96/118, closet-indexer ~100/100, ICICI cost-switch, PPFAS 107/71 Hold), IPS + deployment + overlap. Normalised eq60/mf34/cash6, top10 42%. Tested.
- [x] slidekit.py (Deck class: content/table/kpi_strip/score_bar/callout/scope_tag/score_band/section_divider/pic/pill) + engine.py (registry, canonical order, graceful skip) + tiers.py (HNI_DEEP/STANDARD/RM_SIMPLE) + charts.py bridge + build_azby.py. Smoke render VERIFIED (cover+dividers+disclaimer, saves pptx, missing modules skip).

## PAUSED FOR LAPTOP RESTART (2026-07-25 ~13:44) — RESUME HERE
- **All 35 module renderers ARE WRITTEN to `modules/`** (front/xray/equity/funds/recs/annexe sections all delivered by the parallel build). `out/AZBY_Family_STANDARD.pptx` already rendered (~48KB) — the integrator was mid-run when we paused.
- Workflow wf_cad8524e-560 was STOPPED (not orphaned). Section-agent + integrator work up to the stop is cached.

### RESUME — 3 quick steps next session:
1. **Render all 3 tiers directly** (fastest — modules are on disk):
   `cd .../09_PRODUCT/pr_template && PYTHONIOENCODING=utf-8 <python> build_azby.py`
   → produces out/AZBY_Family_{HNI_DEEP,STANDARD,RM_SIMPLE}.pptx. Read the [ERR]/[skip] log.
2. **Heal any [ERR] modules** — Read modules/<id>.py + slidekit.py, fix API misuse/overflow/ctx-key bugs, re-run. (Self-heal loop; the integrator was doing exactly this.)
3. **Verify** HNI_DEEP > STANDARD > RM_SIMPLE slide counts (tier system), decks open, then optionally re-run the layout critique. To resume the FULL workflow incl. Opus critique instead:
   `Workflow({scriptPath: "<...>/ndpms-v9-module-build-wf_cad8524e-560.js", resumeFromRunId: "wf_cad8524e-560"})` — cached section agents replay instantly; only integrator+critique re-run.
- Then: PDF export, journal, present the 3 decks. Spec = TEMPLATE_V9_SPEC.md is complete and authoritative.

## NEW FILES (engine)
`pr_template/{slidekit,engine,tiers,charts,build_azby}.py`, `pr_template/data/azby_family.py`, `pr_template/modules/*.py`, `scripts/chart_lib_ext.py`. Out decks → `pr_template/out/AZBY_Family_{HNI_DEEP,STANDARD,RM_SIMPLE}.pptx`.

## KEY DECISIONS BAKED IN
- Fund scoring CONSUMES QFRA 2.0 (qfra2-rerun skill) — never re-derive. For AZBY demo, synthesize NAV series → compute capture/Sortino/maxDD/worst-year locally (self-contained demo).
- Advisory-owned content (IPS wording, benchmark def, core-satellite, risk grid, deployment rationale, tax rates) = SLOT + data contract; illustrative drafts tagged [OPINION]/[ILLUSTRATIVE], never shipped as firm-ratified on a real deck. AZBY (fictional) may carry illustrative authored text.
- Score discipline (F13): every score paired with a human read; score-position band on exactly 3 core slides; no book-level weighted score to client.
- SEBI: Sell/Trim/Hold (equity), Hold/Trim/Switch/Redeem-to-Direct/Exit (funds) — never Buy.
- Tier guardrails: exec counts == book counts (assert); suppress dangling annexure cross-refs in light tiers; disclaimer always-on.

## PATHS
- Engine dir: `Shreyas_Ionic_AMC/09_PRODUCT/pr_template/`
- Charts: `Shreyas_Ionic_AMC/09_PRODUCT/scripts/chart_lib.py` (extend) ; style `ionic_style.py`
- Scored data: `Shreyas_Ionic_AMC/04_RND_LAB/STOCK_SCORECARD_750/results/{portfolio_quant.csv, pf_qual_*.json}`
- Python: `C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe` (PYTHONIOENCODING=utf-8)
