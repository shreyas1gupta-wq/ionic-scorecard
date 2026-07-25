# NDPMS Portfolio-Review Template Engine (v9)

**The analysts' standing PPT toolkit** — build a full Ionic-styled client review in one command instead of hand-making decks. One codebase, three audience tiers, ~56 slide modules, 30+ chart types, all in the house style with the no-AI-tell and SEBI guardrails baked in.

## Quick start
```
cd Shreyas_Ionic_AMC/09_PRODUCT/pr_template
python build_azby.py                 # demo client, all 3 tiers -> out/ABXY_Family_*.pptx
python build_azby.py HNI_DEEP        # one tier only
python build_master.py               # out/NDPMS_TEMPLATE_MASTER.pptx (every template + chart gallery + style kit)
```
(Use the firm python: `C:\Users\<user>\AppData\Local\Python\pythoncore-3.14-64\python.exe`, `PYTHONIOENCODING=utf-8`.)

## For a real client
1. Copy `data/azby_family.py` → `data/<client>.py`; replace holdings/schemes/IPS with the client's (ctx schema is in the module docstring). Equity scores/rationale come from the scored universe (`04_RND_LAB/STOCK_SCORECARD_750/results`).
2. Leave **advisory-owned slots** empty until supplied (IPS wording, benchmark definition, core-satellite text, risk-profile bands, deployment rationale, tax rates) — see `TEMPLATE_V9_SPEC.md` §5. Never fabricate them on a live deck.
3. Point `build_azby.py` at the new dataset, pick the tier, build, then run the checks below.
4. **No client deliverable ships without Principal sign-off** (skill: `agentic-fund-manager`).

## Tiers (same numbers, different audience)
- `HNI_DEEP` — everything incl. the 28-slide annexure (per-name sell cards, per-scheme scorecards, 18 illustration slides)
- `STANDARD` — core + selected annexure
- `RM_SIMPLE` — plain-language core for RM-led reviews

## Quality gates (run before shipping)
```
python check_geometry.py out/<deck>.pptx      # overlaps / off-slide / overflow — must be 0 findings
python ../..\..\.claude/skills/style-lint/scripts/lint.py <extracted-text>   # zero P0, zero em-dash
```
NOTE: OneDrive dehydrates files — copy the pptx to a local temp path before opening with python-pptx.

## Layout of the engine
`slidekit.py` (Deck: house primitives — content header, standfirst, tables w/ totals, KPI strip, pills, score bar, callouts, pullquote, dividers) · `engine.py` (module registry + build) · `tiers.py` (presets) · `charts.py` + `../scripts/chart_lib*.py` + `chart_ext_[ab].py` (all charts) · `modules/*.py` (one `render(deck, ctx, tier)` per slide) · `gallery.py` (chart gallery + style reference for the master file).

House rules enforced in code: Sell/Trim/Hold (equity) & Hold/Trim/Switch/Redeem-to-Direct/Exit (funds), never Buy · escalated names render "Under review" · every score paired with a human read · em-dashes/banned tells scrubbed at render time · every synthetic figure tagged [ILLUSTRATIVE] with a source line.

Spec: `TEMPLATE_V9_SPEC.md` · Build log: `PROGRESS.md`
