# S8 — Score-Bucket Calibration Re-Evaluation (Principal's 2026-07-18 methodology correction)

**Owner:** Dr. Sameer Bhat (Overfit & Sensitivity Analyst, E-027). **Date:** 2026-07-18. **Step:** S8, follow-up to S7.
**Status:** Re-judging under the Principal's new evaluation philosophy. Does NOT rebuild any score. Pure
read-and-compute pass over `absolute_scorecard.parquet`, `RELATIVE_SCORECARD_v1.parquet`, `panel_pit.parquet`.

**Script:** `rnd/scorecard/S8_calibration_eval.py`. **Determinism:** run twice, `calibration_tables.parquet`
SHA-256 `dd021646199a16bb94313a9efea2332141569def330c55d7f22e51a2c813f924` on both runs — byte-identical. [DATA]

**Hard gates unchanged:** 1M ABSOLUTE stays **FAKE / KILL** — the lag-test leakage failure (deltas 1.05g/0.51
rerating vs a 0.25 bar) is a structural leakage finding, not a lens artifact, and this methodology correction does
not reopen it. It is included below only for completeness/context, never for a verdict upgrade. [OPINION — firm rule]

---

## 0. Method notes [DATA/INFERENCE]

- `log_intensity = ln(1+E_return)`, `log_realized_return = ln(1+fwd_ret_h_raw)`. Verified no `fwd_ret_h_raw <= -1`
  or `E_return <= -1` in either dataset (min values −0.91/1M, −0.996/1Y, −0.996/5Y realized; −0.51/−0.60/−0.84
  modeled) — logs are well-defined everywhere, no guard triggered.
