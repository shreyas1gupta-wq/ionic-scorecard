# Audit — Fund-book verdict-flip cascade + layout fixes (2026-07-29)
Fresh skeptical re-check of the last 48h of changes (5 fund flips, fund_actions/tax_impact layout
fixes, None-safety fixes). Build re-run from scratch: `PR_SUFFIX=_audit1`, HNI_DEEP, 75 slides.
Output: `out/AnandReddy_HNI_DEEP_audit1.pptx`, previews in `out/preview_audit1/`.

## Findings, severity-ordered

### HIGH — fake "Fund score/Grade" for the 2 no-research placeholder funds (new, unflagged)
`data/client_b.py`'s `(0,0,0,0)` placeholder pattern (HDFC NIFTY 50 Index Fund, HDFC Floating
Rate Debt Fund — "no independent research run") was fixed at the source for `cagr3y`/`alpha_ann`/
`bench_cagr3y` (now `None`, correctly renders "n/a" everywhere). **But `qfra`/`merit` were never
covered by that fix**: line 457, `qfra = _qscore(f3 - b3, f1 - b1) if (f3 or f1) else 50` —
placeholder funds get a hardcoded neutral `qfra=50`, `merit="C"`. This renders as a real-looking
score in two places:
- `modules/fund_book_scored.py` (the MAIN fund-book table, slides 20 & 22, **not just the
  annexure**): "HDFC NIFTY 50 Index — Fund score 50/100, Grade C" and "HDFC Floating Rate Debt —
  50/100, Grade C" sit in the same table, same score-bar styling, as every genuinely-scored fund
  — directly under the slide's own banner **"the score is the input, the desk sets the verdict"**,
  which is false for these two rows (no score was actually computed; the Sell is pure portfolio
  construction, as the row's own rationale says).
- `modules/scheme_scorecards.py` (slide 64, HDFC Floating Rate Debt — the index fund is correctly
  excluded via `category != "passive"` so doesn't get this page at all): same "50/C" KPI, same
  half-filled score bar, immediately above text saying "Sell... not a concern with the scheme's
  mandate or management."
This is the exact bug class the Principal's 2026-07-28 ruling was written to kill ("downstream
code read literal 0 as a real finding") — it just resurfaced in a field (`qfra`/`merit`) the fix
never touched. Fix: default `qfra=None`/`merit=None` (or a dedicated "n/a" render path) for
`_no_research` funds, same treatment as the other three fields.

### HIGH — internal doc reference ("DATA_GAPS") leaks onto a real client slide
`data/client_b.py:427`, HDFC Overnight Fund's `structural_reason`: "...NOTE: the value of this
holding is MISSING from the client's statement, see DATA_GAPS." Renders **verbatim** on slide 65
(scheme scorecard, Annexure) of the real Client B deck. "DATA_GAPS" is an internal
end-of-file comment-section name, meaningless and unprofessional to a client. `tellscan.py`'s
buckets (INTERNAL_JARGON/DATA_QA_VOCAB) don't include this literal term, so both the automated
gate and this session's first `tellscan.py` pass on the built pptx (4 findings, all 3
previously-accepted) missed it — only the visual-QA render step (`render_preview.py` + actually
looking) caught it, confirming the SKILL.md QA LAW's own warning that gates are necessary but not
sufficient. Fix: reword to "...the value of this holding is missing from the client's statement,
pending confirmation" (drop the internal pointer), and consider adding `DATA_GAPS` to tellscan's
DATA_QA_VOCAB bucket as a standing catch.

### MEDIUM — tax_impact.py row-height floor: confirmed future overflow, quantified
`rowh = max(0.30, min(0.42, 3.0/len(rows)))` keeps the table's bottom edge clear of the y=5.5
callouts only while `len(rows) <= 10` (table bottom = `2.02+0.33+rowh*len(rows)`). At the CURRENT
real count (7 fund actions -> 8 rows incl. total), rowh=0.375, bottom=5.35 — clears the callouts by
0.15in (tight but fine, confirmed visually on slide 29, no overlap). The 0.30in floor stops
shrinking further once `len(rows)>10`, but row count keeps growing, so table height grows linearly
past that point:
| fund actions | rows | rowh | table bottom | vs y=5.5 |
|---|---|---|---|---|
| 9 | 10 | 0.300 | 5.35 | clear |
| **10** | **11** | **0.300** | **5.65** | **overlap** |
| 12 | 13 | 0.300 | 6.25 | overlap (worse) |
Exactly confirms the "OPEN" risk flagged in the 2026-07-29 journal entry. Not a live bug (today's
7 actions are safe), but the formula is not scale-invariant beyond n=9 — needs either a
`maxrows`+overflow-to-annexure fallback, or a floor that keeps shrinking (e.g. drop `fs` further /
cap at 8-9 visible rows with a "+N more" line) before a client with more debt/liquid holdings hits it.

### MEDIUM — fund_actions.py column layout: confirmed negative textbox height at n=13, no floor/pagination
Card height is unbounded below: `card_h = min(1.62, 4.3/rows_per_col - 0.12)`, and the reason-text
box is given height `card_h - 0.9` with **no floor**. Computed directly (UW=11.493in from
slidekit.py):
| n (non-Hold funds) | ncols | rows/col | card_h | reason-box height |
|---|---|---|---|---|
| 7 (today) | 3 | 3 | 1.31in | 0.41in (fine) |
| 9 | 3 | 3 | 1.31in | 0.41in |
| 12 | 3 | 4 | 0.96in | 0.06in (barely) |
| **13** | 3 | 5 | 0.74in | **-0.16in (negative)** |
| 20 | 3 | 7 | 0.49in | -0.41in |
Reproduced directly in python-pptx: `add_textbox(..., Inches(-0.16))` saves without error (stores a
negative-EMU height in the XML) — PowerPoint's handling of a negative-height textbox is undefined
and commonly renders as an overlap with the row above or a flipped/clipped box. The module never
adds a 4th column and never floors `card_h`, so this degrades silently, not gracefully, starting
exactly at the 13-fund threshold the task asked about. Today's real deck (n=7) is unaffected and
confirmed clean on slide 26. Fix: cap rows-per-column (e.g. paginate to a second slide, or add a
4th column) once card_h would drop the reason-box below a legible minimum (~0.35in).

### MEDIUM — funds_equity.py: `or 13.0` fallback re-introduces the "0 is falsy" bug class
Lines 42 and 83: `bv = [f.get("bench_cagr3y") or 13.0 for f in bfunds]` and
`d = f["cagr3y"] - (f.get("bench_cagr3y") or 13.0)`. Both `bfunds`/table rows are already filtered
to `cagr3y is not None` (correct, catches the real placeholder funds). But if any *included* fund
ever had a genuinely-computed `bench_cagr3y` of exactly `0.0` (a flat benchmark over 3y — unlikely
but not impossible), `or 13.0` would silently substitute a fabricated 13% comparison benchmark,
distorting both the paired-bar chart and the "vs BM" delta/color in the table. This is the identical
pattern (0 treated as "missing") the Principal's 2026-07-28 ruling explicitly fixed elsewhere in
this same file's sibling checks (`down_capture is not None`, line 39/58 use `is not None`
correctly). Currently dormant — no fund in this book has `bench_cagr3y == 0.0` — but should be
`is not None` for consistency and defense against a future client.

