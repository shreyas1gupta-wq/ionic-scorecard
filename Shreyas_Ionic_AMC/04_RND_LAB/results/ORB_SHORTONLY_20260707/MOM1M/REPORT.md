# SHORT-ONLY OR-LOW-BREAKDOWN x MOMENTUM-50 (1-MONTH momentum) — RESULTS
Owner: Arjun Rao (Head of Quant). Generated 2026-07-07 13:59.
Follow-up to ORB_MOMENTUM50_20260707 (3m/3m6m bidirectional). Narrowed to the ONLY live piece: SHORT side.

## HEADLINE — CAGR/XIRR (PRIMARY metric this round)
Position sizing = **equal-notional, daily-equal-weight book**: each trading day, capital is split
equally across that day's short signals, fully deployed intraday, flat overnight (EOD exit),
P&L reinvested daily -> compounded strategy equity curve. CAGR on 252-td basis; XIRR = calendar-basis
(actual/365.25) money-weighted cross-check (equals CAGR here — single account, full reinvestment, no external flows).

| Timeframe | Net CAGR | Net XIRR | Gross CAGR | CAGR @2x-slip | Net CAGR (equal-risk) | Final net equity (x) |
|---|---:|---:|---:|---:|---:|---:|
| 5m-ORB | -68.6% | -67.9% | +9.7% | -89.0% | -68.7% | 0.010 |
| 15m-ORB | -66.0% | -65.3% | +11.4% | -87.3% | -66.3% | 0.014 |

## SUMMARY TABLE (per-trade & risk-adjusted, net of 1x costs)
| Timeframe | N | Win% | PF | W/L | Avg gross bps/tr | Avg net bps/tr | Ann.Sharpe(net) | Sharpe(gross) | MaxDD(net) | Sharpe@2x |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5m-ORB | 33,819 | 21.8 | 0.45 | 1.61 | +8.6 | -40.7 | -16.61 | 1.41 | -99.0% | -30.59 |
| 15m-ORB | 28,544 | 30.8 | 0.51 | 1.16 | +10.7 | -36.1 | -13.07 | 1.40 | -98.6% | -24.17 |

Sample: 2022-01-03 -> 2026-01-21. Trades/day: 5m 33.8, 15m 28.5. Days with signals: 5m 1001, 15m 1001.
Round-trip cost drag/trade: 5m 49.3 bps, 15m 46.8 bps (15bps/side slip, doubled on stop/gap exits, +~8.2bps STT/exch/stamp/brokerage).

## Data lineage
- Ranking: HF daily close `swing_momentum/data/hf_stock_minute/day/train-00000.parquet` — ALREADY split/bonus-adjusted (verified prior run) => raw close, NO re-adjust. Trailing 21-td (1-month) price return, causal (as-of last day before month start).
- Universe: `NIFTY500_TICKER_2005_2025_Final.xlsx` 42 semi-annual PIT snaps; most-recent<=month (causal, L6). Top-50 by 21-td return, MONTHLY rebalance. 49 months, 570 union syms.
- Execution: HF minute (2022-01-03 -> 2026-01-21 IST). UTC+5:30; time>=09:15 (L2 preopen dropped). Resampled to BOTH 5-min (idx 0..74) and 15-min (idx 0..24) bars.
- Guards: L1 IST-date, L2 preopen, L5 next-bar entry (strictly after signal), causal Wilder ATR(14) on continuous per-symbol series, zero-volume=no-fill.

## Method (SHORT-ONLY, frozen)
- **5m-ORB**: OR = first 5-min bar (09:15-09:19); **15m-ORB**: OR = first 15-min bar (09:15-09:29). Self-consistent timeframe (OR + breakdown bars same size) = the conventional meaning of '5m ORB' / '15m ORB'.
- SHORT signal = a later same-timeframe bar CLOSES < OR-low (close-confirmation, not intrabar wick). First short signal/day only; ENTER at NEXT bar OPEN (L5).
- Stop = entry + 1.0xATR(14) (proven-best from 3m test; 0.25x = whipsaw, NOT re-tested). Exit = EOD flat at last bar close (proven-best; trailing NOT re-tested). Gap-through honored (open>=stop => fill at open).
- Per-trade ret = %-of-ENTRY (stable denom, FIRM RULE). CAGR/XIRR from equal-notional daily-book compounded equity.

### 5m-ORB detail
- N=33,819 | win 21.8% | PF 0.45 | avg gross +8.6bps (t=+13.1) | avg net -40.7bps | net@2x -81.9bps
- Net CAGR -68.6% | Gross CAGR +9.7% | Sharpe(net) -16.61 | Sharpe(gross) 1.41 | MaxDD(net) -99.0% | MaxDD(gross) -7.0%
- Exit mix: STOP 74%, EOD 26%, GAP 1%
- Concentration: top-1 symbol = 0.7% of |net P&L|. Degenerate flags: ['negative without top-5 trades']
- Per-year (N, win%, gross bps/tr, net bps/tr, Sharpe(net), net CAGR%):
  | Year | N | Win% | Gross bps | Net bps | Sharpe | Net CAGR% |
  |---|---:|---:|---:|---:|---:|---:|
  | 2022 | 8,394 | 22.9 | +11.7 | -37.5 | -15.83 | -66.4 |
  | 2023 | 8,335 | 21.8 | +8.2 | -41.1 | -16.48 | -68.0 |
  | 2024 | 8,370 | 21.7 | +7.0 | -42.4 | -15.00 | -70.7 |
  | 2025 | 8,173 | 21.0 | +7.7 | -41.8 | -20.52 | -69.1 |
  | 2026 | 547 | 19.2 | +6.4 | -43.5 | -16.89 | -69.7 |

### 15m-ORB detail
- N=28,544 | win 30.8% | PF 0.51 | avg gross +10.7bps (t=+14.0) | avg net -36.1bps | net@2x -74.7bps
- Net CAGR -66.0% | Gross CAGR +11.4% | Sharpe(net) -13.07 | Sharpe(gross) 1.40 | MaxDD(net) -98.6% | MaxDD(gross) -10.6%
- Exit mix: STOP 57%, EOD 43%, GAP 0%
- Concentration: top-1 symbol = 0.9% of |net P&L|. Degenerate flags: ['negative without top-5 trades']
- Per-year (N, win%, gross bps/tr, net bps/tr, Sharpe(net), net CAGR%):
  | Year | N | Win% | Gross bps | Net bps | Sharpe | Net CAGR% |
  |---|---:|---:|---:|---:|---:|---:|
  | 2022 | 7,187 | 32.4 | +15.8 | -30.8 | -11.82 | -62.0 |
  | 2023 | 6,946 | 31.2 | +10.3 | -36.4 | -15.80 | -64.8 |
  | 2024 | 7,031 | 29.9 | +7.4 | -39.5 | -11.15 | -69.7 |
  | 2025 | 6,908 | 30.0 | +9.8 | -37.2 | -15.94 | -66.6 |
  | 2026 | 472 | 28.0 | +2.1 | -45.6 | -16.68 | -73.1 |
