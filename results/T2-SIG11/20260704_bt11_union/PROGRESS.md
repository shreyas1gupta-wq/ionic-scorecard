# BT-11 UNION RE-RUN — progress checkpoint (resumable)

Owner: Devika (E-016). Run dir: results/T2-SIG11/20260704_bt11_union/
Purpose: quantify survivorship bias in BT-11 by re-running on the PIT UNION RETURN panel.

## Panel version (FROZEN in my run dir; do NOT re-read the live dir)
- Source: datasets/derived/pit_union_panel_v1/close_panel_return.parquet
- Version tag: **v1** (base build 2026-07-04T20:53:55 UTC; Manoj's v1.1 alias/ipo-age passes
  were IN PROGRESS in the live dir at snapshot time — my close_panel_return.parquet is the
  20:52 base = v1). md5 of my copy = 9f5b5d42159ff810e8d554bbab35499c
- Schema: LONG [date, symbol, close, source, spliced]. **CLOSE-ONLY** (no open/high/low/volume/oi).
- 6,878,226 rows, 2,556 symbols, 2000-01-03 -> 2026-01-22. dup(sym,date)=0.
- Basis: RETURN (dividend-adjusted / total-return). Deviation from CURRENT_STATE note that
  "PRICE basis is right for P&L backtests" — brief explicitly directs the RETURN panel; TR basis
  is the correct holding-period-return basis for a long-only equity momentum book. STATED LOUDLY.

## KEY ADAPTATIONS (deviations from original bt11, all stated loudly in config/VERDICT)
1. ENTRY/EXIT FILL: union panel is close-only -> entries & exits at NEXT-DAY **CLOSE**
   (original used next-day OPEN). Same slippage stack. Conservative, ~1-day later, stated.
2. VOLUME/breakout_vol_flag: union has no volume. Splice HF volume where the (sym,date) exists;
   union-only names -> volume=NaN -> breakout_vol_flag=False. breakout is only a +5 composite
   NUDGE, never a hard gate, so this cannot fabricate ALL_PASS.
3. LIQUIDITY/ADV gate: original bt11 selection did NOT apply an ADV gate (only ALL_PASS +
   price_floor). We match that (signal-only). Separately REPORT volume-coverage of chosen names
   (with-vol vs union-only) as the "liquidity gate" both-ways read.
4. PIT match: apply symbol_aliases.csv (old->new) so PIT tickers (HEROHONDA...) resolve to the
   union's current tickers. PIT snapshots are Mar/Sep (data11 already anchors month-start).
5. START extended to 2014-01 (union 2014 coverage 95.5% N200 / 93.6% per brief). 2014-2015 are
   NEW (no old-HF comparison). Old comparison window stays 2016-2026.

## STATUS — COMPLETE 2026-07-04
- [x] Snapshot 3 files into run dir
- [x] Read engine + deps + old metrics/shuffle baseline + coverage
- [x] Write data11_union.py (union loader) + bt11_union.py (adapted engine)
- [x] D-028 lookahead audit: PASS (0 FAIL, 15 WARN dispositioned) -> LOOKAHEAD_AUDIT.md
- [x] Run base (N10/N20 x 1x/2x), 2014-2026 (102s) -> metrics.json
- [x] Shuffle (50 draws, 1x, size-matched) -> shuffle_percentile.json
- [x] Delta table vs old-HF -> delta_per_year.csv, delta_summary.json; VERDICT.md

## HEADLINE
Survivorship inflated CAGR ~4 pp/yr, like-for-like 2016-start (N10 10.79->6.80; N20 12.64->8.49).
Bias is ~entirely 2016 (-23pp, thinnest HF coverage year); post-2018 within +/-5pp (caveat confirmed).
Shuffle percentile 98/100 -> 86/88 (still beats null; null bar rose because union pool has losers).
Fails 2x cost on the honest panel too (binding constraint for paper, not the survivorship haircut).
