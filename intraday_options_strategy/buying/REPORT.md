# NIFTY Option-BUYING Strategy — Build & Honest Verdict
**Date:** 2026-07-01 | Location: `intraday_options_strategy/buying/`

## Mandate
Low capital → **option-buying only**, structure limited to **max 1 buy + 1 sell** (single
long option or a debit spread), holding **few minutes to few days**, ≤5–30 trades/day,
realistic retail costs. Build on 2021-05→2025-12; **forward-test untouched on 2026-01→2026-06-02.**

## Data
- NIFTY 1-min index options, real prices: **261 valid weekly expiries** 2021-05-27 → 2026-06-02.
- Skipped: `2023-06-29` (corrupt), `2026-06-09` (18-min stub). Each expiry file holds the
  full multi-day life of that weekly at 1-min, ~78–145 strikes. Volume ~100%, OI partial (2025+).
- Costs modeled: brokerage ₹20/order, STT 0.0625% sell-side, exch txn 0.0495%, GST 18%,
  SEBI, stamp, **slippage 0.5%/leg** (weekly ATM retail).

## Research findings (build set only)
1. **Intraday directional buying — NO EDGE (killed).** Every ORB/momentum/breakout signal
   gave a signed forward spot move of ~+0.00% to +0.04%; option breakeven over the hold is
   ~+0.3–0.5%. Signals are 10–25× too weak, hit rate ≈ coin flip, payoff symmetric (no skew).
   2024 full backtest: 398 trades, gross ≈ ₹0, net negative purely from costs.
2. **Cheap-vol buying — NO EDGE (killed).** Realized ≈ implied even on the cheapest-vol days
   (edge −0.01%). The money is on the RICH side (VRP) → that favors *selling*, not buying.
3. **Short/PE side — NO EDGE (killed).** NIFTY drifts up; every bearish signal failed.
4. **Long-only trend/momentum — a thin, real edge.** Bullish 10/20 EMA cross in an uptrend
   → +0.46% over 2–3 days at 70% hit (but rare). This is the equity upward-drift + convexity.

## Best honest config (locked on build set)
`emacross_ITM2`: bullish EMA(10/20) cross with close > EMA50, buy **2-strike ITM weekly CE**
(3–9 DTE), hold ≤4 days, target +100% / trail 35% / stop 35%.

| | Build 2021-2025 | Forward 2026 H1 (untouched) |
|---|---|---|
| Trades | 22 (~4.8/yr) | **2** |
| Win rate | 45% | **0%** |
| Profit factor | 2.81 | 0.00 |
| Total return (₹3L cap) | +17.1% | **−1.9%** |
| CAGR / MaxDD | +3.5% / −3% | — |

## VERDICT: option-buying has no robust, tradeable edge here
- **In-sample profit is 99.5% from 4 of 22 trades** (₹51,186 of ₹51,420). Remove those four
  big up-move captures → strategy is flat. Extreme concentration = fragile, not fundable.
- **Forward test failed to confirm:** 2/2 losers, −1.9%. Too low-frequency (~5/yr) to validate
  in 5 months — which is itself a verdict: unvalidatable = untradeable with confidence.
- Economic reason is sound (upward drift + convexity) but the effect is too thin to overcome
  theta + costs + the volatility risk premium, which all structurally penalize buyers.

## Recommended pivot (fits the SAME 1-buy-1-sell, low-margin constraint)
Flip the vertical from **debit** (buying) to **credit** (defined-risk selling):
a **bull-put credit spread** (sell nearer put + buy farther put) harvests the robust VRP —
the edge that actually exists in this data and in Track 1 — with **capped, low margin**
(≈ spread width × lot − credit), no naked blow-up risk. This directly addresses the
low-capital/margin worry while trading the edge that survives. Not yet built/validated.

## Exhaustive intraday MFE/MAE hunt (for "hold seconds→hours, 100%+ CAGR" ask)
Measured signed max-favorable / max-adverse excursion over 30/60/120 min — what a
trailing-exit intraday buyer actually harvests. Build set, 2,544 breakout signals.

| Population | H | E[MFE] | E[MAE] | MFE/\|MAE\| | n |
|---|---|---|---|---|---|
| ALL breakouts | 60m | +0.19% | −0.19% | **1.00** | 2544 |
| ALL breakouts | 120m | +0.25% | −0.25% | 1.03 | 2544 |
| STRONG (>1 ATR) | 60m | +0.20% | −0.19% | 1.05 | 361 |
| VERY STRONG (>2 ATR) | 30m | +0.22% | −0.08% | 2.84 | **37 (~8/yr)** |
| HIGH-vol day | 120m | +0.38% | −0.30% | 1.25 | 536 |
| Morning (≤10:00) | 60m | +0.19% | −0.19% | 0.98 | 1977 |

