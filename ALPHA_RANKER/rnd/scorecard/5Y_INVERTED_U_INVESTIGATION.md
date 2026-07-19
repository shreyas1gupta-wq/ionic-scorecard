# 5Y Inverted-U Investigation — WHY does growth-longevity hurt, and is the top bucket's underperformance real or an artifact?

**Owner:** Dr. Sameer Bhat (Overfit & Sensitivity Analyst, E-027). **Date:** 2026-07-18.
**Trigger:** S3 (`S3_RELATIVE_5Y_REPORT.md`) drop-one finding (growth-longevity *reduces* IC when
dropped, both limbs) + S8 (`S8_CALIBRATION_REPORT.md`) calibration finding (5Y top score bucket
ties-or-loses to the bottom bucket, both scorecards) converging on the same anomaly from two
independent methods. **Method:** pure read-and-compute over `rel_score_5Y.parquet`,
`absolute_scorecard.parquet`, `panel_pit.parquet`, `stock_valuation_pit.parquet`,
`_w6fg2_scored.parquet`. No fitting, no new signal search. Script run twice (fresh interpreter,
independent recomputation) — bucket tables and cut statistics byte-identical both runs (no RNG
anywhere in this analysis). [DATA]

**EXIT_TRIGGER_SPEC.md does not exist yet** — checked, absent from `rnd/scorecard/`; the R7
valuation-ceiling link the task asked me to check is therefore deferred, not applicable today. [DATA]

---

## 1. Replication (sanity check before digging further)

Recomputed both bucket tables independently from source parquets (not from S3/S8's saved
diagnostics) — matches their reported shapes:

**RELATIVE 5Y** (`rel_score_5Y.parquet` × `panel_pit.fwd_ret_5Y_raw`, hit = beat cross-sectional
median, n=28,871 scored rows, 162 dates 2007-05→2020-10 pre-forward-return-availability cutoff):

| bucket | n | hit_rate | mean fwd 5Y ret |
|---|---|---|---|
| <0 | 14,692 | 0.476 | 1.543 |
| 0-30 | 4,371 | 0.517 | 1.777 |
| **30-50** | 2,843 | **0.553** | 1.783 |
| 50-75 | 3,630 | 0.523 | 1.761 |
| >75 | 3,335 | 0.506 | 1.765 |

**ABSOLUTE 5Y** (`absolute_scorecard.parquet`, horizon=5Y, hit = `fwd_ret_h_raw>0`, n=28,512):

| bucket | n | hit_rate | mean fwd ret | median PE | mean PE_fair | mean g | mean rerating | mean mktcap_log |
|---|---|---|---|---|---|---|---|---|
| <0 | 14,223 | 0.786 | 1.721 | 26.25 | 28.72 | −0.008 | 0.887 | 24.91 |
| 0-30 | 4,211 | 0.821 | 1.682 | 22.00 | 28.31 | 0.145 | 1.069 | 25.12 |
| **30-50** | 2,902 | **0.812** | 2.060 | 19.78 | 28.17 | 0.192 | 1.172 | 25.07 |
| 50-75 | 3,537 | 0.765 | 1.642 | 18.86 | 32.30 | 0.263 | 1.228 | 24.85 |
| >75 | 3,639 | 0.765 | 1.848 | **13.13** | **43.38** | **0.349** | **1.552** | 24.60 |

Both confirm S3/S8: inverted-U, peak at 30-50, top bucket ties-or-loses to bottom. Good — this is a
real feature of the data, not a one-off computation slip in either prior report.

## 2. Top-bucket cuts (the "why")

### 2a. Valuation — REJECTS the "already priced-in / bid-up compounder" hypothesis in the direction expected

Contrary to the FM-lens hypothesis the task asked me to test, the top bucket is **the cheapest
bucket, not the most expensive**:

