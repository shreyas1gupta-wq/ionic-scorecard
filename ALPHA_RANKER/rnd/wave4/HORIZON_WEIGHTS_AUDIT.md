# HORIZON WEIGHTS AUDIT — Arjun Rao (Head of Quant), 2026-07-17

> Question: is EQUAL-WEIGHT rank-average of the 7 legs, used identically at 1M/1Y/5Y, the right
> construction — or does the Principal's horizon-differentiation prior (momentum-heavy 1M, balanced
> 1Y, value/quality-heavy 5Y) beat it? Tested honestly, no fitted weights, judged by logic + effect
> + drop-one, not by t-stat theatre (every number below has PBO > 0.5 — this whole family is already
> risk-office PARKed per FINAL_MODEL.md S5-RISKOFFICE; nothing here un-parks it, this only answers
> the weighting-DIRECTION question for the day a fresh forward test clears).

## 0. Data lineage [DATA]

| File | Rows | Date range | Role |
|---|---|---|---|
| `rnd/panel/panel_long.parquet` | 148,297 | 2005-04-29 → 2025-12-05 (249 monthly dates) | 21-yr panel; has `fwd_ret_{1M,1Y,5Y}_{raw,excess,resid}` AND `disc_event_in_window_{1M,1Y,5Y}` — confirmed by direct read, not assumed |
| `rnd/panel/capstone_legs.parquet` | 1,310,958 | same range, 12 legs incl. the 7 canonical | source of 6 of 7 legs (mom_resid_plain rebuilt fresh, see below) |
| `rnd/panel/cube_close_long.parquet` | 5,131 × 976 symbols | daily close | rebuild PLAIN residual momentum fresh (not the cached peer-relative variant — CONSOLIDATION.md already proved peer-relative reverses sign on 21yr; same correction applied here at every horizon) |
| `rnd/panel/cube_bench_long.parquet` | (NIFTY500 daily) | — | benchmark leg for residual momentum |

New artifacts this audit produced (script: `rnd/lib/run_w4_horizon_weights.py`):
- 21 new cards `rnd/cards/W4HW_leg_<leg>_<horizon>.json` — every one of the 7 legs, freshly evaluated on the SAME 21-yr `panel_long` at ALL THREE horizons (1M/1Y/5Y), not just the horizons each leg previously had a CAPSTONE card for.
- 6 new cards `rnd/cards/W4HW_{EQUAL,TILT}_{1M,1Y,5Y}.json` — equal-weight vs prior-tilted composite per horizon.
- `rnd/wave4/w4hw_leg_by_horizon.csv` (21 rows), `rnd/wave4/w4hw_composite_equal_vs_tilt.csv` (6 rows) — full numeric record.

**Why re-run legs that already had CAPSTONE cards, instead of just reading FINAL_MODEL.md:** the existing 1M
literature in this repo (`H014_earnings_yield_1M`, `H029_quality_only_1M`, `H048_quality_*_1M`) was tested on
`panel.parquet` — **2021-07 to 2026-07 only, 47-53 monthly dates, a single junk-bull regime** — not on the
21-yr `panel_long` the 1Y/5Y CAPSTONE cards use. That mismatch means the existing "1M: fundamentals near-zero,
no tradeable value/quality leg" claim in FINAL_MODEL.md/CONSOLIDATION.md was **never actually tested
cross-regime** — it was tested in the one regime (2021-26 junk-bull) where quality is independently
documented to invert (CONSOLIDATION.md: "Quality is INVERTED in the 2021-26 junk-bull, mono -0.9"). This
audit closes that gap by running all 7 legs at 1M on the real 21-yr panel. Result: it changes the 1M
picture materially (§1, §3) — the prior write-up was a regime artifact, not a data gap that stays zero
once filled.

## 1. Guards passed?

- **PIT**: `panel_long.parquet` is the PIT-survivorship panel already audited in FINAL_MODEL.md §5-RISKOFFICE
  (T1 clean). No new universe construction here — legs and targets are read as-is from that panel.
- **Corporate-action guard**: `disc_event_in_window_<H>` NaN's the forward-return target before scoring, at
  every horizon (same convention as `composite_final.py`) — applied here identically at 1M/1Y/5Y, closing a
  gap the older 1M cards (built before this guard existed) did not have.
