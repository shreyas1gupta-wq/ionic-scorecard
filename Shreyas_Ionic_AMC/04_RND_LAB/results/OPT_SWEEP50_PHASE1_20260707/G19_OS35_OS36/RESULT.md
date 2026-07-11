# G19 — OS-35 & OS-36 — Phase-1 fast triage (Arjun Rao, Quant)
_Campaign OPT-SWEEP-50 · 2026-07-07 · FAST/CHEAP pass, 1x COST_STANDARDS, next-liquid-quote fill, edge in Rs-points + %-spot (never %-premium)._

## Data lineage
- NIFTY index options 1-min: `intraday_options_strategy/datasets/raw/hf_index_options_1m/options/NIFTY/*.parquet` — 262 weekly expiries, 2021-05-27 -> 2026-06-09.
- NIFTY spot 1-min: `.../hf_index_options_1m/index/NIFTY.parquet` (477,738 rows), filtered >=09:15 (auction bug).
- INDIA VIX daily: `datasets/index_daily/india_vix.parquet` (2,591 rows, 2016->).
- Regime break VERIFIED on disk: last Thursday expiry 2025-08-28, first Tuesday expiry 2025-09-02. PRE=222 expiries / POST(Tue)=40.
- Trade tapes: `os35_trades.csv` (259 rows), `os36_trades.csv` (254 rows).
- Cost model (points/unit, 1x): slip 0.25%/side liquid-ATM-index, STT 0.1% sell, exch 0.035%/side, GST 18%, brokerage Rs20/order (2/leg RT), stamp 0.003% buy, SEBI Rs10/cr. Lot=75.

## OS-35 — expiry-day 0DTE ATM straddle short (pin capture), Tuesday-regime target
Entry: sell ATM CE+PE at first liquid quote >=09:20 on expiry day. Exit: buy-to-close ~15:25 (fallback intrinsic-at-settle). 0 no-fills.

| Slice | n | mean net (pts) | %-spot | median | winrate | perTrade Sharpe | t-stat |
|---|---|---|---|---|---|---|---|
| ALL pooled | 259 | +1.36 | +0.0045% | 13.51 | 59% | 0.015 | 0.24 |
| PRE (Thu <2025-09-02) | 222 | **-1.31** | **-0.0058%** | 12.93 | 58% | -0.014 | -0.21 |
| POST (Tue >=2025-09-02) | 37 | **+17.33** | **+0.0662%** | 19.15 | 68% | 0.199 | 1.21 |

- Pre/post split (PRIMARY kill test): edge is NOT a pooling artifact — pooling DILUTES it. The edge lives ENTIRELY in the target Tuesday regime; the identical structure was net-NEGATIVE across 222 Thursday expiries.
- Cost is not binding (post: gross 19.46 vs cost 2.13 pts). Robust to fill: net vs intrinsic-exit nearly identical (17.33 vs 17.31).
- Degenerate/tail flags: median>>mean (fat left tail, classic 0DTE pennies-vs-steamroller). Post regime already carries 3 steamroller days (2026-01-20 -212, 2026-05-12 -196, 2026-04-07 -183 pts ~= -0.83%/spot each); +17 mean rides 34 small winners vs 3 big losers in a **calm-vol window**, tail under-sampled.

**VERDICT: SURVIVE (MARGINAL — DO NOT ADVANCE).** Does not trip any pre-registered Phase-1 kill (positive in target Tuesday regime in both units; not a pooling artifact; fill-robust). BUT n=37, t=1.21 (insignificant), tail barely sampled, and the Tuesday edge is confounded with the recent low-vol period. Not worth a Phase-2 slot ahead of the Family-A VRP survivors. Route to expiry_seasonality owner to accrue Tuesday-regime sample.
**Weakest assumption:** the whole edge = 37 calm-window Tuesday trades; one bad expiry-day trend prints -0.8%/spot and wipes ~12 winners.

## OS-36 — results-cluster (Jan/Apr/Jul/Oct) index strangle short
~1SD (16-delta proxy via VIX) weekly strangle, entry Monday 09:20, hold to expiry (intrinsic settle). Cluster = expiry month in {1,4,7,10}. 1 no-fill.

| Slice | n | mean net (pts) | %-spot | winrate | perTrade Sharpe | t-stat |
|---|---|---|---|---|---|---|
| ALL weeks (unconditional parent) | 253 | +16.37 | +0.0835% | 76% | 0.146 | 2.32 |
| **CLUSTER (Jan/Apr/Jul/Oct)** | 80 | **+15.52** | **+0.0749%** | 76% | 0.139 | 1.24 |
| NON-CLUSTER (other 8 mo) | 173 | +16.76 | +0.0874% | 76% | 0.148 | 1.95 |

By cluster-month: Jan **-10.34** (win 63%) · Apr +57.67 (win 90%) · Jul +37.83 (win 86%) · Oct **-28.83** (win 63%).

- Raw cluster edge is positive, so literal kill #1 (edge<=0) does not fire, and it is positive in both pre and post regimes (not a pooling artifact).
- BUT the OS-36 thesis is affirmatively FALSE: cluster edge (15.52) does NOT beat its unconditional parent (16.76) — it is marginally WORSE. There is no distinct "earnings-season vol lag" premium. The positive number is pure generic VRP already OWNED by S-04 / OS-01 / OS-03 (incremental = ~zero; CIO book rule #1).
- Thesis is not even internally coherent: 2 of the 4 "results clusters" (Jan, Oct) LOSE money; the positive average is carried entirely by Apr + Jul (calendar-luck, opposite signs = noise, not an earnings mechanism).

**VERDICT: KILL.** Conditioner that fails to beat its unconditional parent (A.19); zero incremental edge over the owned short-vol book; results-cluster thesis unsupported (2/4 cluster months negative). The positive edge is short-vol beta, not a cluster alpha.
**Weakest assumption:** that Jan/Apr/Jul/Oct share a common realized-lags-implied mechanism — the by-month signs (2 up / 2 down) say they do not.

## Summary
| Setup | Edge (target slice, Rs-pts / %-spot) | Verdict |
|---|---|---|
| OS-35 | +17.33 / +0.0662% (Tue regime, n=37, t=1.21) | SURVIVE-MARGINAL, do-not-advance (fragile, thin sample) |
| OS-36 | +15.52 / +0.0749% (cluster) but < parent 16.76 | KILL (no incremental edge; thesis false) |
