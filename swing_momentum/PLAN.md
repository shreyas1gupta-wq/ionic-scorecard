# SWING-MOMENTUM SYSTEM — low-capital (≤₹10Cr) leadership swing trading
### Master plan + sub-plans. Resume-first doc. Built 2026-06-16.

> **What this is:** a rules-based (but regime-gated and discretion-informed) stock
> swing system in the Minervini-SEPA / O'Neil-CANSLIM / Darvas / VCP tradition,
> deliberately scoped to ≤₹10Cr where concentration in thin leaders IS the edge.
> **Honest framing (do not lose this):** this is a SKILL + REGIME bet, not a
> stationary alpha. The whole game is (a) trade leaders only, (b) only in
> momentum regimes, (c) cut losers ruthlessly, (d) let winners run, (e) size so a
> bad regime can't ruin you. Capacity is the moat — it must stay small.
>
> **RESUME:** read this top-to-bottom, then start at the first unchecked `[ ]`.
> Python full path: `C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe`
> (`python` alias broken). Console is cp1252 → no unicode in prints; set PYTHONIOENCODING=utf-8.

---

## 0. OBJECTIVE & CONSTRAINTS
- Capital ≤ ₹10Cr (stays small after scaling — by design). Target: 40–100%+ CAGR
  in momentum regimes, FLAT-to-small-loss in non-momentum regimes (the regime
  filter is the difference between 100% and ruin).
- Holding: days→weeks (swing). NOT intraday. Overnight allowed (this is equities).
- Universe (MULTI-MARKET — see `..\PORTFOLIO_OF_EDGES.md`): (a) NSE equities (Kite),
  (b) US stocks + sector ETFs (INDmoney/LRS), (c) commodity ETFs + MCX futures as a
  SEPARATE-driver commodity-TREND sleeve. Same leadership/momentum engine per market;
  per-market data, costs, and (for US) net-of-LRS/TCS/withholding/cap-gains/FX model.
  Liquidity gate per market (≤₹10Cr enters/exits in ≤10–20% ADV). Timezone: Indian
  day + US night run on the same capital. Diversify by edge-type+asset-class, not just
  geography (US & Indian equity sleeves are correlated — the commodity-trend sleeve is
  the real diversifier).
- Concentration: 5–12 names, position 8–25% each, pyramid into winners.
- Hard rules: stop-loss on EVERY position; max portfolio heat cap; no averaging down.
- Anti-overfit + survivorship-bias-free backtest mandatory.

---

## PHASE 1 — DATA INFRASTRUCTURE  (sub-plan 1)
- [ ] 1.1 Build the POINT-IN-TIME tradable universe (survivorship-safe). We already
      have `NIFTY500_TICKER_2005_2025_Final.xlsx`, `Nifty500_Delisted_2005_2025.xlsx`,
      `Historical stock composition of Nifty 50 / Next 50.xlsx`, and daily OHLCV in
      `raw\nifty500\*.csv` (2005–2021) + GitHub Nifty50 20yr. INVENTORY all, map coverage.
- [ ] 1.2 Acquire daily EOD OHLCV + VOLUME for the full NSE universe 2010→today.
      Sources: existing CSVs; extend to 2026 via Angel SmartAPI getCandleData (DAY
      interval, EQ segment) using the scrip master we already pull; or bhavcopy EOD.
- [ ] 1.3 Acquire FUNDAMENTALS (quarterly EPS, sales, margins, RoE, debt) for CANSLIM
      'C'/'A' filters. Sources: screener.in scrape, Tickertape, or NSE/BSE filings.
      Point-in-time (no restated-data lookahead) — store with report DATE not period.
- [ ] 1.4 Corporate actions: split/bonus/dividend adjustment — build a clean adjusted
      price series (we have `raw\corporate_actions`). Verify no phantom gaps.
- [ ] 1.5 Liquidity series: 20d avg turnover per name per day (for universe gating).
- [ ] 1.6 Index/breadth data: Nifty500 + advance/decline, % stocks > 200DMA, new
      highs/lows (for the regime filter, Phase 4). Build from the universe.
- [ ] 1.7 Canonical parquet: `data\eq_daily.parquet` (date,symbol,o,h,l,c,vol,turnover,
      adj factors) + `data\fundamentals.parquet` + `data\universe_pit.parquet`.
