# ALPHA_RANKER — Wave-4 Test Results
Owner: Arjun Rao (Head of Quant), guilty-until-proven-innocent review. One base test + at most one
refinement per hypothesis, per RESEARCH_PROTOCOL.md. Cards: `rnd/cards/W4T_*.json`. These are
NEXT-SLEEVE candidates only — NOT added to the frozen composite (canonical_7leg_scores.parquet
untouched).

---

## W4-08 — Amihud illiquidity premium (size-residualized) — 2026-07-17

**Data lineage:** `panel/cube_close_long.parquet` (5,131 rows × 976 symbols, 2005-04-01→2025-12-05),
`panel/cube_volume.parquet` (1,238 rows × 751 symbols, **2021-07-16→2026-07-16, 5yr-only — disclosed
constraint in the hypothesis itself**), joined on 604 common symbols. Daily rupee-volume = close×volume;
ILLIQ = trailing-252d mean(|ret|/rupee_vol), log-transformed, then cross-sectionally **residualized on
`panel_long.mktcap_log`** per date (OLS, raw illiq_log vs mktcap_log corr = **−0.825** confirming the
hypothesis's own concern that raw ILLIQ is mostly a size proxy — residualization is not cosmetic here).
Evaluated against `panel/panel_long.parquet` via `lib/harness.py::evaluate()`, basis=resid.
Effective sample after residualization + rebalance-grid join: **only 48 monthly dates** (1M) / **35**
(1Y) — the 5yr volume window collapses to ~4.5 years of usable history, one market regime
(2022 selloff → 2023-25 recovery/bull), no cross-regime confirmation possible.

**Guards:** ran through `harness.evaluate()` (imports guard-equivalent PIT/schema checks internally);
no raw-file hacks, no manual date slicing beyond the documented volume-window constraint.

| Horizon | n_dates | IC_mean | IC_IR | lag_delta (≤0.25) | placebo\|IC\| (≤0.02) | PBO (<0.25 SOP) | DSR (per-family, n=2) | mono |
|---|---|---|---|---|---|---|---|---|
| 1M | 46 | 0.007 | 0.088 | **0.331 FAIL** | −0.004 PASS | **0.996 FAIL** | 0.005 | 0.54 |
| 1Y | 35 | 0.075 | **1.187** | 0.059 PASS | 0.001 PASS | **0.918 FAIL** | 0.990 | 0.88 |

Top-half-liquidity subuniverse (mandatory cost-honesty re-check, 302/604 symbols): IC_IR 0.35 (1M) /
0.96 (1Y) — same PBO failure persists (0.98 / 0.98). Top-illiquidity-decile median daily rupee volume
≈ ₹15.7 cr vs universe median ≈ ₹38 cr — real capacity constraint, not a free lunch even before PBO.
Corrected annualization (the harness's fixed `*12` scalar over-states 1Y/5Y labels by 12×/60× — see
`pragmatic_score_v2.py` comment): true 1Y gross ≈ **14.1%**, net-of-1x-cost ≈ **13.3%**, net-of-2x-cost
≈ **12.5%** (not the raw card's 168%/167% field, which is the known harness annualization bug, not a
real return). Corr vs `canonical_7leg_scores.parquet` = **0.098** (< 0.3 — genuinely orthogonal, as
expected since no current leg touches volume).

**Degenerate flags:** IC_IR 1.19 at 1Y is itself a "too good" flag on only 35 non-independent,
heavily-overlapping (1Y forward return, monthly step) observations; PBO fails by a wide margin at
BOTH horizons and in the liquid-subuniverse cut — CSCV is telling us this result does not survive
resampling. lag_delta at 1M is noisy because IC_mean≈0 there (denominator effect) but doesn't rescue
the verdict since 1M has no real signal anyway.

**Refinement:** hypothesis's own fallback (Datar share-turnover) SKIPPED — the failure mode here is
small-sample/single-regime data coverage (cube_volume literally has no more history), not
skew/noise in the Amihud construction itself; a turnover variant would face the identical 5yr
ceiling and would not fix PBO. Re-testing would burn a second trial for no expected gain.

**VERDICT: KILL / FRAGILE.** Hard gates (lag+placebo) pass in isolation at 1Y, but PBO fails
catastrophically (0.92–1.0) at every cut tried, on a sample too small (35–48 dates, one regime) to
certify. **Single weakest assumption: that 35–48 monthly snapshots drawn from one 2022–2025 market
era constitute enough independent trials to trust a 1.19 IC_IR** — they don't. Resurrection condition:
re-test only if/when cube_volume history is backfilled pre-2021 (would need a genuinely new rupee-volume
source, not currently in the data catalog).

---

## W4-12 — Momentum-WITHIN-quality double-sort (combination method) — 2026-07-17

**Data lineage:** `panel/capstone_legs.parquet` (1,310,958 rows, legs `quality_QMJ` — per-date
percentile rank 0–1, 144,870 rows, 2005-04-29→2025-12-05 — and `mom_resid_peer` — per-date z-score,
123,734 rows, 2006-07-31→2025-12-05), inner-joined on (date,symbol) → 123,720 obs, 234 dates. Both
legs reused UNCHANGED from the existing capstone builders (no rebuild). Evaluated against
`panel/panel_long.parquet`, basis=resid.

**Construction (3 variants, same universe/dates, so the comparison is apples-to-apples):**
- **DS** (double-sort): per date, keep only QMJ-rank ≥ 0.5 (top half), momentum (raw resid-mom value,
  Spearman-invariant to monotonic rescaling) scored only within that half; bottom half → NaN/unscored.
- **RA** (rank-average, the incumbent combination method): 0.5×qmj_rank + 0.5×mom_rank, full universe.
- **MOMONLY** (reference): plain `mom_resid_peer`, same universe/dates as DS/RA, no quality gate.

**Guards:** harness lag+placebo hard gates checked per variant per horizon; no lookahead beyond
what's already certified in the underlying QMJ/mom_resid_peer legs.

| Variant | Horizon | n_dates | IC_mean | IC_IR | lag_delta | placebo\|IC\| | mono | PBO |
|---|---|---|---|---|---|---|---|---|
| DS | 1Y | 221 | 0.034 | **0.297** | **0.272 FAIL** | −0.002 PASS | **0.12** | 0.996 |
| DS | 1M | 232 | 0.028 | 0.259 | 0.048 PASS | 0.001 PASS | 0.39 | 1.000 |
| RA | 1Y | 221 | 0.136 | **0.798** | 0.033 PASS | 0.001 PASS | **0.99** | 0.965 |
| RA | 1M | 232 | 0.065 | 0.446 | 0.005 PASS | −0.001 PASS | 0.88 | 0.983 |
| MOMONLY | 1Y | 221 | 0.063 | 0.552 | 0.114 PASS | 0.001 PASS | 0.88 | 0.983 |
| MOMONLY | 1M | 232 | 0.040 | 0.347 | 0.020 PASS | 0.001 PASS | 0.64 | 0.996 |

**Judge (per task spec): does the double-sort beat the rank-average on IR net-of-turnover? NO.**
RA's IC_IR is **2.7× DS's at 1Y** (0.798 vs 0.297) and **1.7× at 1M** (0.446 vs 0.259). Corrected
(horizon-aware, /HORIZON_YEARS not ×12) net-of-1x-cost annual return: RA 1Y ≈ **13.3%** vs DS 1Y ≈
**2.9%** (and DS turns *negative*, −0.2%, net of 2x-cost). DS also breaches the harness's own hard
lag-gate at 1Y (0.272 > 0.25) and has near-zero decile monotonicity (0.12, i.e. the sequential gate
scrambles the smooth rank structure RA preserves at 0.99).

**Secondary check — hypothesis's own pre-registered win (vs plain momentum, not RA):** required
high-vol IC to improve by ≥+0.05 AND full-period IC_IR to degrade <10%. Actual: high-vol regime IC
went from MOMONLY −0.039 to DS −0.056 (**worse by −0.017, wrong direction** — the crash-hedge
rationale did not materialize), and full-period IC_IR degraded from 0.552 to 0.297 (**−46%**, far
beyond the 10% budget). DS fails its own pre-registered success criterion as well as the task's
rank-average judge.

**Incidental note:** corr(RA, canonical_7leg score) = 0.62 — expected and uninformative as an
"incremental" test, since QMJ and mom_resid_peer are already 2 of the 7 legs inside that composite;
this is a combination-METHOD trial on existing inputs, not a new orthogonal signal, so the standard
<0.3 incrementality gate does not apply here (noted, not silently skipped). 8-leg IR delta rebuild
was NOT run — moot once DS is killed on its own construction merits; would burn compute testing
incrementality of a dead factor.

**VERDICT: KILL for the double-sort operator.** Confirms and EXTENDS the prior finding
(H029/H030/H046: rank-product interactions hurt) to a structurally different operator — sequential
conditioning/gating also hurts, here specifically because it (a) throws away half the cross-section's
rank information, (b) destroys monotonicity, and (c) makes the momentum leg's already-documented
high-vol fragility *worse*, not better. **Rank-average (the incumbent) wins outright — no change to
the composite's combination method is warranted.** Single weakest assumption: momentum's raw
(non-rank) value was used inside the top-quality half on the claim that Spearman IC is invariant to
monotonic transforms — true for the IC/decile calc, but the harness's turnover and cost-drag figures
are sensitive to how ties/edge cases in that raw-value ranking play out inside a halved, more
homogeneous quality-screened universe; this is a second-order concern given the size of DS's
across-the-board loss to RA.

## 2026-07-17 -- NEXT-SLEEVE forensic candidates (Arjun Rao)

Base 7-leg reconstructed (min_legs=5, capstone_legs.parquet cache) for reference: IC_IR=1.3374, mono=0.9999999999999999, gates_pass=True (frozen composite itself is NOT touched; this is a research-only recombination).

| Factor | Horizon | Signed IC_IR (1Y) | Gates (lag<=0.25 / |placebo|<=0.02) | Corr vs 7-leg composite | Incremental IR delta (8th leg) | Verdict |
|---|---|---|---|---|---|---|
| W4T_01_noa_neg (W4T_NOA) | 1Y | 0.1063 | lag=0.077(P)/placebo=0.0022(P) | -0.010 | -0.0510 | CANDIDATE |
| W4T_01_dnoa_neg_refine (W4T_NOA) | 1Y | 0.1407 | lag=0.479(F)/placebo=-0.0028(P) | 0.007 | n/a (refinement, not tested) | KILL (hard gate fail) |
| W4TF_01_dep_health (W4T_DEP) | 1Y | 0.1579 | lag=0.073(P)/placebo=0.0026(P) | 0.065 | 0.3205 | SURVIVOR |
| W4TF_02_clean_surplus_health (W4T_CS) | 1Y | 0.6923 | lag=0.039(P)/placebo=0.0023(P) | 0.267 | 0.4752 | CANDIDATE |
| W4TF_02_clean_surplus_divadj_refine (W4T_CS) | 1Y | 0.4488 | lag=0.027(P)/placebo=-0.0010(P) | 0.203 | n/a (refinement, not tested) | CANDIDATE |

---

## 2026-07-17 -- Sanjay Kulkarni (FM Fundamental Quality & Value): W4B-02 + W4P-03

**Scope**: 2 candidate value/risk factors backtested as potential NEXT-SLEEVE
material for ALPHA_RANKER. **NOT added to the frozen composite** -- screening-
layer test only, per this task's explicit instruction. One base test + at most
one pre-registered refinement per factor, PIT discipline throughout
(`available_date`-gated merge_asof, no lookahead).

Code: `rnd/lib/builders_w4t_sanjay.py` (builders), `rnd/run_w4t_sanjay.py`
(runner/diagnostics), `reports/W4T_sanjay_results.json` +
`reports/W4T_distress4_refine.json` (raw output).

### W4T-01 / W4B-02: Distress composite (adapted Ohlson O-score / CHS)

Construction: per-date cross-sectional z-score rank-average (no fitted
weights) of leverage, size(-mktcap_log), profitability(negated),
interest-coverage(inverted), negative-equity dummy, earnings-deterioration
dummy, equity-vol (vol_252) -- all oriented high=distressed, then negated so
`score` = HIGH means LOW distress. Data: `MASTER_fundamentals_pit.parquet`
(annual PIT, merge_asof backward on `available_date`) + `panel_long.parquet`
(mktcap_log, vol_252). Evaluated on `panel_long` (969 symbols, 2005-2025), 1Y
and 5Y horizons, `resid` basis.

| test | horizon | n_dates | ic_mean | ic_ir | NW-t | mono | lag_delta | placebo_ic | PBO | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 7-component base | 1Y | 223 | 0.032 | 0.174 | 0.78 | -0.95 | 0.047 | 0.004 | 0.987 | KILL |
| 7-component base | 5Y | 174 | -0.007 | -0.038 | -0.10 | -0.99 | 0.176 | 0.001 | 0.922 | KILL |
| 4-component refinement (leverage,size,profitability,earn-deter only) | 1Y | 223 | 0.003 | 0.017 | 0.06 | -0.93 | **0.663** | 0.001 | 0.974 | KILL |
| 4-component refinement | 5Y | 174 | -0.010 | -0.066 | -0.18 | -0.96 | 0.010 | 0.001 | 0.870 | KILL |

**HARD GATES (per this task's criteria)**: lag_test_delta<=0.25 -- PASS for
7-comp (both horizons) and 4-comp-5Y; **FAIL for 4-comp-1Y (0.663)**. Placebo
|IC|<=0.02 -- PASS on all 4 rows (max 0.004). So the base 7-component
construction cleanly passes both mandated hard gates at both horizons, but
carries essentially NO exploitable signal (IC_IR 0.174 and -0.038, both well
under the 0.20 promote-consideration floor, and the harness's own decile
monotonicity is strongly NEGATIVE (-0.95, -0.99) -- i.e., decile means do not
line up with the direction the composite's own IC would imply, an internal
inconsistency that itself argues against a stable relationship, not merely a
"weak but real" one). The pre-registered 4-component refinement is worse on
every axis and additionally **fails the lag-test hard gate at 1Y** (0.663 >>
0.25), meaning whatever residual "signal" the 4-component version shows is not
stable to a one-period lag -- a classic sign of a spurious/turnover-driven
artifact, not real economic content.

**Sign test (the whole point of this factor)**: the "distress-risk-puzzle"
(distressed firms globally earn LOWER, not higher, forward returns) predicts
score(=safety) should have a **positive** signed IC. 1Y shows a weak positive
IC (0.032, consistent with the puzzle direction but far too weak/noisy to
trade); 5Y flips to weakly negative (-0.007). **No reliable, horizon-stable
sign was found in this India sample** -- neither confirms nor exploitably
refutes the distress-risk-puzzle; it just isn't there at a tradable magnitude
on this construction.

**Incremental test vs the 8-leg composite**: pooled Spearman corr(distress7,
`canonical_7leg_scores.score`) = **0.24** (passes the <0.3 orthogonality bar
on its own). But the "8-leg IR delta" diagnostic (50/50 per-date rank blend of
the canonical composite score + this factor, evaluated identically) shows
canon-solo 1Y IC_IR = 1.356 vs blend 1Y IC_IR = 0.921 -- **delta = -0.435**.
Blending this factor IN would materially **hurt** the composite's own IC_IR
in-sample. This is decisive on its own: even setting aside the weak standalone
IC_IR, adding this factor is a net negative for the book.

**VERDICT: KILL both base and refinement.** No resurrection condition is
being registered -- the kill is clean (both mandated hard gates pass at the
base construction, no data/lookahead artifact found), the signal is simply
too weak and inconsistent across horizons to be tradable, and the composite-
level blend test actively argues against inclusion. [DATA] all figures above
read directly from `rnd/cards/W4T_distress7_1Y_resid.json`,
`W4T_distress7_5Y_resid.json`, `W4T_distress4_1Y_resid.json`,
`W4T_distress4_5Y_resid.json`, `W4T_distress7_blend8leg_1Y_resid.json`,
`W4T_canonSolo_1Y_diag.json`.

---

### W4T-02 / W4P-03: Cyclical-sector normalized (5-7yr avg) earnings yield

Construction: within cyclical macro_sectors only (Metals & Mining, Automobile
and Auto Components, Capital Goods, Construction Materials -- **NBFC dropped**,
disclosed caveat: `sector_map.parquet`'s fine taxonomy bundles NBFC with banks
under one "Finance" label, no clean split available without fabricating a
name-keyword heuristic), normalized_EY = trailing 5-7yr PIT-available AVERAGE
`eps in rs` / price, vs plain TTM-EY (latest PIT annual EPS / price) computed
from the **same** price source (`cube_close_long.parquet`, per this task's
DATA section -- deliberately NOT reusing `builders_value.py`'s
`build_H014_earnings_yield`, which reads a different price file, to keep the
head-to-head clean). Cyclical universe: 532 symbols tagged, 195 present in
`panel_long` (~148 names/date cross-section). 1Y horizon, `resid` basis
(the construct's whole reason to exist is a value/timing read, 1Y is the
natural single test; 5Y not run, staying within the one-base-test budget).

| leg | n_dates | ic_mean | ic_ir | NW-t | mono | lag_delta | placebo_ic | PBO | verdict |
|---|---|---|---|---|---|---|---|---|---|
| TTM-EY (cyclical subset, baseline) | 186 | 0.058 | **0.422** | 1.99 | 0.47 | 0.035 | 0.004 | 0.996 | KILL (PBO only) |
| Normalized-EY (cyclical subset, the new construct) | 114 | 0.029 | **0.230** | 0.90 | 0.27 | 0.009 | -0.002 | 0.991 | KILL (PBO only) |

**HARD GATES**: both legs cleanly PASS lag_test_delta<=0.25 (0.035, 0.009) and
placebo |IC|<=0.02 (0.004, -0.002). The plain incumbent TTM-EY leg actually
shows a genuine, borderline-significant standalone edge within cyclicals
(IC_IR 0.42, t~2.0) -- expected, EY is an established leg. The new
cycle-normalized construct is **weaker on every metric**: lower IC_IR (0.230
vs 0.422), non-significant t-stat (0.90 vs 1.99), weaker monotonicity (0.27 vs
0.47), and a materially thinner usable sample (114 vs 186 dates -- the 5-7yr
EPS-history requirement drops the newest listings and any name with a gap in
its annual filing history).

**Does it beat TTM-EY within cyclicals (the construct's entire reason to
exist)? NO.** This directly answers the value-trap hypothesis test the card
asked for: in this sample, cycle-normalizing earnings for cyclical-sector
names does **not** fix the "cheap-on-TTM-EY-at-peak-earnings" value trap
better than plain TTM-EY already does -- if anything it is a noisier, thinner
version of the same signal.

**Incremental test vs the 8-leg composite**: pooled Spearman corr(normalized-
EY, `canonical_7leg_scores.score`, cyclical subset) = **0.12** (well under the
0.30 bar -- genuinely distinct from the composite within this subset, as the
hypothesis card itself expected "should diverge meaningfully inside it"). But
the same 8-leg IR delta diagnostic: canon-solo(cyclical) 1Y IC_IR = 0.988 vs
blend 1Y IC_IR = 0.592, **delta = -0.396** -- again net negative to blend in,
consistent with a weaker, noisier signal diluting a stronger existing one.

**VERDICT: KILL.** No refinement attempted (none pre-registered in the
hypothesis card for W4P-03, and the result is clean/conclusive as-is: the
construct underperforms its own baseline on every axis, hard gates pass so
this isn't a data artifact, it's a real negative result). No resurrection
condition registered. [DATA] figures from
`rnd/cards/W4T_cycEY_baselineTTM_1Y_resid.json`,
`W4T_cycEY_normalized_1Y_resid.json`, `W4T_cycEY_blend8leg_1Y_resid.json`,
`W4T_canonSoloCyc_1Y_diag.json`.

---

### Cross-cutting findings from this run (flagged, not fixed -- ownership boundary)

1. **[DATA] Harness annualization bug for 1Y/5Y horizons** (`rnd/lib/harness.py`
   line ~702, `periods_per_year = 12` hardcoded for ALL horizons): for a 1Y
   or 5Y forward-return label, `long_short.ann_return_LS` /
   `costs.net_of_cost_ann_return` multiply an ALREADY-annual (or already-5-
   year) mean return by 12 again, producing nonsensical magnitudes (e.g. this
   run's raw `W4T_distress7_5Y_resid` card shows `ann_return_LS = -58.85`,
   i.e. -5885% annualized -- not a real number; note this matches the same
   bug independently flagged above in the W4-08 Amihud entry). Corrected
   figures (undo the x12, then correctly annualize: divide by 1 for 1Y,
   geometric `(1+r)^(1/5)-1` for 5Y) computed separately in
   `run_w4t_sanjay.py::correct_annualization()` and included in
   `reports/W4T_sanjay_results.json` (`annualization_corrected*` keys) --
   e.g. distress7 1Y corrected net-of-cost = -24.9%/yr (vs the raw card's
   nonsensical -298.8%/yr). **Not fixed in harness.py itself** (owned by
   Sameer Bhat per RESEARCH_PROTOCOL S3 one-code-path rule; this run flags
   it rather than silently patching a shared module).
2. **[INFERENCE] DSR=0.000 on every card in this run** is very likely an
   artifact of the GLOBAL trial counter (`trials_counter.json`, 457+ trials
   firm-wide at time of this run) crushing the expected-max-Sharpe benchmark
   per Bailey-Lopez de Prado's formula, not evidence these two factors are
   uniquely bad on a per-family basis -- `harness.py`'s own
   `dsr_from_stats()` docstring (2026-07-17, Sameer Bhat) flags this exact
   issue and offers a per-family recompute path via `pragmatic_score_v2.py`,
   not invoked here (out of scope for this task; the KILL verdicts above do
   not rely on DSR, they rely on IC_IR + the two mandated hard gates + the
   composite-blend delta, all of which are DSR-independent).
