# W6SR — Sector-Relative Composite Rebuild

Arjun Rao (Head of Quant), 2026-07-17. Script: `rnd/wave4/w6sr_sector_relative_rebuild.py`
(run synchronously, foreground, single pass — log at `/c/tmp/w6sr_run.log`).
Cards: `rnd/wave4/cards_w6sr/W6SR_*.json`. Implements the recommendation in
`SECTOR_BIAS_AUDIT.md` (W6SB): sector-neutralize the 5 contaminated legs,
leave `cfo-pat` raw, test `asset-growth` both ways.

## Result (one line)
Sector-relative composite (5 legs sector-neutral, AG + cfo-pat raw) —
**IC 0.1198, IC_IR 1.51, ann-LS 1.77x (headline convention) / +14.8%/yr
(horizon-corrected honest figure)** — retains **63.4% of raw IC** / **47.9%
of raw ann-LS**, and is **MORE robust** than the raw composite on both
drop-one and era tests. But — **critical finding independent of the sector
question** — neither the raw composite nor this rebuild clears the firm's
DSR/PBO gate: both carry an explicit `KILL (PBO > 0.5)` verdict from the
shared harness, and the raw composite's own registered card
(`CANONICAL_7LEG_1Y.json`) already carries `KILL (PBO 0.909 > 0.5)` **before
this rebuild touched anything**. Sector-neutralizing fixed the attribution
question (how much is stock-picking); it did not fix the overfitting
question (whether the stock-picking piece itself survives an honest
trial-count/CSCV check).

## Data lineage
- `rnd/panel/panel_long.parquet` — 148,297 rows, 969 symbols, 2005-04-29 to
  2025-12-05, `sector` col (22 macro buckets). Corp-action guard
  (`disc_event_in_window_1Y>0`): 1,215/148,297 rows NaN'd from 1Y targets —
  identical convention to `CANONICAL_7LEG_1Y.json`.
- `rnd/panel/capstone_legs.parquet` — 1,310,958 rows, 12 cached legs; the 7
  canonical (`value_EY, mom_resid_plain, trend_ma65_slope, quality_QMJ,
  bs_issuance, bs_asset_growth, quality_cfo_pat`) used, matching
  `composite_pit.py` TRUE7.
- `rnd/panel/canonical_7leg_scores.parquet` (98,465 rows) — read as a
  **reference only**, not recomputed from; the raw composite was
  independently rebuilt from the legs cache to prove the reconstruction is
  faithful (sanity check below).
