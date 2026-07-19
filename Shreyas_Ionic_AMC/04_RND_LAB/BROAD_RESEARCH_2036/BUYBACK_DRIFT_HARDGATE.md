# Buyback board-meeting-intimation drift — Gate-4 hard-gate battery
**By:** Dr. Sameer Bhat (Overfit & Sensitivity Analyst, E-027) | **Date:** 2026-07-18
**Trigger:** D1_SPECIAL_SITUATIONS_FIRSTCUT.md (Prof. Aditya Verma, 2026-07-18) — the first genuinely
new, positive finding across tonight's broad sweep (+1d excess +0.74% p=0.005, +5d excess +1.24%
p=0.025, evaporating by +10-20d, survives sibling's own lag test). Standard-practice dedicated
skeptical pass, same rigor as `REVERS_5D_VERIFICATION.md`.

**Pre-registered thresholds (set before running anything below):** placebo-shuffle = real result
must clearly separate from a 5-draw randomized-date placebo distribution (z≳2 soft bar, no single
draw should beat the real result); era-split = no single year should carry the entire effect;
drop-one-year = no single year's removal should collapse significance (p crossing 0.05) or take the
mean below ~50% of baseline; confound = the real-vs-placebo excess must not be explained away by (or
concentrated entirely in) momentum or size/liquidity tier. Any one miss on the tradeable horizon
(+5d, the only one that was ever gross-of-cost positive at 2x stress per the sibling's memo) is
grounds for a hard flag; a miss confined to +1d (already sub-2x-cost per the sibling) is a lesser
flag on an already-marginal claim.

## [DATA] Lineage / reproduction
- Reused verbatim: `Shreyas_Ionic_AMC/04_RND_LAB/results/D1_SPECIAL_SITS_CHEAPTEST_20260718/events_with_returns.csv`
  (252 events / 161 symbols, `bm_timestamp` PIT anchor, entry_pos already computed) — no re-derivation
  of the event definition, no edits to the sibling's script or outputs, per "verify from disk."
- Baseline reproduced exactly from the sibling's saved event table: +1d mean +0.85% (t=3.33), +5d mean
  +2.01% (t=3.77) — matches `RESULTS.md` to the row.
- New script (not the sibling's): `buyback_hardgate.py` (scratchpad, available on request) — imports
  the sibling's saved event table and the same PIT price panel
  (`datasets/derived/pit_union_panel_v1/close_panel_price_v11.parquet`), rebuilds the same exclusion
  windows the sibling used, and adds the five tests below. Also pulls `ALPHA_RANKER/rnd/panel/panel_pit.parquet`
  (`mktcap_log`, monthly snapshots) and `ALPHA_RANKER/data/prices/{SYM}.parquet` (OHLCV, 750-name liquid
  universe, coverage starts ~2021-07) for the confound and liquidity checks.
- Outputs saved alongside the sibling's files: `hardgate_shuffle_draws.csv`, `hardgate_shuffle_summary.csv`,
  `hardgate_era_split.csv`, `hardgate_drop_one_year.csv`, `hardgate_confound.csv`, `hardgate_pooled_confound.csv`,
  `hardgate_adv_check.csv` — all under `results/D1_SPECIAL_SITS_CHEAPTEST_20260718/`.

## 1. Randomized-date placebo shuffle (5 draws, seed=42)
Beyond the sibling's single 10-draws-per-event placebo pool, five *independent* one-draw-per-event
placebo sets (same symbols, random non-event trading days from that symbol's own history, same ±15-day
exclusion around any real event) — testing whether the excess-over-placebo finding is stable across
independent random draws, not an artifact of the sibling's one specific draw.

| window | real mean | placebo-draws mean | placebo-draws std | z | draws beating real (of 5) | raw draws |
|---|---|---|---|---|---|---|
| +1d | +0.85% | +0.05% | 0.20% | **4.09** | **0/5** | 0.10%, 0.18%, 0.20%, −0.29%, 0.03% |
| +5d | +2.01% | +0.33% | 0.28% | **5.99** | **0/5** | 0.01%, 0.51%, 0.26%, 0.70%, 0.14% |
| +10d | +2.05% | +0.62% | 0.33% | 4.32 | 0/5 | 0.48%, 1.04%, 0.15%, 0.76%, 0.64% |
| +20d | +2.28% | +1.59% | 0.30% | 2.26 | 0/5 | 1.74%, 1.88%, 1.08%, 1.63%, 1.62% |

**PASS, cleanly.** This is a materially stronger placebo separation than the `revers_5d` case (z≈1.26,
1/5 draws beat the real result, automatic FAIL) — no draw out of 20 total (5 windows × ... well 4
windows × 5 draws = 20 cells, focusing on the tradeable +1d/+5d) comes anywhere near the real mean.
The announcement-day/week reaction is not a base-rate artifact of "these 161 symbols tend to drift
up on random days."

## 2. Era-split by year (bm_date)

| window | 2020 (n=56) | 2021 (n=40) | 2022 (n=60) | 2023 (n=35) | 2024 (n=41) | 2025 (n=20) |
|---|---|---|---|---|---|---|
| +1d mean (t, p) | +2.43% (3.01, **0.004**) | +1.14% (1.46, 0.15) | +0.03% (0.12, 0.90) | −0.07% (−0.19, 0.85) | +0.17% (0.38, 0.70) | +1.36% (1.88, 0.076) |
| +5d mean (t, p) | +3.25% (1.88, 0.065) | +2.07% (1.99, 0.054) | +0.67% (0.94, 0.35) | +0.93% (0.91, 0.37) | +2.90% (2.57, **0.014**) | +2.47% (1.17, 0.26) |

**+1d is heavily era-concentrated: only 2020 clears p<0.05 on its own** (2020-only p=0.004; every
other year individually is non-significant, p=0.076-0.90). This lines up exactly with this desk's
standing lesson ("2026-07: 90%+ win rates in 2024-26 [and, per this result, 2020-26] samples are
regime artifacts until proven otherwise") — 2020 was the COVID-crash-recovery year, a period of
unusually strong mean-reversion/re-rating across the board, and buyback-considering firms are not
obviously exempt from that.
**+5d is more evenly spread** — no single year is required for overall significance (see drop-one
below), though 2022/2023 are individually weak.

## 3. Drop-one-year robustness

| window | full (n=252) | drop 2020 | drop 2021 | drop 2022 | drop 2023 | drop 2024 | drop 2025 |
|---|---|---|---|---|---|---|---|
| +1d mean | +0.85% | **+0.40%** | +0.80% | +1.11% | +1.00% | +0.99% | +0.81% |
| +1d % of full | 100% | **47%** | 94% | 130% | 118% | 116% | 95% |
| +1d p | 0.001 | **0.077** | 0.003 | 0.001 | 0.001 | 0.001 | 0.003 |
| +5d mean | +2.01% | +1.65% | +2.00% | +2.43% | +2.18% | +1.83% | +1.97% |
| +5d % of full | 100% | 82% | 99% | 121% | 109% | 91% | 98% |
| +5d p | 0.0002 | 0.0006 | 0.0011 | 0.0003 | 0.0003 | 0.0025 | 0.0004 |

**+1d: FAIL.** Dropping 2020 alone cuts the mean to 47% of baseline and pushes significance from
p=0.001 to p=0.077 — the exact "single year does most of the work" signature that killed `revers_5d`
(there: 2023 removal, Sharpe 1.08→0.55, -49%). Here it is 2020, and the +1d claim does not survive
its removal.
**+5d: PASS.** Every drop-one-year variant stays significant at p<0.003 and retains 82-121% of the
baseline mean — no single year is load-bearing for the 5-day horizon.

## 4. Confound check — momentum and size/liquidity tier
Two independent probes, both built directly from the price panel / `panel_pit.parquet` (PIT monthly
`mktcap_log` snapshots, asof-merged strictly on-or-before the event/placebo date; trailing momentum =
126-trading-day return ending 21 days before entry, skip-a-month convention, computed from the same
close panel the sibling used):

**(a) Momentum tercile split, real events only** — rules out "momentum in disguise":

| momentum tercile | n | fwd_1d mean | fwd_5d mean |
|---|---|---|---|
| low_mom | 84 | +1.27% | +2.71% |
| mid_mom | 83 | +0.44% | +1.23% |
| high_mom | 83 | +0.93% | +2.26% |

No concentration in the high-momentum tercile — if anything the **low**-momentum tercile shows the
largest effect. **Momentum-in-disguise: REJECTED.**

**(b) Size/liquidity-coverage split, real events only** — 61 of 161 symbols (38%) are entirely absent
from `panel_pit.parquet` (the firm's broader factor-panel universe), leaving 110 of 252 events (44%)
outside standard size/liquidity coverage entirely. Comparing these two groups directly (real events
only):

| group | n | fwd_1d mean | fwd_5d mean |
|---|---|---|---|
| **not** in panel_pit (thinner/uncovered names) | 110 | **+1.49%** | **+2.50%** |
| in panel_pit (broader covered universe) | 142 | +0.36% | +1.63% |
| Welch t / p, fwd_1d | | **t=-2.10, p=0.037** | |
| Welch t / p, fwd_5d | | t=-0.78, p=0.44 | |

**+1d excess is significantly larger in the thinner/uncovered names (p=0.037) — this is a genuine
size/coverage confound, not momentum.** Re-running the real-vs-placebo comparison restricted to ONLY
the panel_pit-covered (broader-universe) names:

| window | real (covered, n=142) | placebo (covered, n=1097) | t | p |
|---|---|---|---|---|
| +1d | +0.36% | +0.11% | 0.90 | **0.37 (not significant)** |
| +5d | +1.63% | +0.56% | 1.69 | **0.093 (marginal, not conventionally significant)** |

Within tercile-of-size-among-the-covered-subset itself there is no clean small→large monotonic
pattern (fwd_5d: small +1.49%, mid +1.60%, large +1.80%) — the confound is **coverage/liquidity tier**
(covered vs not), not smoothly "smaller cap = bigger effect" once inside the covered group. A pooled
OLS (`fwd_Nd ~ is_real + mom_pre + mktcap_log`, HC1 robust SE, restricted to the mktcap-available
subsample, n=1221) shows the same thing from a different angle: `is_real` coefficient is not
significant with or without momentum/size controls (+1d: coef 0.23-0.26%, p=0.36-0.40; +5d: coef
1.04-1.08%, p=0.087-0.097) — but this regression is already run on the size-restricted subsample, so
it is confirming, not adding to, the split-sample finding above.

**Reading this:** the headline full-sample significance is disproportionately carried by symbols
outside the firm's standard liquid/broad-universe coverage. At +1d this is a clean FAIL (p=0.37 within
the covered universe, vs p=0.005 headline). At +5d it survives directionally (real ~3x placebo) but
only at a marginal p=0.093 in the covered subsample (n=142, likely underpowered rather than cleanly
null) — not a clean pass, not a clean kill.

## 5. Liquidity / capacity check
`ALPHA_RANKER/data/prices/{SYM}.parquet` (the firm's 750-name liquid-universe OHLCV source, coverage
from ~2021-07) matched only **79 of 252 events (31%)** — i.e., 69% of the raw buyback-announcement
sample sits outside a standard curated liquid-name universe entirely (partly a coverage-window
artifact for pre-mid-2021 events, but the overlap with the panel_pit-uncovered group above is strong:
92 of 110 panel_pit-uncovered events also lack ADV data). Among the 79 events where ADV IS computable
(20-day pre-event average traded value):

| stat | value |
|---|---|
| median ADV | ~₹35.5 crore/day |
| mean ADV | ~₹142.7 crore/day |
| % events with ADV < ₹5 crore/day | 7.6% |
| % events with ADV < ₹1 crore/day | 1.3% |

Where liquidity data exists, it looks reasonably tradeable at modest size — but that 31% subset is
exactly the more liquid, better-covered tail where §4 shows the statistical effect is weakest
(p=0.37 at +1d, p=0.093 at +5d). The events driving the headline significance are disproportionately
the ones this desk has the LEAST confidence are fillable at any meaningful size (landmine #7b:
thin-volume slippage 2-3x, circuit-lock no-fills — exactly the profile of the uncovered tail).

## DSR/PBO
Not computed, for the same reason as `revers_5d`: this is one construction under scrutiny (not a
searched family), and the battery above already returns independent flags — drop-one-year FAIL and
liquidity-confound FAIL at +1d, marginal confound at +5d — that already determine the certification
outcome. A DSR/PBO pass would not change this verdict. [OPINION] If escalated to a capital
conversation, the honest-trials count (1 construction × 4 windows × 1 lag variant, this hard-gate
pass adds 0 new "trials" since it verifies rather than searches) should still be logged in the family
ledger for the /oos-audit trail.

## Lookahead note (D-028 lens)
No new T1-class finding beyond the sibling's own lag-robustness result (which this memo reproduces
context for but does not re-derive): entry anchored on `bm_timestamp`, not the future `bm_date`, and
the lag-shifted entry collapses the effect almost completely — the correct signature of a genuine,
correctly-dated announcement reaction, not a lookahead artifact. This memo's scope is the five named
hard-gate tests; a full `LOOKAHEAD_CONTROLS.md` T1-T10 filing was not separately re-run since the
sibling's construction and lag test already cover the relevant taxonomy items (PIT anchor choice,
future-date lookahead) and nothing in the tests above (shuffle/era/drop-one/confound/liquidity)
implicates a lookahead mechanism — the confound found is economic (coverage/liquidity tier), not
temporal.

## Verdict: **FRAGILE-AT(liquidity/coverage-tier confound, 2020-era concentration on +1d)**
Not a clean ROBUST pass, and not a full OVERFIT kill either — the tests split cleanly by horizon:

- **+1d claim: effectively dead.** Already sub-2x-cost per the sibling's own memo, it now also fails
  drop-one-year (2020 alone explains more than half the effect, significance collapses on removal)
  AND fails the liquidity-confound test (not significant, p=0.37, once restricted to the
  broader-universe/covered names). Two independent, pre-registered fails on an already-marginal
  claim — do not use the +0.74% number for anything.
- **+5d claim (the only one that was ever thin-positive net of 2x cost, ~+0.2%): survives the
  placebo-shuffle and drop-one-year tests cleanly, is NOT a momentum-in-disguise effect, but rests
  disproportionately on symbols outside the firm's standard liquid-universe coverage** (real-vs-placebo
  within the covered subset alone: p=0.093, not clean significance, real mean nonetheless ~3x
  placebo). Combined with only 31% of the raw sample having verifiable ADV/liquidity data at all, the
  honest capacity-adjusted picture is: this may be a real, small, announcement-week effect, but the
  version of it that is provably tradeable (liquid, covered names) is statistically thinner than the
  headline, and the version that is statistically strongest (thin/uncovered names) is the one least
  likely to survive realistic fills.