- `abs_score = 200*(rank_pct(E_return)-0.5)` computed **within-date, within-horizon**, over the subset of
  (date,symbol) rows where `E_return` is not-null for that horizon (52,210/date-symbol-horizon triples scored out
  of 99,415 — the model doesn't score every name every date). Same -100..+100 convention as `rel_score_h`
  (verified: `rel_score_h` empirically ranges -99.7..+100, mean≈0, matching the same rank_pct construction).
- Bucket edges: `<0 / 0-30 / 30-50 / 50-75 / >75` — five bands, chosen to extend the task's suggested
  ">75/50-75/30-50" language down through the full signed range (unlike a native 0-100 scale, these scores can be
  negative, so a bare "<30" bucket would silently merge "mildly negative" with "very negative"). Not fitted to the
  outcome data — fixed before computing hit-rates. [OPINION — my bucket-edge call, one-line change if disputed]
- Comparator: **ABSOLUTE** hit = `fwd_ret_h_raw > 0` (literal binary per the Principal's framing). **RELATIVE** hit
  = `fwd_ret_h_raw > cross-sectional median that date` (over the same scored+realized population), since a
  cross-sectional ranker's honest test is beating the pack that date, not beating zero.
- Consistency = (a) `yearly_hitrate_std` — std-dev of the bucket's hit-rate across calendar years, and (b)
  `frac_years_beats_below` — fraction of years this bucket's hit-rate exceeds the bucket-immediately-below's, same
  year. Both reported; both in `calibration_tables.parquet` (30 rows = 2 scorecards × 3 horizons × 5 buckets).
- **Overlap caveat (carried from S3/S4, re-confirmed here):** the panel samples monthly, so "years" at the 1Y and
  especially 5Y horizon are NOT independent windows — a 5Y forward return sampled every month overlaps its
  neighbors by ~98%. `yearly_hitrate_std` and `frac_years_beats_below` at 5Y are read as **directional**, not
  as an independent-sample stability test (that remains DSR/PBO's job, unchanged, still advisory/thin-n).

---

## 1. Bucket-calibration tables

### ABSOLUTE scorecard (hit = `fwd_ret_h_raw > 0`)

**1M** (context only — hard-gate KILL stands, never quotable)

| Bucket | n | hit-rate | mean log-realized-ret | yearly hit-rate std | frac beats below |
|---|---|---|---|---|---|
| <0 | 25,648 | 0.543 | 0.0113 | 0.094 | — |
| 0-30 | 7,618 | 0.552 | 0.0113 | 0.089 | 0.643 |
| 30-50 | 5,202 | 0.550 | 0.0125 | 0.113 | 0.429 |
| 50-75 | 6,404 | 0.545 | 0.0131 | 0.068 | 0.500 |
| >75 | 6,514 | 0.551 | 0.0154 | 0.116 | 0.643 |

Spearman(bucket, hit-rate) = **0.3** (flat/weak). Spearman(bucket, magnitude) = **0.9** (clean monotonic).

**1Y**

| Bucket | n | hit-rate | mean log-realized-ret | yearly hit-rate std | frac beats below |
|---|---|---|---|---|---|
| <0 | 23,484 | 0.637 | 0.135 | 0.270 | — |
| 0-30 | 6,974 | 0.642 | 0.141 | 0.207 | 0.692 |
| 30-50 | 4,766 | 0.610 | 0.130 | 0.223 | 0.154 |
| 50-75 | 5,856 | 0.631 | 0.147 | 0.267 | 0.615 |
| >75 | 5,977 | 0.618 | 0.149 | 0.247 | 0.462 |

Spearman(bucket, hit-rate) = **-0.6** (inverted — top bucket has a LOWER hit-rate than the bottom bucket, 0.618
vs 0.637). Spearman(bucket, magnitude) = **0.7** (weak positive, dips at 30-50). Inter-bucket hit-rate spread
(≈3pp: 0.610-0.642) is smaller than the within-bucket year-to-year std (0.21-0.27) — **the hit-rate "calibration"
is not distinguishable from noise at this n.**

**5Y**

| Bucket | n | hit-rate | mean log-realized-ret | yearly hit-rate std | frac beats below |
|---|---|---|---|---|---|
| <0 | 14,223 | 0.786 | 0.550 | 0.144 | — |
| 0-30 | 4,211 | 0.821 | 0.636 | 0.193 | 0.556 |
| 30-50 | 2,902 | 0.812 | 0.642 | 0.145 | 0.556 |
| 50-75 | 3,537 | 0.765 | 0.481 | 0.101 | 0.222 |
| >75 | 3,639 | 0.765 | 0.563 | 0.152 | 0.556 |

Spearman(bucket, hit-rate) = **-0.7**. Spearman(bucket, magnitude) = **-0.1**. **Inverted-U, not monotonic: the
highest-score bucket (>75) UNDERPERFORMS both middle buckets (0-30, 30-50) on hit-rate AND magnitude, and is
statistically tied with the LOWEST-score bucket (<0) on hit-rate (0.765 vs 0.786).** This is the score-bucket
analogue of a single-spike-in-the-middle parameter surface — by Gate-4 convention (best cell should be at the top
of a monotonic surface, not buried mid-range) this is a genuine calibration failure, not noise dressed up: the
model's own highest-conviction names are not its best names.

### RELATIVE scorecard (hit = `fwd_ret_h_raw >` that date's cross-sectional median)

**1M**

| Bucket | n | hit-rate | mean log-realized-ret | yearly hit-rate std | frac beats below |
|---|---|---|---|---|---|
| <0 | 46,174 | 0.475 | 0.0040 | 0.023 | — |
| 0-30 | 13,795 | 0.509 | 0.0111 | 0.024 | 0.85 |
| 30-50 | 9,284 | 0.521 | 0.0129 | 0.035 | 0.65 |
| 50-75 | 11,538 | 0.524 | 0.0143 | 0.033 | 0.55 |
| >75 | 11,663 | 0.543 | 0.0193 | 0.039 | 0.70 |

Spearman(bucket, hit-rate) = **1.0**. Spearman(bucket, magnitude) = **1.0**. Clean monotonic on both dimensions,
every year (20/20 present) — **the strongest calibration in the entire study**, corroborating S1's REAL verdict
via a completely different lens.

**1Y**

| Bucket | n | hit-rate | mean log-realized-ret | yearly hit-rate std | frac beats below |
|---|---|---|---|---|---|
| <0 | 13,834 | 0.461 | 0.112 | 0.199 | — |
| 0-30 | 4,110 | 0.535 | 0.161 | 0.023 | 0.875 |
| 30-50 | 2,794 | 0.522 | 0.159 | 0.130 | 0.500 |
| 50-75 | 3,446 | 0.540 | 0.172 | 0.070 | 0.625 |
| >75 | 3,574 | 0.541 | 0.187 | 0.274 | 0.500 |

Spearman(bucket, hit-rate) = **0.9**, Spearman(bucket, magnitude) = **0.9** — one small dip at 30-50, otherwise
clean monotonic. **Confirms** S2's forward-test-candidate framing: the calibration lens supports usability, the
weakness is thin independent-n (>75 bucket's yearly std 0.274 — big single-year swings), not absence of signal.

**5Y**

| Bucket | n | hit-rate | mean log-realized-ret | yearly hit-rate std | frac beats below |
|---|---|---|---|---|---|
| <0 | 14,913 | 0.472 | 0.503 | 0.261 | — |
| 0-30 | 4,417 | 0.520 | 0.603 | 0.154 | 0.909 |
| 30-50 | 2,883 | 0.554 | 0.691 | 0.258 | 0.545 |
| 50-75 | 3,669 | 0.529 | 0.649 | 0.163 | 0.500 |
| >75 | 3,391 | 0.506 | 0.620 | 0.245 | 0.400 |

Spearman(bucket, hit-rate) = **0.3**, Spearman(bucket, magnitude) = **0.6** — same **inverted-U** shape as
ABSOLUTE 5Y: peaks at 30-50, and the top bucket (>75) is WORSE than 30-50/50-75 on both dimensions. This
independently corroborates the already-escalated growth-longevity drop-one anomaly (S3, consolidated escalation
#2): whatever is pushing names into the top score band at 5Y (both scorecards share the growth-longevity leg) is
not the same thing that predicts the best outcomes.

---

## 2. Reliability-ordering test: does 5Y > 1Y > 1M hold?

**No — the actual data shows the opposite ordering in both scorecards: 1M > 1Y > 5Y.**

| Scorecard | Horizon | avg |spearman| (hit-rate, magnitude) | mean yearly hit-rate std (lower=more stable) |
|---|---|---|---|
| ABSOLUTE | 1M | 0.60 | 0.096 |
| ABSOLUTE | 1Y | 0.05 | 0.243 |
| ABSOLUTE | 5Y | -0.40 | 0.147 |
| RELATIVE | 1M | 1.00 | 0.031 |
| RELATIVE | 1Y | 0.90 | 0.139 |
| RELATIVE | 5Y | 0.45 | 0.216 |

Both monotonicity strength and year-to-year stability degrade from 1M to 5Y — the reverse of the hypothesized
"longer horizons average out noise" ordering. [INFERENCE] The most likely cause is not that longer horizons carry
less genuine information; it is **effective independent-sample size**: 1M forward returns sampled monthly are
close to non-overlapping, while 5Y forward returns sampled monthly overlap ~98% with their neighbors, so the
"20 years" of 5Y observations behind these tables are really ~1.5-2 independent draws (the same thin-n problem
S3/S4 already flagged for DSR/PBO). The calibration lens is not immune to that problem — it just makes the
symptom visible in a new place (inverted-U top buckets) rather than in a DSR number. **Report the finding as-is:
the hoped-for ordering does not hold in this data, and the most defensible read is a sample-size artifact
compounding with the growth-longevity leg issue, not proof that long-horizon investing is unreliable per se.**

---

## 3. Revised verdicts — ABSOLUTE 1Y and 5Y (calibration lens; supersedes the Calmar-loss reasoning in S7)

**1Y ABSOLUTE — remains FRAGILE, recharacterized.** Under the new lens this is not "loses to a placebo on Calmar"
— it is a **direct calibration weakness**: magnitude shows a modest, mostly-monotonic positive tilt (mean
log-return 0.135→0.149 bottom-to-top, ~10% relative, one dip at 30-50) but hit-rate is **flat-to-inverted**
(0.637 at the bottom vs 0.618 at the top) and the inter-bucket hit-rate spread (≈3pp) is smaller than the
within-bucket year-to-year noise (21-27pp std). A PM cannot trust the score to raise the ODDS of being right; at
best it weakly raises the SIZE of the win conditional on being right, and even that is noisy. Not upgraded to REAL.

**5Y ABSOLUTE — remains FRAGILE, and the calibration lens makes the problem MORE concrete, not less.** This is
the sharper finding of the two: the top score bucket (>75) is tied with or worse than the BOTTOM bucket (<0) on
both hit-rate (0.765 vs 0.786) and magnitude (0.563 vs 0.550 — barely above), while the true best-performing
bucket is the mid-range (30-50: hit-rate 0.812, magnitude 0.642). This is an inverted-U, not a plateau or a
monotonic surface — by the same logic that flags a single-spike parameter cell as fragile, a scorecard whose
highest-conviction bucket is not its best bucket is not usable for conviction-sizing as currently built, regardless
of what it does on Calmar. **This is not a "more positive" verdict than S7's — it is the same negative conclusion
reached by an honest, independent lens, with a more specific and more actionable diagnosis** (points at the
growth-longevity leg, same one already escalated from S3).

**No horizon in the absolute scorecard clears this bar today.** 1M is hard-gate killed (leakage, unchanged). 1Y's
calibration is too weak/noisy to trust on the dimension that matters most (hit-rate). 5Y is actively anti-calibrated
at its own top end.

### Supplementary calibration confirmation — RELATIVE scorecard

1M relative: clean monotonic on both dimensions across every year — the calibration lens is the strongest
independent confirmation yet of the existing REAL verdict. 1Y relative: strong, slightly noisy at the top
(large single-year swings) — confirms the "usable forward-test candidate, thin-n" framing, no change. 5Y
relative: weak/inverted-U, same shape as 5Y absolute — this is new evidence (not present in S3's IC/decile
framing) that the 5Y FRAGILE verdict's weakest-assumption note (growth-longevity leg) deserves priority
resolution before 5Y relative is trusted at higher conviction, on either scorecard.

---

## 4. Fund-manager lens (Principal's instruction, 2026-07-18)

Under this more honest calibration lens, here is what I would actually let a PM trust from the ABSOLUTE
scorecard: **nothing, today, at any surviving horizon.** 1M is leakage-killed. At 1Y the score does not reliably
move your odds of being right — only a small, noisy tilt on how big the win is if you're already right, too small
to separate from year-to-year randomness. At 5Y the score is actively misleading at its own top end: the names
the model is MOST confident in are not better, and are sometimes worse, than names it is moderately confident in
— that is a worse practical failure mode than "loses to a coin-flip on Calmar," because a PM using this score to
size conviction would be sizing UP exactly the wrong names. If I had to salvage one thing, it would be to
re-examine the growth-longevity leg flagged in S3 (drop-one IMPROVES the 5Y models in both scorecards) as the
prime suspect for the inverted top bucket, before anyone screens on `E_return`, `intensity`, or absolute score at
any horizon. Until that's resolved, the absolute scorecard stays off every PM's screen — same practical
conclusion as S7, reached this time by evidence a PM would recognize from their own P&L (hit-rate and dollar
magnitude by conviction band), not just a backtest statistic.

---

**Files:** `rnd/scorecard/S8_calibration_eval.py` (script), `rnd/scorecard/calibration_tables.parquet` (30 rows,
bucket-level), `rnd/scorecard/S8_calibration_diag.json` (full diagnostics incl. per-bucket dicts + monotonicity
table), this report.