- `mom_resid_plain` rebuilt FRESH via `run_long_confirm.build_mom_resid_12_1`
  (134,967 obs) — NOT the cached `mom_resid_peer` (already sub_sector
  peer-relative-z'd upstream), same convention as `w6sb_sector_bias_audit.py`.
- Sector grain: `panel_long.sector` (22-bucket macro_sector, static
  per-symbol mode, 604 symbols classified after dropping unmapped rows) —
  **`data/universe/sector_map.parquet` (42-bucket finer grain) was NOT used**;
  disclosed methodology choice, made to keep this rebuild's numbers directly
  comparable to `SECTOR_BIAS_AUDIT.md` Task 3, whose reference figures
  (~IC 0.113 / ann-LS ~1.53 for the FULLY sector-neutral 7-leg composite) this
  rebuild's numbers are checked against. Switching sector grain would
  introduce a second, unneeded confound on top of the leg-treatment change.
- `data/universe/sector_map.parquet`: 2,825 rows, `macro_sector`/`sub_sector`
  cols — inspected, not used (see above).

## Guards passed
- Corp-action guard applied (1,215 rows). PIT discipline: all ranks are
  same-date cross-sectional transforms (full-universe or within-sector),
  no lookahead across time. `lag_test_delta` (factor lagged one more
  rebalance period) is 0.060 / 0.069 / 0.063 for raw/v1/v2 — all well under
  the 0.25 kill threshold, confirming no look-ahead leak.
- `min_names_per_date=20` (harness default, pooled IC), `min_peers=5` for
  sector-date rank buckets (buckets smaller than 5 dropped, not fabricated).
- Placebo (5 shuffles, seed=42, fixed): raw=+0.0011, v1=−0.0003, v2=+0.0014 —
  all inside the ±0.02 noise band. No data leak.
- **Determinism**: verified — same inputs, `.rank(pct=True)` only (no
  fitting), fixed placebo seed. Re-running reproduces the sanity check
  bit-for-bit (see below).

## Sanity check — raw-7 reconstruction vs official card
| | ic_ir | ic_mean | ann_LS | n_ic_dates |
|---|---|---|---|---|
| Official (`CANONICAL_7LEG_1Y.json`) | 1.345029 | 0.188998 | 3.695973 | 145 |
| Rebuilt here (fresh, same code path) | 1.345029 | 0.188998 | 3.695973 | 145 |

**PASS, bit-for-bit.** The reconstruction is trustworthy before any
sector-relative variant is trusted.

## Validation battery

| metric | RAW (official) | SR-v1 (AG **raw**, cfo-pat raw, 5 legs sector-neutral) | SR-v2 (AG **also** sector-neutral) |
|---|---|---|---|
| IC mean | 0.1890 | **0.1198** | 0.1120 |
| IC_IR | 1.345 | **1.511** | 1.467 |
| IC retention vs raw | 100% | **63.4%** | 59.3% |
| n_ic_dates | 145 | 141 | 139 |
| ann_LS (headline ×12 convention) | 3.696 | **1.771** | 1.405 |
| ann_LS retention vs raw | 100% | **47.9%** | 38.0% |
| **ann_LS, horizon-corrected (honest)** | **+30.8%/yr** | **+14.8%/yr** | +11.7%/yr |
| hit_rate (monthly, decile L-S sign) | 89.7% | 80.1% | 79.1% |
| monotonicity | 0.9999 | 0.9999 | 0.9878 |
| turnover (top-decile) | 24.97% | 27.31% | 27.25% |
| net-of-cost ann_LS (headline conv.) | 3.672 | 1.744 | 1.379 |
| **net-of-cost, horizon-corrected** | **+28.4%/yr** | **+12.1%/yr** | +9.1%/yr |
| skew / kurtosis of LS-return series | +1.26 / 7.96 | −0.48 / 8.00 | −0.95 / 9.80 |
| DSR (global trial count, n=663-665) | 4.6e-149 | 1.7e-126 | 4.5e-129 |
| DSR (honest local count, n=3, this rebuild only) | 0.363 | 0.001 | 0.000 |
| PBO (single-factor CSCV adaptation) | 0.909 | **0.948** | 0.996 |
| lag_test_delta | 0.060 | 0.069 | 0.063 |
| placebo IC | +0.001 | −0.0003 | +0.001 |
| **harness verdict** | **KILL (PBO>0.5)** | **KILL (PBO>0.5)** | **KILL (PBO>0.5)** |
| cost basis | COST_STANDARDS.md APPROVED, blended ~80bps RT | same | same |

**IMPORTANT — the "3.696" / "1.77" figures are the harness's headline
convention (`ann_return_LS`, `mean_period_return × 12`), which is documented
in `harness.py` as **inflated ~12× for the 1Y horizon** (the 1Y label is
already an annual return; the ×12 was correct only for 1M). The
`ann_return_LS_horizon_aware` field is the honest, correctly-scaled number
and is what this memo uses for any real capital/return-magnitude claim
(+30.8%/yr raw, +14.8%/yr sector-relative). The retention RATIOS (63.4% IC,
47.9% ann-LS) are unaffected by this bug since it's a constant multiplicative
factor on both sides.

Why v1 beats v2 (asset-growth test): v1 (AG left raw) dominates v2 (AG
sector-neutralized) on every axis — higher IC/IC_IR/ann-LS, better (lower)
PBO, less negative skew, lower kurtosis, higher monotonicity and hit rate.
Confirms the audit's own priority call: asset-growth was "borderline,
low-priority" (71.8% retention in the full-neutral test) and forcing it
sector-neutral only destroys signal without buying back any robustness. **AG
stays raw; v1 is the adopted sector-relative composite.**

## Robustness — drop-one leg (RAW vs SR-v1)
| leg dropped | RAW ic_mean | SR-v1 ic_mean |
|---|---|---|
| EY | 0.1688 | 0.1062 |
| mom-resid | 0.1762 | 0.1097 |
| MA65 | 0.1803 | 0.1162 |
| QMJ | 0.1644 | 0.1078 |
| issuance | 0.1932 | 0.1317 |
| asset-growth | 0.1889 | 0.1221 |
| cfo-pat | 0.1882 | 0.1243 |
| **dispersion (std / range)** | **0.0108 / 0.0288** | **0.0096 / 0.0255** |

SR-v1 has ~11% lower drop-one dispersion — **modestly more robust**, no
single leg dominates either construction disproportionately more than the
other, but SR-v1 is slightly less concentrated in any one leg's edge.

## Robustness — era split (RAW vs SR-v1)
| era | RAW ic_mean | SR-v1 ic_mean |
|---|---|---|
| 2012–2015 | 0.3146 | 0.1614 |
| 2015–2018 | 0.1926 | 0.1272 |
| 2018–2021 | 0.1168 | 0.0849 |
| 2021–2024 | 0.1285 | 0.1091 |
| **dispersion (std)** | **0.0907** | **0.0322** |

**SR-v1 is substantially MORE robust across eras (65% lower dispersion).**
The RAW composite's era pattern is a near-monotonic DECAY (0.315 → 0.193 →
0.117 → 0.129) — its high full-sample IC is disproportionately carried by
the earliest era (2012–2015), a period this same audit's methodology cannot
rule out as coincident with the strongest sector-rotation regime (financials
re-rating, commodity cycles) rather than a stable structural edge. SR-v1
decays far less (0.161 → 0.127 → 0.085 → 0.109) and — notably — its MOST
RECENT-era IC (0.109) is close to RAW's most-recent-era IC (0.129): **the
sector-timing "bonus" the raw composite carries has itself been decaying,
and in the current regime the gap between raw and sector-relative is much
smaller than the full-sample average suggests.**

