PURE_OPTIONS_BOOK_20260803 -- Aakash Jain, PROGRESS checkpoint (survives connection drops)
STATUS: COMPLETE. Script build_pure_options_book.py ran clean (exit 0), all checkpoints on disk,
run_log.txt has full trace. Final synthesis returned to coordinator in chat. SPAN-reality bug
(S1_F wrongly gross-leveraged) was caught and fixed before being quoted -- see script section 7b.


GOAL: pure-options (no futures) multi-sleeve book, forward-STT-costed, vs BALANCED comparator.

STATUS AT LAST CHECKPOINT: analysis essentially complete, writing final synthesis to chat (not to
a report .md file per this agent's own harness rule -- OPTIONS_BOOK_WRITEUP.md name was suggested
by the coordinator but the harness instruction to return findings directly overrides it).

KEY UPDATED FACTS (received mid-task from coordinator, VERIFIED on disk, use these not older ones):
- BALANCED comparator (PORTFOLIOS_REFIT_20260803/PORTFOLIOS_REFIT_WRITEUP.md, both bugs fixed):
  CAGR 5.14%, MaxDD -3.66%, Calmar 1.405, Sharpe 1.38 (FITTED: SWEEP1.9/CAL35/OV15/LD20/BOOK22.7)
- Honest max across all mandates: HIGH_CAGR loosened-cap variant, CAGR 19.49%, MaxDD -24.77%,
  Calmar 0.787 -- capacity confirmed non-binding (SWEEP 0.0139% of ADV at HIGH_CAGR size).
- SELL_PLUS_TAIL final: bare-10%-margin core MaxDD -69.82%, COVID -33.30%; min compliant k=3.2-4;
  same k with/without hedge (hedge fixes COVID, dd relocates to 2022 whipsaws); unhedged dominates
  CAGR at compliant k; no hedge cell net-hedge-positive in cash (60/60).

SCRIPT: build_pure_options_book.py (this folder) -- WRITTEN TO DISK (not just scratchpad).
Data sources (all pre-existing, reused not rebuilt): FINAL_RANKING_20260730/all_sleeves_daily.json,
STACKED_BOOK_20260711/book_daily_pnl.csv (s1f col), RATIO_CALENDAR_20260730/grid_a+grid_b_trades_raw.csv,
LONGDATED_SELLING_20260730/best_config_trades.csv, S1F_SPEC.md (margin convention), THREE_PORTFOLIOS
PORTFOLIOS.md (SWEEP crash-window table).

FINDINGS LOCKED IN (from completed run, checkpoints/*.csv on disk):
1. Sleeve-sleeve corr (common window 2022-2025, monthly): all pairs |r|<0.21 -- LOOKS diversified.
   Quarterly corr much higher (S1_F-ROLLED_RATIO_CAL 0.497, LD_SELL-CALENDAR 0.447) -- monthly noise
   masks a slower-moving shared factor. Verdict: moderate shared variance-factor signal, confirmed
   structurally (all 4 core sleeves are short gamma/vega on the same NIFTY index) even though the
   firm's own crash sample is too thin (2-7 obs) to prove it statistically at daily/monthly res.
2. ROLLED_RATIO_CAL tested and EXCLUDED from core book: standalone maxDD -12.41% (vs CALENDAR's
   -1.66%) cuts max-compliant-gross from ~19.75x to ~6.75x for materially thinner Sharpe gain --
   correlation to CALENDAR (0.12mo/0.31q) was NOT the reason (within Principal's 0.2-0.4 band); its
   OWN crash-era tail was.
3. SPAN-REALITY BUG CAUGHT AND FIXED: S1_F's bare margin/native-unit is ~81% (spec: lots=floor(0.75x
   equity/margin)) vs LD_SELL/CALENDAR/OVERSHOOT's ~9-16% -- S1_F is NOT capital-light and must NOT
   be scaled by the same "gross" leverage multiplier as the other three (naive first pass wrongly
   implied Rs1.46cr of S1_F margin alone inside a Rs1cr book at gross=6 -- caught before shipping).
   FIX: S1_F gets a FIXED weight (no extra leverage); gross multiplier applies ONLY to the
   light-pool {LD_SELL, CALENDAR, OVERSHOOT}.
4. NEXT STEP (if resuming): re-run gross scan with the SPAN-fixed two-tier construction (S1_F fixed
   weight ~0.20-0.25, light pool gets remaining capital + gross scan), recompute Lens A/B (fix the
   double-division-by-NATURAL_CAP bug already spotted), recompute Lens C pessimistic bound with
   corrected S1_F scale, and do the final BALANCED comparison against the NEW 1.405 Calmar / 1.38
   Sharpe bar (much harder to beat than the earlier 1.034/1.10 vintage).
5. Whole-book tail (RISK_LIMITS "vol-spike-correlation, all sleeves' worst month simultaneously" +
   COVID window + pessimistic 1d/5d/20d bound) all computed in the script; numbers to be finalized
   post SPAN-fix re-run.

OUTPUT PATHS: this folder's checkpoints/*.csv + standalone_metrics.json (sleeve stats), run_log.txt
(full execution trace). Final answer returned directly in chat per harness rule, not as a .md file.