**Intraday MFE/MAE is essentially symmetric (≈1.0) — zero convexity.** Best-case
favorable excursion (~0.14–0.38%, and you can't catch the exact top) sits AT or BELOW
the ~0.3–0.5% option breakeven. The only convex niche (>2 ATR breakouts) is ~8 trades/yr
and still sub-breakeven. On high-vol days MFE is larger but so is the option premium (IV)
→ wash.

### FINAL VERDICT on intraday option-buying (secs→hours)
No edge capable of 100%+ CAGR exists in this data. Triple-confirmed: (1) endpoint forward
returns ≈ 0; (2) MFE/MAE ≈ 1.0 (no capturable convexity); (3) the one convex niche is too
rare and still sub-breakeven. 100%+ CAGR intraday buying would require repeatedly capturing
MORE than the entire (small, symmetric) intraday move net of theta+costs — not possible.
Also: "few seconds" is un-backtestable — the data is 1-minute bars.

## Mean-reversion buying (user-suggested) — NO EDGE (killed)
Oversold→buy CE, overbought→buy PE (RSI2, RSI14, Bollinger, TWAP z-score), 15,812 signals.
All triggers: fwd_mean ≈ 0 (+0.009% to −0.026% @60m), hit 44–54%, MFE/|MAE| 0.78–1.12.
**Skew NEGATIVE for oversold-bounce buys (−0.24 to −0.70)** = the wrong skew for a buyer
(small wins, rare big loss). Mean-reversion is a SELLER's edge, not a buyer's.

## Bull-put credit spread (short-vol, 1 sell + 1 buy) — mediocre + fails forward
Build 2021-2025: 237 trades, WR 70.5%, **PF 1.15**, +1.6% CAGR (risks ~₹13k to collect
~₹2k → one stop erases many wins). Forward 2026 H1: WR 38%, **PF 0.22, −12.7%** (blew up).
Both the long-CE buy AND the bullish credit spread lost in 2026 H1 → that window was a
bearish/choppy regime punishing anything bullish.

## SCOREBOARD — every path tested (nothing reaches Sharpe>2 / 100% CAGR, all fail OOS)
| Approach | In-sample | Forward 2026 H1 |
|---|---|---|
| Intraday momentum/breakout buy | gross ≈ 0, net<0 | — (no edge) |
| Multi-day trend buy (best: emacross ITM) | Sharpe 0.80, PF 2.8* | Sharpe −2.26, −1.9% |
| Cheap-vol buy | no edge | — |
| Mean-reversion buy | fwd ≈ 0, neg skew | — |
| Bull-put credit spread | PF 1.15, +1.6% CAGR | PF 0.22, −12.7% |
\* 99.5% of in-sample profit from 4 of 22 trades — fragile, not fundable.

## FULL intraday 1-min run (user-requested) — CATASTROPHIC (account wiped)
Ran the 1-min intraday engine (entries/exits at 1-min, squared off same day) over
2021-2026, 3 variants, ~1,600-2,500 trades each, ₹3L capital:

| Variant | Trades | WR | Build net | Build MaxDD | Fwd 2026 total |
|---|---|---|---|---|---|
| base_ATM | 1639 | 41% | −₹298,525 | −100% | −14.3% |
| ITM_convex | 2557 | 40% | −₹324,567 | −108% | −10.6% |
| spread_fast | 1639 | 39% | −₹314,209 | −105% | −7.7% |

**All three lost essentially the ENTIRE ₹3L account.** Negative per-trade expectancy
(~−1% after theta+costs) × thousands of trades = ruin. This is the definitive proof.

⚠️ The forward "Sharpe 2.21 / 3.51" printed by the script are NUMERICAL ARTIFACTS of a
blown-up (near-zero/negative) equity base — the forward TOTAL RETURN is still NEGATIVE
(−10.6%, −7.7%). A textbook example of how a Sharpe number can lie once the account is
ruined. Do not trust a Sharpe without checking the actual return + equity curve.
Graph: `pnl_intraday.png` (equity crashes ₹3L → ~0).

## Selective 1:2 R:R filter-mining (fixed 1 lot, user-requested)
Mined WR across hour / day / trend / vol / DTE / strength for a fixed 1:2 setup, 1,364
build trades. **No filter reaches 60% WR** (breakeven at 1:2 is 33%). Best buckets: CE
39.1%, strong-breakouts 42.4% (n=59), Monday 39.2%, high-vol 37.9%. Overall WR 34.8%,
net −₹327k. **Every bucket lost money.** Confirms: symmetric moves ⇒ can't get 60% WR at 1:2.

## Regime-aligned multi-timeframe (user's design: 3m>0 + >20DMA + >200DMA + MTF 5min + 5dRSI)
`ORB + regime + MTF + RSI`, fixed 1 lot, 1:2:
- Build 234 trades WR 38.5%, net −₹29,638, PF 0.85. **bull longs n=196 WR 40% net −₹9,922
  (~breakeven before costs — the closest anything got)**; bear n=38 WR 32% net −₹19,716.
- Forward: 10 trades WR 30%, net −₹7,416.

**Constructive finding: regime alignment WORKS directionally** — it lifted bull-long WR to
40% and to ~breakeven-before-costs. But (a) it still can't clear theta+costs, and (b) the
short side has no edge (drift) and drags it down. Europe-open trigger was worse (WR 31.7%).

## Bull-only + convex exits (final logical test) — WORSE
Bull-regime only, calls only, ITM, target 1.5 / trail 0.4: build 196 trades WR 30.6%,
net −₹45,991 (worse than the 1:2 version). Intraday has no convexity (MFE/MAE≈1.0), so
letting winners run just gives gains back. Forward +₹1,215 on 3 trades = noise.

## DEFINITIVE CONCLUSION (after ~10 approaches, incl. all user suggestions)
Intraday NIFTY option BUYING cannot be made profitable in this data. The best-case config
(regime-aligned bull-long 1:2) reaches only ~breakeven-BEFORE-costs; theta + slippage +
brokerage are the final wall. Regime alignment / MTF / selectivity (all correct principles)
help but cannot rescue a structurally negative-edge activity. The edge in NIFTY options is
on the SELL side (VRP) — see Track 1. The 100%+ CAGR ambition belongs in Track 2 (small-caps).

## Delta selection (user idea: 0.3/0.5/0.7 delta + strict SL, convex exits) — all negative
Regime-bull ORB trigger, real BS deltas, fixed 1 lot, SL 35% / target 100% / trail 40%:
| Target delta | Build n | WR | Net | PF | note |
|---|---|---|---|---|---|
| 0.30 (OTM) | 196 | 31% | **−₹14,428** | 0.87 | least-bad (small premium = small loss) |
| 0.50 (ATM) | 196 | 33% | −₹57,922 | 0.75 | |
| 0.70 (ITM) | 196 | 38% | −₹102,074 | 0.71 | worst (big premium × strict SL = big loss) |

0.3-delta is the *least-losing* (small per-trade risk) but still net negative — convexity
(max win ₹7.5k) can't overcome frequent small losses + costs. No delta makes buying profitable.

## Overnight hold (user idea) — real drift, but un-capturable via options
Close→next-open spot return (build): ALL mean **+0.075%** (57% hit); bull +0.092%. This is
the documented overnight-return premium — REAL but tiny. Option overnight-buy needs mean
>> +0.3% to beat 1 day theta + gap → hopeless. BUT the drift is capturable by holding the
INDEX/futures/ETF overnight (no theta): ~+0.08%/night ≈ ~18%/yr gross. A genuine anomaly —
just not an options-buying trade. Worth pursuing via NIFTYBEES/futures, not options.

## Buy 0.7Δ + sell 0.3Δ bull call spread (user idea) — WORSE than naked
Regime-bull ORB, fixed 1 lot: build 196 trades, **WR 41%** (highest yet — low theta = few
stops, 128 EOD exits), but net **−₹73,195**, PF 0.70. Worse than naked 0.5Δ long (−₹57,922).
The paradox: the short 0.3Δ leg cuts theta (WR up) but CAPS the upside — clipping exactly the
rare big up-move (convexity) that is the buyer's only friend. On a directionless underlying,
capping upside hurts more than the theta savings help. Net: worse than a naked long.

## ~14 structures tested; every one net-negative. Question is exhaustively settled.
Nothing changes the three structural facts: no intraday directional edge; no convexity
(MFE/MAE≈1.0); buyer pays theta+VRP+costs. The ONE real lead found: overnight drift
(+0.08%/night) — capturable via NIFTYBEES/futures (no theta), NOT via option buying.

## Files
- `chain.py` — option-chain accessor (expiry map, nearest-weekly, real-price pulls)
- `signal_research.py`, `signal_research2.py` — edge diagnostics (the kills)
- `engine.py` — intraday directional engine (proved no-edge)
- `engine_swing.py` — long-only trend swing engine (the best-case buyer)
- `compare.py` — trigger × structure grid on build set
- `forward_test.py` — one-shot 2026 H1 out-of-sample test
