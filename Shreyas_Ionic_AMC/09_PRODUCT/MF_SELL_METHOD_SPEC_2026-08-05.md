# MF sell method — spec v1 (non-linear, gated, escalating)
**Principal rulings 2026-08-05.** Written before coding, so the method is agreed rather than
discovered in a diff. Covers FM comments #3, #6, #7, #9, #17, #19, #21, #25.

Design rulings taken:
- **Non-linear**, not a linear weighted sum (#6). Rules flexible, with AI-analyst and FM discretion,
  escalating to a human analyst when it cannot resolve.
- **Discretion is one-directional** — it may veto or soften an action, never manufacture one. Same
  asymmetry as QFRA-2's Stage-2 gate, and the reason judgment does not become invention.
- **Equity counted gross**, footnote not flag (#1).
- **Risk-free 6.5%** unless supplied per run (#8).

---

## Why not a linear weighted sum

A weighted average lets a good score on one axis pay for a disqualifying score on another. A fund
with a broken risk profile but a large unrealised gain averages out to "hold", which is the wrong
answer arrived at arithmetically. Both QFRA-1 and QFRA-2 already avoid this — each uses **gates plus
ranks**, not a single linear blend — and this method follows the same shape.

## Layer 1 — HARD GATES. Binary, no compensation, checked first.

| Gate | Action | Source |
|---|---|---|
| Debt bought before 1-Apr-2023 | **Never sell for optimisation or rebalancing.** A credit or governance event still overrides | FM #21 + Finance Act 2023 grandfathering |
| Track record under 7 months | **No View.** No score is emitted at all | existing firm floor |
| Block as-of staler than threshold for a material holding | **No View + escalate.** Do not print a number we cannot date | `check_freshness.py`; 40.5% of ACE rows are behind the file's own month-end |
| Manual override / avoid-list hit | Forced action, override reason recorded | FM #18, #23 |

Gates run before scoring. A gated holding never receives a score, because a score would imply an
assessment we did not make.

## Layer 2 — CONTINUOUS SCORE with saturating, non-linear responses

Five inputs (FM #17), each mapped through a response curve chosen for how the quantity actually
behaves, not through a flat weight:

| Input | Curve | Why that shape |
|---|---|---|
| **Performance** vs its own blended benchmark | Sigmoid | Small under- or out-performance should not move a decision; large gaps should saturate. A fund 20% behind is not "twice as sell-worthy" as one 10% behind — both are already decisive |
| **Risk-adjusted return** (Sortino / IR / Sharpe, rf 6.5%) | Sigmoid **with a floor that becomes a gate** | Below a hard bar this stops being a score and becomes a disqualification |
| **IPS gap** | Piecewise: flat inside the band, steeply rising outside | Genuinely non-linear. Inside the band there is no problem at all; 1pp outside is minor; 10pp outside is a breach. A linear term would penalise a compliant fund |
| **Tax position** | **Asymmetric**, not symmetric | LTCG mildly reduces sell urgency. **STCG reduces it strongly — an STCG holding is a low-priority sell, never suppressed entirely** (FM #19) |
| **Concentration** | Convex, rising faster than linearly | Matches the house guidance already in the stock scorecard: 5-10% acceptable, above 10% a concern, above 20% extreme |

**Underperformance is scored explicitly**, not just as the negative tail of performance (FM #9):
persistent shortfall against a fund's *own* blended benchmark across consecutive windows is its own
term, because a fund that is reliably 2% behind is a different problem from one that is violently
behind once.

## Layer 3 — DISCRETION BAND

Scores in the middle band do **not** auto-decide. They route to the AI analyst for a reasoned call,
which the FM may override. One-directional: this layer can veto or soften a sell, never create one.
Every discretionary call records its reason, so the next review can see why.

## Layer 4 — ESCALATION (the standing rule)

Where discretion cannot resolve it, escalate to the human analyst **at the end**, once everything
resolvable is resolved, in this shape: the situation and how much of the book it affects; our view
with its evidence; the counter-view argued honestly; and the specific datum or ruling that would
settle it. Recorded in `.claude/skills/ionic-wealth-complete/SKILL.md` as a firm-wide standing rule.

---

## Churn rule (FM #3, #25) — Principal: implement

- Compute total churn as **% of portfolio value** recommended for sale.
- **Churn ≤ 20%** → present every sell as a single list, unsegmented.
- **Churn > 20%** → segregate into **high priority** and **low priority**, without degrading the
  existing slide format. Implementation: the priority split becomes a **grouping within the existing
  sell table** (a subhead row and a priority column), not a new page and not a different layout — the
  deck's row-pagination and column widths are unchanged.
- Priority is assigned from the Layer-2 score, with two overrides: **STCG holdings are always low
  priority** (FM #19), and any gate-forced action is always high priority.
- The 20% figure is the FM's own (comment 25) and is recorded as his, not derived.

## Tail measure (FM #7, approved with latitude to improve)

1. **Common 3-year window** for every fund, so comparison is valid by construction rather than by
   coincidence of launch dates.
2. **Expected shortfall at 90%** — mean of the worst decile of rolling 1-month returns. This is the
   Principal's "extreme 10th percentile", averaged over roughly 70 observations rather than resting
   on a single worst-drawdown reading, which is one noisy point.
3. **Regime-coverage test.** Does the fund's history actually span a stress episode — Mar-2020,
   Jan-2018 small-cap, Sep-2018 IL&FS, Oct-2021 to Jun-2022? If not, the estimate is extrapolation
   and is labelled as such. This is the Principal's pre-COVID versus post-COVID point made explicit
   instead of buried in a number.
4. **Safety factor.** The Principal proposed ~2.5x. **To be validated, not assumed:** compute ES90
   over a calm 3-year window for the benchmark and compare with the realised COVID drawdown to see
   what multiple the ratio actually is. If it lands near 2.5 the factor is evidence-backed. Until
   that check runs, no 2.5x number is quoted as validated.
5. **Category-relative**, so a small-cap fund is not penalised for being a small-cap fund.

## Hybrid scoring (FM #9, #20) — flexible benchmark

The reason hybrids cannot be scored against one category benchmark: Balanced Advantage funds range
from **52.8% to 90.4% equity**, so a single benchmark punishes whichever manager was correctly
defensive.

- Build **each fund its own blended benchmark** from its **trailing 3-year average disclosed mix**:
  (avg equity% x equity TRI) + (avg debt% x debt index) + (avg others% x proxy).
- **Degradation path, stated honestly.** ACE supplies a month-end snapshot, so a 3-year average needs
  36 monthly extracts. Until they accumulate, the benchmark is built from the **latest snapshot** and
  labelled "current-mix" rather than "3-year-average mix". The method gets more accurate every month
  instead of pretending to be right on the first file.
- Judge on: outperformance versus that blended benchmark; **down-capture** against it (from QFRA-2);
  **6-month total capture** (from QFRA-1); persistent underperformance; and **suitability** — does the
  fund's actual disclosed mix fit this client's IPS bands?
- Then the same five inputs and the same four layers as above.

---

## Open, and deliberately not invented
- **Layer-2 curve parameters and the discretion band's edges.** Shapes are set above; the numbers need
  either the FM's thresholds or a backtest. Nothing ships with invented cut-offs.
- **Whether this scoring replaces the fund frameworks for client work or sits on top of them.** My
  recommendation remains **on top**: the originating leg keeps its 906-formation evidence and this
  score decides priority among sells rather than manufacturing them.
- **House view on duration and credit** (FM #10) and the **client's seven IPS aspects** (FM #12) —
  both awaiting documents.

---

## BUILT 2026-08-06 (FM #17/#20/#1, Vikram Shah) — Layer 2-4, hybrid blended benchmark, core/satellite

Principal ruled the same day: #17 "create it and show me best way logically we cannot backtest";
#20 hybrid "you create method basis adjusted bm and best possible"; #1 core/satellite confirmed
70/30 flexible **with midcap moved into core** (correcting an earlier proposal). #15 (risk-free
6.5%, ideal 3y window) and #16 (leave a clean tail-risk interface, no hardcoded number) both apply
directly to this build. This section is the as-built record; the layer descriptions above are the
architecture that was agreed *before* coding and are left unedited.

### Code
| File | What it is |
|---|---|
| `pr_template/lib/mf_sell_score.py` | Layer 2 (5-axis saturating score), Layer 3 (discretion, one-directional, enforced by raising `ValueError` on any attempt to raise a band, not just documented), Layer 4 (`build_escalation()` — situation/our view/counter-view/what-would-settle-it). `score_all(ctx)` runs it over every un-gated fund. |
| `pr_template/lib/mf_sell_gates.py` (extended) | Added the Layer-1 gate row this file's own docstring had left open: `load_restrictions()` (Excel-or-nil, FM #18/#23), `check_avoid_list()` (analyst-callback-or-nil, FM #18/#23), `apply_manual_override_gate()`, and `refine_priority_with_score()` — a one-directional (softens only) opt-in link to the new score. `apply_to()` gained two optional kwargs with nil defaults; every existing caller (`data/azby_family.py`) is unaffected — verified by re-running its build and the pre-existing `scripts/test_fund_matching.py`. |
| `pr_template/lib/hybrid_benchmark.py` | Per-fund blended benchmark (#20) — see below. |
| `pr_template/lib/core_satellite.py` | Fund-sleeve core/satellite classifier + 70/30 guidance readout (#1). |
| `pr_template/lib/test_mf_sell_score.py`, `test_hybrid_benchmark.py`, `test_core_satellite.py` | Plain assert-based unit tests (house convention, see `scripts/test_fund_matching.py`) — 60+ checks, all passing. `Run: python test_<name>.py` from `pr_template/lib/`. |
| `09_PRODUCT/scripts/mf_sell_score_sensitivity.py` | The sensitivity sweep — see table below. Writes `pr_template/out/mf_sell_score_sensitivity.csv`. |

### Layer 2 — five axes, combined by MAX (not sum/mean), plus a tax damper
The spec above rejects a linear weighted sum at the *methodology* level (a good score paying for a
disqualifying one). A plain average of five saturating axis-scores would reintroduce exactly that
compensation one level down — so the axes combine by **MAX**: the single most concerning axis
decides the score, generalising the risk-adjusted-return row's own "floor becomes a gate" rule to
every axis. Tax position is **not** a sixth max-axis (it isn't evidence the fund is bad, it's a
cost-of-acting modifier) — it damps the combined result instead.

| Axis | Curve | Parameter(s) | Justifying sentence |
|---|---|---|---|
| Performance vs blended benchmark | Sigmoid | `PERF_GAP_MIDPOINT_PP=8.0`, `PERF_GAP_STEEPNESS=0.30` | Midpoint placed at the middle of the spec's own illustrative "10% mild / 20% decisive" range — **documented default**, not derived; no house number exists yet. |
| Risk-adjusted return (Sortino) | Sigmoid, floor-becomes-gate | `SORTINO_FLOOR=0.0`, `SORTINO_COMFORTABLE=0.5` | Floor is principled: a Sortino ≤ 0 means the fund did worse than doing nothing (the risk-free rate, #15) on its own downside-risk terms. Comfortable=0.5 is a market **convention** [OPINION], not house-derived. |
| IPS gap | Piecewise flat-then-quadratic, attributed to the equity-oriented side only | `IPS_GAP_SATURATE_PP=10.0` | One quadratic through the spec's own two anchors ("1pp outside is minor, 10pp is a breach") reproduces both in a single formula. No IPS on file → axis = 0 (ruling #18/#23's nil-restriction pattern applied consistently). |
| Concentration | Convex, two segments + saturating tail | `CONC_CONCERN_PP=10`, `CONC_EXTREME_PP=20`, scores 15/70 at those anchors | Anchors **are** the existing house guidance (5-10% acceptable / >10% concern / >20% extreme) verbatim — not invented. The curve *between* the anchors is this module's own interpolation, and is the part open to argument. |
| Persistent underperformance | Fraction of horizons behind (≥2 needed) | `PERSISTENCE_MIN_HORIZONS=2` | One data point cannot demonstrate a pattern by definition. [INFERENCE flagged in code]: ACE's 1Y/3Y/5Y trailing figures from one snapshot are not truly independent windows — weaker than rolling history, still real, not fabricated. **Field this axis needs (`fund['horizon_vs_bench']`) does not exist in any ctx-builder yet** — axis reports a gap on every fund today. |
| Tax position (damper, not an axis) | Asymmetric multiplier, floored | `TAX_DAMPING_LTCG=0.92`, `_STCG=0.70`, `_UNKNOWN=1.00`, `_FLOOR=15.0` | "LTCG mildly reduces, STCG strongly reduces, never to zero" (FM #19) taken literally: two damping strengths plus a numeric floor. Honesty note in the code: at today's other defaults the floor cannot actually bind (45×0.70=31.5>15) — it's a backstop for future tuning, proven live in the tests under a perturbed config, not an active constraint today. |
| Tail risk (FM #16) | — | `TAIL_SAFETY_FACTOR=None` | **Deliberately inert.** Guarded import of `lib.tail_risk.es90()`; absence or an unset safety factor both degrade to "axis unavailable," never a guessed ES90 or multiple. |

Discretion band: `DISCRETION_LOW=45.0`, `SELL_THRESHOLD=70.0` — **the single most consequential,
least-justified pair of numbers in the file**, placed so a single axis's own sigmoid midpoint
(score 50) falls inside the band rather than on an edge. No backtest exists to fit them; this is
exactly what the sensitivity table below is for.

### Sensitivity table (the substitute for a backtest)
Run against the ABXY demo book (`data/azby_family.py`, 11 funds — **[INFERENCE] synthetic, not a
real client**; shape/direction is informative, re-run once a real book flows through this).
Baseline: 0 sell, 0 discretion, 10 hold, 1 gated (debt grandfather), 0 escalations. Every one of
the 19 numeric `mf_sell_score` parameters and both `core_satellite` parameters, swept ±20%:

**Result: 0 of 11 funds changed band under every single ±20% perturbation, on both modules.**
This is a real, checked result, not an assumption — full CSV at
`pr_template/out/mf_sell_score_sensitivity.csv`. It is *not* evidence the model is insensitive by
construction: the closest fund (LIC MF Multi Cap, concentration-driven, raw score 19.5) sits 27.1
points of headroom below `DISCRETION_LOW=45` — nothing in this particular book is concentrated,
Sortino-poor, or IPS-breaching enough to be *close* to the boundary, so ±20% on any one lever
can't reach it. Confirmed separately: scaling the concentration-axis anchors alone by **3x** does
flip a fund into the discretion band — the mechanism works, this book is just calm. A genuinely
useful, unplanned finding surfaced by the same run: **look-through equity is 88.5%** (funds'
own equity sleeves counted in) **against a direct-only figure of 60%**, and the client's IPS
Equity band caps at 85% — the book reads compliant on the naive number and breaches on the honest
one, which is the entire reason FM #2's look-through fix mattered. `TAIL_SAFETY_FACTOR` and the
hybrid performance axis showed 0 sensitivity for a different reason: both are wired but **inert**
today, pending the two interfaces below — their true sensitivity is unknown until those land.

### Hybrid blended benchmark (#20)
`hybrid_benchmark.blended_return(fund, start, end)` = `equity_pct% × NIFTY 500 TRI + debt_pct% ×
NIFTY Composite Debt Index + others_pct% × risk-free (6.5%, #15)`. Equity leg is one broad index,
not cap-specific, because ACE's hybrid disclosure gives an equity/debt/others split, not a
cap-wise breakdown of the sleeve — Nifty 500 TRI matches this codebase's own existing "Flexi"
convention. Debt leg and the "others" proxy are **reused, not invented**: "NIFTY Composite Debt
Index" is the exact name already inside today's fixed "NIFTY 50 Hybrid Composite 65:35" (see
`data/azby_family.py`'s `BENCH` dict); the risk-free proxy for "others" reuses #15's own number
rather than inventing a second figure.

**Degradation path, exactly as ruled:** `record_snapshot()` appends one row per fund per ACE month
to `05_DATA_OFFICE/mf_mix_history.csv` (append-only, idempotent — verified in tests). `trailing_mix()`
reports `"current-mix"` (the Principal's own words) until **≥6 months** exist (`MIN_MONTHS_FOR_TRAILING_AVG`
— two points barely differ from one and would misleadingly claim a stabilised average), then flips
to `"trailing-Nmo-average"` and keeps improving monthly toward the full 36. **Verified today: on a
fresh store the basis reads `current-mix`; after 6 synthetic months it correctly flips and the
average is arithmetically exact** (test asserts the literal mean).

Borrowed and re-pointed at the new blended benchmark rather than a fixed category one:
`down_capture_vs_blended()` (QFRA-2 concept), `total_capture_6m()` (QFRA-1 concept),
`suitability_vs_ips()` (does this fund's *own* mix fit the IPS Equity band — different from the
score's book-level IPS-gap axis, no second threshold invented). All three, plus `blended_return()`
itself, depend on exactly **one** pending primitive and degrade to an explicit gap reason without
it — never a guessed number:

> `lib.benchmark_returns.get_series(index_key: str, start_date, end_date) -> list[float] | None`
> — periodic (monthly) % returns for one named index (`"NIFTY 500 TRI"`, `"NIFTY Composite Debt
> Index"`), month-aligned. This is the entire ask of that workstream.

### Tail risk (#16) — interface only, confirmed inert
`mf_sell_score._axis_tail()` guarded-imports `lib.tail_risk` and calls `es90(fund, window_years=3)`
if it exists; `TAIL_SAFETY_FACTOR=None` in CONFIG blocks the axis from ever scoring even once ES90
values appear, until someone deliberately sets a validated factor. Verified today: with no
`lib/tail_risk.py` on disk, the axis returns `None` with reason `"tail-risk module not yet
available"` on every fund, every run — confirmed via the sensitivity sweep (0 contribution) and
unit tests. No file named `lib/tail_risk.py` or `lib/benchmark_returns.py` was created by this
build, on purpose — both are owned by separate in-flight workstreams; creating a stub risked a
collision with their actual work landing.

### Core / satellite (#1)
`core_satellite.py`. Core = index, large, mid **(corrected into core today, was wrongly proposed
satellite earlier)**, largemid, flexi, multi, hybrid, debt (all sub-labels), gold, plus ELSS/
dividend-yield/focused/value (style tilts on a broad mandate, not named by the ruling but placed
by the stated default rule, listed explicitly in code for audit). Satellite = keyword match
(sector/thematic/small/international/factor/contra/mnc) against category or name. Target 70/30,
`BAND_PP=10` **guidance, not a breach test** (his own words: "broad direction/idea") —
`within_guidance_band` is a plain readout, never a red/green gate. On the ABXY demo book, fund
sleeve alone: **98.8% core vs the 70% target** (gap +28.8pp, outside the guidance band) — thin
satellite allocation, for what it's worth on a synthetic book.

**Collision found while building this, resolved rather than left dangling:** the literal ruling
names fund categories only, so `lib/core_satellite.py`'s primary classifier was built fund-sleeve-
only. But `modules/core_satellite.py` — a slide renderer, built the same day by a **different,
concurrent pass** (Product/Tanvi) — independently answered the "does direct equity count too?"
question, the other way: yes (gold by name → core, `mcap_band=='Small'` → satellite, else core).
Rather than ship two silently-diverging answers to the same ruling on the same day,
`lib/core_satellite.py` now mirrors that exact rule as `classify_equity()`, and `book_split()`
takes an optional `equity=` argument so a caller can get either the fund-only split (the literal
ruling) or the whole-book split (matching the renderer's scope) from one function — tested both
ways. **Also found and NOT silently fixed** (different file, possibly still in flight):
`modules/core_satellite.py`'s own `_CORE_FUND_CATS` set has no `"mid"` entry at all — it lands
midcap at Core only via its catch-all default, the same *outcome* as this file's explicit
membership but a more fragile *mechanism* (one future edit to its satellite-keyword list could
silently flip it). Flagged for a reconciliation pass, not edited here.

### Left as documented defaults (no principle available, not a fitted number)
`SORTINO_COMFORTABLE`, `DISCRETION_LOW`/`SELL_THRESHOLD`, `PERF_GAP_MIDPOINT_PP`/`_STEEPNESS`, the
concentration curve's *shape between* the anchors, `TAX_DAMPING_*` magnitudes, `BAND_PP` for
core/satellite, and `MIN_MONTHS_FOR_TRAILING_AVG`. Every one lives in a `CONFIG` dict at the top of
its module with the sentence above next to it in code; none is hidden inside a formula.
