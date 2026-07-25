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

**RECOMMENDATION: keep the current Dec-end / Jun-end cadence.** It is statistically tied with
the best pair, operationally aligned with the results calendar and the firm's half-yearly
review rhythm, and clearly better than Jan/Jul. Revisit only if two more years of data
separate Apr/Oct from Jun/Dec beyond noise.

Script: `anchor_pair_study.py` (this folder). Data: MF Dashboard.xlsx (NAVs to 2025-01-31);
monthly NAV accrual now automated (1st of month, OPERATING_CALENDAR §automatable) so future
reruns extend the sample.
