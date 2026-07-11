# IDEA FACTORY — high-throughput funnel (Principal order 2026-07-11: "we can have 1000s of ideas; sample on 1-2yr, which passes run full")
**Replaces the few-deep-cards default for IDEA GENERATION. The deep-card machinery (freeze/run-cards/red-team) moves to the BOTTOM of the funnel where it belongs.**

## The funnel
1. **INTAKE (target 100+/wave):** ideas from (a) online sweeps — papers, quant blogs, strategy sites, practitioner forums (agents harvest, sonnet tier); (b) quant-trader archetypes (momentum/reversal/seasonality/vol/flow/liquidity across every dataset we own); (c) technofunda combos (PIT earnings x technicals — our unique data edge); (d) Principal ideas — always jump the queue. Each idea = ONE canonical spec (JSON, harness-schema) fixed at intake. NO per-idea tuning at screen stage — a variant is a new intake row.
2. **STAGE-1 SCREEN (cheap, minutes each):** standardized harness, SCREEN WINDOW = 2024-07-01..2026-06-30 (recent 2yr), coarse costs (25bps/side stocks swing; asset-class defaults). GATE: net expectancy > 2x cost AND t >= 1.5 AND n >= 30 AND direction consistent. Every screened idea LOGGED (id, spec, result) — the ledger records the full denominator.
3. **STAGE-2 VALIDATION (survivors only):** full untouched history (2013/2015..2024-06 — never used by the screen) + placebo-shares-exit control + era split + realistic costs. Bars: t >= 2.5, beat placebo95, eras consistent. This window's p-values stay honest BECAUSE the screen never saw it.
4. **STAGE-3:** Gate-4 realism + red-team battery (B1b template) -> IC -> paper-first. Existing law unchanged.

## Why this beats both extremes
- vs. today's deep-cards-only: ~15x more shots on goal per session; discovery rate scales with idea count.
- vs. naive mass backtesting: the screen/validate WINDOW SPLIT is the multiple-testing control — promoting 20 of 1,000 on window A and confirming on untouched window B is a pre-registered holdout design, not p-hacking. Screen hits that fail validation are logged as such (expected: most).
- Kills stay cheap: a screen fail costs minutes, not a day.

## Harness (04_RND_LAB/IDEA_FACTORY/harness.py)
Spec schema: {"id", "name", "source", "asset": "stocks_daily|index_daily|crypto_1m|gold_1m|fo_daily", "signal": {"type": <primitive>, "params": {...}}, "direction": "long|short|both", "entry": "next_close", "exit": {"type": "bars|trail_dma|target_sl", "params": {...}}, "universe": "pit_n500|nifty|btc|..."}
Signal primitives v1 (extensible): dma_cross, rsi_thresh, nday_breakout, nday_low, gap_pct, vol_expansion, distance_from_dma, consec_days, seasonality_dow/dom, earnings_event (PIT), vix_thresh, flow_quintile (participant-OI), pair_zscore. Composites = AND of <=3 primitives.
Universe/costs/calendar/PIT/survivorship handled once, centrally. Every run emits a row to IDEA_FACTORY/screen_ledger.csv.

## Governance interface
- Screen window + gate frozen in THIS file (this commit). Validation specs auto-freeze per survivor (one commit per wave, listing survivor ids, BEFORE stage-2 runs).
- Trials ledger: one row per WAVE with the full denominator; DSR at stage-3 uses screen-count honestly.
- Streams already killed by deep cards (standalone stock meanrev, basket-ORB-EOD, PCR filters, option buying) are BLOCKED at intake unless the spec differs structurally (curator check).

## WAVE-1 ARCHETYPES RESULT (2026-07-11): 0/60 gate passes — the screen is calibrated correctly
- Every generic high-n stocks idea (breakouts 20/55/100d, breakdowns, gap follow/fade, trend+pullback) is DECISIVELY negative net of 50bps RT: -0.4 to -0.9%/trade at |t| 7-25. Consistent with every deep-card kill: generic constructions cannot pay retail stock friction. NOT a harness bug - a market fact.
- Near-misses (logged, NOT promoted - gate stands): W1-AR-25 turn-of-month stocks (+0.123% net/trade, t=+2.60, n=11,680 - fails the 2x-cost expectancy bar but statistically strongest positive in the wave); W1-AR-20 (+1.18%, t=1.83, n=22); W1-AR-60 gold 7/21 momentum (+1.07%, t=1.87, n=13). Gold/crypto n-thin per auditor coverage caveat.
- **Wave-2 design consequence:** the stocks 1%-net hurdle dominates everything - future waves tilt to (a) low-cost assets (index futures ~16bps hurdle, gold/crypto), (b) bigger-move constructions (longer holds, tail/event conditioning), (c) PORTFOLIO-level constructions (e.g. a turn-of-month monthly overlay evaluated on Sharpe - NEW intake, not a retro-promotion of AR-25).
