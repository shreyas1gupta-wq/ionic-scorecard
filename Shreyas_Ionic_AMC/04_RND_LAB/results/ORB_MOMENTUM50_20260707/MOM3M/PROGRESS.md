# ORB x MOMENTUM-50 (PURE 3-MONTH momentum) — PROGRESS

Owner: Arjun Rao (quant-head). Task: 15-min ORB on monthly-rebalanced NIFTY500 momentum-50 (PURE 3m rank).
Parallel agent owns the 3m+6m combined rank; I own PURE-3m ONLY.

## DESIGN (frozen)
- UNIVERSE: PIT snapshot (NIFTY500_TICKER_2005_2025_Final.xlsx, 42 semi-annual snaps Mar/Sep) — use most-recent snap <= month start (causal). Rank members by trailing 3m (63 trading day) SPLIT/BONUS-ADJUSTED price return as of last trading day BEFORE month start (causal, no month-M data). Top 50. Monthly rebalance.
- RANK SERIES: HF daily close (swing_momentum/data/hf_stock_minute/day/train-00000.parquet), IST date via guards.fix_ist_dates, adjusted with datasets/derived/corporate_action_factors.parquet (split+bonus only, cum-product). Same symbol namespace as minute data => no cross-dataset naming mismatch.
- EXECUTION DATA: HF minute (minute/train-0000{0..7}.parquet), UTC->IST (+5:30), filter time>=09:15. 8 shards, sorted by symbol (boundary overlap => read filtered across all shards).
- ORB: OR = first 15-min bar 09:15-09:30. LONG signal = a 15-min bar CLOSES > OR-high; SHORT = closes < OR-low. BIDIRECTIONAL (mandate default; momentum names => expect long>short, will decompose). Close-confirmation (not intrabar wick). ONE trade/stock/day = FIRST signal of day. ENTRY = OPEN of NEXT 15-min bar (strictly after signal bar => passes L5). Signal must be <= 15:00-15:15 bar (need a next bar). Fill guard: entry bar volume>0 else NO FILL (COST_STANDARDS zero-vol rule).
- ATR: Wilder ATR(14) on CONTINUOUS 15-min series per symbol (does NOT reset daily, else early-session breakouts have no ATR). TR uses prior 15-min close (overnight gap in first-bar TR, dampened by 14-avg). Causal (ATR at signal bar). Stop distance = ATR at signal bar.
- 4 COMBOS = {SL 0.25xATR (very tight, requested), SL 1.0xATR (my "better": 0.25x is inside one avg bar range => insta-whipsaw; 1.0x = one bar of breathing room, still a hard cap)} x {EOD exit (flat 15:30 close), TRAILING (chandelier: long exit when close < highestClose-1.0xATR; short when close > lowestClose+1.0xATR; initial hard SL is the floor; else EOD — no overnight hold)}.
- COSTS (COST_STANDARDS, binding): per-side slippage 15bps (blend large10/mid20, momentum-50 skews mid-liquid); exit slippage DOUBLED to 30bps on HARD-STOP exits (panic/exit-into-weakness). +STT intraday sell 2.5bps, exch/GST ~0.8bps, stamp buy 0.3bps, brokerage Rs40/trade @Rs1L notional=4bps. Round-trip base ~0.40% (EOD/trail) / ~0.55% (stop exit). Report net@1x and 2x-stress.
- ACCOUNTING: per-trade ret = %-of-ENTRY-PRICE (stable denom, comparable across prices — FIRM HARD RULE). Sharpe = on DAILY equal-weight book return (mean of day's net trade rets), *sqrt(252). NOT per-trade annualized (my 2026-07-04 lesson). MaxDD from compounded daily equity. PF = sum(win)/|sum(loss)| net.

## STAGES
- [ ] S1 baskets: adjusted daily -> momentum-50 per month -> baskets.parquet + union symbol set. OUT: baskets.csv, union_symbols.txt
- [ ] S2 minute -> 15-min bars for union symbols (shard loop, filtered). OUT: bars15_<shard>.parquet cache
- [ ] S3 ORB engine: 4 combos on active days -> per-trade CSVs (trades_comboN.csv)
- [ ] S4 metrics + degenerate detectors + REPORT.md

## STATUS: ALL 4 STAGES DONE. Deliverables in this dir: REPORT.md + trades_combo{1..4}.csv (44,594 trades each) + baskets.csv.
VERDICT: net-negative all 4 combos, all 5 years. Gross edge tiny (+7.5bps best) and ENTIRELY SHORT-side (t=+15.6; long dead t=-0.04). combo3 (1.0xATR+EOD) least-bad; 0.25xATR=whipsaw, EOD>trail. Costs ~47.5bps = 6x edge => DEAD as pitched. Concentration low. Only residual: short-only OR-low-breakdown needs real TCA.
CAUGHT: HF daily ALREADY split/bonus-adj — do NOT re-adjust (fake 10x). Degenerate 'negative without top-5' flag is trivially-true here (net<0), not a concentration signal.
