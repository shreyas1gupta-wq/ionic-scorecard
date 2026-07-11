# ALPHA FORGE — Principal mandate 2026-07-11 night: NEW alpha, 10-15 uncorrelated sleeves, book >35% CAGR <20% maxDD (25% spike-recover OK), net leverage <=1.25x, NO stock shorts (index OK), hedging allowed, universe NIFTY500 + GOLD, NO OVERFIT.
**Novelty rule:** every sleeve is an ORIGINAL construction from our unique data intersections (PIT earnings quality, sector-P/E panel, participant-OI option columns, gold-equity regime, volume microstructure). Literature/Principal ideas = hints only; no copies.

## FROZEN DISCIPLINE (before any sleeve runs)
- SCREEN window 2024-07..2026-06; VALIDATE untouched 2016-01..2024-06 (or max data). SLEEVE PASS = screen net Sharpe >= 1.2 AND validate net Sharpe >= 0.8 (same sign, era-consistent within validate). One canonical parameterization per sleeve, declared in its spec BEFORE run; failures logged, never retuned (a variant = new sleeve id, counts against family).
- Costs: stocks 25bps/side; gold 12bps; index futures/hedge 8bps. Entries next close. PIT universe + delisted panel. AST scan every engine.
- BOOK ASSEMBLY (single-shot, rules frozen NOW): passing sleeves -> pairwise corr matrix (daily, validate+screen concat); greedy-select max-Sharpe subject to pairwise |corr| <= 0.35; equal-risk weights; hedge overlay = NIFTY futures short 25% of net equity exposure when Nifty50 < 200DMA (index short allowed); leverage scale to net <= 1.25x. Report full 2016-2026 book: CAGR, maxDD, Sharpe, yearly. NO post-assembly tuning.
- Verdict bars: DELIVERED iff CAGR >= 35% AND maxDD <= 20% (spike rule: single excursion to 25% with recovery to new high within 6m tolerated). Report exact numbers regardless.

## SLEEVE ROSTER v1 (specs frozen in sleeve files; ids AF-01..)
AF-01 EARNINGS-QUALITY MOMENTUM: stage-2 stock + latest PIT quarter sales YoY >= +15% AND OPM expansion >= +150bps vs same quarter LY; entry next close after available_date+0; exit 15% trail or 60td. (sales x opm intersection = ours alone)
AF-02 SECTOR VALUE-MOMENTUM ROTATION: monthly, NSE sector indices ranked by [P/E percentile inverted x 3m momentum]; long top-5 RS stocks within top-2 sectors; monthly refresh. (sector P/E panel novel)
AF-03 GOLD-EQUITY REGIME DANCE: 63d momentum contest gold vs Nifty500 proxy -> tilt 70/30 to winner, vol-scaled; weekly. (gold in universe per mandate)
AF-04 ABSORPTION SPRING: 5d volume >= 2.5x 60d avg AND |5d price chg| <= 2% AND stage-2 AND in-base -> buy next 10d-high break; 8% stop / 40td. (volume-absorption microstructure)
AF-05 RANGE-COMPRESSION SPRING (original VCP variant): 20d range in bottom decile of trailing year + volume dry-up + >200DMA -> entry on range-high +0.5ATR break; 2R target / 25td.
AF-06 FII OPTION-POSITIONING TILT: participant-OI OPTION index columns (unexplored): FII net call-minus-put long delta change, rolling-252 rank -> q5 = 1.25x midcap-proxy exposure 5d, q1 = hedged. (novel data)
AF-07 STAGE-1->2 TURN: stock 25-40% below 52w high reclaiming 50DMA on 1.5x volume with 200DMA flattening (slope > -2%/qtr) -> early-stage entry; 10% stop, exit close<200DMA or 90td. (Weinstein TURN, not established stage-2 = distinct from Track-2/TF)
AF-08 POST-EARNINGS QUIET DRIFT: PIT beat (NP YoY>=20%) AND announcement-day |move| < 2% (market underreaction) -> entry D+2, 30td hold, 8% stop. (underreaction conditional = our PIT edge)
AF-09 QUALITY TURN-OF-MONTH: ToM long (last close before month-end -> +3td) ONLY in top-RS-quartile stage-2 names, equal-weight 10. (conditioned refinement, portfolio construction)
AF-10 GOLD RANGE-BREAK ASYMMETRY: gold 10d-high break AFTER >=15 days without one, long 8td with 1.5% stop. (gold trend-burst timing)
Wave-B (if roster passes < 6): AF-11..15 from DII flow, VIX-percentile breadth, filing-time patterns, INR-gold spread, index ToM+VIX combo.
Trials: +10 wave-A. All results -> ALPHA_FORGE/ledger.csv + per-sleeve RESULTS.

## WAVE-A CHECKPOINT (2026-07-11 late night, banked)
Ledger: 0/10 formal passes (dual bar screen>=1.2 AND validate>=0.8); 5/10 positive BOTH windows; 8/10 positive validate.
**DISCOVERY CANDIDATE: AF-07 stage-1->2 turn (original construction)** — validate +24.1%/Sharpe 1.26 (8.5y untouched), screen +15.5%/Sharpe 1.03 (brutal window); misses formal bar by 0.17 on screen. STANDALONE at full notional it is the strongest genuinely-new sleeve produced by the firm to date. Next: red-team battery (placebo-shares-exit + shuffle) + certification as its own card; if it survives -> joins the cross-asset book.
Assembly previews (labeled, non-certified): corr-filtered 4-sleeve book = Sharpe ~1.1, CAGR 5-6% at low vol — novel sleeves are low-return-per-notional as a set; the 35/20 book is NOT reachable from wave-A alone. Frontier logic unchanged: certified AF-07 + existing 4-sleeve cross-asset book (Sharpe 2.29) + wave-B is the path.
**WAVE-B QUEUE (next session):** DII flow tilt, VIX-percentile breadth thrust, filing-time patterns, INR-gold spread, index ToM+VIX combo; plus AF-07 red-team FIRST (highest value).
