# Scalping System V7 — NIFTY 50 index backtest

Data: `intraday_options_strategy/datasets/processed/nifty_1min.parquet` (NIFTY 50 spot 1-min, 2015-01-09 09:15:00 -> 2026-05-14 15:29:00, 1,047,541 bars, 2,794 trading days). Trade window from 2015-04-01 (warmup).

Fills at signal-bar CLOSE + 1pt/side slippage; futures-equiv statutory costs (STT 0.02% sell, brokerage Rs20x2/lot=75, exch/stamp/sebi/GST). P&L booked at EXIT bar. Denominator for %-return = entry price.


## Summary (base costs)

| TF | Variant | N | Win% | PF | Pts/trade | %price/trade | Ann.Sharpe | MaxDD% | AvgBars | NetPts |
|---|---|---|---|---|---|---|---|---|---|---|
| 5m | v1_base | 10347 | 25.7 | 0.56 | -5.52 | -0.0389 | -5.63 | -404.56 | 4.0 | -57095 |
| 5m | v2_4h | 5501 | 25.4 | 0.56 | -5.31 | -0.0371 | -4.46 | -205.93 | 4.1 | -29213 |
| 5m | v3_daily | 5321 | 25.2 | 0.56 | -5.38 | -0.0374 | -4.35 | -200.61 | 4.1 | -28634 |
| 15m | v1_base | 3314 | 34.5 | 0.78 | -4.24 | -0.0267 | -1.26 | -91.18 | 3.6 | -14047 |
| 15m | v2_4h | 1899 | 33.2 | 0.79 | -3.83 | -0.0223 | -0.78 | -42.97 | 3.5 | -7274 |
| 15m | v3_daily | 1785 | 33.5 | 0.83 | -3.16 | -0.0172 | -0.55 | -36.94 | 3.5 | -5646 |

## 2x cost stress (slippage & statutory doubled) — pts/trade & net

| TF | Variant | Pts/trade@2x | NetPts@2x | Still net+? |
|---|---|---|---|---|
| 5m | v1_base | -12.10 | -125150 | NO |
| 5m | v2_4h | -11.88 | -65358 | NO |
| 5m | v3_daily | -11.96 | -63648 | NO |
| 15m | v1_base | -10.83 | -35896 | NO |
| 15m | v2_4h | -10.41 | -19765 | NO |
| 15m | v3_daily | -9.75 | -17403 | NO |

## Degenerate detectors (guards.degenerate_flags)

- 5m_v1_base: ['negative without top-5 trades']
- 5m_v2_4h: ['negative without top-5 trades']
- 5m_v3_daily: ['negative without top-5 trades']
- 15m_v1_base: ['negative without top-5 trades']
- 15m_v2_4h: ['negative without top-5 trades']
- 15m_v3_daily: ['negative without top-5 trades']

## Per-year points/trade (regime check)

| TF | Variant | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5m | v1_base | -3.6(695) | -3.4(945) | -4.8(974) | -5.2(936) | -5.2(930) | -4.6(957) | -4.9(887) | -3.7(926) | -6.1(903) | -9.5(954) | -8.3(910) | -8.2(330) |
| 5m | v2_4h | -3.6(369) | -3.4(508) | -4.4(513) | -4.7(499) | -5.3(473) | -3.6(536) | -5.9(483) | -3.3(490) | -6.0(475) | -8.7(513) | -9.0(478) | -6.3(164) |
| 5m | v3_daily | -3.5(348) | -2.9(487) | -4.2(505) | -4.4(475) | -5.6(460) | -4.1(517) | -6.3(459) | -4.0(478) | -6.8(473) | -9.6(503) | -7.1(456) | -6.1(160) |
| 15m | v1_base | -0.9(207) | -1.5(288) | -3.8(318) | 1.4(283) | -5.7(329) | -4.3(314) | -5.8(276) | -0.7(290) | -4.0(291) | -13.0(308) | -7.3(305) | -2.4(105) |
| 15m | v2_4h | -2.9(125) | -3.3(166) | -3.3(186) | 1.6(172) | -4.9(181) | 4.9(184) | -12.4(150) | 5.2(158) | -7.2(163) | -11.2(186) | -9.2(162) | -3.8(66) |
| 15m | v3_daily | -0.5(116) | -0.5(154) | -2.2(168) | 2.9(161) | -6.1(180) | 1.5(172) | -9.5(143) | 0.6(150) | -3.4(148) | -8.8(176) | -7.5(156) | -4.6(61) |

## Notes / assumptions (faithful-translation quirks)

