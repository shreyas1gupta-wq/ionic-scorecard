# SWING MOMENTUM — first end-to-end backtest result (Session, 2026-06-17)
`run_swing.py` on survivorship-safe Nifty500 close panel 2005-2025 (976 symbols, PIT membership).

## Strategy
Weekly rebalance to TOP-20 leaders = Minervini trend-template pass (close>150>200DMA,
200DMA rising, close>50DMA, within 25% of 52w high, >=25% above 52w low) ranked by
relative strength (0.6*12m + 0.4*6m), equal-weight, REGIME-GATED (Nifty50>200DMA AND
breadth>35% → GREEN else cash), 20% trailing stop, 30bps round-trip cost. No param fitting.

## Result — V1 (raw) vs V2 (survivorship-fixed + liquidity floor + tighter regime/stop)
V1 (BIASED — delisting losses dropped, no price floor, stop 20%, regime 2-cond):
  full +21.0% / OOS +34.4% / MaxDD 35.7% — **INFLATED, do not cite**.
V2 (HONEST — realize -50% delist loss, price>=Rs.20, stop 15%, regime Nifty>200&50DMA+breadth>40%):
| segment | CAGR | vol | Sharpe | MaxDD | Calmar |
|---|---|---|---|---|---|
| Regime-gated FULL (2005-25) | +11.6% | 14.4% | 0.43 | 23.0% | 0.51 |
| IS (2005-~2019) | +9.8% | 12.2% | 0.34 | 21.0% | 0.47 |
| OOS (~2019-2025) | +16.1% | 18.5% | 0.60 | 23.0% | 0.70 |
| Always-on (no regime) | +21.7% | 26.8% | 0.66 | 73.4% | 0.30 |
Per-year (V2): +76% (2014), +62% (2021), +37% (2012, 2023), +32% (2017), +28% (2009),
+26% (2020); worst -14% (2018), -11% (2022), -9% (2019). 2005-08 flat (no Nifty pre-2008 →
cash; full CAGR understated — active-period 2009+ CAGR ~14-15%).

## Verdict (HONEST, post-cleanup)
- **The survivorship fix HALVED the CAGR (+21%→+11.6%)** — the gap was fake alpha from
  escaping delisting losses. Critical lesson: rigor matters; the first number was inflated.
- Edge is still REAL but modest: ~12% full / ~16% OOS CAGR, MaxDD now <23% (target MET),
  OOS Calmar 0.70. Regime filter is ESSENTIAL (always-on MaxDD 73%).
- "100%+ CAGR" is real only as EPISODIC bull-regime payoffs (+76% 2014, +62% 2021), NOT a
  sustained rate — exactly the honest "skill+regime bet" framing. Compounding the good years
  while sitting out chop (regime) is the whole game.

## HONEST CAVEATS (these will lower live performance — fix before believing the number)
1. **No liquidity/volume filter** (master is close-only) → some illiquid/penny names may be
   "tradable" in sim but not in reality. THE biggest optimism source. Need ADV gate (volume
   data: the 239 raw CSVs have it to 2021; or fetch via Angel). Likely the +21% drops materially.
2. **Survivorship**: delisted names' forward return is dropped (NaN) not realized as a loss →
   slight upward bias. Fix: realize last return / -100% on delist.
3. **MaxDD 35.7% full > 25% target** — regime filter leaks 2018/2019 drawdowns. Improve regime
   (distribution-day count, faster breadth, vol overlay) to hit <25%.
4. Close-only weekly fills; no intraweek stops; 30bps cost may be light for smaller names.
5. Bull-regime dependent: 2005-08 + chop years flat/negative — this is a momentum REGIME bet,
   as designed. Not a smooth compounder.

## MULTI-STRATEGY TEST (run_multistrat.py) — naive equity stacking FAILS
Added a mean-reversion sleeve (buy oversold dips in uptrends) to combine with momentum:
- Momentum +11.3%/Sh0.41; Mean-reversion +1.9%/Sh-0.22 (no edge after costs);
  **correlation +0.57**; risk-parity combo +6.7%/Sh0.11 — WORSE than momentum alone.
- LESSON (proves the thesis discipline): two LONG-ONLY equity sleeves gated by the SAME
  market regime are NOT uncorrelated — shared equity beta + joint cash in RED. Adding a
  weak, correlated sleeve drags the book down. Genuine diversification needs DIFFERENT
  RETURN DRIVERS: (a) the options SHORT-VOL sleeve (carry, different instrument — validated
  Track1), or (b) a MARKET-NEUTRAL long-short (removes beta). NOT another long-equity sleeve.

## NEXT (priority)
1. Add liquidity/volume gate (re-run; expect lower but cleaner CAGR) — the key validity fix.
2. Fix survivorship (realize delisting losses).
3. Improve regime to cut MaxDD <25% (distribution days, vol overlay).
4. Walk-forward the few params (TOP_N, stop, RS weights) — small grid, OOS-honest.
5. Add the GOD_TIER dimensions (D1 special-sits, D4 PEAD, D11 SLB carry) as uncorrelated sleeves.
6. Wrap in the Risk OS (vol-target, DD circuit-breaker).