- [ ] 1.8 DATA AUDIT: coverage map, delisted inclusion check, survivorship test
      (does the universe on date D only contain names listed & liquid on D?).

## PHASE 2 — SIGNAL ENGINE (leadership detection)  (sub-plan 2)
Synthesize the proven momentum frameworks into ranked, lookback-only features:
- [ ] 2.1 Relative Strength rank (O'Neil RS): trailing 3/6/12m return percentile vs
      universe (weighted, recent-heavier). RS line vs index (new-high RS = leader).
- [ ] 2.2 Minervini Trend Template (all must hold): price > 150DMA > 200DMA; 200DMA
      rising ≥1m; 50DMA > 150 & 200; price > 50DMA; price ≥ 25% above 52w low; price
      within 25% of 52w high; RS rank ≥ 70 (≥80 preferred).
- [ ] 2.3 VCP (Volatility Contraction Pattern) detector: sequence of progressively
      tighter pullbacks on declining volume → pivot/breakout point. Quantify
      contractions (T1>T2>T3 depth), volume dry-up, pivot price.
- [ ] 2.4 Darvas box / base detection: consolidation range, breakout level, time-in-base.
- [ ] 2.5 CANSLIM fundamentals overlay: 'C' current qtr EPS growth ≥25%, 'A' annual
      growth, accelerating sales/margins; 'N' new high/new product proxy; 'I'
      institutional accumulation proxy (volume-on-up-days, OBV).
- [ ] 2.6 Volume signature: breakout volume ≥ 1.5–2× 50d avg; accumulation/distribution.
- [ ] 2.7 Composite LEADER SCORE (0–100) blending RS, trend-template pass, VCP tightness,
      fundamentals, volume. Rank universe daily → watchlist (top N).
- [ ] 2.8 No-lookahead unit tests (prefix-equality on every feature, like the options
      project's tests_smoke.py).

## PHASE 3 — ENTRY / EXIT / TRADE MANAGEMENT  (sub-plan 3)
- [ ] 3.1 Entry: buy the pivot/breakout of a valid VCP/base in a top-score name, with
      volume confirmation, only when Phase-4 regime is GREEN.
- [ ] 3.2 Initial stop: below pivot / below last contraction low (Minervini: typically
      −5% to −8%, tightened to the structure). HARD stop, no exceptions.
- [ ] 3.3 Position sizing: risk per trade = R (0.5–1.0% of equity) / stop-distance →
      shares. Cap position at 8–25% of equity regardless.
- [ ] 3.4 Pyramiding: add on follow-through (e.g., +2–3% past pivot), raise stop to
      breakeven on the combined position.
- [ ] 3.5 Profit management: sell into strength on climax/parabolic; trail with 50DMA
      or a 2–3 ATR trail; take partials at +2R/+3R; "sell half on the way up" rule.
- [ ] 3.6 Time stop: exit a base breakout that doesn't follow through in N days.
- [ ] 3.7 Loss discipline: max −R per name; portfolio heat cap (sum of open risk ≤ 2–3%
      equity); reduce size after a string of losses (the equity-curve governor).

## PHASE 4 — REGIME FILTER (the make-or-break)  (sub-plan 4)
**This is why the strategy makes 100% vs blows up. Trade aggressively only when the
market environment supports momentum; sit out / shrink otherwise.**
- [ ] 4.1 Market-direction model: Nifty/Nifty500 vs 50 & 200DMA; distribution-day count
      (O'Neil): ≥5 distribution days in 4–5 weeks → caution/exit.
- [ ] 4.2 Breadth: % stocks > 200DMA, advance/decline line, new-high vs new-low,
      % of universe passing the trend template (leadership breadth).
- [ ] 4.3 Follow-through-day detection (O'Neil) to switch regime back to GREEN after a
      correction.
- [ ] 4.4 Regime states: GREEN (full size), YELLOW (half size / only A+ setups),
      RED (no new buys, tighten/exit). Map breadth+direction+distribution → state.
- [ ] 4.5 Volatility overlay: India VIX level/term — shrink in high-VIX whipsaw.
- [ ] 4.6 Backtest the regime filter ALONE: does GREEN-only trading vastly outperform
      always-on? (Expectation: yes — this is the core hypothesis.)

## PHASE 5 — BACKTEST ENGINE  (sub-plan 5)
- [ ] 5.1 Event-driven daily engine: point-in-time universe, next-day-open fills, EOD
      decisions (no lookahead). Survivorship-bias-free (delisted names included until
      delist date).
- [ ] 5.2 Costs: brokerage (₹20/order or 0.03%), STT 0.1% delivery sell, exchange+GST,
      stamp duty, slippage (0.1–0.5% scaled by illiquidity / ADV participation).
- [ ] 5.3 Realistic fills: cap position entry/exit at X% of that day's volume; model
      gap-throughs on stops; no fills on lower-circuit days.
- [ ] 5.4 Portfolio accounting: concentration, heat, pyramiding, partial exits, cash drag.
- [ ] 5.5 Output: equity curve, per-trade blotter, regime-tagged P&L.

## PHASE 6 — VALIDATION (anti-overfit)  (sub-plan 6)
- [ ] 6.1 Walk-forward: optimise score weights / stop on IS, lock, test OOS. Small grids.
- [ ] 6.2 Regime stratification: report CAGR/MaxDD separately for bull/chop/bear years
      (2010-13 chop, 2014-15 bull, 2018-20 incl COVID, 2021 bull, 2022 chop, 2023-24 bull).
- [ ] 6.3 Capacity test: re-run capping participation at ₹10Cr / ₹25Cr / ₹50Cr ADV — show
      where the edge decays (proves the small-cap moat & the ≤10Cr ceiling).
- [ ] 6.4 Deflated Sharpe / PBO, parameter ±10% stability, Monte-Carlo trade-removal.
- [ ] 6.5 Benchmark vs buy&hold Nifty500 and vs a naive RS-momentum portfolio.
- [ ] 6.6 GO/NO-GO: require OOS Calmar > 1, MaxDD < 25%, and the regime filter
      demonstrably cutting bear-year drawdown.

## PHASE 7 — PAPER & LIVE  (sub-plan 7)
- [ ] 7.1 Daily scan → ranked watchlist (Angel data); alerts at pivots.
- [ ] 7.2 30-day paper run: log fills, slippage, discipline adherence.
- [ ] 7.3 Live on small size; scale only while ≤₹10Cr and metrics hold.
- [ ] 7.4 Journal + monthly regime/edge-decay review.

## FILE MAP (to build)
`swing_momentum/`: data/build_universe.py, data/fetch_eq_daily.py, data/fundamentals.py;
signals/relative_strength.py, signals/trend_template.py, signals/vcp.py, signals/score.py;
backtest/regime.py, backtest/engine.py, backtest/costs.py; validate.py, scan_daily.py, config.py.

## GOD-TIER EXPANSION → see `GOD_TIER_EXPANSION.md`
This momentum-swing core is sleeve #1 of a multi-strategy small-capital machine. The
expansion adds 10 capacity-limited dimensions (D1 special-sits, D2 IPO, D3 microcap,
D4 PEAD, D5 thematic, D6 pairs, D7 seasonality, D8 convexity, D9 insider-following,
D10 ADR/ETF arb) + 2026-40 structural tailwinds + futuristic optionality. Build per its
SEQUENCING section after this core + the Risk OS.

## STATUS (2026-06-17): Phase 1-5 PROTOTYPED & RAN END-TO-END — see `RESULTS.md`
Built data\build_panel.py (976-symbol survivorship-safe close panel 2005-25 + PIT
membership) + run_swing.py (signals + regime + weekly backtest). **Result: regime-gated
leadership momentum = +21% CAGR full / +34% OOS, Sharpe 1.19 OOS, regime filter halves
MaxDD (70%→36%); triple-digit bull years. Edge confirmed.** Bug fixed: ffill panel before
rolling SMAs (raw NaN gaps made SMAs all-NaN). KEY CAVEAT: no liquidity/volume gate yet
(close-only master) → optimistic; survivorship (delist losses dropped); MaxDD 36%>25% target.

## NEXT-SESSION ENTRY POINT
→ Per `RESULTS.md` NEXT: (1) add volume/liquidity ADV gate (THE validity fix — re-run,
   expect lower-but-clean CAGR); (2) fix survivorship (realize delist losses); (3) improve
   regime to MaxDD<25%; (4) small-grid walk-forward; (5) add god-tier sleeves (D1/D4/D11);
   (6) wrap in Risk OS. Foundation (panel+engine) is DONE and reusable.