- Counter quirk (note 1) replicated: longTrades/shortTrades increment on EVERY bar enterLong/enterShort evaluates true, even while a position is open; caps at 3 per trend segment; resets on EMA trend flip.

- reLong/reShort/longContinue/shortContinue and strongBull/strongBear are DEAD (visual/unused) code in the source and do not affect state — not implemented.

- HTF filter folded into the enter signal itself (so it also gates the 3-trade counter), matching 'additionally require'. 4H = 2 session-anchored bars/day ([09:15,13:15) confirm 13:15; [13:15,close] confirm post-session). Daily confirmed post-session -> intraday day D uses <= D-1. merge_asof(backward) enforces no peek into a still-forming HTF candle.

- EMA seeded ewm(adjust=False), RSI Wilder ewm(alpha=1/14). TV seeds first value with SMA; difference washes out well before the 2015-04 trade start.

- Fill = signal-bar close + slippage. Real execution would fill at next-bar open (adverse); this close-fill is the source script's own convention and is mildly optimistic — flagged as the weakest assumption.



---

# REVERSED variants (auto-triggered on 5m Sharpe<-2; 15m added by desk request)

Faithful directional reversal: each original trade keeps its exact entry/exit bar & price; only the position SIDE flips (long<->short), exit mirrors on the same bar; per-side statutory recomputed. RAW = pre-all-cost price move (the clean directional signal); NET = after 1pt/side slippage + statutory. By construction reversed RAW = -(original RAW) exactly. Same trade population as originals (N identical).


## Original vs Reversed — side by side (all 6)

| TF | Variant | Side | RAW pts/trd (pre-cost) | NET pts/trd | %price/trd | Win% | PF | Ann.SR | MaxDD% | N |
|---|---|---|---|---|---|---|---|---|---|---|
| 5m | v1_base | ORIGINAL | +1.06 | -5.52 | -0.0389 | 25.7 | 0.56 | -5.63 | -404.6 | 10347 |
| 5m | v1_base | REVERSED | -1.06 | -7.64 | -0.0552 | 38.8 | 0.36 | -8.87 | -571.2 | 10347 |
| 5m | v2_4h | ORIGINAL | +1.26 | -5.31 | -0.0371 | 25.4 | 0.56 | -4.46 | -205.9 | 5501 |
| 5m | v2_4h | REVERSED | -1.26 | -7.83 | -0.0571 | 37.5 | 0.34 | -6.85 | -314.1 | 5501 |
| 5m | v3_daily | ORIGINAL | +1.20 | -5.38 | -0.0374 | 25.2 | 0.56 | -4.35 | -200.6 | 5321 |
| 5m | v3_daily | REVERSED | -1.20 | -7.78 | -0.0567 | 37.8 | 0.34 | -6.64 | -301.8 | 5321 |
| 15m | v1_base | ORIGINAL | +2.35 | -4.24 | -0.0267 | 34.5 | 0.78 | -1.26 | -91.2 | 3314 |
| 15m | v1_base | REVERSED | -2.35 | -8.95 | -0.0673 | 50.1 | 0.56 | -3.24 | -224.3 | 3314 |
| 15m | v2_4h | ORIGINAL | +2.75 | -3.83 | -0.0223 | 33.2 | 0.79 | -0.78 | -43.0 | 1899 |
| 15m | v2_4h | REVERSED | -2.75 | -9.33 | -0.0719 | 48.9 | 0.53 | -2.47 | -139.9 | 1899 |
| 15m | v3_daily | ORIGINAL | +3.42 | -3.16 | -0.0172 | 33.5 | 0.83 | -0.55 | -36.9 | 1785 |
| 15m | v3_daily | REVERSED | -3.42 | -10.01 | -0.0769 | 50.0 | 0.52 | -2.44 | -140.6 | 1785 |

## Cost decomposition & verdict

- **5m base**: original RAW pre-cost edge +1.06 pts/trd; all-in cost hurdle 6.58 pts/trd (~2pt slippage RT + STT-dominated statutory); reversed RAW -1.06.

- **15m base**: original RAW pre-cost edge +2.35 pts/trd; all-in cost hurdle 6.59 pts/trd (~2pt slippage RT + STT-dominated statutory); reversed RAW -2.35.

- **Cost-dominated hypothesis: CONFIRMED.** On both timeframes the raw directional edge is tiny (single-digit pts, either sign) and dwarfed by the ~6-7pt round-trip cost. Reversing merely flips a near-zero edge's sign; every reversed variant stays net-negative. There is no directional-sign fix here — the signal has no exploitable edge net of cost at 5m or 15m.