### LOW — stale comment in DATA_GAPS section (item 1 ask, confirmed)
`data/client_b.py` end-of-file DATA_GAPS #2 still reads "Real 3y/1y performance was still
verified (**Hold**), but value_inr is set to 0" for HDFC Overnight Fund — the verdict flipped to
Sell on 2026-07-29 and this comment was never updated. Internal-only, zero client-facing impact,
but exactly the "stale comment assuming the old state" pattern the task asked to hunt for.

### LOW — `_fmt()`'s negative-zero guard is looser than `_no_negzero()`, saved only by a data-layer invariant
`scheme_scorecards.py`'s `_no_negzero()` (`round(v,1)==0`) is correctly tight — it matches the 1dp
display precision it's used with, so it cannot mask a real negative that would read differently at
that same precision (verified: SBI Gilt's stored `alpha_ann` is already `round(f3-b3,1)`, i.e.
pre-rounded to 1dp at the data layer, so it collapses to literal `-0.0`, and `-0.0==0` is `True` in
Python — this is why the weaker `_fmt()` guard, `round(v,6)==0`, still happens to catch it today).
If a future value were ever hand-entered at higher precision (e.g. a literal `-0.04` typed
directly into `_RISK_BATTERY` instead of pre-rounded), `_fmt()`'s 6dp check would miss it and print
"-0.0%" again in the KPI strip (confirmed: `round(-0.03,6) != 0` but `f"{-0.03:+.1f}%"` still
prints "-0.0%"). Recommend tightening `_fmt()`'s guard to `round(v,1)==0` to match `_no_negzero()`
for defense-in-depth; not a live bug today.

