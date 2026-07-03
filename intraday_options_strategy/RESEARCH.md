# RESEARCH NOTES (v0 — from model knowledge, web verification PENDING)

> Status: the web-research fan-out hit the org token limit before returning.
> These notes are from training knowledge (cutoff Jan 2026). Each item is
> tagged [VERIFY] where a citation should be added later. Re-run plan: one
> topic per session via single WebSearch calls (see PLAN.md).

## 1. Volatility risk premium (VRP), India
- India VIX has historically averaged a premium over subsequently realized
  Nifty vol (order of 2–5 vol points in calm regimes; inverts sharply in
  crashes — Aug 2015, Feb 2018, Mar 2020, Jun 2024 election day). [VERIFY]
- Implication: systematic short-ATM-premium earns the spread but with heavy
  left tail → only tradable with hard SLs, event filters, VIX band gates.
- Intraday theta on weeklies is strongly convex into expiry; the largest
  clean decay window is roughly 09:30–14:30 on expiry day. [VERIFY]

## 2. Intraday short straddle ("9:20 straddle") evidence
- Widely backtested by Indian retail quant communities: sell ATM straddle
  ~09:20, per-leg or combo SL 20–40%, square off 15:00–15:25. Reported win
  rates ~55–65% with PF 1.1–1.4 AFTER costs on Nifty/BankNifty; results are
  regime-dependent (poor in sustained trend years like H2-2020 rally days,
  good in range years). [VERIFY — marketing bias risk high]
- Known failure mode: gap-and-trend days (global shocks); event-day filter
  and gap filter materially improve PF. [VERIFY]
- Day-of-week: expiry-day and day-before-expiry historically best for sellers
  (max theta), Monday worst (weekend gap risk realized). [VERIFY]

## 3. 0DTE dynamics
- US SPX 0DTE research (CBOE/academic, 2023–25): no systematic mispricing
  either side after costs for naive rules; intraday sellers earn theta but
  face gamma spikes; edge concentrates in disciplined risk caps. [VERIFY]
- India: weekly Nifty expiry (Thu→Tue from Sep-2025); SEBI 2024-25 measures
  (lot 25→75, single weekly expiry per exchange, higher expiry-day margins
  via ELM +2%) reduce but don't eliminate the trade. SEBI studies: ~90% of
  retail F&O traders lose money — the losing cohort is dominated by naked
  long options and unhedged leverage. [VERIFY]

## 4. Regime classification & allocation
- Practical day-typing at 09:20 with OHLCV+VIX only: gap%, opening-range
  width percentile, prior-day range, VIX level/Δ5d, ADX(5m). Trend-day
  precursors: wide gap + narrow prior range + VIX jump; range-day: small gap
  + mid VIX + low ADX. (Standard practitioner heuristics; formal: Lopez de
  Prado regime HMMs — overkill at this data granularity.)
- Allocation: vol-parity across sleeves + rolling-Sharpe gating beats equal
  weight when sleeves are genuinely uncorrelated; fractional Kelly (≤0.25)
  on top as a cap, not a target. Drawdown governor (halve at -4%, quarter
  at -8%, hysteresis) is the single highest-value risk overlay. [VERIFY]

## 5. Execution (NSE retail)
- ATM Nifty weekly spreads: typically ₹0.05–0.50 (tight); deep OTM and
  high-VIX moments widen sharply. Market orders acceptable ONLY when spread
  ≤ ~0.05% of premium or on stop-outs; otherwise join-the-mid limits.
- Freeze quantity Nifty: 1800 (24 lots×75) per order — split larger. [VERIFY]
- Angel One SmartAPI: REST + websocket quotes, ~10 req/s class limits; fine
  for 1-min decision loop, NOT for sub-second. Kotak Neo similar. Plan the
  live loop at 1–5s cadence, decisions on bar close. [VERIFY]

## 6. Alpha decay & overfit guards
- McLean & Pontiff: published anomaly returns decay ~30–60% post-publication
  → assume any public Indian options edge is partially arbitraged; demand
  margin of safety (OOS Sharpe > 1, PF > 1.25 after 2× cost stress).
- Bailey/Lopez de Prado: deflated Sharpe & PBO — with ~650-combo grids,
  in-sample Sharpe must clear a high bar; our guard: small grids, WFO,
  one-shot OOS, paper month before capital.

## Adopted rule set (carried into STRATEGY_V2.md sleeves)
S2 range-day short straddle: gap<0.3%, VIX∈[11,22], ADX5m@09:20<25, no
event/expiry day; combo SL 30%, PT at 50% credit capture, exit 15:00.
S3 0DTE: expiry days only (post 2019-02), gap<0.4%, VIX<24; SL 25%, PT 60%,
exit 14:30, half risk of S2.
S4 trend rider: ADX>28 + ORB break + TR expansion + |bias|≥1 agreeing; long
ATM option; partial 50% @ +35%, trail 25%, SL 30%, max 2/day.
S1 momentum (v1): only in trend regime with bias agreement; WFO params.
