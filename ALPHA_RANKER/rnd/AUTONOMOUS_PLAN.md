# ALPHA_RANKER — Overnight Autonomous Research Plan (Principal asleep ~9h)

GOAL: keep researching/iterating/improving the repeatable -100..+100 scores for 1M/1Y/5Y (regime-aware,
NON-fixed weights), extracting durable alpha — WITHOUT descending into infinite senseless failure-combos.
Deep PER-STOCK analysis is NOT now (Principal: after full framework, in 1-2 days). Save continuously.

## HONEST CONSTRAINTS (read first)
- No true 9h continuous solo run: progress advances via completing agents/scripts + an hourly cron tick. A hard usage-limit PAUSES everything until Principal reopens — cron is session-only, cannot resurrect. If limit hits, Principal should reopen; RND_PROGRESS + CONSOLIDATION resume cleanly.
- No social-platform alpha scraping (X/Reddit/Quora/TradingView are auth/anti-bot/noise). We WebSearch PUBLISHED strategies/indicators/investor frameworks and TEST them on the harness. No fabricated "sentiment alpha".
- API currently overloaded (529s) → run waves of ~8-10 that COMPLETE, not 25 at once; hourly cron sustains throughput.
- Money-first: hard gates ONLY = lookahead(lag) + placebo. PBO/DSR advisory (both miscalibrated on our sample — see CONSOLIDATION §harness fixes).

## STOP CONDITIONS (anti-infinite-loop — enforce every wave)
1. Per hypothesis: 1 test + at most 1 refinement child. Child fails → PARK/KILL, do not spawn more.
2. Per wave: if 0 new lag/placebo-clean IC_IR>0.3 survivors → STOP broadening; switch to refining/confirming existing survivors on the 21yr panel.
3. Data-blocked → PARK immediately with a note (never retry-loop a missing source).
4. Respect budget; checkpoint every card; a wave that only reproduces known results = signal to change tack, not repeat.

## ALPHA SOURCES (backtestable only; rotate across waves)
Internal: FRAMEWORK_CATALOG, KILLED_IDEAS, backlog_scout, existing 259+ cards.
Published/WebSearch: factor lit (AQR, Fama-French, Novy-Marx, Frazzini-Pedersen BAB, Cooper-Gulen-Schill), investor frameworks (Buffett/Munger quality, Lynch GARP, Greenblatt, O'Neil CANSLIM, Minervini/Weinstein stage, Dalio regime/risk-parity, Marcellus/Indian PMS), technical (breakout/VCP/cup-handle/swing/RS), market indicators (breadth A/D, India-VIX-equiv, put-call), macro/regime.
Data on disk: prices(5y+21yr), fundamentals PIT(FY02-26), sector_map, factor NAVs, options(index-only), delivery(stale 2024), shareholding(stale 2023).
NOT usable now: single-stock options (thin), social platforms (noise), FRED US-macro (proxy-blocked → stooq/home-network).

## PHASES (aspirational; best-effort under limits)
- Wave A (now, ~hour 0-1): regime continuous-overlay, DCF, macro(stooq+flag FRED), alpha-source websearch, valuation refine, microcap relative-cap-tiers, prioritizer/monitor. + market-state (running).
- ~Hour 1.5: MODEL CHECK — consolidate survivors, DSR-per-family fix + rescore, red-team top picks, update CONSOLIDATION.
- Hours 1-5: iterate/refine confirmed factors; re-confirm everything on 21yr panel across bears; build the regime-aware non-fixed weight model; ~20-throughput.
- Hours 5-6: finalize framework spec + IC-memo candidate set.
- Hours 6-8: second pass on REJECTED sources (resurrect killed ideas under new method/data).
- Every ~1h: cron monitor tick — check tasks, dispatch next wave from backlog by priority, guard stop-conditions, checkpoint.

## DATA-TRUST & MANIPULATION-ERA (Principal directive — all agents honor)
- **Accuracy decays with age.** Recent ~5yr fundamentals + peer-reviewed research = high trust. Pre-2015 fundamentals = LOWER trust (thin + error-prone). Rule: DOWN-WEIGHT (never delete) old data; widen error bars on pre-2015-driven backtests; prefer conclusions CONFIRMED in the recent 5-10yr; explicitly FLAG any "survivor" whose edge concentrates pre-2015 as low-confidence.
- **Manipulation rose 2010→2020→2025.** Be skeptical of: small/micro-cap-only edges (esp. 2010-2020 low-float pumps), round-number technicals (50DMA — already shown non-special), and thin-volume signals. Prefer edges robust in LARGE/MID caps AND the recent era. Forensic layer + technical factors should be era/cap-aware. A signal that only worked in old small-caps is suspect, not gold.

## DEEP PER-STOCK ANALYST PHASE (AFTER the final model — ~6-8h from now, NOT before)
Once the final regime-aware model is built & IC-memo-ready: run deep 10yr-analyst-grade research on NIFTY-750 names, **25 at a time**, each covering business/fundamentals/technicals/concall/forensic + everything researched. Concall transcripts (task below) feed this. This is the LAST phase; do not start per-stock deep-dives until the model is frozen.

## DELIVERABLE
Repeatable, regime-conditional (non-fixed) -100..+100 per horizon = rank-average of confirmed durable factors,
weights switching by causal regime; calibration to probability + per-stock deep analysis deferred (Principal order).
All in rnd/CONSOLIDATION.md (living), scoreboard.csv, cards/.