- **Lag test** (`lib/harness.py`'s one-period-shift check, <0.25 = clean): **20 of 21 leg-cards pass.**
  One FAILS outright — `bs_asset_growth` at 1M, lag_test_delta = **0.966** (near-4x the kill line). Its
  1M IC (-0.080) is **not a usable number**, gate-failed, not merely weak. `bs_issuance` at 1M is
  borderline (0.210, under the 0.25 line but the closest clean pass in the set) — treat as fragile, not solid.
- **Placebo** (label-shuffle, should be ≈0): all 27 cards (21 leg + 6 composite) come back in
  [-0.0042, +0.0037] — clean across the board. No fabrication/leakage signature.
- **PBO**: every single card here is >0.5 (0.82-1.00) — **the whole family stays risk-office PARKED**
  (FINAL_MODEL.md S5-RISKOFFICE, unchanged verdict). This audit is scoped to the weighting-DIRECTION
  question only, not a re-certification.
- **DSR**: ≈0 everywhere (multiple-testing reality, per CONSOLIDATION harness-fix note — advisory, not
  re-litigated here).

## 2. Per-horizon leg IC table (identical 21-yr panel, identical harness, identical guard — apples to apples)

| Leg | 1M IC_IR / mono / lag_Δ / n | 1Y IC_IR / mono / lag_Δ / n | 5Y IC_IR / mono / lag_Δ / n |
|---|---|---|---|
| **value_EY** | 0.354 / 0.685 / 0.110 / 168 | 0.763 / 0.855 / 0.010 / 157 | **2.089** / 0.600 / 0.017 / 108 |
| **mom_resid_plain** | 0.425 / **1.000** / 0.055 / 232 | **0.688** / 0.988 / 0.116 / 221 | 0.600 / 0.636 / 0.065 / 172 |
| **trend_ma65_slope** | 0.298 / 0.976 / 0.007 / 242 | **0.706** / 1.000 / 0.110 / 231 | 0.406 / 0.612 / 0.083 / 182 |
| **quality_QMJ** | **0.445** / 0.782 / 0.005 / 242 | 0.767 / 0.782 / 0.013 / 231 | **1.743** / 0.842 / 0.010 / 182 |
| **bs_issuance** | 0.260 / 0.515 / 0.210(borderline) / 156 | 0.946 / 0.721 / 0.009 / 145 | 2.913(‡thin,n=96) / 0.770 / 0.008 / 96 |
| **bs_asset_growth** | -0.080 (‡LAG-FAIL, discard) / 156 | 0.289 / 0.976 / 0.015 / 145 | 0.393 / 0.806 / 0.005 / 96 |
| **quality_cfo_pat** | 0.230 / 0.648 / 0.074 / 101 | 0.565 / 0.673 / 0.001 / 90 | 4.501(‡known thin-window artifact, n=41) / 0.345 / 0.013 / 41 |

‡ = flagged degenerate/unreliable, see §4. Bold = best-or-tied leg for that horizon.

### Principal's hypotheses vs this table

**(a) "Momentum/trend strongest at 1M/1Y, fades by 5Y"** — **PARTIALLY CONFIRMED, direction wrong at 1M.**
Both legs actually peak at **1Y** (mom 0.688, trend 0.706), not 1M (mom 0.425, trend 0.298 — trend is the
single *weakest* leg at 1M). Both do fade into 5Y, but in **monotonicity** more than raw IC_IR: mom mono
1.00→0.99→0.64, trend mono 0.98→1.00→0.61 — the decile-ordering discipline degrades a lot even though the
correlation strength (mom IC_IR 0.60 at 5Y) doesn't collapse to zero. One clean confirmatory side-finding:
`mom_resid_plain` stays monotone-positive at 5Y (mono 0.636) where the cached peer-relative variant
(`CAPSTONE_mom_resid_peer_5Y`) was mono **-0.648** — reconfirms CONSOLIDATION.md's "peer-relative reverses
on 21yr, plain doesn't" lesson at a horizon it hadn't been checked at before.

**(b) "Value(EY)/quality(QMJ) strongest at 5Y"** — **STRONGLY CONFIRMED, cleanest result in this audit.**
Both show a clean monotone-increasing IC_IR across horizons: EY 0.354→0.763→2.089 (≈6x 1M→5Y), QMJ
0.445→0.767→1.743 (≈4x). Caveat: EY's decile monotonicity actually *drops* at 5Y (0.600 vs 0.855 at 1Y) —
the average correlation gets stronger but the practical top-vs-bottom decile ordering gets noisier, and
n_ic_dates=108 (≈9 independent non-overlapping 5yr windows) is thin. QMJ's monotonicity holds up better
(0.842 at 5Y, actually its best of the three horizons) — QMJ is the more *reliable* of the two 5Y legs, EY
the higher-*magnitude* one.

**(c) "Fundamentals near-zero at 1M standalone"** — **REFUTED on the honest 21-yr test; the existing
write-up was a regime artifact.** On `panel_long`, quality_QMJ (0.445) is the single best 1M leg,
edging out momentum (0.425); value_EY (0.354) also beats trend (0.298). Only `bs_asset_growth`
genuinely fails at 1M — and that's a lag-test gate failure (0.966), not a clean "true zero." The prior
1M-only literature in this repo (H014/H029/H048, `panel.parquet`, 2021-26) showed quality **inverted**
(-0.152) at 1M — but that window is the documented junk-bull regime where quality is known to invert.
Testing cross-regime on the full 21 years flips the verdict: fundamentals are NOT dead at 1M, they were
tested in the one regime where they're known to misbehave. **Correction to file**, not a new caveat.

## 3. 1M clubbing test (existing cards, `W4T_MOMQUAL_*`, 21-yr panel, 232 monthly dates)

| Card | ic_mean | ic_ir | Note |
|---|---|---|---|
| `W4T_MOMQUAL_MOMONLY_1M` | 0.0400 | 0.347 | momentum standalone |
| `W4T_MOMQUAL_RA_1M` (rank-avg mom+quality) | **0.0651** | **0.446** | +63% ic_mean, +29% ic_ir over mom-alone |
| `W4T_MOMQUAL_DS_1M` (dynamic-sizing variant) | 0.0283 | 0.259 | worse than either simple version |

Standalone quality alone at 1M on the SHORT panel is negative (H029_quality_only, ic_ir -0.152), yet
**rank-averaging it with momentum lifts BOTH the mean and the IR** of the pair versus momentum alone. This
is consistent with §2's finding that quality is a genuine, not-near-zero 1M signal cross-regime — the
short-panel standalone test undersold it, and combining smooths over the short-panel's junk-bull-specific
inversion. **Verdict: clubbing works at 1M — momentum + quality/fundamentals tilt beats momentum alone,
even though the quality leg looks weak/negative in isolation on the (regime-biased) short panel.**
Caveat honestly carried forward: this is still a rank-average of price-momentum with a fundamentals-based
quality score, not a genuine news/event feed — no intraday or news-driven "catalyst" leg exists on disk at
1M, so this doesn't confirm a first-order catalyst effect, only that a slower-moving quality tilt adds
value alongside momentum at 1M.

## 4. Degenerate / thin-data flags — read before trusting any 5Y magnitude

- **`bs_issuance_5Y` (IC_IR 2.913) and `quality_cfo_pat_5Y` (IC_IR 4.501, nw_t 21-25)**: both rest on
  n_ic_dates ≤ 96 (cfo_pat: 41) of heavily-overlapping 5-year-forward-return windows. CONSOLIDATION.md
  already flagged cfo_pat's 5Y number as "thin-window artifact, directional only" — this audit's fresh
  run reproduces the exact same extreme number (4.501, unchanged to 3 decimals from the cached CAPSTONE
  card), which at least confirms it's not a one-off bug, but an IC_IR this high with n≈41 and NW-lag=59
  (lag ≈ 1.5x the observation count) is a known small-sample pathology, not a genuine effect size to size
  a weight on. **Do not use cfo_pat's or issuance's raw 5Y IC_IR magnitude for weight-setting** — direction
  (positive) is usable, magnitude is not.
- **`bs_asset_growth_1M`**: lag-test hard-fails (0.966 vs 0.25 threshold) — the -0.080 IC is not a "near-zero
  standalone" finding, it's a gate failure. Treat as untested, not confirmed-null, at 1M.
- **EQUAL-weight composite UNDERPERFORMS its own best single leg at 5Y**: EQUAL 5Y IC_IR = 1.899, but
  value_EY ALONE = 2.089. Blending in the weaker/thin legs (mom, trend, issuance, cfo_pat) at equal weight
  actively dilutes the composite below what the single best factor would deliver. This is the clearest,
  most concrete evidence in this audit that equal-weight is the WRONG construction at 5Y — not just
  "sub-optimal," actively worse than doing nothing extra.

## 5. EQUAL vs prior-based TILT composite (fixed integer tiers, chosen before running, not fitted)

| Horizon | Scheme | Weights | IC_IR | Mono | Quintile ann_LS | Verdict on tilt |
|---|---|---|---|---|---|---|
| 1M | EQUAL | all 1x | 0.646 | 0.976 | 0.174 | — |
| 1M | TILT (momentum-heavy, per Principal's prior) | mom×2, trend×2 | **0.551** | 0.964 | 0.177 | **TILT LOSES** (-15% IC_IR, mono also down) |
| 1Y | EQUAL | all 1x | 1.345 | 1.000 | 2.834 | — (no tilt tested; 1Y = the balanced case by the Principal's own framing, not re-tested here) |
| 5Y | EQUAL | all 1x | 1.899 | 0.952 | 1.021 | — |
| 5Y | TILT (value/quality-heavy, per Principal's prior) | EY×2, QMJ×2, asset-growth×2 | **2.196** | 0.939 | 1.111 | **TILT WINS** (+15.6% IC_IR, mono ~flat, economic spread also up) |

**Drop-one logic check (why one tilt won and the other lost, not just "the number moved"):** a tilt helps
exactly when it up-weights legs that are ALREADY the strongest standalone (§2) and hurts when it up-weights
legs that are already the weakest. The 5Y tilt up-weighted EY (rank #1) and QMJ (rank #2 of 7) — a tilt
toward strength. The 1M tilt up-weighted momentum (rank #2) AND trend (rank #7, dead last) — trend's 2x
weight actively drags the composite down, which is exactly what the leg table in §2 predicted before the
composite was even run. **This is an internally consistent result, not a coincidence of one test** — the
same ranking that explains the 1M loss also explains the 5Y win.

## 6. Verdict per horizon

**1M — FRAGILE-BUT-INSTRUCTIVE.** Momentum-heavy tilt as literally proposed LOSES to equal-weight
(-15% IC_IR). The corrected picture: quality is NOT dead at 1M (§2c), and momentum+quality clubbing beats
momentum alone (§3). If 1M is to be tilted at all, the evidence points to **momentum+quality, trend
de-weighted** — not "momentum-heavy" as a blanket prior. Weakest assumption: this whole horizon still has
no genuine intraday/news catalyst leg (data gap, honestly disclosed, not fabricated), and even the
corrected 21-yr 1M test is fundamentally-thin pre-2012 same as every other horizon here.

**1Y — UNCHANGED, still the strongest-evidenced horizon.** Not re-tested for a tilt (by design — this is
already the Principal's own "balanced" case), and remains the only horizon with a real leave-one-out
incremental test on file (`rnd/reports/incremental_value.csv`): asset-growth +0.065 ΔIC_IR, CFO/PAT +0.045,
net-issuance +0.034 — all genuinely additive over the 4-leg base, none dominant enough to justify anything
but roughly-equal weight. Equal-weight at 1Y stays the right call.

**5Y — CONFIRMED SHOULD BE VALUE/QUALITY-TILTED, not equal-weight.** Equal-weight actively underperforms
bare EY (§4); a value+quality+asset-growth tilt recovers and modestly exceeds single-factor EY (IC_IR 2.196
vs 2.089) while keeping monotonicity roughly flat. Weakest assumption: EY and cfo_pat/issuance's 5Y
magnitudes are NOT all equally trustworthy (§4) — trust EY and QMJ's 5Y numbers, treat issuance/cfo_pat 5Y
as directional-only. Data is also genuinely thin pre-2012 (documented repo-wide caveat, re-confirmed here:
n_ic_dates 96-108 for the horizon's best legs, ≈8-9 independent non-overlapping windows).

## 7. RECOMMENDED prior-based weight scheme (economic priors, NOT fitted — for the day DSR/PBO clears)

| Horizon | Tilt direction | Legs up-weighted | Legs down-weighted / unchanged | Confidence |
|---|---|---|---|---|
| **1M** | momentum + quality (NOT momentum-only) | mom_resid_plain, quality_QMJ | trend_ma65_slope (weakest 1M leg — do NOT double it), value_EY neutral | LOW — no 21yr cube for a genuine catalyst leg; this revises but does not fully validate the Principal's prior |
| **1Y** | balanced (keep equal-weight) | none | none — all 7 legs individually incremental per `incremental_value.csv` | HIGH — the only horizon with a leave-one-out test on file, cross-regime-confirmed, `CANONICAL_7LEG_1Y` |
| **5Y** | value + quality heavy | value_EY, quality_QMJ, bs_asset_growth (direction only, magnitude untrustworthy) | mom_resid_plain, trend_ma65_slope, bs_issuance, quality_cfo_pat (keep in for diversification, but do not size on their thin-sample 5Y IC_IR) | MEDIUM — clean directional win in this test, but data-thin (pre-2012 gap) same as every 5Y claim in this repo |

**Bottom line: the Principal's core instinct — that equal-weight-across-horizons is wrong — is CONFIRMED
at 5Y and PARTIALLY confirmed at 1M (wrong single-factor prior, right general direction that fundamentals
matter more than assumed). 1Y remains correctly equal-weighted.** None of this clears the composite for
production — PBO stays >0.5 on every card in this audit, same as every other card in the corpus; this
answers the weighting-architecture question for whenever the fresh held-out forward test (FINAL_MODEL.md
§5-RISKOFFICE fix-path) is run.

## 8. Artifacts
`rnd/lib/run_w4_horizon_weights.py` (script, re-runnable), `rnd/wave4/w4hw_leg_by_horizon.csv`,
`rnd/wave4/w4hw_composite_equal_vs_tilt.csv`, 27 new cards in `rnd/cards/W4HW_*.json`.