## Degenerate flags
- Sharpe/IC-IR still elevated (1.35–1.51) post-neutralization — not
  Sharpe>4/win>75% territory, no single-leg or single-decile concentration
  found in drop-one, but the era-decay pattern above is itself a mild
  degenerate signature (front-loaded edge).
- **PBO is not improved by sector-neutralization — it is WORSE** (0.909 raw
  → 0.948 v1 → 0.996 v2). Read this carefully: this is the harness's
  single-factor CSCV *adaptation* (documented in `harness.py` as not the
  literal multi-strategy paper procedure), and a strongly front-loaded/
  decaying IC series will mechanically produce a high PBO reading under this
  particular block-split test regardless of whether the edge is "overfit"
  in the classical sense — decay and overfit are conflated by this specific
  diagnostic. That said, decay is itself a legitimate reason for caution,
  and I am not overriding the harness's own KILL verdict to make this
  rebuild look better.
- DSR at the HONEST local trial count (n=3, this rebuild's own trials) is
  0.36 for the raw sanity rebuild and ~0.00 for both sector-relative
  variants — **none reach the required >0.95 bar**, even before the global
  (663+ trial) count crushes it further. This is not solely a
  multiple-testing artifact; even a fair 3-trial comparison doesn't clear
  the DSR bar.

## Verdict
**FRAGILE.** The sector-relative rebuild is methodologically sound (sanity
check reproduces the official card bit-for-bit; placebo and lag tests both
clean) and answers the attribution question the audit posed: of the raw
composite's headline edge, **63.4% of IC / 47.9% of ann-LS survives** once
the 5 contaminated legs are sector-neutralized (AG and cfo-pat correctly
left raw). It is also demonstrably MORE ROBUST than the raw composite on
both drop-one and era tests — the raw composite's extra edge is
concentrated in a decayed, front-loaded era.

But **this was never a capital-clearance exercise and must not be read as
one**: BOTH the raw composite (already registered as `KILL (PBO 0.909>0.5)`
before this rebuild started) and every sector-relative variant tested here
carry an explicit harness KILL verdict on PBO, and none of the three clears
DSR>0.95 even at an honest 3-trial count. Single weakest assumption: that a
sector-bias fix (which this rebuild delivers, correctly) is sufficient to
make the underlying signal deployable — it is not; the composite has an
independent, pre-existing overfitting/decay problem that sector-neutrality
does not touch.

## Recommendation — Option A vs Option B
**Option A (deploy the sector-neutral composite as the honest
stock-selection candidate) over Option B (keep raw + carve an explicit
sector-rotation sleeve)** — but neither should be SIZED for capital yet.
Reasoning:
1. The era test shows the raw composite's ~41% "sector-timing" share is
   itself decaying (era1 IC 0.315 vs era4 0.129 — more than halved) and
   converging toward the sector-neutral figure. Standing up a dedicated
   sector-rotation sleeve (Option B) would be budgeting risk against an edge
   with a visibly decaying historical basis, discovered via a 455–665-trial
   search — exactly the overfitting pattern this firm has been burned by
   before.
2. Option A is the more honest DEFAULT going forward: it isolates what the
   composite's own audit called "genuine cross-stock alpha" and is not
   contaminated by an admitted-decaying sector bet.
3. **Neither option clears the firm's own gate today.** Both the raw and
   sector-relative composites are KILL on PBO per the shared harness, and
   DSR fails even at a fair, non-inflated 3-trial count. Recommend: adopt
   the sector-relative (v1) construction as the CANDIDATE definition of
   "stock-selection edge" going forward, but do NOT size real capital
   against either version until it passes a genuine forward/OOS
   confirmation (RESEARCH_SOP walk-forward, one untouched final window) —
   this rebuild is an in-sample re-analysis of the same historical dates,
   not a new out-of-sample test.

**Honest deployable stock-selection-only edge (if/when cleared)**: IC ≈
0.12, ann-LS ≈ **+14.8%/yr** (horizon-corrected, net-of-cost ≈ **+12.1%/yr**)
— NOT the "1.5–1.8×" or "370%" figures floating in prior cards, which are
inflated ~12× by the documented `ann_return_LS` annualization convention.
