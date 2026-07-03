# EXECUTIVE SUMMARY — Nifty Intraday Options Strategy

**Data & rigour.** 11.4 years of 1-minute Nifty 50 + India VIX + BankNifty
(2015–2026, 2,794 clean trading days). Strict no-lookahead (next-bar-open
entry, shift-tested indicators), conservative costs (₹102/round-trip-lot ≈
0.91% of premium), 70/30 IS/OOS split, 126-fold walk-forward, full robustness
suite. No curve-fitting: small grids, one-shot OOS.

**Edge — what we found.** The original brief (intraday long-option signals,
WR ≥ 55%, R:R ≥ 1.5) is **not achievable**: across 126 walk-forward folds,
only 0.8% contained a feasible parameter set; OOS win rate sits ~40% (R:R 1.66,
PF 1.14, marginally positive P&L but Sharpe < 0 — return below cash because a
disciplined Kelly halts deployment on weak edge). Buying premium intraday pays
theta and crosses spreads every trade. The accessible edge is the **opposite
side**: harvesting the volatility risk premium via **0DTE expiry-day short
straddles**. A break-even analysis shows this sleeve turns profitable once real
ATM IV exceeds VIX by ~1.5× (OOS PF 1.19 at 1.5×, 2.6 at 1.8×) — and IS/OOS
break-evens agree exactly, indicating a structural, non-overfit effect.
Intraday weekly straddles were rejected (need ~1.8× IV — implausible).

**Scalability.** ₹1 Cr is comfortably inside Nifty weekly/expiry liquidity at
≤10 lots/leg; slippage and freeze-quantity are the binding constraints, not
size.

**Practical risks.** (1) All option P&L is synthetic (Black-Scholes at VIX, no
smile, no crash spread-widening) — the 0DTE result MUST be confirmed on real
NSE option prices before capital. (2) Short premium has fat left tails — the
drawdown governor, event filter and hard stops are essential, not optional.
(3) Post-publication alpha decay and SEBI F&O changes (lot 75, single weekly
expiry) compress the edge.

**Recommended next steps.** 1) Acquire NSE F&O EOD bhavcopy; measure the real
IV-vs-VIX multiplier by DTE. 2) Re-validate the 0DTE sleeve on real prices. 3)
Small-grid WFO on the surviving sleeve only. 4) 30-day Angel One paper run to
calibrate slippage/fills. 5) Go live on Kotak Neo only if OOS PF > 1.25 after
2× cost stress. **Verdict: not yet deployable; one clear, testable edge
identified with a concrete validation path.**