- RELATIVE 5Y: mean PE-percentile (within-date, full universe) top=**0.251**, mid(30-50)=0.430,
  bottom=0.621 — top-bucket names are cheaper on trailing PE than every other bucket, not more
  expensive. [DATA]
- ABSOLUTE 5Y: median trailing PE falls monotonically bucket-to-bucket, 26.3x (bottom) → **13.1x**
  (top) — same direction, sharper. [DATA]

But the model's **forward** valuation view inverts this: `PE_fair` and `rerating` (its own
implied fair-multiple and expected re-rating) climb monotonically to their maximum in the top
bucket (fair PE 43.4x on a 13.1x current price = ~1.55x rerating expected, the single highest of
any bucket), and `g` (expected growth) is also monotonically highest in the top bucket (0.349).
[DATA] **So the top bucket is not "quality that's already been bid up" — it is the model's most
extreme cheap-price-plus-huge-expected-re-rating bet**, and those extreme bets are exactly the ones
failing. [INFERENCE]

### 2b. Sector concentration — confirms a cyclical/commodity tilt, not a diversified quality tilt

Top-bucket sector share vs the scored-universe base rate (percentage-point over/under-weight):

| Sector | base % | top(>75) % | top − base | mid(30-50) − base |
|---|---|---|---|---|
| Metals & Mining | 3.6 | 8.4 | **+4.8** | −0.3 |
| Oil Gas & Consumable Fuels | 5.0 | 9.0 | **+4.0** | +1.8 |
| Textiles | 2.0 | 4.3 | +2.3 | +0.5 |
| Information Technology | 5.3 | 7.5 | +2.2 | +1.2 |
| Power | 3.6 | 5.6 | +2.0 | +0.3 |
| Capital Goods | 10.6 | 12.0 | +1.4 | −1.2 |
| Consumer Durables | 6.2 | **1.4** | **−4.8** | +0.4 |
| Healthcare | 9.8 | **5.1** | **−4.7** | −0.7 |
| Fast Moving Consumer Goods | 8.5 | **5.3** | **−3.3** | +0.1 |
| Consumer Services | 3.0 | 0.8 | −2.2 | −2.0 |

The top bucket over-indexes hard on classic earnings-cyclical/commodity sectors (Metals & Mining,
Oil & Gas, Power, Capital Goods) and under-indexes defensive quality/consumer sectors (Healthcare,
Consumer Durables, FMCG) *relative to the mid bucket, which is comparatively balanced* — mid
bucket's biggest tilt is Chemicals (+3.8pp), and it does not show the Healthcare/Consumer Durables
underweight the top bucket shows. [DATA] Cyclicals trading on temporarily-depressed trailing PE
with a recent earnings/margin upswing is the textbook profile that a trailing-quarters "confirmed
acceleration" metric (`composite_v2_confirmed`, `sub_op_persistent`) cannot distinguish from a
genuinely durable structural grower — it has no mechanism to tell "commodity cycle at/near peak"
from "structurally compounding business." [INFERENCE]

### 2c. Market cap — REJECTS the large-cap-crowding hypothesis

Mean `mktcap_log` is **lower** in the top bucket than every other bucket (24.60 top vs 24.91-25.12
elsewhere, absolute scorecard; RELATIVE shows the same ordering: top=24.57, mid=25.04, bottom=25.11).
[DATA] The failure is not "everyone's favorite large-cap compounder, no room left to re-rate" — if
anything the top bucket skews smaller-cap, where a "confirmed growth acceleration" read is more
likely to be built on a thinner, noisier trailing-earnings base. [INFERENCE]

## 3. Sub-component ablation — does growth-longevity specifically define the bad bucket?

Rebuilt `sr_5Y`, `abs_merit_5Y`, `composite_5Y` **excluding growth-longevity entirely from the
ranking construction** (reusing `build_rel_score_5Y.py`'s own leg objects and
`weighted_combine`/`rank_pct_within_date` functions — same universe gate, same other 7 legs,
renormalized weights), then re-bucketed **on the alternate score** (this redefines *which names
land in which bucket*, not just a diagnostic IC delta):

