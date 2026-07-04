# S-03 SIZING RE-CHECK (Principal challenge, 2026-07-05): "were we too hard?"
**Finding: the kill holds for EQUAL-SPREAD books; it does NOT hold under PREMIUM-NORMALIZED sizing with liquidity caps.**
| Sizing basis | Build | Forward (2025-26) |
|---|---|---|
| Equal spreads (kill metric) | +6.49 pts | **-6.68 pts (LOSES)** |
| Equal premium, uncapped (old backtest's implicit sizing) | +14.0%/trade | **+10.2%/trade** |
| Equal premium, 3x median liquidity cap | +Rs12.43/Rs100 | **+Rs9.91/Rs100 (POSITIVE)** |
| Equal premium, 5x cap | +Rs13.42 | +Rs10.16 |
WHY: forward losses concentrate ENTIRELY in the dearest-premium quartile (med Rs226 back-leg: -44.4 pts/trade) while cheap/mid quartiles win (+2 to +11 pts). Equal-spread booking puts 4x the rupees into exactly the losing bucket; equal-premium sizing (or a max-premium-per-spread filter) removes it.
CAVEATS: 199 forward trades; capacity per trade modest (cap binds at 3-5x median spreads); slippage flat 1.5% (thin cheap strikes may cost more); this is 3 NEW family trials (count them).
ROUTE: /resurrect K-012 evidence — NOT an auto-unkill. Needs: Sameer sensitivity on the premium-cap parameter + Nikhil placebo (is 'avoid expensive calendars' just a vega-size effect?) + circuit/volume fill audit on the cheap-strike fills.
