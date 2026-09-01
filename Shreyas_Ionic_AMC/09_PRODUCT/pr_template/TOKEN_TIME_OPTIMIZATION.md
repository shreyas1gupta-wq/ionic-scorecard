# Token/Time Optimization Review — pr_template NDPMS Deck Pipeline
(Analysis only, no code changed. Basis: engine.py, tiers.py, check_geometry.py/2.py,
render_preview.py, slidekit.py, 4 modules, ndpms-deck SKILL.md, git commits 03d3d87/6c8f39f.)

## 1. Permanently fixed — not a recurring cost for the next client

Confirmed by diffing `6c8f39f` (shared `modules/*.py`/`slidekit.py` code, not client data):

1. **No-IPS-on-file honesty gap** (`exec_summary.py`): used to assert a fabricated
   foreign-allocation target and a fake "avoidable fee" gap even with no IPS or reg_drag=0.
   Now branches on `ips_on_file`/`show_fee_row`/`show_switch_row` and prints honest fallback
   copy. Any future no-IPS or all-Direct client never re-triggers this.
2. **Trim-row mislabeling** (`priority_actions.py`): fund-exit cash was silently mislabeled as
   a stock-concentration trim whenever a book had zero Trim-rec equities (old leftover-math
   coincidentally matched). Now computed off the real cap breach, threaded through
   proceeds/tax/deployment — closes the whole bug class, not one instance.
3. **`short_name()` trailing-separator strand** (`slidekit.py`): truncation could leave "HDFC
   Floating Rate Debt -". Fixed generically (strips trailing `-`/`–`) — protects every future
   scheme/stock name, not just this fund.
