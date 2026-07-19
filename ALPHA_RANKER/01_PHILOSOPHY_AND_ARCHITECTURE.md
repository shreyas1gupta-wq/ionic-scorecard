# 01 — Philosophy & Architecture

## 1. The core thesis: a conviction engine, not a classifier
A classifier maps features → a label ("Buy"/"Sell") through fixed rules. That fails because:
- Stock returns are driven by a *shifting* set of forces — geopolitics, global risk appetite, liquidity, rates, commodities (gold/silver/crude), earnings, valuation (absolute, relative, and vs own history), price action, momentum, volatility, mean-reversion, overbought/oversold, positioning/holdings, volume, debt, manipulation, and more — and **the weight of each force changes with the holding horizon and the market regime.**
- A rule like `ROE > 15%` is meaningless out of context: 12% ROE compounding at 25% with a widening moat beats 20% ROE that is flat and being disrupted. Context, not cutoffs.

So ALPHA_RANKER outputs a **probabilistic conviction**, not a verdict:
- **Sign** = direction of the edge (positive = attractive to be long over this horizon).
- **Magnitude** = strength of conviction, a blend of *expected edge × probability × breadth of confirming evidence − penalty for red flags and uncertainty*.
- Alongside the score it emits **P(positive return over horizon)**, an **expected-return distribution**, a **win-rate** (historical base rate of comparable setups), and a **downside probability**. These make the score *auditable* and *actionable for sizing*.

## 2. Horizon theory — why one model can't serve all periods
Every factor has a **half-life** — how long its predictive signal persists. Weights ≈ the inverse of how fast the factor decays relative to the horizon.

| Force | 1M weight | 1Y weight | 5Y weight | Why |
|---|---|---|---|---|
| Price momentum / RS | **High** | Medium | Low | 1–12m momentum is the strongest short/medium anomaly; irrelevant to a 5y compounder except entry timing. |
| Mean-reversion / overbought-oversold | **High** | Low | ~0 | Reverts over days–weeks. |
| Flow / positioning / F&O OI / PCR | **High** | Low | ~0 | Sentiment mechanics, short-lived. |
| Event catalyst (earnings date, rebal, ex-div) | **High** | Medium | Low | Datable, decays post-event. |
| Estimate-revision momentum | Medium | **High** | Medium | Revisions trend for 1–4 quarters (drift). |
| Valuation (vs own history / peers) | Low | **High** | **High** | Weak 1m signal, dominant re-rating & long-run driver. |
| Earnings growth trajectory & quality | Low | **High** | **High** | Compounds over years. |
| Moat durability / reinvestment runway / capital allocation | ~0 | Medium | **Dominant** | The whole 5y game. |
| Management integrity / promoter quality | Penalty-only | Medium | **Dominant** | Slow to matter, catastrophic when it breaks. |
| Structural tailwind vs disruption risk | Low | Medium | **Dominant** | TAM growth vs obsolescence (e.g. AI vs IT services). |

Design consequence — **character of each lens:**
- **1M** = systematic & quant-heavy. Mostly market-microstructure + catalyst + positioning. Fundamentals are ~static over a month, so they act as a *gate/penalty*, not a driver.
- **5Y** = discretionary & narrative-heavy. Growth × valuation × moat × management. Price action matters *only* for the entry point.
- **1Y** = the blend — the horizon where earnings revisions + valuation re-rating + relative strength all fire together.
- **MICROCAP** = a different game entirely (see `07`): the edge is *mispricing from neglect*, and the dominant risk is *fraud/governance*, so forensics and promoter analysis outweigh everything, and liquidity constrains sizing.

## 3. The stack (data → score)
```
        ┌─────────────────────────────────────────────────────────────┐
  L0    │ DATA LAYER  (09) — yfinance, screener, NSE/BSE, company sites, │
        │ HF, macro (RBI/FRED/MOSPI), Bloomberg dump (last resort)      │
        └───────────────┬───────────────────────────────────────────────┘
                        ▼
  L1    FACTOR LIBRARY (04–07) — each factor scored RELATIVE (z / percentile)
        within peer set, own history, sector, cap. PIT-guarded. Sign-adjusted.
                        ▼
  L2    THEME SCORES — factors grouped: Momentum · Value · Quality · Growth ·
        Sentiment/Flow · Catalyst · Forensic/Risk. (interpretable middle layer)
                        ▼
  L3    HORIZON COMPOSITE — theme scores × w(horizon, regime, sector, cap).
        Weights are calibrated (Phase 6–7), never hand-fixed.
                        ▼
  L4    OVERSIGHT CASCADE (03) — global→national→sector gates/shifts the composite;
        override forces a written justification.
                        ▼
  L5    FORENSIC / RED-FLAG OVERLAY (08) — nonlinear, size- & regime-conditional
        penalty; short hard-veto list; longer heavy-penalty list.
                        ▼
  L6    PROBABILITY CALIBRATION (02, 11) — composite → P(up), E[return], win-rate
        via historical mapping (isotonic/logit) per horizon per regime.
                        ▼
  L7    CROSS-HORIZON COUPLING — large negative 1M taxes 5Y (entry-timing).
                        ▼
  L8    SYNTHESIS + RED-TEAM + HUMAN GATE (10) — score [-100,+100] + 1-para thesis;
        devil's-advocate pass (mandatory 1Y/5Y); analyst sign-off on edge cases.
```

## 4. What "flexible, not rigid" means operationally
- **Relative scoring, always.** A factor's raw value is converted to a rank/percentile/z within the *right* comparison set (sector peers of similar size, and the stock's own 5–10y history). "Cheap" for an FMCG name ≠ "cheap" for a PSU bank.
- **Regime-conditional weights.** The same factor gets a different weight in a low-vol uptrend vs a high-yield credit-scare downtrend. The regime classifier (`03`) picks the weight vector.
- **Documented override protocol.** Soft base weights are the *starting point*. An agent/analyst may override any weight or the final score, but must write the reason (logged). This is the "guide for a research analyst," not an autopilot.
- **Judgment on red flags.** No red flag is auto-fatal except the short hard-veto list. Everything else is a heavy, context-scaled penalty (`08`).

## 5. Output contract (every stock, every lens)
```
{
  ticker, lens (1M|1Y|5Y|MICROCAP), as_of_date, regime_tag,
  score:        int  [-100, +100],
  p_up:         float [0,1],           # P(return > 0 over horizon)
  e_return:     float,                 # expected return over horizon
  return_dist:  {p10, p25, p50, p75, p90},
  win_rate:     float,                 # historical base rate of analog setups
  downside:     {p_drawdown_gt_X, expected_shortfall},
  theme_scores: {momentum, value, quality, growth, sentiment, catalyst, forensic},
  top_drivers:  [ {factor, contribution, direction} ... ],  # explainability
  red_flags:    [ {flag, severity, veto|penalty} ... ],
  thesis:       "one crisp paragraph — buy case & exit/thesis-break triggers",
  overrides:    [ {who, what, why} ... ],
  confidence:   "high|medium|low"      # driven by data completeness + factor agreement
}
```
The **thesis paragraph** is systematic-quant-flavoured for 1M (setup, catalyst, invalidation level) and discretionary growth-valuation-flavoured for 5Y (moat, runway, price paid, thesis-break).

## 6. Non-goals / guardrails
- Not a price target machine; it ranks probability-weighted attractiveness.
- No fixed cutoffs shipped to production.
- No factor/weight enters production without passing the R&D loop (IC + DSR/PBO + ablation + lookahead audit).
- No real capital. Research/paper only.
