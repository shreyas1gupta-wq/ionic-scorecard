# S3 — RELATIVE 5Y SCORECARD — build + validation report

**Builder:** Arjun Rao (Head of Quant), 2026-07-18. Implements `SCORECARD_BLUEPRINT.md` §2.3
mechanically — no leg swaps, no weight search beyond the two explicit [MY CALL] slots the
blueprint itself left open (exact sr_5Y overweight/downweight magnitudes; abs_merit_5Y weights),
both disclosed below. Script: `rnd/scorecard/build_rel_score_5Y.py`, run synchronously,
foreground, single pass. Log: `C:\tmp\s3_rel5y_run.log`.

## Result (one line)

`composite_5Y` (0.60·sr_5Y + 0.40·abs_merit_5Y) scores **IC 0.0794, IC_IR 1.59, hit_rate 91.3%,
mono 0.71**, clears both HARD gates (lag-test delta 0.042 < 0.25; placebo IC 0.0014 inside
±0.02) on `panel_pit.parquet` (survivorship-free), 92 monthly rebalance dates, 2007-2020. **PBO
(0.926) and honest local DSR (0.892, n_trials=3) do not clear 0.95** — per this program's own
rule these are ADVISORY, not gating, at this horizon's inherently thin independent-sample count.
**Verdict: FRAGILE.** Single weakest assumption: the 92 "monthly" IC observations are 5-year
**overlapping** forward-return windows — the true independent-sample count is ≈92/60 ≈ **1.5
non-overlapping 5Y periods**, thinner even than the blueprint's own disclosed "~3-4" estimate.
Every Sharpe/IC_IR/DSR number in this card is computed on a heavily autocorrelated series and
should be read as directional, not precise.

## Data lineage [DATA]

| Input | File | Rows used | Date range |
|---|---|---|---|
| Evaluation panel (survivorship-free) | `rnd/panel/panel_pit.parquet` | 99,415 rows, 933 symbols | 2005-04-29 → 2025-12-05 |
| 7 canonical legs (6 of 7 read directly) | `rnd/panel/capstone_legs.parquet` | 1,310,958 rows, 12 legs present | matches panel grid |
| `mom_resid_plain` | **rebuilt fresh** via `run_long_confirm.build_mom_resid_12_1(close, bench, panel_pit dates)` | 134,967 obs | — the cached `mom_resid_peer` in `capstone_legs.parquet` was **not** used (S1.1 caveat) |
| Growth-longevity inputs | `rnd/wave4/_w6fg2_scored.parquet` (`composite_v2_confirmed`, `sub_op_persistent`) | 143,907 rows | 2002-06 → 2025-06, already on the panel's monthly grid (verified: `_w6fg2_scored` dates ⊂ `panel_pit` dates, 249/249 match) |
| Sector grain | `panel_pit.sector` (22-bucket macro_sector, static per symbol — verified 0 symbols with >1 sector value over time) | 604 symbols classified | — |