4. **Footer-collision safety valves** (`tax_impact.py`, `data_notes.py`): `max_h`/valve
   constants were tuned to demo-length text and let real client text overlap the fixed
   `deck.source()` footer band (y=6.66). Valves now keyed to the actual footer y, not a guessed
   number. **This "tuned-for-demo, breaks-on-real-data" class was the single most expensive
   bug type this session hit** — only 2 of ~57 modules have been audited (see Rec #6).
5. **Raw snake_case leak** (`fund_book_scored.py`): `Dividend_Yield` now humanized — one
   instance of the broader "internal field name reaches client text" class.
6. **Client-specific tier variant idiom proved out** (`build_client_b.py`): register
   `ANANDREDDY_{TIER}` at runtime by copying/patching `T.TIERS[base]`, never touching shared
   `tiers.py`. Every future client with unusual slide-cut needs reuses this directly.

**Net effect:** none of bugs #1-5 costs QA-scan tokens again — the fix lives in shared code.
**Not yet closed:** the general safety-valve-tuned-to-demo-data class; only 2 of ~57 modules
with fixed-y layout math have been checked. One-time proactive sweep recommended (Rec #6).

---

## 2. Prioritized recommendations

### #1 — `tellscan.py` as a standing, versioned script (HIGH value, LOW effort)
Codify the ad hoc per-session text-scan into a script beside `check_geometry.py`, run
identically every build (spec in §3). This session's tell-scan was reinvented live from memory
against SKILL.md rules each time. A script converts that LLM-judgment pass into a ~2-second
deterministic gate. **Est. 1,000-3,000 tokens/iteration saved** (no LLM re-reading text to hunt
jargon) plus several minutes/iteration since it runs unattended before any PNG is opened.
**Effort:** small — half the term logic already exists as `_TELL_RE`/`_TAG_RE` in
`slidekit.txt()`; just needs a scan-and-report wrapper mirroring `check_geometry.py`'s CLI.

### #2 — Per-module render cache (MEDIUM-HIGH value, MEDIUM effort)
`engine.build()` re-imports and re-executes all ~57 modules every call — confirmed, `_load()`
does a fresh `importlib.import_module` + `m.render()` unconditionally, no cache layer exists.
Across 8 iterations touching ~2-5 modules each, ~45-50 of 57 renders/iteration were pure waste.
Rendering is deterministic Python (near-zero token cost), but wall-clock and downstream review
cost is real (feeds Rec #3). **Effort:** true dependency-tracking (module -> relevant ctx
subset) is hard since modules read arbitrary nested ctx keys; a pragmatic middle ground is a
PNG-level cache keyed on (module_id, full ctx hash, tier), invalidated only for modules named
in an explicit "changed" list supplied by the build script — far cheaper than real hashing and
captures most of the win.

### #3 — Diff-based visual QA (HIGH value, depends on #2 for full benefit)
`render_preview.py` writes `slide_NN.png` by fixed index; every slide is re-rasterized every
call regardless of whether its module/ctx changed. Since `engine.MODULES` order is fixed and
slide count only shifts when an optional module toggles, index-based diffing is feasible:
thread `engine.build()`'s existing `manifest` (`[(mod_id, n_slides), ...]`) through to
`render_preview.py` to get a module->slide-range map, then only re-open PNGs in ranges whose
module was in that iteration's changed set. **Savings:** this was the most expensive manual
step this session (reading ~82 PNGs x 8 iterations, potentially 600+ image reads). For
iterations 3-8 (2-5 modules changed each), this cuts image reads by roughly **80-90%**. Run one
full-deck scan near the end regardless, since cross-panel consistency needs the whole deck in
view. **Effort:** small-medium — emit manifest.json (data already exists), track "changed
modules since last iteration" (record what was edited, not auto-detect), then use the diff
before defaulting to "look at everything."

### #4 — Model-tier reassignment (MEDIUM value, LOW effort — a dispatch decision, not code)
- **Haiku-appropriate:** running the geometry/tellscan gates and summarizing JSON output into a
  punch list; mechanical field-wiring in `data/<client>.py` once a schema is given; running
  `pptx_to_pdf.py` and checking exit status; re-running `build_*.py` across tiers and reporting
  manifest slide counts.
- **Sonnet-appropriate:** module hardening design (deciding what honest fallback copy should
  say, as in `exec_summary.py`); root-causing geometry findings; cross-panel consistency checks
  (do these two numbers reconcile).
- **Opus/high-effort:** client-safe copy sign-off ("does this still lean with the call"),
  factual-accuracy review vs MF Dashboard/PIT data, final QA-LAW sign-off before shipping.
**Savings:** by this firm's own D-036 finding, Sonnet ties/beats Opus on review-type work at
1/10-1/15th cost; the same logic applied to mechanical steps here (geometry-summary, PDF
conversion, field-wiring) plausibly saves 60-80% of token cost on those specific steps with no
quality loss, since they're transcription of already-deterministic script output.
**Effort:** low — document as a short table in the ndpms-deck SKILL.md QA LAW section.

### #5 — Ctx-file placeholder linter, pre-build (LOW-MEDIUM value, LOW effort)
Several fixed bugs (TER placeholder, fabricated IPS target, zero-Trim mislabel) stem from a
client ctx field being missing, a flat placeholder, or structurally absent. A pre-build check
comparing client values against known demo placeholder constants (`azby_family.py`) — e.g. flag
every-TER==0.55 or foreign_target_pct matching the demo default exactly — catches these at
ctx-authoring time, not PNG-review time. **Savings:** would have caught ~2 of the 5 bug classes
one iteration earlier (~1/8 of this session's iteration cost). **Effort:** low, one checklist
script.

### #6 — Proactive sweep for safety-valve-tuned-to-demo bugs (MEDIUM value, MEDIUM effort)
Only `tax_impact.py`/`data_notes.py` were fixed, reactively. Read (not just grep — the bug is
about values, not patterns) every module's fixed-y layout constants (`max_h=`, `y + h >`, etc.)
against the real `deck.source()` footer y (6.66) in one batch pass. **Savings:** prevents this
exact class recurring module-by-module across future real clients, each recurrence otherwise
costing a full rebuild+rescan cycle. **Effort:** medium, single Sonnet-tier session across ~57
modules.

---

## 3. Draft `tellscan.py` spec (worked example for Rec #1)

```
tellscan.py — deterministic client-safe-copy scan for rendered NDPMS decks.
Usage: python tellscan.py out/DECK.pptx [--json out.json]
        python tellscan.py data/<client>.py   # scan raw ctx source too

def extract_texts(src) -> list[(location, text)]:
    # pptx: walk every text_frame shape per slide, like check_geometry.txt_of()
    # .py ctx file: extract string literals (ast.parse + Str/Constant nodes)

def scan(texts) -> list[dict]:
    # {"loc": location, "kind": <bucket>, "term": <matched>, "text": <ctx[:60]>}
```

**Term buckets** (from SKILL.md QA LAW §3 + this session's actual catches):
- `AI_TELL`: `—`, ` -- `, `genuinely`, `genuine`, `truly`, `robust`, `seamless`, `holistic`,
  `delve`, `boasts` (belt-and-suspenders on raw ctx strings; `txt()` only scrubs at render time).
- `RECOMMENDATION_LANGUAGE`: `\bBuy\b` as a call token (exclude "buy-side" etc.) — hard rule,
  never Buy.
- `INTERNAL_JARGON`: `SENTINEL`, `QFRA`, `QFRA-1/2`, `MERIT`, `pf_qual`, `AZBY` (should already
  be scrubbed to ABXY — flag any leak), and `ABXY` itself on a real-client deck (cross-check
  against client name).
- `DATA_QA_VOCAB` (CEO sweep 2026-07-26 class): `stale`, `does not reconcile`, `data feed`,
  `data cut`, `quant snapshot`, `data snapshot`, `Data Office`, `CoPilot`.
- `SOURCE_CITATIONS`: `screener.in`, `MF Dashboard`, `NSE bhavcopy`, bare `.csv`/`.xlsx`/`.json`
  filenames, team/analyst names (pull from `00_GOVERNANCE/TEAM_ROSTER.md` at scan time so new
  hires are auto-covered, not hardcoded).
- `SNAKE_CASE_FIELDS`: regex `^[a-z]+(_[a-z]+)+$` minus an explicit allowlist — catches the
  `Dividend_Yield`/`fcf_yield` class generically, not one string at a time.
- `SYNTHETIC_DEMO_LEAK`: `demo`, `synthetic`, `placeholder`, `illustrative` on any slide outside
  annexure/opportunity_set (the only contexts allowed to say "Illustrative").
- `GLYPH_HYGIENE`: `→`, `≤`, `≥` — Bahnschrift can't render these; catching it in ctx source
  (not just at render-time scrub) surfaces the underlying data-authoring bug instead of hiding it.

**Output contract:** mirror `check_geometry.py` — bucket counts, top-N examples, optional
`--json`; a clean "0 findings" line so it composes as a third gate alongside the two geometry
checkers. Must support both rendered-pptx scanning (what reaches the client) and raw ctx-source
scanning (SKILL.md: "the scrub can't rescue whole sentences of QA talk" — data files must be
clean at the source, not just patched at render time).
