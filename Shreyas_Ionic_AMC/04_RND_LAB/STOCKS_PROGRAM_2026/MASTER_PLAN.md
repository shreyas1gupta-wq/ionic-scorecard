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
**T-B-CARD OUTCOME (2026-07-11, frozen @ e4de961): KILL both cells.** rsi3 -0.15%/tr (t=-4.8, n=21,343), z5 -0.19% (t=-7.2, n=30,156); both eras negative; placebo itself -0.43% (short-hold exits are cost-dominated at 50bps RT). Honest residual: signals beat placebo by ~+0.28% -> relative reversion timing EXISTS but never covers standalone costs. RESURRECTION: only as a zero-marginal-cost ENTRY-TIMING overlay on positions already being taken (T-A entries / investment line adds) - new card required. Evidence: results/TB_MEANREV_UPTREND_20260711/. Trials +2.

### T-C-CARD SPEC (FROZEN 2026-07-11 pre-run commit) — post-breakout ORB window (Principal priority)
**Events:** signal_triggers_pit.csv from the audited BREAKOUT_SCAN (PIT chartlink triggers). Window = E+1..E+10 trading days (K=10 primary; K=20 secondary reported). Sample = events intersecting minute-panel span (2022-01..2026-01-21, UTC->IST per landmine #1).
**Intraday engine (per stock-day in window):** OR = 09:15-09:30 (15-min) from 1-min bars; LONG only (with-trend) on first 1-min close > OR-high after 09:30; SL = OR-low on 1-min close, fill next close (2x cost on stop). Two PRE-DECLARED variants:
- **V1-EOD (Principal literal ask):** exit 15:25 same day. Bars: net > 0 AND gross >= 40 bps/trade (killed-cell hurdle) AND t >= 2.5.
- **V2-HOLD (cost-regime changer, the killed-ORB resurrection path):** hold overnight; trail = max(OR-low, prior day low); exit on daily close < trail or window end. Bars: net > 0 AND t >= 2.5 AND PF >= 1.3 AND beat placebo95.
**Placebo (institutionalized):** same ORB engine on 200x frequency-matched random NON-breakout stage-2 stock-days.
**Costs:** 15 bps/side (30 on SL fills). Era split (2022-10..2024-06 / 2024-07..2026-01) reported; conflict -> KILL that variant. n < 150 triggered trades in a variant = INSUFFICIENT.
Pre-run: AST scan + RUN_CARD with freeze hash. Trials +2 (V1, V2).
**T-C-CARD OUTCOME (2026-07-11, frozen @ 4692e17): KILL both variants — the decisive one.** V1-EOD: GROSS -11.1 bps (negative BEFORE costs; not a friction story), net -45.2, t=-16.3, n=6,646 — post-breakout stocks FADE intraday ORB triggers, not continue them. V2-HOLD: +8.7 bps t=0.54 PF 1.05 era-flip = noise. Placebo (-38 bps) shows ORB-EOD structurally negative on ALL stage-2 days; events merely less-bad. INTRADAY-ORB FAMILY NOW CLOSED from every construction (baskets 07-07, puts vehicle, event-conditioned today). Evidence: results/TC_POSTBREAKOUT_ORB_20260711/. Trials +2.

### TF-1-CARD SPEC (FROZEN 2026-07-11 pre-run commit) — TechnoFunda composite (Principal flagship: Minervini VCP + O'Neil CANSLIM + Weinstein stages + waves + PIT fundamentals, NIFTY500)
**Data:** Saintforest daily OHLCV 2000-2026 (landmine #1 tz fix), PIT NIFTY500 membership (42 snapshots), PIT earnings available_date. Costs 25bps/side. Entries/exits at next-day close.
**Composite (ALL point-in-time at signal date D):**
1. STAGE-2 GATE (Weinstein/Minervini trend template): close>150dMA AND close>200dMA AND 200dMA rising vs 21d ago AND 50d>150d>200d AND close>=1.3x 52w-low AND close>=0.75x 52w-high.
2. RS RANK (O'Neil): 126d return in top 30% of PIT members that day.
3. FUNDAMENTAL C/A (CANSLIM, PIT): latest quarterly NP YoY >= +20% with available_date <= D.
4. VCP (Minervini): 10d ATR%% < 0.67x its value 40d ago AND 10d avg volume < 0.8x 50d avg AND close within 5%% of 20d high.
5. BASE/WAVE: trailing-40d max drawdown within [5%%, 35%%] (built a base, not extended).
6. ENTRY TRIGGER: close breaks prior 20d high on volume >= 1.5x 50d avg.
Signal = 1 AND 2 AND 3 AND (4 OR 5) AND 6.
**Exits:** hard stop close <= entry x 0.92 (O'Neil 8%%); trend exit close < 50dMA. Portfolio: max 15 concurrent, equal weight, 60d re-entry lockout per symbol.
**Run:** 2016-01..2026-01 full; era split 2016-20 / 2021-25; placebo x200 (random stage-2-gate stocks, same exits - drift control); per-trade + portfolio NAV metrics.
**FROZEN BARS:** PASS iff portfolio net CAGR >= 15%% AND Sharpe >= 1.0 AND maxDD <= 30%% AND per-trade mean > placebo95 AND both eras profitable. KILL iff Sharpe < 0.5 OR era conflict. Else PARK (single iteration allowed only as a NEW card). Trials +1.
**TF-1-CARD OUTCOME (2026-07-11, frozen @ 47e8a00): PARK — selection alpha REAL, vehicle starves it.** Per-trade +2.10% net (t=1.88, 329 trades, win 34%) BEATS placebo95 (+1.25%, null mean +1.00%) -> the composite genuinely picks better breakouts than random stage-2. Portfolio CAGR only +5.1% / Sharpe 0.51: six ANDed layers fire ~33x/yr -> 15 slots mostly EMPTY (deployment, not philosophy, is the failure). Era untestable (PIT earnings coverage -> effectively 2021-26; same blocker as T-E; 2015-19 earnings-date backfill = shared data intake). maxDD -26.4% OK.
**TF-2 iteration sanctioned (PARK rule: one NEW card):** same signal stack, deployment fixed - 8 slots, entry tiers (full composite = full weight; stage2+RS+fund without VCP/breakout-timing = half weight), no other changes. Evidence: results/TF1_TECHNOFUNDA_20260711/. Trials +1.

### TF-2-CARD SPEC (FROZEN 2026-07-11 pre-run commit) — TF-1 deployment fix (the sanctioned iteration)
Identical signal layers and exits to TF-1 (frozen @ 47e8a00). Changes ONLY: (1) 8 slots; (2) two entry tiers - TIER-A full composite signal (weight 1/8), TIER-B = stage2 AND rs>=0.70 AND fund_ok AND base AND close>=0.97x 20d-high (no volume-breakout requirement; weight 1/16, max 4 tier-B); (3) same stops/exits.
**FROZEN BARS (same family):** PASS iff CAGR >= 15% AND Sharpe >= 1.0 AND maxDD <= 30% AND tier-A per-trade beats placebo95. KILL iff Sharpe < 0.5. Else PARK-FINAL (no third iteration; family goes to data-intake dependency). Trials +1.

### EQ-MAX-CARD SPEC (FROZEN 2026-07-11 pre-run commit) — stocks-only max-MAR book (Principal bar: 30%/-10%; stretch 40%)
**Sleeves (banked ledgers, equal starting weight):** A = breakout champion realistic-REGIME daily P&L; B = midsmall Var-B daily returns; C = TF-1 trade stream (as daily equal-weight portfolio returns from its NAV).
**Overlays (THE card - one canonical parameterization, pre-declared, NO grid):**
1. VOL-TARGETING (Barroso-Santa-Clara / Moreira-Muir): daily exposure = clip(12% / realized_20d_annvol_of_combined, 0.25, 1.5). Leverage cap 1.5x (MTF/futures-financeable).
2. REGIME HARD GATE: exposure x0.25 when Nifty 50 close < its 200DMA (indices_close panel).
**Window:** Oct-2022..Dec-2025 (intersection of sleeve ledgers; satisfies Principal 3y-window test). Costs already inside sleeve ledgers; overlay trading drag 2bps per 10% exposure change applied.
**BARS:** DELIVERED iff CAGR >= 30% AND maxDD <= 10%. STRETCH flag at >= 40%. Report exact numbers regardless - no tuning pass permitted after seeing results (single-shot card). Trials +1.
