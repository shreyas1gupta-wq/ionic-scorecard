# ORB SHORT-ONLY x MOMENTUM-50 (1-MONTH) — PROGRESS / CHECKPOINT
Owner: Arjun Rao (quant-head). Follow-up to ORB_MOMENTUM50_20260707. I own 1-MONTH lookback (parallel agent owns 2-week).

## STATUS: ALL STAGES DONE. Deliverables in this dir: REPORT.md, trades_{5m,15m}.csv, equity_{5m,15m}.csv, baskets.csv, union_symbols.txt.
Scripts (reusable): scripts/s1_baskets.py (21-td mom-50), s2_bars.py (5m+15m bars, resume-safe per-shard cache), s3_orb.py <tf> (short-only engine), s4_metrics.py (CAGR/XIRR + report).

## DESIGN (frozen)
- Universe: PIT NIFTY500 (42 semi-annual snaps, causal), top-50 by trailing 21-td (1-month) price return, MONTHLY rebalance. 49 months, 570 union syms. HF daily close ALREADY split/bonus-adj (do NOT re-adjust).
- Rebalance: MONTHLY chosen (not bi-weekly) — matches prior 3m test's cadence for clean apples-to-apples isolation of the LOOKBACK variable; faster rebalance only adds turnover/noise without a thesis. 2-week rebalance is the parallel agent's lookback lane, not mine.
- SHORT-ONLY OR-low breakdown, close-confirm, enter next-bar open, SL 1.0xATR(14), EOD exit (all proven-best from 3m test, NOT re-tested). 5m-ORB = first 5-min bar OR; 15m-ORB = first 15-min bar OR (self-consistent timeframe).
- Costs: 15bps/side slip (2x on stop/gap), +8.2bps fixed. Round-trip ~47-49bps. net@1x, net@2x.
- Sizing for CAGR: equal-notional daily-equal-weight book, fully-invested intraday, reinvest daily. Equal-risk as robustness (same result).

## RESULT (honest, net-negative — same story as 3m, WEAKER edge)
- Gross short edge REAL + significant BOTH tf (15m +10.7bps t=+14.0 grossSharpe 1.40; 5m +8.6bps t=+13.1 grossSharpe 1.41) but WEAKER than 3m short-side (+13.3bps t=+15.6 grossSharpe ~2.4). 1-month lookback did NOT improve; degraded it.
- Net destroyed by cost wall: net -36bps (15m) / -41bps (5m); net CAGR -66%/-68.6%; maxDD -99%. Positive every-year GROSS, negative every-year NET.
- 15m BEATS 5m on every metric (more trades but weaker per-trade edge + higher cost drag on 5m).
- Reversal rule: net Sharpe<-2 triggers literally, but GROSS/directional Sharpe = +1.40 (short is correct direction); long side already proven dead in 3m run (t=-0.04). Reversed long version unwarranted + already-refuted — NOT run.
- CAVEAT (short book): not all NIFTY500 names are reliably shortable intraday (SLB borrow availability, no naked carry, broker intraday-short lists, ban-period exclusions). Backtest assumes all fillable — real net is worse, not better.

## VERDICT: FAKE-as-tradable / net-negative capital-destroyer. Gross signal REAL but ~4-5x sub-cost. 3-month > 1-month for this signal. DEAD.
