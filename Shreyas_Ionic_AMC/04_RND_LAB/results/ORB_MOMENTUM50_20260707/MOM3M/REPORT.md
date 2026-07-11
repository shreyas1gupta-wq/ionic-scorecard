# 15-min ORB x MOMENTUM-50 (PURE 3-month momentum) — RESULTS
Owner: Arjun Rao (Head of Quant). Generated 2026-07-07 12:53.

## Data lineage
- Ranking: HF daily close `swing_momentum/data/hf_stock_minute/day/train-00000.parquet` (6,968,616 rows, 2,535 syms, ends IST 2026-01-22). ALREADY split/bonus-adjusted (verified TTKPRESTIG 10:1, IRCTC 5:1 => NO re-adjustment). Price-return momentum (ex-dividend).
- Execution: HF minute `.../minute/train-0000{0..7}.parquet` (713M 1-min bars, 2022-01-03->2026-01-21 IST). UTC+5:30; time>=09:15 (L2). Resampled to 12.27M 15-min bars; 509 momentum-universe syms ALL found (namespace match).
- Universe: `NIFTY500_TICKER_2005_2025_Final.xlsx` 42 semi-annual PIT snaps; most-recent<=month (causal, L6-survivorship). Top-50 by trailing 63-td return, monthly rebalance. 49 months, 509 union syms.
- Guards: L1 IST-date, L2 preopen, L5 next-bar entry (strictly after signal bar), causal Wilder ATR(14) on continuous 15-min series, zero-volume=no-fill.

## Method
- OR = first 15-min bar 09:15-09:29. LONG = a later 15-min bar CLOSES > OR-high; SHORT = closes < OR-low (CLOSE-confirmation, not wick). BIDIRECTIONAL. First signal/day only; ENTER at NEXT 15-min bar OPEN. Max signal bar 23 (need next bar).
- ATR(14) Wilder on continuous 15-min series (does not reset daily). Stop distance = ATR at signal bar.
- Exits: EOD = flat at last 15-min close (no overnight). TRAIL = chandelier (long: exit when close-bar low <= highestClose-1.0xATR; short symmetric), initial hard SL as floor; else EOD. Gap-through honored (open beyond stop => fill at open).
- Costs (COST_STANDARDS): slippage 15bps/side; DOUBLED to 30bps on stop/trail/gap exits (exit-into-weakness); +STT sell 2.5 + exch/GST 1.4 + stamp 0.3 + brokerage 4bps@Rs1L = ~8bps fixed. Round-trip ~0.38% (EOD) / ~0.53% (stop). net_2x = 2x slippage stress.
- %-of-ENTRY-PRICE per trade (stable denom, FIRM RULE). Sharpe on DAILY equal-weight book return x sqrt(252) (NOT per-trade annualized). MaxDD from compounded daily equity.

## SUMMARY TABLE (net of 1x costs)
| Combo | SL x Exit | N | Win% | PF | W/L | Avg gross %/tr | Avg net %/tr | Ann.Sharpe | MaxDD | Total net % | Sharpe@2x |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| combo1 | SL 0.25xATR + EOD | 44,594 | 9.1 | 0.25 | 2.49 | +0.035 | -0.481 | -29.96 | -99.2% | -21463 | -55.12 |
| combo2 | SL 0.25xATR + Trail | 44,594 | 9.7 | 0.18 | 1.64 | +0.025 | -0.504 | -46.96 | -99.4% | -22477 | -87.89 |
| combo3 | SL 1.0xATR + EOD | 44,594 | 28.1 | 0.51 | 1.30 | +0.075 | -0.400 | -13.95 | -98.4% | -17827 | -26.66 |
| combo4 | SL 1.0xATR + Trail | 44,594 | 21.4 | 0.32 | 1.17 | +0.040 | -0.484 | -27.24 | -99.3% | -21583 | -51.65 |

All combos share IDENTICAL entries (44,594 filled trades; ~45/day over 1002 trading days) — they differ ONLY in stop/exit. Avg cost drag/trade: combo1 0.517%, combo2 0.529%, combo3 0.475%, combo4 0.524%.

