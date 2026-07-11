# MEANREV/RSI CAMPAIGN — 4 Principal-specified concrete tests (2026-07-07)
Owner: Arjun Rao (quant-head). Persisted by DESK — agent's own write to this path was blocked by subagent policy; content below is verbatim from the agent's final report.

## Escalate/kill call: 0 of 6 variants clear Sharpe>1.5. Nothing advances to Phase-2 Gate-4.

Data: NIFTY 1-min spot + weekly options, 2021-05→2026-06, via `data_loader.py` (enforces tz + pre-open-auction landmines). Costs per COST_STANDARDS (file is marked APPROVED D-021, not DRAFT as briefed — flag: the brief's DRAFT-status assumption for COST_STANDARDS appears outdated). P&L booked at EXIT, denominator-free premium POINTS + %spot, dead strikes DROPPED (no fabricated fills, D-031). Scripts: `test_a_zscore.py`, `test_bc_rsi.py`, all in this folder.

### The 6 results (1x cost)

| Variant | N | win% | mean net pts | %spot | ann Sharpe | verdict |
|---|--:|--:|--:|--:|--:|---|
| A EMA100 (30m z-score, sell 100-OTM) | 159 | 69.8 | -6.6 | -0.051 | -0.24 | **KILL** (negative; negative ex-top5) |
| A EMA200 (30m z-score, sell 100-OTM) | 118 | 76.3 | +26.7 | +0.116 | 0.83 | **MARGINAL — hold, do NOT escalate** |
| B delay (RSI(5) extreme, sell ATM, 1d delay) | 21 | 61.9 | +21.6 | +0.098 | 0.29 | **KILL** (N=21, underpowered) |
| B limit (RSI(5) extreme, sell ATM, next-day limit) | 18 | 66.7 | +27.3 | +0.137 | 0.32 | **KILL** (N=18, underpowered) |
| C delay (RSI(5) extreme, buy 200-OTM, 1d delay) | 21 | 47.6 | +14.3 | +0.008 | 0.13 | **KILL** (lottery payoff, negative ex-top5) |
| C limit (RSI(5) extreme, buy 200-OTM, next-day limit) | 18 | 50.0 | +28.8 | +0.085 | 0.24 | **KILL** (lottery payoff) |

### Why A-EMA200 (the one "positive" print) still fails scrutiny
The edge is entirely one-sided: selling PUTS into selloffs (fade-fear) is win 85% / +64 pts/trade; selling CALLS into rallies LOSES (-11 pts/trade). This is a naked short-vol tail-seller (win/loss ratio 0.48, win-rate 76% -> degenerate-flag pattern), and it got run over in the 2023 trend (-1313 pts that year). Matches `INTRADAY_STUDY_20260707` section C: far-OTM selling only works on down-spikes, not symmetrically.

**Resurrection note:** the down-spike put-sell sub-signal is real and prior-consistent, but is only worth pursuing re-scoped as a *defined-risk* spread with a vol/DTE gate and tested across a real crash slice — as a NEW hypothesis, not this symmetric naked spec.

### Why B/C (RSI(5) extremes) are dead
RSI(5) crosses <10 only 3x and >90 only 20x in 5 years (independently verified) — structurally uncertifiable at the >=30-trades-per-parameter bar the firm requires. Limit-or-skip entry style only dropped 3 trades vs delayed entry; changed nothing material.

### Methodology notes (for challenge)
- Data lineage: spot `intraday_options_strategy/datasets/raw/hf_index_options_1m/index/NIFTY.parquet` (463,826 bars, 1,238 days, 2021-05-24 to 2026-06-03); options `.../options/NIFTY/*.parquet` (262 weekly expiries to 2026-06-09); accessor `Shreyas_Ionic_AMC/09_PRODUCT/fno_game/server/data_loader.py`.
- Guards applied: L1/L2 via data_loader; L5 (entry strictly after signal bar, causal); L7 (no settle past DATA_MAX 2026-06-03); D-031 no-fill=drop (A-EMA200 dropped 12 trades, B/C-limit dropped 3 each); LOT=75; slippage 0.25%/0.5%/1.0% one-way for ATM/100-OTM/200-OTM; 2x-cost stress computed (all variants stay sub-1.5 Sharpe; A-EMA200 drops to 0.77).
- Direction split for A-EMA200: PE leg n=59 win 85% +3796 pts total; CE leg n=59 win 68% -646 pts total.
- A-EMA200 yearly P&L: 2021 -63, 2022 +654, 2023 -1313, 2024 +1814, 2025 +1370, 2026 (partial) +688.
- Test A exit rule (stated explicitly for challenge, not swept): exit on z-revert to |z|<=0.5, else 5-trading-day max-hold, else weekly-expiry settle. Realized mix for EMA200: 40% revert / 6% max-hold / 54% expiry; average hold ~3 trading days. The +-0.5 revert band and 100-point OTM offset were the agent's judgment call, not parameter-swept — sensitivity/plateau check deferred to Gate-4 (moot here since nothing escalates).

### Artifacts (all in this folder)
`test_a_zscore.py`, `test_bc_rsi.py`, `trades_TestA_EMA100.csv`, `trades_TestA_EMA200.csv`, `trades_TestB_delay.csv`, `trades_TestB_limit.csv`, `trades_TestC_delay.csv`, `trades_TestC_limit.csv`, `stats_A.csv`, `stats_BC.csv`.