**Single most fragile assumption:** that the sibling's full 252-event, 161-symbol sample is a
homogeneous, uniformly tradeable population. It is not — 44% of events sit on names outside the
firm's broader factor-panel universe and 69% sit outside the curated liquid-price universe, and that
exact untracked/illiquid tail is carrying the lion's share of the +1d effect and a material share of
the +5d effect. A capital conversation on this signal must be scoped to the liquid/covered subset from
the start, not the full announcing population, and even then the +5d number should be treated as
marginal (p≈0.09) rather than the headline p=0.025.

## Recommendation
**Keep as a forward-watch candidate for the +5d horizon only, explicitly rescoped to liquid/covered
buyback announcers** (not the full sample) — this is "thin data, partially sound logic, real cracks
under scrutiny," not a clean survive-everything result and not a clean collapse-to-noise kill either.
**Do not carry the +1d number forward in any form** — it fails both drop-one-year and the liquidity
confound independently, on top of already failing the 2x-cost bar in the sibling's own memo.
Natural next cheap step if pursued further: re-run the same battery restricted from the outset to
panel_pit-covered / ADV-available symbols only, rather than testing the confound post hoc, to get a
clean (not underpowered) read on whether p=0.093 at +5d would tighten or evaporate with the full
liquid-only sample properly re-drawn (this hard-gate's covered-subset placebo pool was a filtered
slice of the original 2,520 draws, not a fresh liquid-only placebo construction).

## Files
- Sibling's construction (reused, unedited): `Shreyas_Ionic_AMC/04_RND_LAB/results/D1_SPECIAL_SITS_CHEAPTEST_20260718/`
  (`d1_buyback_cheaptest.py`, `RESULTS.md`, `events_with_returns.csv`, `placebo_draws.csv`, `summary_by_window.csv`).
- This memo's new outputs (same directory): `hardgate_shuffle_draws.csv`, `hardgate_shuffle_summary.csv`,
  `hardgate_era_split.csv`, `hardgate_drop_one_year.csv`, `hardgate_confound.csv`, `hardgate_pooled_confound.csv`,
  `hardgate_adv_check.csv`.
- Data sources used fresh: `ALPHA_RANKER/rnd/panel/panel_pit.parquet` (`mktcap_log`),
  `ALPHA_RANKER/data/prices/{SYM}.parquet` (OHLCV, liquid-universe ADV).
- Script (scratchpad, available on request): `buyback_hardgate.py`.