| bucket | WITH growth-longevity (current) mean fwd ret | WITHOUT growth-longevity mean fwd ret |
|---|---|---|
| <0 | 1.543 | 1.435 |
| 0-30 | 1.777 | 1.679 |
| 30-50 | 1.783 | 1.864 |
| 50-75 | 1.761 | **2.169** (new best bucket) |
| >75 | 1.765 | 1.904 |

Top-bucket (>75) membership overlap between the two constructions: **55.2%** — removing one
component (weighted 2.0× in `sr_5Y`, tied-highest at 0.45 in `abs_merit_5Y`) changes who is in the
top bucket for **nearly half** the names. [DATA]

Without growth-longevity, the best bucket moves from mid (30-50, 1.783) to upper-mid (50-75,
2.169) — a materially better and more usable "top of book" — though a smaller top-end dip remains
(>75 at 1.904, still below 50-75), most plausibly attributable to `value_EY`'s own pooled
(non-sector-neutral) ranking in `abs_merit_5Y` also pulling in some of the same cheap-cyclical
names. Growth-longevity is the single largest contributor to the inversion, but not the entire
story. [INFERENCE]

## 4. Single-episode-artifact check

Split the 162 scored+realized dates into three ~60-month non-overlapping epochs (matching S3's own
"~1.5-2 independent 5Y windows" characterization):

- **Epoch 0 (2007-05→2012-04, n=60 dates but only ~121 total scored rows):** degenerate —
  pre-2012 fundamentals coverage is thin (disclosed in S3/blueprint), several buckets have n≤7 and
  hit_rate literally 0 or undefined. Not usable for any conclusion. [DATA]
- **Epoch 1 (2012-05→2017-04, n=60 dates, ~12,300 rows):** hit-rate <0=0.470, 0-30=0.538,
  **30-50=0.570 (peak)**, 50-75=0.513, >75=0.503 — inverted-U reproduces cleanly within this
  single non-overlapping window on its own. [DATA]
- **Epoch 2 (2017-05→2020-10, n=42 dates, ~14,450 rows):** hit-rate <0=0.480, **0-30=0.496,
  30-50=0.539**, 50-75=0.532, >75=0.517 — non-monotonic again, top bucket again not the best.
  [DATA]

