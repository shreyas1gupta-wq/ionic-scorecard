# FINDINGS — Adaptive Momentum Fusion (Pine) backtest, long-only, NIFTY500 PIT 2015→2026-01-22
DESK-100 · 2026-07-16 · SCREEN-grade (no DSR/PBO/walk-forward). Author: Arjun Rao (Sonnet).
Close-only panel → only close-based engines (Efficiency, Momentum) tested faithfully; Volatility/
Fractal/Volume/Composite + divergences BLOCKED (need bhavcopy OHLCV pull, D-033).

## VERDICT: does NOT beat NIFTY500 buy-hold. Efficiency = FRAGILE, Momentum = FAKE.
Raw run showed 49-53% CAGR — **fake**, driven by a data-corruption bug (see below). After removing
corrupted prints:

| cell | CAGR% | Sharpe | MaxDD% | vs NIFTY500 CAGR |
|---|---|---|---|---|
| Efficiency/MACD/V1 (default) | 7.00 | 0.48 | -58.0 | **-5.96** |
| Efficiency/* (all 6 cells) | 6.6-7.0 | ~0.48 | ~-58 | ~-6.0 |
| Momentum/* (all 6 cells) | -0.83 to -4.41 | ~0 | -64 to -71 | -13.8 to -17.4 |

Benchmark NIFTY500 CAGR = 12.96% (index history starts 2016-01-01 — flagged; strategy trades from 2015).

## Why it fails (validation battery)
- **Placebo: FAILS in all 12 cells.** Default mean_net 1.87%/trade vs random-entry placebo 3.66% — the
  crossover TIMING adds nothing over a random entry into the same stock held the same ~28 days.
- **2x-cost gate: FAILS.** Default gross 14.83% → net@0.67% 7.00% → net@1.07% 2.58% → net@2x -0.30%.
  Cost-heavy signal: ~8.9x/yr one-way turnover.
- **One-day-lag (D-028): PASS** (7.8% collapse) — execution mechanics honest; corruption was orthogonal.
- **t-stat ≈13 is a large-N mirage** — trades cluster around shared regime turns (2020/2021/2023-24),
  true DoF << 22,000; real SE understated (same class as the IC-1 portfolio-SR lesson).

## DATA-CORRUPTION BUG FOUND (cross-cutting — the real headline)
`datasets/derived/pit_union_panel_v1/close_panel_price.parquet` `source=="DELISTED"` segment alternates
day-to-day between two price scales for some 2020-era small/mid names. **~981 corrupted (symbol,date)
prints, 44 in this universe** (e.g. MAGMA 17.60→1000.00 = fabricated +5,581% trade). In Momentum/MACD/V3,
57 contaminated trades (0.08%) contributed 303% of pooled P&L. **EARN_MOM_SWEEP cross-checked = 0
contamination (it gates on liquid N500 PIT names).** But ANY future backtest on this panel touching a
2020-era delisted small/mid name will fabricate spurious results. → Kavya to quarantine/patch.

## FILES
`results_CLEANED.csv` (USE THIS) · `results.csv` (raw/contaminated — do not use) · amf_engine.py,
amf_backtest.py, lag_test.py, clean_rerun.py · 12× ledger_*.csv · 12× nav_*.csv · missing_tickers.txt.

## FOLLOW-UPS
1. DATA (urgent, Kavya): quarantine the DELISTED two-scale corruption in the price panel.
2. If AMF pursued further: the OHLCV engines (Volatility/Fractal/Volume/Composite) need a bhavcopy
   full-OHLCV pull — but given the close-based engines fail placebo + costs, low priority.