### combo1 — SL 0.25xATR + EOD
- Long: N=19,210 win 7.0% avg net -0.518% | Short: N=25,384 win 10.7% avg net -0.454%
- Exit mix: STOP 90%, EOD 10%, GAP 0%
- Concentration: top-1 symbol = 0.9% of |net P&L|. Top-5 net contributors: LICI +5%pts, INDUSINDBK +1%pts, RAILTEL +0%pts, SIGNATURE -3%pts, JSWSTEEL -4%pts
- Degenerate flags: ['negative without top-5 trades']
- Per-year (N, win%, avg net%/tr, sum net%, Sharpe):
  | Year | N | Win% | Avg net% | Sum net% | Sharpe |
  |---|---:|---:|---:|---:|---:|
  | 2022 | 11,116 | 9.0 | -0.483 | -5370.3 | -40.15 |
  | 2023 | 10,865 | 9.1 | -0.484 | -5257.6 | -39.31 |
  | 2024 | 10,881 | 9.5 | -0.466 | -5069.4 | -18.52 |
  | 2025 | 11,086 | 9.1 | -0.487 | -5400.3 | -46.67 |
  | 2026 | 646 | 6.3 | -0.565 | -365.2 | -89.99 |

### combo2 — SL 0.25xATR + Trail
- Long: N=19,210 win 7.9% avg net -0.536% | Short: N=25,384 win 11.0% avg net -0.480%
- Exit mix: STOP 81%, TRAIL 18%, EOD 2%, GAP 0%
- Concentration: top-1 symbol = 1.0% of |net P&L|. Top-5 net contributors: SIGNATURE -2%pts, JMFINANCIL -3%pts, LICI -3%pts, RKFORGE -4%pts, RAILTEL -4%pts
- Degenerate flags: ['negative without top-5 trades']
- Per-year (N, win%, avg net%/tr, sum net%, Sharpe):
  | Year | N | Win% | Avg net% | Sum net% | Sharpe |
  |---|---:|---:|---:|---:|---:|
  | 2022 | 11,116 | 9.5 | -0.511 | -5679.9 | -57.42 |
  | 2023 | 10,865 | 9.6 | -0.504 | -5478.0 | -57.48 |
  | 2024 | 10,881 | 10.5 | -0.493 | -5368.1 | -31.58 |
  | 2025 | 11,086 | 9.2 | -0.504 | -5587.3 | -63.10 |
  | 2026 | 646 | 7.3 | -0.564 | -364.2 | -122.83 |

### combo3 — SL 1.0xATR + EOD
- Long: N=19,210 win 23.3% avg net -0.484% | Short: N=25,384 win 31.7% avg net -0.336%
- Exit mix: STOP 62%, EOD 38%, GAP 0%
- Concentration: top-1 symbol = 1.1% of |net P&L|. Top-5 net contributors: INDUSINDBK +16%pts, KIOCL +16%pts, LICI +15%pts, GUJALKALI +15%pts, TITAGARH +10%pts
- Degenerate flags: ['negative without top-5 trades']
- Per-year (N, win%, avg net%/tr, sum net%, Sharpe):
  | Year | N | Win% | Avg net% | Sum net% | Sharpe |
  |---|---:|---:|---:|---:|---:|
  | 2022 | 11,116 | 28.8 | -0.373 | -4149.6 | -12.97 |
  | 2023 | 10,865 | 28.0 | -0.398 | -4328.7 | -16.24 |
  | 2024 | 10,881 | 27.9 | -0.413 | -4497.5 | -10.99 |
  | 2025 | 11,086 | 27.9 | -0.408 | -4518.6 | -19.05 |
  | 2026 | 646 | 24.6 | -0.515 | -332.9 | -33.77 |

### combo4 — SL 1.0xATR + Trail
- Long: N=19,210 win 19.2% avg net -0.545% | Short: N=25,384 win 23.0% avg net -0.437%
- Exit mix: TRAIL 75%, STOP 20%, EOD 5%, GAP 1%
- Concentration: top-1 symbol = 0.9% of |net P&L|. Top-5 net contributors: LICI +0%pts, TCIEXP -1%pts, GOCOLORS -2%pts, RAILTEL -2%pts, ZEEL -3%pts
- Degenerate flags: ['negative without top-5 trades']
- Per-year (N, win%, avg net%/tr, sum net%, Sharpe):
  | Year | N | Win% | Avg net% | Sum net% | Sharpe |
  |---|---:|---:|---:|---:|---:|
  | 2022 | 11,116 | 22.2 | -0.472 | -5250.5 | -26.09 |
  | 2023 | 10,865 | 20.9 | -0.485 | -5273.5 | -32.69 |
  | 2024 | 10,881 | 22.3 | -0.490 | -5334.7 | -21.56 |
  | 2025 | 11,086 | 20.4 | -0.483 | -5356.3 | -33.50 |
  | 2026 | 646 | 16.6 | -0.571 | -368.6 | -72.16 |

