# FF near-month vehicle — REVERSED structure (SELL OTM CE / BUY ATM CE) — 2026-07-07
Owner: Arjun Rao. Agent's own write to this path was blocked by subagent policy; content below is verbatim from the agent's final report.

## Verdict: KILL (over-determined)

**Structure / polarity:** SELL near-month OTM CE / BUY near-month ATM CE, same expiry. This is a **NET DEBIT bull-call spread** — a capped-risk, net-long-delta directional-bullish bet, NOT a premium-harvesting credit structure. Measured entry: Rs 31.47/share net DEBIT (99.8% of trades are debits; mean spread width Rs 82). Opposite polarity to the killed bear-call version — do not read it with that intuition.

**Change vs the killed (non-reversed) version:** sides swapped (ATM now LONG, OTM now SHORT), and the short-OTM strike uses the liquidity-informed rule from the live-chain finding earlier the same day: among OTM1-OTM6 candidates clearing an ex-ante floor (trailing-5-session median volume > 0, PIT), pick the most liquid (argmax trailing-5 median volume), else DROP. Drop rate 6.4% — liquidity is not the binding constraint here. Chosen short-leg distance mean 2.69 strikes (mix 1:185, 2:168, 3:88, 4:77, 5:69, 6:43): the rule systematically reaches past the nearest OTM to deeper, more-liquid strikes, which widens the spread and roughly doubles the debit (Rs 31.5 vs Rs 17.6 for a nearest-OTM tight spread) — dragging net to -8.12 vs a tight-mirror estimate of about -6.3.

**N / win / PF:** 630 filled of 673 signals (6.4% drop). Win 30.8%, PF 0.49.

## Full validation battery (slippage + statutory, denominator-free)

| Cohort | n_fill | Rs 1x | Rs 2x | %spot 1x | %spot 2x | win | PF | Sharpe(pt) | Sharpe(mo) |
|---|---|---|---|---|---|---|---|---|---|
| FULL | 630/673 | -8.12 | -13.34 | -0.377 | -0.564 | 0.308 | 0.49 | -3.32 | -2.25 |
| BUILD | 446/474 | -7.56 | -12.30 | -0.380 | -0.548 | 0.294 | 0.54 | -3.15 | -2.20 |
| FWD (OOS) | 184/199 | -9.48 | -15.85 | -0.371 | -0.600 | 0.342 | 0.34 | -3.89 | -2.46 |
| REGIME pre-2025-09 | 569/610 | -7.77 | -13.03 | -0.378 | -0.556 | 0.306 | 0.52 | -3.32 | -2.28 |
| REGIME post-2025-09 | 61/63 | -11.35 | -16.14 | -0.372 | -0.630 | 0.328 | 0.24 | -4.02 | -2.00 |

Negative every single cut, both cost levels. FWD (true out-of-sample) is worse than BUILD (Sharpe -3.89 vs -3.15) — no rescue from the holdout period.

**Per entry-year (Rs 1x / %spot / win):** 2021 -13.60/-0.64/0.19 · 2022 -5.20/-0.63/0.21 · 2023 -4.94/-0.33/0.28 · 2024 -9.91/-0.21/0.37 · 2025 -7.46/-0.34/0.35 · 2026 -21.79/-0.56/0.27. Negative every year.

## Why reversing was never going to work
Friction-free gross is **-2.70 Rs/trade** — negative before a rupee of cost, and the exact sign-mirror of the bear-call's gross **+2.51 Rs/trade**. Costs (~Rs 5-8 round-trip) are sign-invariant/always adverse, so flipping a cost-dominated loser makes it strictly worse by roughly 2x the gross. The tiny gross edge in this signal family sits on the **short-premium/short-delta** side (the naked short-ATM reference was +0.39%/spot), not the long side. Directional diagnostic: underlying moved only +0.045% over holds on average (flat) -> the long-delta bet got no drift, just bled theta + costs (corr(P&L, underlying move) = +0.27, weak).

DSR/PBO not owed per CIO precedent (no positive raw forward edge to certify). Degenerate scan is clean — no suspicious-good flags, it is simply a loser, broad-based across names/years/regimes, not concentrated in a few trades.

## Data lineage
Signal: `results/S-03/20260705_resurrection/causal_per_trade.csv` (`ff_v3_causal.py`), 673 causal `signal==True` rows, entries 2021-2026. Option prices/vols via `fill_audit.py` + `dispersion_strategy.py` loaders (reused verbatim). Fills: D+1, both legs same day. Exit: 2 sessions pre-expiry.

Files: `ff_nearmonth_vertical_reversed.py`, `per_trade_reversed.csv` (673 rows), `summary_reversed.json` (all in this folder). Originals (`ff_nearmonth_vertical.py`, `per_trade.csv`, `summary.json`) untouched. IDEA_PIPELINE.md updated with a distinct row (own trial count = 1, not merged into K-012's or the bear-call's ledger).

## Bottom line for the whole FF near-month family
The consistent read across the bear-call, this bull-call reversal, and the naked references is that the FF signal's monetizable gross edge lives on the short-premium/short-delta side but is only about +2.5 Rs/trade — below this vehicle family's ~Rs 6 cost floor. **The binding constraint on the entire near-month family is transaction cost versus a thin gross edge, not direction and not liquidity.** Any future FF vehicle needs either a materially cheaper cost stack or a larger gross edge before it clears the bar — reversing which leg is bought vs sold cannot manufacture either.