### LOW (observational, not a defect) — Sell pill sits directly above a positive alpha KPI
Slide 57 (Aditya Birla Sun Life Regular Savings) shows a bold "+2.4%" under "Net alpha p.a." right
beside a red SELL pill, with the "not a performance call" explanation two panels below. Factually
correct and consistent with the fund_actions card's own language — just a layout ordering that
could read as contradictory on a fast skim. No fix required unless the Principal wants it changed.

## Area verdicts
1. **Verdict-flip cascade (`data/client_b.py`)** — CLEAN. All 7 Sell funds are correctly present
   in `_RISK_BATTERY`, `_CV`, `_AMC`; `proceeds`/`fund_action_val`/tax counts all use
   `action != "Hold"` and correctly sum all 7 (verified via `sum(1 for f in funds if
   f['action']!='Hold')` in `de_gap_note` and the flags text, both say "7"). One stale comment
   (LOW, above). The `(0,0,0,0)` placeholder detection is theoretically fragile (a real fund with
   exactly-zero 1y/3y returns on both fund and benchmark would falsely trigger it) but not
   currently manifesting — no fund in this book has that profile.
2. **fund_actions.py column fix** — CLEAN at today's n=7 (confirmed visually, slide 26). Breaks
   concretely and reproducibly at n=13 (negative textbox height); no pagination/floor exists beyond
   3 columns.
3. **tax_impact.py row-height fix** — CLEAN at today's n=7 (0.15in margin, confirmed visually,
   slide 29). Breaks concretely at 10 fund actions (11 rows); floor stops shrinking, rows keep
   growing.
4. **funds_hybrid/funds_equity/scheme_scorecards** — MOSTLY CLEAN. All 7 exits are visible
   somewhere (fund_actions + tax_impact always; 6 of 7 also get scorecard pages, index fund
   correctly skipped by design) — nothing vanishes. `funds_hybrid.py`'s `return 0` guard and
   None-safe sort key are both fine. Two real defects found: the qfra/merit fake-score bug (HIGH,
   above) and the `or 13.0` fallback (MEDIUM, above). `_no_negzero()`'s threshold is fine/tight.
5. **Gates + visual QA** — Build: 75 slides, 0 crashes. `check_geometry.py`: 0 findings.
   `check_geometry2.py`: 0 findings. `tellscan.py` on the pptx: 4 findings = exactly the 3
   previously-accepted false positives ("+0.0%" x2 on slide 59/SBI Gilt, "MERIT" slide 22, "genuine"
   slide 46) — no new automated-gate findings. `tellscan.py` on `data/client_b.py`: 286 findings,
   all expected raw-source noise per SKILL.md (citation preambles/snake_case field names that the
   render-time scrub already strips — confirmed clean at the pptx level). Visual QA surfaced the 2
   HIGH findings above, which no automated gate catches.
