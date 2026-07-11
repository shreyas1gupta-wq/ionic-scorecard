# STOCKS_PROGRAM_2026 — mega R&D plan: single-stock swing / positional / intraday-event setups
**Launched 2026-07-11 (Principal order: "if not fno go in stocks... swing positional breakout mean reversion... uptrend+breakout then SL-based ORB 5/15min for few weeks... launch mega rnd plan, use sonnet to save cost").**
Governance: every experiment = pre-registered card FROZEN IN ITS OWN COMMIT before the script runs; RUN_CARD.json per run; AST scanner pre-flight; trials ledger; sonnet-tier agents for judgment/curation only (D-023 max 3); scripts do all computation. The INDEX program's DSR lesson applies from day 1: cards are rationed, the sample is not infinite.

## Data (all local, verified elsewhere)
- Stock minute 1-min 2015+ (Saintforest, 10.4GB/813M rows) — 5/15-min bars derivable; pre-open bug rule applies (>=09:15).
- Stock daily panel + Master Excel (976 tickers 2005-25) + **Delisted Excel (148 tickers)** + PIT NIFTY500 universe (42 snapshots) -> SURVIVORSHIP-CLEAN backtests are possible and MANDATORY (T-universe rule: entries only from names in the PIT snapshot at entry date).
- PIT earnings (86.2% exact dates), fundamentals, F&O stock options (dual schema).
- Execution realism: lib/execution_realism.py — circuit-locked bars = NO FILL; thin-volume slippage 2-3x (landmine #7b). Intraday cost floor from ORB_SHORTONLY post-mortem: ~15 bps/side baseline; D-031 limit-order-or-skip is the sanctioned alternative (no-fill = DROP).

## Streams (cards to be frozen individually; prior-art table below constrains them)
- **T-A BREAKOUT SWING**: daily breakout (e.g., 55d high w/ volume expansion) in stage-2 uptrend (close>200SMA, 50>200SMA) -> hold weeks w/ trailing/SL exits. Prior art: BREAKOUT_SCAN_20260710 (chartlink replication, exit grids — curator to digest verdicts before card freeze).
- **T-B MEAN REVERSION IN UPTREND**: pullback buys (RSI/zscore) ONLY in stage-2 names. Prior art: MEANREV_RSI_CAMPAIGN_20260707 verdicts constrain.
- **T-C POST-BREAKOUT ORB WINDOW (Principal's specific ask)**: universe = stocks that gave a T-A-style breakout in the last K weeks (K in {2,4} pre-declared); for that window trade 5/15-min ORB with SL intraday, long-only with the trend. Hypothesis: breakout stocks have elevated intraday trendiness -> ORB gross edge exceeds the friction floor that killed basket-ORB. MUST clear: 15bps/side cost AND the ORB_MOMENTUM50 kill precedent (differentiation = event conditioning, not ranking).
- **T-D POSITIONAL STAGE-2 TREND (investment setups)**: weekly Weinstein/Minervini stage filters + breakout adds, months-horizon; overlaps Track-2 legacy (swing_momentum PLAN) — curator to map what's already known.
- **T-E PEAD DRIFT**: post-earnings drift with PIT dates. Prior art: PEAD_EARNINGS_TRAIL_20260707 v1/v2 verdicts constrain.

## Phase 0 (this weekend): prior-art digest + data audit + card drafting (sonnet agents, 3 max)
1. CURATOR: digest every stocks-relevant results dir (BREAKOUT_SCAN, ORB_*, MEANREV_RSI, PEAD_*, SCALPING_V7 stocks, MIDSMALL_MOM, swing_momentum track) -> ALIVE/DEAD/CONSTRAINT table appended here. Nothing killed gets re-tested without a structurally new construction.
2. DATA AUDIT: stock-minute panel — coverage by year/name, 5/15-min bar sanity, circuit-day frequency, gap stats; writes a data-fitness note for T-C.
3. CARD DRAFTS: T-C first (Principal priority), then T-A; frozen bars proposed for CIO-style review, then committed pre-run per provability rule.
## Phase 1: run T-C + T-A cards (scripts). Phase 2: survivors -> Gate-4 w/ execution realism + red-team battery (the B1b template). Phase 3: paper-first.
**Sizing note (D-031/D-032):** T-A/T-D are candidate INVESTMENT-line setups (positional), T-C is TRADING-line. Capacity 10L-10cr band applies.

## PRIOR-ART TABLE (Phase 0, appended as curated)
**ORB family (Lakshmi digest 2026-07-11):** 3 killed cells span {5m,15m OR} x {0.25x,1.0x ATR SL} x {3m,2w momentum universes} x {cash short, monthly puts} — ALL converge: real +8-13 bps gross, dead vs 35-50 bps intraday RT friction; puts structurally mismatch (theta/delta capture ~0-3% of move). NO resurrection via parameter reshuffles. **BINDING CONSTRAINT on T-C: the card must change the COST REGIME — (i) multi-day hold (the stated resurrection path), and/or (ii) pre-declared gross hurdle >=40 bps/trade for any EOD-exit variant, and/or (iii) limit-order-or-skip execution (D-031). Event-conditioning (post-breakout window) is the gross-edge lever being tested, not by itself a new vehicle.**

**Full sweep (curator #2, 2026-07-11):**
| Stream | Prior art | Status | Routing decision |
|---|---|---|---|
| T-A breakout swing | BREAKOUT_SCAN_20260710 (Chartlink VCP scan, CAGR 31.8%/Sharpe 1.67 w/ skip-filters, audited) | **ALIVE, pre-freeze** | NO new card — route existing pack to red-team battery + forward paper (D-030). Duplication forbidden. |
| T-B uptrend meanrev | MEANREV_RSI_20260707 (index options, 5/6 KILL) | family fragile | T-B card allowed but: >=30 trades/param bar + directional-asymmetry check pre-declared. |
| T-C post-breakout ORB | ORB family kills (real 8-13bps gross, dead vs friction) | constraint banked | NEW card (Principal ask) — event-conditioning lever + cost-regime change mandatory. Uses BREAKOUT_SCAN event list as trigger. |
| T-D positional stage-2 | THREE parallel builds exist: BREAKOUT_SCAN, MIDSMALL_MOM Var-B (ALIVE, CAGR 22.8%/Sharpe 1.14, fwd-confirmed CY26 +13.9% vs -2.4%), Track-2 engine (+34% OOS proto, liquidity/survivorship unfixed) | **duplication risk HIGH** | NO new build — T-D = finish Track-2 Phase-1.5/1.8 fixes (liquidity gate, delisted losses) + consider Var-B extension. |
| T-E PEAD | PEAD v2 (single quarter, t=1.28, promising) | PARTIAL | T-E card = the prescribed 2015-2026 multi-year event study on v2 construction. |
**Cross-flag:** 3 independently-built momentum/breakout packs never cross-referenced — consolidation is itself a deliverable. Lakshmi filing KB + KILLED_IDEAS entries as follow-up.

### T-E-CARD SPEC (FROZEN 2026-07-11 pre-run commit) — PEAD multi-year event study (the v2 prescription)
**Construction (locked to PEAD v2 template, no new DOF):** events = quarterly PIT earnings (unified_quarterly_pit, available_date) 2015-01..2026-04; buckets: (B1) YoY net-profit growth >= 100%, (B2) loss-to-profit turnaround. Universe gate: symbol in PIT NIFTY500 snapshot covering the event date (42-snapshot file). Prices: close_all bhavcopy panel (2013+, delisted included). Entry: close of first trading day AFTER available_date (D+1 close). Exit: close < DMA50 trail (primary; DMA20 secondary reported), max hold 120 td. Costs 25 bps/side.
**Controls:** (i) regime control = same-window mean drift of ALL PIT-universe names (event-matched calendar windows); (ii) placebo = frequency-matched random events x200.
**FROZEN BARS:** PASS iff excess-over-control per trade > 0 with t >= 2.5 AND n >= 300 events AND era halves (2015-20 / 2021-26) both positive AND real > placebo 95th pct. KILL iff t < 1.5 OR era signs conflict. Else PARK. Censored (still-open at data end) trades reported separately, never counted as wins. Family trials to date: v1 (killed, wrong signal) + v2 (single quarter) + this = 3 on ledger.
Pre-run: AST scan + RUN_CARD with freeze hash. Trials +2 (B1, B2 buckets).
**T-E-CARD OUTCOME (2026-07-11, frozen @ b12264b): PARK.** 1,230 live events: excess-over-control +1.24%/trade t=2.54 (real, modest) BUT raw +3.48% fails placebo 95th (+4.70%) - the DMA50-trail structure harvests bull-market drift (placebo null mean +2.14%!); era bar UNTESTABLE (PIT exact dates start ~2019 -> "multi-year" is really 2021-26). Script's KILL print was a nan-era code artifact; card text applied -> PARK. Reopen via (a) 2015-19 earnings-date backfill (data-office intake) or (b) beta-hedged construction as NEW card. Trials +2. Evidence: results/TE_PEAD_MULTIYEAR_20260711/.

### T-B-CARD SPEC (FROZEN 2026-07-11 pre-run commit) — mean reversion in uptrend (stocks, daily)
**Construction:** universe = PIT NIFTY500 members (42 snapshots) with close_all prices (2013+, delisted incl). Stage-2 gate at signal date: close > 200DMA AND 50DMA > 200DMA. Trigger (PRIMARY): RSI(3) < 15. Secondary sub-trial: zscore(5) < -1.5. Long only. Entry: NEXT day close after signal. Exit: close > 5DMA or 10-td cap. Costs 25 bps/side.
**Controls (T-E lesson institutionalized):** placebo x200 = random stock-days passed through the SAME stage-2 gate population and SAME exit engine — any trail/cap exit harvests drift, so the placebo shares the exit; regime control secondary.
**FROZEN BARS:** PASS iff real mean net > placebo 95th AND t >= 2.5 AND n >= 300 AND eras (2015-20 / 2021-26) both positive. KILL iff t < 1.5 OR era signs conflict (both eras testable here - no nan escape). Else PARK. Curator constraint honored: >=30 trades per parameter cell or the cell is INSUFFICIENT.
Pre-run: AST scan + RUN_CARD with freeze hash. Trials +2 (RSI3, zscore5).
