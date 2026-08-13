# 6M anchor-pair study — which two month-ends should the MF model run on? (2026-07-26)

**Question (Principal):** we run the fund model twice a year, 6M apart. Which month pair
(Jan/Jul … Jun/Dec) gives the best recommendations? Judge on median + trimmed mean.

**Method:** QFRA-1's exact decision logic (6M downside-capture cutoff → total-capture rank →
BUY top-3; SELL = trailing-12M excess<0 AND quadrant-4) replayed at every month-end anchor
2012-01 … 2024-07 on all 6 category sheets of MF Dashboard.xlsx (small/flexi/large/largemid/
mid/multi, live LO1 cutoffs), forward 6M excess vs the category benchmark. 906 formations.
QFRA-2 uses 3-5y windows and is anchor-insensitive by construction — not the discriminator.

| pair | n | BUY median | BUY trim-mean | B−S spread med | spread trim | hit rate |
|---|---|---|---|---|---|---|
| **04/10 (Apr/Oct)** | 150 | **+2.59%** | **+2.59%** | +2.31% | +2.43% | 66% |
| **06/12 (Jun/Dec)** | 150 | +2.22% | +2.34% | +2.13% | **+2.42%** | 66% |
| 02/08 | 150 | +2.34% | +2.04% | +2.23% | +2.09% | 58% |
| 03/09 | 150 | +1.82% | +2.10% | +1.90% | +1.78% | 55% |
| 01/07 (Jan/Jul) | 156 | +1.31% | +1.77% | +1.77% | +1.88% | 58% |
| 05/11 | 150 | +1.94% | +1.98% | +1.38% | +1.27% | 58% |

**Read:** Apr/Oct ranks first on point estimates; Jun/Dec is a close second (gap ~0.3pp on
medians — NOT statistically meaningful at this n with cross-category correlation; per the
firm's low-t policy we rank on logic + effect size, we don't over-claim). Jan/Jul — the pair
the Principal asked about — is near the BOTTOM on every metric.

**Theory agrees with the top two:** Jun-end sits after the full-year (Mar-quarter) results are
digested; Dec-end after the Sep-quarter/H1 results. Both anchors read capture windows over
fully-informed prices. Jan/Jul anchors sit mid-digestion (Dec-quarter results land mid-Jan–Feb;
Jun-quarter mid-Jul–Aug) — the 6M capture window ends right as new information is landing.

**DESK RECOMMENDATION was keep Dec/Jun (statistical tie). PRINCIPAL RULING (2026-07-26):
"lets keep april and oct" — cadence moves to APR-END / OCT-END, the top pair on every point
estimate (BUY median +2.59% vs +2.22%, hit 66%).** Next model run: Oct-end 2026 (the Dec-2026
run is superseded). Skills (qfra1-rerun, qfra2-rerun, mf-nav-refresh) and OPERATING_CALENDAR
updated same day. Monthly NAV accrual (1st) is unaffected and feeds either cadence.

Script: `anchor_pair_study.py` (this folder). Data: MF Dashboard.xlsx (NAVs to 2025-01-31);
monthly NAV accrual now automated (1st of month, OPERATING_CALENDAR §automatable) so future
reruns extend the sample.

---

# EXTENSION, 2026-08-04 (Principal asks: untrimmed results, smallcap-only, month-end or start?)

Script: `anchor_pair_study_ext.py` · output: `ANCHOR_PAIR_EXT.csv`, `ext_run.log`.
Identical formation logic — **906 formations reconciled exactly**, and the median / 10%-trimmed
columns reproduce the table above to the decimal.

### Q: is the anchor month-END or month-START?
**Month-END.** `pd.date_range("2012-01-31", "2024-07-31", freq="ME")` — every anchor is a
month-end close, and the 6M capture window is `(t − 6 months, t]`. "Apr/Oct" therefore means the
model runs on data through **30-April** and **31-October**. It has never meant 1-Apr / 1-Oct.
Practically: the April capture window is Nov→Apr and the review is taken in early May; the October
window is May→Oct, reviewed in early November.

### Q: 1-April vs 30-April (and the same for October / every other month)? TESTED. [DATA]
Script: `anchor_monthstart_vs_monthend.py` · output `ANCHOR_MS_VS_ME.csv`, log `ms_vs_me.log`.
Both conventions produce exactly **906 formations**, so they are directly comparable.

**30-April wins clearly, and it is not close on the untrimmable measure:**