**Universe gate funnel:** 144,870 (date,symbol) pairs with a `quality_score` → 116,045 pass
`quality_score ≥ 0.20` → **79,194 pass quality AND ≥5-of-7 raw legs present** (final gated
universe, = the row count of `rel_score_5Y.parquet`). Growth-longevity itself only covers
65,236/79,194 (82%) of the gated universe — fundamentals coverage gap, disclosed, not a
scoring error (its absence is skip-NA'd in the weighted blend, never fabricated as zero).

Corporate-action guard: `disc_event_in_window_5Y > 0` NaN'd **1,649/99,415** rows from the 5Y
forward-return targets before any evaluation (same convention as `SECTOR_RELATIVE_REBUILD.md`).

**Data-thinness flag (blueprint-mandated disclosure):** panel_pit's 5Y forward-return label is
only non-null 2005-09 → 2020-10 (price data runs to 2025-26 but a full 5-year-forward window
needs 5 more years of data than "now"). Pre-2012 fundamentals coverage is materially thinner than
post-2012 (visible in the era split below — era1 has the fewest names per date). **5Y magnitudes
here are DIRECTIONAL, not precision estimates**, exactly as the blueprint flags.

## Guards passed

- **Corp-action guard**: applied (1,649 rows NaN'd from 5Y targets).
- **PIT discipline**: all ranks are same-date cross-sectional transforms; `_w6fg2_scored`'s
  `available_date`-based PIT alignment happened upstream (verified its date grid is identical to
  `panel_pit`'s, so no re-alignment risk here); `panel_pit` itself is the 42-snapshot
  survivorship-free build.
- **`mom_resid_plain` rebuilt fresh**, not substituted from the cached peer-relative leg — verified
  by construction (called `build_mom_resid_12_1` directly), not by comparison to a reference card
  (no official 5Y `mom_resid_plain` card exists to sanity-check against, unlike the 1Y case in
  `SECTOR_RELATIVE_REBUILD.md`; disclosed as a residual gap — nothing in this build depends on
  `mom_resid_plain` alone since it enters at a downweighted 0.5 slot in sr_5Y only).
- **`min_names_per_date=20`** (harness default), **`min_sector_peers=5`** (SR-v1 convention, smaller
  sector-date buckets dropped, not fabricated).
- **Lag-test** (one-more-period lag): sr_5Y 0.042, abs_merit_5Y 0.055, composite_5Y 0.042 — all
  **well under the 0.25 kill threshold** → no look-ahead leak.
- **Placebo** (5 shuffles, seed=42, fixed): sr_5Y +0.0031, abs_merit_5Y +0.0004, composite_5Y
  +0.0014 — **all inside the ±0.02 noise band**.
- **Determinism**: `build_all()` run twice from scratch (independent recomputation, not a
  cached-variable comparison) → **`out1.equals(out2)` = PASS, byte-identical**, confirmed via
  `pd.testing.assert_frame_equal(check_exact=True)` as a backstop. Logged explicitly in
  `C:\tmp\s3_rel5y_run.log`: `DETERMINISM CHECK: PASS (byte-identical)`. Zero `.fit()` calls in the
  scoring path; the only RNG anywhere is the harness's placebo shuffle (seed=42).

## Validation battery

| Metric | sr_5Y | abs_merit_5Y | composite_5Y (blend) | Role |
|---|---|---|---|---|
| IC mean | 0.0831 | 0.0520 | 0.0794 | PRIMARY |
| IC_IR | **1.821** | 0.851 | 1.593 | PRIMARY |
| Newey-West t (lag=59) | 8.69 | 3.97 | 6.12 | context |
| n_ic_dates | 92 | 92 | 92 | — |
| Decile monotonicity | **0.455 (weak)** | **0.927 (strong)** | 0.709 | PRIMARY |
| hit_rate (LS sign, monthly) | 78.3% | 82.6% | 91.3% | context |
| ann_return_LS, headline ×12 convention | 5.72 | 6.81 | 8.47 | **inflated ~60× at 5Y — do not quote** |
| ann_return_LS, horizon-aware (honest, /5) | **+9.5%/yr** | **+11.3%/yr** | **+14.1%/yr** | the real magnitude |
| net-of-cost, horizon-aware | +8.0%/yr | +10.1%/yr | +12.6%/yr | gate for deployability |
| turnover (top decile) | 16.1% | 12.5% | 16.0% | low, as expected at 5Y |
| **lag_test_delta** | 0.042 | 0.055 | 0.042 | **HARD GATE — PASS** |
| **placebo IC** | +0.0031 | +0.0004 | +0.0014 | **HARD GATE — PASS** |
| DSR (global trial count n≈700) | 8.3e-97 | 1.8e-299 | 1.8e-213 | ADVISORY — global counter crushes everyone |
| DSR (honest local, n_trials=3) | 0.615 | **0.047** | 0.892 | ADVISORY — none clear 0.95 |
| PBO (single-factor CSCV) | 0.965 | 0.896 | 0.926 | ADVISORY — all >0.5, disclosed not gated |
| skew / kurtosis of LS series | 0.31 / 2.79 | 1.67 / 5.54 | 1.30 / 4.09 | right-skewed, not left-tail-fat (benign direction) |

Hard gates = lag + placebo only, per blueprint §2.4. **Both pass for all three series.** DSR/PBO
are disclosed advisory numbers, not applied as kill criteria (firm's low-t rule; this horizon has
~1.5 independent windows, not enough for DSR/PBO to mean what they mean at n=100+).

### Drop-one-leg (direct IC, diagnostic — not a harness trial)

**sr_5Y** (8 components — 7 canonical legs + growth-longevity):

| leg dropped | IC after drop | Δ vs base (0.0831) |
|---|---|---|
| value_EY | 0.0821 | −0.001 |
| **growth_longevity** | **0.1196** | **+0.037 (IC IMPROVES when dropped)** |
| mom_resid_plain | 0.0823 | −0.001 |
| trend_ma65_slope | 0.0814 | −0.002 |
| quality_QMJ | 0.0597 | −0.023 |
| bs_issuance | 0.0711 | −0.012 |
| **bs_asset_growth** | **0.0369** | **−0.046 (most load-bearing leg)** |
| quality_cfo_pat | 0.0807 | −0.002 |

**abs_merit_5Y** (3 components):

| component dropped | IC after drop | Δ vs base (0.0520) |
|---|---|---|
| value_EY | 0.0521 | ~0 |
| **growth_longevity** | **0.0837** | **+0.032 (IC IMPROVES when dropped)** |
| quality_score | 0.0332 | −0.019 (most load-bearing) |

**Blend drop-limb** (= the two limbs' own solo harness IC): dropping sr_5Y → abs_merit_5Y alone
(IC 0.052); dropping abs_merit_5Y → sr_5Y alone (IC 0.083). The blend (0.079) sits between the
two, closer to sr_5Y — consistent with its 60% weight.

**Flag, not buried:** growth-longevity is the blueprint-mandated, explicitly-overweighted (2.0×)
8th component at 5Y — and in BOTH limbs, dropping it *increases* IC (sr_5Y: 0.083→0.120;
abs_merit_5Y: 0.052→0.084). As implemented (rank_pct(0.5·rank_pct(composite_v2_confirmed) +
0.5·rank_pct(sub_op_persistent)), 82% coverage), this component is adding noise, not signal, to
the cross-sectional rank at this horizon — the opposite of its mandated overweight. This is
disclosed as the second-most-important finding after the overlap issue (see verdict).

### Era split (4-way, auto-split on scored dates)

| era | n | sr_5Y IC | abs_merit_5Y IC | composite_5Y IC |
|---|---|---|---|---|
| era1 2013–2015 | 23 | 0.121 | 0.094 | 0.129 |
| era2 2015–2016 | 23 | 0.075 | 0.016 | 0.059 |
| era3 2017–2018 | 23 | 0.041 | 0.008 | 0.031 |
| era4 2018–2020 | 23 | 0.095 | 0.091 | 0.100 |

No monotonic decay pattern (unlike the raw-7 1Y composite's front-loaded decay found in
`SECTOR_RELATIVE_REBUILD.md`) — era3 is the weak spot for all three, era4 recovers. abs_merit_5Y
is markedly weaker than sr_5Y in eras 2–3 (0.016, 0.008) — its edge is concentrated in
era1/era4, a mild dispersion flag for the 40%-weighted limb.

### Year slices (2018/2020/2022/2024/2026 — best-effort)

Only 2018 (n=12, comp IC 0.028) and 2020 (n=10, comp IC 0.110) have any scored 5Y-forward dates —
**2022/2024/2026 have zero rows**, structurally, because a 5Y-forward label starting in
2022+ needs realized returns through 2027+, which does not exist yet. This is a data-availability
fact, not a coverage bug — disclosed per the charter's regime-slice convention, which this
horizon cannot satisfy the same way 1M/1Y can.

## Degenerate flags

- **No Sharpe>4 fabrication pattern.** Annualized Sharpe (sr_hat×√12, headline convention):
  sr_5Y ≈ 3.07, abs_merit_5Y ≈ 2.58, composite_5Y ≈ 3.26 — elevated, approaching but not past the
  Sharpe>4 automatic-suspicion line, and this elevation is fully explained by the overlap issue
  below (autocorrelated monthly sampling of a 5-year label mechanically shrinks the apparent
  std), not a debit-denominator or booking artifact.
- **hit_rate 78–91% is high but not the win>75%/W-L<0.5 degenerate signature**: skew is
  **positive** (0.31–1.67, right-tailed), meaning the edge comes from occasional large winners
  compounding over 5 years (consistent with a value/quality/growth-longevity long-horizon
  factor), not from a thin-premium/fat-tail-loss options-style pattern. Benign explanation,
  disclosed rather than assumed.
- **R² of equity line and ADV/liquidity violations were NOT computed** in this pass — out of the
  blueprint's §2.3/§2.4 explicit scope (no portfolio equity curve or ADV data join was specified
  for S3); disclosed as a limitation, not silently skipped.
- **PBO 0.90–0.97 across all three** is the most negative-looking number on the card. Per
  `SECTOR_RELATIVE_REBUILD.md`'s own finding, this specific CSCV adaptation mechanically produces
  high PBO readings whenever a factor's IC has any block-to-block dispersion (era3 here is
  visibly weaker than era1/era4) — it does not cleanly separate "decaying/dispersed" from
  "overfit" for a single-factor test. Disclosed, not overridden as clean.

## Verdict: **FRAGILE**

Hard gates (lag, placebo) pass cleanly for all three series — no leakage evidence. IC and
monotonicity are directionally sound for abs_merit_5Y (IC_IR 0.85, mono 0.93 — clean, if modest,
decile behavior) and reasonably strong for sr_5Y (IC_IR 1.82) though with weak monotonicity
(0.45). The blend inherits the more IC-favorable but less well-behaved limb's dominant weight.

**Single weakest assumption:** treating the 92 monthly-sampled IC observations as if they were
92 independent trials. They are not — each is a 5-year-forward-return label, so adjacent monthly
observations share 59/60 months of realized return. The true independent-sample count is
≈92/60 ≈ **1.5 non-overlapping 5-year windows** across the entire 2005–2020 scoreable history —
thinner than even the blueprint's own disclosed "~3-4 independent 5Y windows in ~20yr" estimate,
because the gated/corp-action-guarded universe only yields 92 usable dates, not the full ~186
months theoretically available. Every precision-looking number on this card (IC_IR, Newey-West t,
DSR, PBO, the annualized-Sharpe figures) is built on that same heavily autocorrelated series and
should be read as **directional evidence of a plausible 5-year value/growth-longevity/quality
tilt, not a statistically precise estimate of its magnitude.** This is a structural property of
the 5Y horizon itself (can't be fixed by this builder without inventing a new deoverlapping
estimator, which is new research, out of scope per blueprint §5) — not a data bug, not a leakage
bug (lag/placebo both clean), and not something a bigger sample will fix within this dataset's
20-year history.

Second-order finding worth the Principal's / CIO's attention: **growth-longevity, the one
component the blueprint explicitly mandated overweighting at 5Y, reduces IC on drop-one in both
limbs** as implemented here. Either (a) the construction (0.5·composite_v2_confirmed +
0.5·sub_op_persistent, 82% coverage) is a noisy proxy for the intended "growth durability" concept
and needs a cheap-test-level revisit outside this builder's mandate, or (b) growth-longevity earns
its keep in some dimension this drop-one/IC lens doesn't capture (e.g., tail-risk avoidance, not
average-IC). Flagging, not fixing — §5 of the blueprint locks the leg list; this builder does not
swap it out.

## FM-lens paragraph (Principal's 2026-07-18 instruction, mandatory)

Does this make real sense for a 5-year hold? Partly. The economic story — value + a business's
own durable growth carry the return, momentum/trend are close to irrelevant, and quality is a
floor not a driver — is exactly how a real long-horizon fundamental PM underwrites a 5-year
position, and abs_merit_5Y's clean decile monotonicity (0.93) is the most reassuring number on
this card: it says "better business = better realized 5Y return" in an orderly, not-noisy way,
which is what you want from a long-hold selection tool. sr_5Y's much weaker monotonicity (0.45)
is a real tension though — a PM would be uncomfortable building the majority (60%) of a 5-year
book on a signal whose decile 10 doesn't reliably beat decile 9 or 8, even if its average-date IC
looks good; average IC can look fine while individual deciles are noisy in the middle, and that's
exactly what a low monotonicity number with a decent IC_IR is telling us here. On the 0.60/0.40
blend itself: I do not think a thin DSR/PBO number should override this — three or four honest
5-year windows is simply what 20 years of data gives you at this horizon, that's expected, not
disqualifying, and I'd take the same position at 5Y even with n=3 if the logic and drop-one/era
behavior were clean. But the logic itself has one soft spot the stats independently corroborate:
abs_merit_5Y (the better-behaved, more "real business quality" limb) carries the minority weight
(40%) while sr_5Y (the noisier-deciles, momentum/trend-diluted, majority-weighted limb) carries
60% — the era split shows abs_merit_5Y's edge concentrated in 2 of 4 eras versus sr_5Y's steadier
presence across all 4, a genuine argument for keeping sr_5Y as the anchor per the blueprint's own
era-stability reasoning from `SECTOR_RELATIVE_REBUILD.md`. So the 0.60/0.40 split is defensible on
era-stability grounds even though abs_merit_5Y "feels" like the more PM-intuitive limb on decile
behavior alone — a real fund manager would want to see one more OOS confirmation window before
being fully comfortable, exactly the forward-test gate this scorecard is a candidate for, not yet
cleared for.

## Determinism-check confirmation

`build_all()` executed twice, independently, from the on-disk source parquets (not from a cached
in-memory variable) inside `main()`. Result: **`out1.equals(out2)` → True** (79,194 rows × 6
columns both runs), cross-checked with `pd.testing.assert_frame_equal(out1, out2,
check_exact=True)` as a backstop assertion (would raise if not exact). Logged verbatim in
`C:\tmp\s3_rel5y_run.log`:
```
[s3_rel5y 00:51:59] DETERMINISM CHECK: PASS (byte-identical) -- run1 shape=(79194, 6) run2 shape=(79194, 6)
```
Zero `.fit()` calls anywhere in the scoring path. The only RNG in the entire run is the harness's
placebo shuffle, seed=42 (evaluation only, not scoring).

## Output files

- `rnd/scorecard/rel_score_5Y.parquet` — 79,194 rows: `date, symbol, sr_5Y, abs_merit_5Y,
  composite_5Y, rel_score_5Y` (rel_score_5Y ∈ [−100, +100]).
- `rnd/scorecard/weights_5Y_fragment.json` — all frozen parameters (quality gate 0.20, min_legs 5,
  min_sector_peers 5, sr_5Y weights, abs_merit_5Y weights, 0.60/0.40 blend, determinism-check
  result, universe-gate funnel diagnostics).
- `rnd/scorecard/cards_S3_rel5Y/` — harness cards (`S3_REL5Y_sr_5Y.json`,
  `S3_REL5Y_abs_merit_5Y.json`, `S3_REL5Y_composite_5Y.json`) + `S3_REL5Y_SUMMARY.json` (full
  battery incl. drop-one, era-split, year-slices, local DSR).