**The inverted-U appears independently in both usable non-overlapping ~5-year windows** (2012-17
and 2017-20), which are genuinely different market regimes (the first spans the 2013 taper-tantrum
recovery through demonetization; the second spans the 2018 NBFC crisis through COVID). This is
evidence *against* the single-bad-episode hypothesis — a true one-off artifact (e.g., one GFC-era
cohort of names) would not be expected to reproduce in two disjoint later regimes with different
macro drivers. [INFERENCE] It does not, however, rule out that "extreme growth-longevity + cheap
trailing PE mis-timing a commodity cycle" is *itself* a recurring-but-still-narrow phenomenon
(section 2b's sector concentration is consistent with this every cycle, not a single episode).

## 5. Verdict

**(a) Real economic effect, amplified into a first-order problem by a construction choice that the
blueprint itself mandated.** [OPINION — my synthesis, evidence above]

This is not simply "noise from too few 5Y windows" — the pattern (i) reproduces in both usable
non-overlapping epochs, (ii) is concentrated in a specific, economically coherent set of sectors
(commodity/capex cyclicals), (iii) is REJECTED as a valuation-crowding story (top bucket is the
*cheapest* bucket on trailing PE, and *smallest*-cap, exactly the opposite of "everyone's favorite
expensive large-cap compounder"), and (iv) responds in the expected direction to a targeted
ablation (removing growth-longevity from the ranking construction materially improves, though does
not perfectly fix, bucket monotonicity, and changes top-bucket membership for ~45% of names).

The mechanism, most likely: `sub_op_persistent`/`composite_v2_confirmed` measure earnings/margin
acceleration **confirmed in recently reported quarters**, with no mechanism to separate a
structurally durable grower from a cyclical/commodity name at or near an earnings-cycle peak — and
a name at a cyclical peak *also* screens cheap on trailing PE (the classic value-trap setup,
mirrored here as a growth-trap: recent-quarters acceleration mistaken for durability). The
blueprint's own 2.0×/0.45 overweight of this leg at 5Y (`SCORECARD_BLUEPRINT.md §2.3`, explicitly
mandated on the FM logic that "momentum barely matters, valuation + growth-longevity drive 5Y
returns") is precisely what pushes these names to the extreme top of the score, where the
mis-timing is most concentrated.

**FM-lens reconciliation:** the task's suggested framing ("strong-but-not-extreme growth at a
reasonable multiple beats the market's most-loved compounders, already bid up") is directionally
right in spirit — moderate buckets (30-50/50-75) do beat the extreme bucket — but the mechanism is
not "bid-up compounder." It is closer to a mirror-image, equally well-known equity pattern:
**stocks with the single most extreme recent-quarters growth confirmation are the least reliable
predictors of continued growth** (mean-reversion in reported growth rates, most acute in cyclical
sectors), not because they are expensive, but because the growth read itself is least trustworthy
at the extreme. A PM would recognize this as "don't buy the steepest hockey-stick, buy the
steady compounder" — same practical lesson, different diagnosis than "overpriced."

**Recommended fix (for the Principal/CIO, not self-authorizing a construction change under this
builder's mandate — blueprint §5 locks the leg list):** dampen growth-longevity's influence at the
extreme tail rather than treating it linearly — e.g., winsorize/concave-transform
`composite_v2_confirmed`/`sub_op_persistent` before the 2.0×/0.45 weighting so the single most
extreme acceleration reading does not dominate the rank, or add a sector-cyclicality discount
specifically for the four over-represented sectors (Metals & Mining, Oil & Gas, Power, Capital
Goods) before scoring growth-longevity. This is the 5Y-horizon analogue of a valuation-ceiling
rule (R7/`EXIT_TRIGGER_SPEC.md`, not yet built) but on the **growth-extrapolation** axis rather
than the price axis — a "growth-realism ceiling," not a "price ceiling," since these names are
already cheap on price.

**What this verdict is NOT saying:** it is not a claim that growth-longevity has zero value, nor
that the sr_5Y/abs_merit_5Y composites are unusable — the mid/upper-mid buckets (30-50, 50-75) are
functioning as intended (monotonic hit-rate improvement over the bottom bucket, per S8). The
specific, narrow, and fixable problem is the top decile-ish tail of the growth-longevity-heavy
extreme.

## 6. Honest limitations [OPINION — disclosure]

- Only 2 of 3 non-overlapping epochs are usable (epoch 0 pre-2012 is data-thin); "reproduces in
  both usable epochs" is n=2, not a large-sample confirmation — consistent with, but not able to
  fully rule out, some remaining regime-dependence.
- The sector-concentration evidence is descriptive (percentage-point tilts), not a formal test;
  I did not run a sector-neutralized version of growth-longevity itself to quantify how much of
  the effect that specific fix would remove (natural next cheap-test, not done here — out of this
  investigation's scope, which was diagnosis not a rebuild).
- `EXIT_TRIGGER_SPEC.md` does not exist yet, so the R7 valuation-ceiling link is a forward pointer,
  not a validated cross-reference.

## Files

- Analysis script: `C:\Users\SHREYA~1.1GU\AppData\Local\Temp\claude\...\scratchpad\investigate_5y_inverted_u.py`
  (run twice, byte-identical console output and diagnostics both times — no RNG in this analysis).
- Diagnostics JSON: same scratchpad dir, `investigation_diag.json`.
- No source parquets or scoring scripts were modified — read-only investigation.