| Apr/Oct anchored on | 10% trim | median | hit rate |
|---|---|---|---|
| **month-END (30-Apr / 31-Oct)** | **+2.59%** | **+2.59%** | **66.0%** |
| month-START (1-Apr / 1-Oct) | +2.00% | +1.92% | 53.3% |
| month-END advantage | **+0.59pp** | +0.67pp | **+12.7pp** |

**WHY, and it is mechanical:** the capture window is `(t − 6 months, t]`, so an anchor of 1-Apr closes
its window on the last trading day ≤ 1-Apr — i.e. it reads **essentially the same data as a 31-Mar
anchor**. Month-start is not a small tweak; it is a one-month backward shift of the whole window.
The data confirms the correspondence almost exactly — month-START month *m* ≈ month-END month *m−1*:

| month-START pair | its 10% trim | ≈ month-END pair | that trim |
|---|---|---|---|
| May/Nov | +2.64% | **Apr/Oct** | +2.59% |
| Apr/Oct | +2.00% | Mar/Sep | +2.10% |
| Mar/Sep | +2.15% | Feb/Aug | +2.04% |
| Feb/Aug | +1.72% | Jan/Jul | +1.77% |

**[INFERENCE] The real conclusion: the optimum is the same actual window under either convention —
the six months ending end-April / end-October.** Under month-start labelling the best pair becomes
May/Nov (+2.64% trim, 64% hit), which *is* the end-April window wearing a different name. So the
convention does not change the answer, only the label; and under the convention our code actually
uses (the workbook's `<cat>2` engine sheets are month-end anchored), the correct label is **Apr/Oct**.

**This also gives the earnings-digestion theory direct empirical support**, which it previously lacked:
1-April sits before the March-quarter/full-year results are out, and it scores 12.7pp worse on hit
rate than 30-April, which sits after them. The theory and the measurement now agree.

### PRESENTED MEASURE = the 10% TRIMMED MEAN (Principal ruling 2026-08-04)
This is the statistic that goes on the QFRA-2 committee deck. **It is pre-registered, not
post-hoc:** the Principal's original framing on 2026-07-26 was *"Judge on median + trimmed mean"* —
specified **before** the study ran (see the question at the top of this file). On both
pre-registered measures the ranking is the same and the conclusion holds:

| Measure | 1st | last |
|---|---|---|
| 10% trimmed mean (presented) | **Apr/Oct +2.59%** | Jan/Jul +1.77% |
| Median (also pre-registered) | **Apr/Oct +2.59%** | Jan/Jul +1.31% |
| Plain untrimmed mean (not specified in advance) | Jun/Dec +2.65% | Feb/Aug +1.99% |

The untrimmed mean is the **only** measure that disagrees, by 0.03pp, and it is the one most
exposed to single-formation outliers — which is exactly why a trimmed statistic was specified up
front. [OPINION] Presenting the trimmed mean is therefore legitimate, **but the deck must still show
the untrimmed mean** (it is drawn as a gold tick on the chart) — the defence is "we pre-registered
the measure and we show you the one that disagrees", never "the measure we picked says we win".
Chart: `09_PRODUCT/scripts/chart_anchor_pair.py` → `pr_template/out/anchor_pair_evidence.png`.

### Q: what happens without trimming? — **it changes the ranking.** [DATA]

| Pair | BUY median | **BUY plain mean** | BUY 10%-trim | Hit rate |
|---|---|---|---|---|
| **Apr / Oct** | **+2.59%** | +2.62% | **+2.59%** | **66.0%** |
| Feb / Aug | +2.34% | +1.99% | +2.04% | 58.0% |
| Jun / Dec | +2.22% | **+2.65%** | +2.34% | **66.0%** |
| May / Nov | +1.94% | +1.94% | +1.98% | 58.0% |
| Mar / Sep | +1.82% | +2.08% | +2.10% | 54.7% |
| Jan / Jul | +1.31% | +2.20% | +1.77% | 57.7% |

**Two claims must be retracted from the earlier write-up:**
1. ~~"Apr/Oct ranks first on point estimates"~~ → **first on the median and the trimmed mean, but
   Jun/Dec wins the plain untrimmed mean, +2.65% vs +2.62%.** A 0.03pp gap is noise, but the
   sentence "leads on every point estimate" is no longer true and must not be used in a deck.
2. ~~"Jan/Jul is near the BOTTOM on every metric"~~ → **bottom on the median (+1.31%, clearly
   last) but 3rd on the plain mean (+2.20%).** Jan/Jul's distribution is carried by a few large
   winners while the typical formation is poor — which is exactly what a median-vs-mean gap of
   +0.89pp means. Say "worst in the typical case", not "worst on every metric".

**What survives untrimmed, and is therefore the load-bearing evidence:** the **hit rate**, which
has no trimming parameter at all. **Apr/Oct and Jun/Dec both 66%; the other four 54.7–58%.** Two
good anchors, four mediocre ones, ~8pp apart. [OPINION] The honest framing for Apr/Oct over
Jun/Dec is *robustness*: Apr/Oct wins where the typical formation is measured (median, trimmed),
Jun/Dec only on the raw mean, i.e. its edge is outlier-carried. That is a reason to prefer
Apr/Oct, not proof that it is better.

### Q: smallcap only, trimmed vs untrimmed [DATA]

| Pair | n | BUY median | BUY plain mean | BUY 10%-trim | Hit |
|---|---|---|---|---|---|
| Mar / Sep | 25 | +3.94% | +2.72% | +3.19% | 68.0% |
| Feb / Aug | 25 | +3.77% | +3.05% | +3.28% | 72.0% |
| **Apr / Oct** | 25 | **+3.49%** | **+2.80%** | **+2.91%** | **72.0%** |
| May / Nov | 25 | +3.45% | +2.08% | +2.55% | 68.0% |
| Jun / Dec | 25 | +3.34% | +2.98% | +3.23% | 76.0% |
| Jan / Jul | 26 | +1.08% | +2.21% | +1.99% | 69.2% |

**Smallcap does NOT single out Apr/Oct — it is 3rd of 6 on the median and 4th on the plain mean,
and Jun/Dec beats it on hit rate (76% vs 72%).** n=25 per pair, so none of these gaps are
meaningful. [OPINION] Do not put a smallcap-only anchor claim in a deck; the pooled 906-formation
result is the defensible one. Smallcap's real message is that *every* anchor works there
(+1.08% to +3.94% median, 68–76% hit) — it is a rising-tide category, consistent with QFRA-2's
own finding that a blind pick also wins in Small.

Apr/Oct BUY cohort by category (n=25 each): flexi +2.61 med / 84% hit · mid +3.48 / 56% ·
small +3.49 / 72% · large +3.32 / 52% · multi +3.12 / 64% · **largemid +0.66 / 68%** (the
weakest, and the one category where the median and mean both sag).

### The SELL leg — measured for the first time, and it is WEAK [DATA]

The Principal's premise was "QFRA-1 sell has backtest credibility". The 906-formation replay
does **not** support that. `sell_hit` = share of formations where the SELL cohort went on to
**underperform** its benchmark (higher = the sell call worked):

| Pair | SELL median | SELL plain mean | SELL 10%-trim | **sell_hit** |
|---|---|---|---|---|
| Apr / Oct | −0.57% | −0.13% | −0.22% | **49.3%** |
| Jun / Dec | −0.09% | **+0.22%** | +0.04% | 47.3% |
| Feb / Aug | −0.19% | −0.07% | −0.16% | 44.7% |
| May / Nov | −0.00% | **+0.30%** | +0.17% | 45.3% |
| Mar / Sep | +0.15% | −0.41% | +0.04% | 45.3% |
| Jan / Jul | +0.02% | **+0.32%** | +0.12% | 44.9% |

**`sell_hit` is below 50% in all six pairs.** The funds QFRA-1 flags for exit went on to
*outperform* slightly more often than not, and on three of six anchors the sold cohort's mean
excess was **positive**. Apr/Oct is the best of the six on both median (−0.57%) and hit (49.3%),
so the cadence choice does help the sell leg — but the leg itself is close to a coin flip.

Smallcap is the exception: Apr/Oct SELL median **−1.05%**, plain mean **−0.92%**, trimmed
**−1.72%**, hit 44% — consistently negative across all three central measures. So in smallcap the
sell fires rarely-right but very-right (tail-weighted, genuine expectancy); pooled, it is noise.

**Bearing on the client Sell rule:** [OPINION] the BUY leg is what this framework has evidence
for (+2.59% median, 66% hit, robust to trimming). Basing a client Sell on the SELL leg inherits a
~coin-flip signal, so a QFRA-1 Sell should stand on the analyst's stated reason, with the capture
statistic as support — never on "the backtest says sell". This is now written into
`09_PRODUCT/scripts/fund_ctx_adapter.py:merge_calls()` and both QFRA skills.
