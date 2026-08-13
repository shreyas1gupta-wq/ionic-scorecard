# 15-MIN CANDLE FORMATIONS x EMA/DMA ALIGNMENT — the result is mostly BETA
**2026-07-30 · DESK-100 · 480 cells → non-overlap replay → beta placebo · 1 of 8 formations survives**

## The ask
Principal: *"CAN WE TRADE SOMETHING BASIS 15MIN CANDLE FORMATIONS AND SIMILARLY WITH WEEKLY CANDLES
COMBINED WITH 9,21 EMA OR 10-20 DMA... FIND SPINERS WITH MAX 10-100 TRADES PER MONTH HIGHLY
PROFITABLE, HIGHER CHANCES OF WIN AND >1.5 RISK REWARD ON AVG"*

## Verdict in one line
A tradeable system exists and clears the retail band — but **~60% of what it earns is index beta
harvested by a wide trailing stop, not candlestick information.** Only ONE of eight formations beats
a matched-random entry.

## How the number fell, in three stages

**Stage 1 — raw sweep, 480 cells.** 346 positive. Best: `THREE_SOLDIERS|none|BE_1R_trail`,
n=8,107, win 53.1%, mean +37.53 pts, avg RR 1.82, exp_R 0.524, **t=9.90**.

**Stage 2 — the overlap defect (mine).** THREE_SOLDIERS fires on 8,172 of 69,848 bars = **11.7% of
all 15-min bars**, and the hold cap was 78 bars = 3 sessions. So ~9-11 positions were open at once
and the sweep summed them as independent trades. Two consequences: untradeable for one retail
account, and the t-stat was counting the same market move ~10 times.
Fixed with ONE POSITION AT A TIME. Measured overlap: **2.9× to 10.7×**.
It survived: n=758, 5.5/mo, win 53.4%, mean +45.52, RR 2.04, exp_R 0.607, Calmar 2.61,
**t_NW 7.85** (Newey-West, 5 lags), CAGR 59.6%, held-out 2026 **+67.56**.

**Stage 3 — the beta placebo, which is what actually decides it.** Every top cell was a BULLISH
formation; not one bearish formation appeared. NIFTY went 8,294 → 23,714 (**+186%**) across the
sample, the winning exit was always the wide trail, and the stop is
`max(prior-candle range, 0.4 × DAILY ATR)` — median **63 index points**, not the ~25 I first assumed.

> **Unconditional LONG on random 15-min bars, same stop/trail/hold: +29.25 pts, exp_R +0.432, win 48.6%.**
> Random SHORT on the same bars: **+13.57 pts.** Both sides pay, because a 63-point trail on a
> tripling index harvests drift with no pattern recognition at all.

## The eight formations against matched-random entry
Random bars matched on count and time-of-day, same side, same exit:

| formation | n | real | exp_R | random | rand p95 | p | short mirror | verdict |
|---|---|---|---|---|---|---|---|---|
| **THREE_SOLDIERS** | 758 | **+45.52** | 0.607 | +26.81 | 35.92 | **0.000** | +8.60 | **PATTERN ADDS** |
| MORNING_STAR | 776 | +33.68 | 0.443 | +26.42 | 34.23 | 0.092 | +16.36 | weak |
| MARUBOZU_BULL | 741 | +33.96 | 0.440 | +27.32 | 39.07 | 0.200 | +12.49 | beta only |
| BULL_ENGULF | 717 | +31.63 | 0.462 | +25.93 | 35.09 | 0.225 | +19.22 | beta only |
| HAMMER | 783 | +29.37 | 0.421 | +25.28 | 33.87 | 0.242 | +20.47 | beta only |
| TWEEZER_BOTTOM | 747 | +24.95 | 0.389 | +27.36 | 38.40 | 0.642 | +18.23 | beta only |
| THREE_CROWS | 755 | +21.21 | 0.306 | +16.09 | 26.74 | 0.233 | +18.61 | beta only |
| SHOOTING_STAR | 761 | +16.16 | 0.207 | +16.40 | 27.93 | 0.517 | beta only | beta only |

**7 of 8 are the wide trail wearing a candlestick costume.** THREE_SOLDIERS genuinely adds
**+18.7 points per trade over matched-random at p=0.000** — that increment is the real finding, and
it is 41% of the headline, not 100% of it.

## The EMA/DMA answer: the filters do not help
Held-out 2026 mean, `THREE_SOLDIERS|BE_1R_trail|hold78`:

| filter | held-out 2026 | in-sample t_NW |
|---|---|---|
| **none** | **+67.56** | 7.85 |
| wk_ema (weekly 9/21) | +86.72 | 5.96 |
| 15m_ema (9/21 on 15-min) | +4.83 | 6.19 |
| d_dma (10/20 daily) | **−44.06** | 4.91 |
| d+wk | −7.43 | 5.46 |

The daily 10/20 DMA filter **inverts** the held-out result. Unfiltered is the honest default. That is
consistent with the earlier finding that MA/RSI regime conditioning failed 0-of-56 cells.

## Retail sizing — the version that fits the band
| variant | trades/mo | win | mean | avg RR | exp_R | t_NW | CAGR | held-out |
|---|---|---|---|---|---|---|---|---|
| hold 26 bars (1 session) | **13.0** | 52.0% | +18.52 | 1.45 | 0.237 | 7.10 | 56.9% | +10.61 |
| hold 52 bars (2 sessions) | 7.8 | 50.4% | +30.41 | 1.80 | 0.426 | 7.23 | 56.2% | +11.01 |
| hold 78 bars (3 sessions) | 5.5 | 53.4% | +45.52 | 2.04 | 0.607 | 7.85 | 59.6% | +67.56 |

Only the 1-session version reaches the Principal's 10-100/month band. It also has the lowest
exp_R, which is the trade-off: the edge lives in the longer hold, and the longer hold is not a spinner.

## The standing risk nobody should ignore
This is a **long-biased wide-trail trend harvest measured entirely inside a +186% bull sample.**
Random longs earning exp_R 0.432 IS the strategy. In a flat or falling decade the same machinery is
negative, and there is no bear-market segment in the data long enough to test that. Any allocation
must be sized as beta with a trend overlay, not as market-neutral alpha.

## Honest gap
Weekly candle FORMATIONS (weekly engulfing / weekly hammer) were computed as columns but only the
weekly 9/21 EMA was used as a filter — weekly formations were never tested as TRIGGERS. The
Principal asked for "similarly with weekly candles" and that half is still owed.

## Files
`candle_mtf.py` (480-cell sweep) · `nonoverlap.py` (one-position-at-a-time + Newey-West) ·
`beta_placebo.py` (the decisive test) · `cells.csv` · `nonoverlap_cells.csv` · `beta_placebo.csv` ·
`placebo.py` (matched-random, written for the overlapping cells) · logs
