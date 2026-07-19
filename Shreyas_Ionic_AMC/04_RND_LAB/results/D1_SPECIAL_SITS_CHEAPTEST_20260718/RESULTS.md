# D1 Special-Situations cheap-test: buyback board-meeting intimations

Real events (usable): 252 | distinct symbols: 161 | placebo draws: 2520

| window | real mean | real median | real t-stat (vs 0) | placebo mean | diff (real-placebo) | Welch t-stat (real vs placebo) | p-value |
|---|---|---|---|---|---|---|---|
| +1d | 0.0085 | 0.0021 | 3.33 | 0.0011 | 0.0074 | 2.83 | 0.0049 |
| +5d | 0.0201 | 0.0094 | 3.77 | 0.0077 | 0.0124 | 2.25 | 0.0250 |
| +10d | 0.0205 | 0.0075 | 3.21 | 0.0158 | 0.0047 | 0.66 | 0.5084 |
| +20d | 0.0228 | 0.0137 | 2.89 | 0.0282 | -0.0054 | -0.62 | 0.5348 |

## Anticipation window (t-5 -> t0, context only, NOT tradeable pre-event)
pre_5d mean=0.0446, median=0.0451, n=252, t=7.96, p=0.0000

## Lag-robustness check (entry shifted +1 extra trading day)
| window | lag1 real mean | lag1 t-stat (vs 0) | lag1 vs placebo diff | lag1 t (vs placebo) | lag1 p |
|---|---|---|---|---|---|
| +1d | 0.0017 | 0.65 | 0.0006 | 0.22 | 0.8255 |
| +5d | 0.0125 | 2.39 | 0.0048 | 0.89 | 0.3741 |
| +10d | 0.0109 | 1.81 | -0.0049 | -0.72 | 0.4738 |
| +20d | 0.0178 | 2.26 | -0.0104 | -1.19 | 0.2332 |