## VERDICT & SELF-RED-TEAM
**FAKE? No — engine verified. REAL result = a robust, honest NET-NEGATIVE across all 4 combos and all 5 years.**

### Gross (pre-cost) diagnostics — where the (tiny) signal actually lives
| Combo | Side | N | Gross avg/tr | t-stat | Win% | Gross daily-book Sharpe |
|---|---|---:|---:|---:|---:|---:|
| combo3 (1.0xATR+EOD) | ALL | 44,594 | +7.54 bps | +11.1 | 33.8 | +2.36 |
| combo3 | LONG | 19,210 | -0.04 bps | -0.04 | 28.1 | (dead) |
| combo3 | SHORT | 25,384 | +13.27 bps | +15.6 | 38.1 | (carries all edge) |
| combo1 (0.25xATR+EOD) | SHORT | 25,384 | +6.05 bps | +11.2 | 11.8 | — |

**Headline finding (inverts the brief's premise):** On a PURE 3-month-momentum universe the intraday ORB edge is entirely SHORT — fading the OR-LOW breakdown of already-extended winners (t=+15.6, gross Sharpe ~2.4). The LONG OR-HIGH breakout is statistically DEAD (t=-0.04). "Long-only because they're momentum names" would be the single worst choice here; the names mean-revert intraday. There are also more short signals (25.4k) than long (19.2k) despite an up-market — high-momentum names open and fade.

### Best combo & the SL/exit lessons (as the brief anticipated)
- **combo3 (SL 1.0xATR + EOD) is the least-bad on every metric and every year** — best gross (+7.5bps), highest win% (28%), least-negative net/Sharpe. It confirms the design hypothesis: **0.25xATR is a whipsaw trap** — median ATR is 0.66% of price, so 0.25xATR≈0.16% stop sits INSIDE one bar of noise (win% collapses 28%->9%, exit-mix 90% STOP). **EOD beats trailing**: the 1.0xATR chandelier (combo4) exits 75-95% of trades early, cutting the few winners and paying the doubled stop-slippage more often (net/Sharpe worse than the plain EOD combo3).

### Cost sensitivity (the binding constraint) & turnover
- Round-trip cost ~38bps (EOD) / ~53bps (stop exit); avg ~47.5bps for combo3. Best gross edge is +7.5bps/trade => **cost is ~6x the edge.** Even at LITERALLY ZERO cost combo3 averages only +7.5bps/trade (marginal); a realistic break-even needs round-trip < ~7.5bps, which is impossible for intraday equity (STT+2-side slippage alone > 10bps). 2x-slippage stress makes every combo worse (Sharpe -14 -> -27). Turnover is extreme: ~45 trades/day, ~44.6k over the sample — this is a cost-maximising, edge-minimising design.

### Concentration — NOT a risk here
- Diffuse: top-1 symbol = ~1% of |net P&L|; top-5 contributors are single-digit %pts and mixed-sign; 509 names, ~45 trades/day. **No name dominates.** NOTE: the `degenerate_flags` 'negative without top-5 trades' fires TRIVIALLY because the book is net-negative overall (t.sum()<0) — it is NOT a concentration signal in this net-negative case. Real concentration (top-1 >30%) is absent.

### Single weakest assumption
**The slippage floor (15bps/side, doubled on stops).** It is the swing variable: the entire verdict is "gross ~0-13bps < cost ~40-53bps." If true executable intraday slippage on these liquid momentum names were ~3-5bps/side (the brief's lighter alternative) the round-trip would fall to ~15-20bps — still > the +7.5bps ALL-side gross, so combo3 stays net-negative, but a SHORT-ONLY combo3 (gross +13.3bps) would approach break-even. That is the only crack worth a follow-up: a **short-only, OR-low-breakdown, wide-stop, EOD** variant with a genuine TCA-grade fill/slippage study (Tara) on a liquid sub-universe. As a long/bidirectional momentum-ORB, this is DEAD. Verdict: **FRAGILE-leaning-FAKE-as-pitched (no net edge); the only live residual is a small short-side intraday-reversion signal that needs a real cost study to matter.**

