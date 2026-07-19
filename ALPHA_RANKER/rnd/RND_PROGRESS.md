# ALPHA_RANKER R&D LOOP — PROGRESS (resume from here)

## >>> FINAL BURST CLOSEOUT (2026-07-17, Arjun Rao) — AUTONOMOUS LOOP STOPPED. AWAITING PRINCIPAL.
Two bounded tasks closed, then the research loop stops (per instruction, no lookahead/fabrication):
1. **Forward-test tracker BUILT + today's scores BANKED.** `rnd/lib/forward_test_tracker.py` content-hashes
   `composite_final.py` (sha256 `9fbfe8d4f6...`, NOT a git commit) and freezes the exact 7-leg spec
   (legs, min_legs=5, equal-weight rank-avg, decile, corp-action guard, score map) into
   `rnd/forward_test/FROZEN_SPEC.md` + `freeze_manifest.json`. Scored the current universe as of the
   latest available panel date (**2025-12-05** — a ~7-month fundamentals-PIT lag vs the 2026-07-17
   freeze date, disclosed, not hidden) → `rnd/forward_test/scores_asof_20251205.parquet`: **976 names
   carry at least one leg, 802 clear min_legs=5 and are scored as the true composite** (symbol, score
   -100..+100, decile, 7 per-leg subscores). Universe cross-ref: `universe_snapshot_asof_20251205.csv`.
   Index of all freezes: `BANKED_SCORES_INDEX.json`. **PRE-REGISTERED protocol in FROZEN_SPEC.md:
   evaluate ONCE at the Principal's chosen horizon, do not peek/grade early, success bar pre-set to
   the ~0.11-class DECAYED 2020-25 realized IC (NOT the in-sample 1.35-1.76 IC_IR figures). The
   tracker contains no grading logic and never self-grades** — grading is a separate, later, one-time
   pass the Principal or a future session runs.
2. **`bs_asset_growth` lag-test gap CLOSED.** It was flagged in LOOKAHEAD_T1T10.md as never
   independently lag-tested at 1Y (only present in the composite-level aggregate + a leave-one-out
   row with no lag field). Ran it standalone through the identical harness/panel/basis as the other 6
   TRUE7 legs (`rnd/lib/standalone_lag_bs_asset_growth.py` → `rnd/cards/STANDALONE_bs_asset_growth_1Y.json`,
   +1 disclosed trial, family STANDALONE_LAGCHECK): **ic_mean 0.0353, ic_lag_mean 0.0348,
   lag_test_delta 0.0132 — PASS (well under the 0.25 threshold).** Addendum appended to
   `rnd/reports/LOOKAHEAD_T1T10.md`. All 7 TRUE7 legs now have an independent 1Y lag_test on record.
3. **Autonomous R&D loop STOPPED.** No new factor tests, sweeps, or broadening dispatched — per the
   binding verdict below, more in-sample compute cannot change the DSR/PBO multiple-testing kill.
   **Disclosed limitation: this subagent has no tool access to the session-level cron/schedule
   registry (`CronList`/`schedule`/`loop`).** The hourly-tick and Fable crons referenced earlier in
   this log were session-bound (per their own prior entries) and this session has already restarted
   at least once since they were armed, so they may already be inert; if either is still live, the
   orchestrating session or the Principal must delete it directly — this file records the STOP
   decision but cannot itself deprovision a scheduled job it has no handle to.
4. **Nothing else changes.** The binding Gate-3 verdict stands untouched: DSR~0, PBO 0.92-0.98 across
   both universes, per FINAL_MODEL.md S5-RISKOFFICE. Both closeout tasks are leak-check/tracker
   closures, not re-certifications. Awaiting Principal for: forward-test horizon decision, calibration,
   IC memo, data refreshes, deep per-stock phase.

## >>> RESEARCH CONVERGED (2026-07-17) — STOP BROADENING. Model = PARK pending FORWARD-TEST (the one gate compute can't close).
FINAL HONEST STATE: canonical 7-leg composite is real/robust/leak-free/survivorship-free, IC_IR 1.76 (PIT, survivorship-free) / 1.345 (biased) — survivorship was NOT the inflation (it sharpened via lower ic_std). T5 survivorship CLOSED. BINDING blocker = 456-trial MULTIPLE-TESTING: DSR~0, PBO 0.92 even survivorship-free → in-sample deflation CANNOT certify. ONLY remedy = fresh forward/held-out test of the FROZEN composite (calendar time + Principal design decision). Backlog EXHAUSTED. Nothing left that more agents can compute changes this verdict.
### TICK DIRECTIVE (next ticks): do NOT dispatch new factor tests / broadening / re-runs (senseless-loop). Permitted only: (a) monitor + checkpoint, (b) build a forward-test TRACKER (freeze composite spec, record today's scores for grading later) IF not already built, (c) light packaging. Otherwise idle. Awaiting Principal for: forward-test design, calibration, IC memo, data refreshes (promoter-drift resurrection), deep per-stock phase.
## VALIDATION WAVE COMPLETE (honest status): model is FRAGILE-BUT-REAL, robust-to-perturbation, NOT yet Gate-4 certifiable.
- PERFORMANCE (authoritative, FINAL_BACKTEST.md): honest edge = market-neutral LONG-SHORT ~12% CAGR / Sharpe ~0.8 / maxDD -38%. Long-only 29-34% is a small/mid SIZE-TILT artifact vs cap-wt NIFTY500 — NOT alpha, don't quote. Breadth+VIX exposure scalar cuts long-book DD -37%→-26%. Costs not the swing factor.
- CONCENTRATION: clean — edge BROAD (19/20 sectors), survives sector-neutral(85%)/size-neutral(107%) → genuine selection, not a sector/size bet.
- AUDIT (PREIC_AUDIT.md): ROBUST to perturbation (no knife-edge). BUT: (a) headline number came from a STALE 4-leg card — true 7-leg PLAIN build is ~1.25-1.36 IC_IR (better) but needs ONE canonical build; (b) IC DECAY 0.19→0.11 across 2015-20→2020-25 eras; (c) portfolio history really ~2012-2025 (fundamentals cliff), factor-IC ~2015-2025 comparable eras — NOT 21yr; 2008/2011 unavailable at portfolio level.
- WAVE-3: event-time PEAD DEAD (absent in India both grains); regime-gated quality REVIVES (size-don't-blend confirmed).
## OPEN GATES before IC memo / production (the certification path):
1. Fix ONE canonical 7-leg PLAIN composite build; re-source all numbers from it.
2. Run formal T1-T10 `lib/lookahead_audit.py` battery (NEVER run on ALPHA_RANKER — D-028 gap).
3. DSR/PBO proper fix = purgedcv, risk-office (Sameer) sign-off (not quant-desk advisory fiat).
4. Disclose IC decay; frame as ~2012/2015-2025 result, not 21yr.
5. Calibration (score→p_up/E[ret]) — deferred per Principal. Then IC memo (CIO+FM).
## TICK LOG (post-FINAL_MODEL): deduped crons (was 4 → now 1 hourly :17 + 1 Fable; deleted stale fc80eeb4/ab540248). 405 cards. Fable oversight = ON-TRACK (validate/converge mode, no drift). Dispatched 4 tick workers: incremental-leave-one-out value of survivors, sector children (W2SEC-C1/C2/C3), FII/promoter-flow drift, cleanup-remaining-untested. Fixed magnitude inconsistency (FINAL_MODEL §5b: 21yr-corrected = authoritative, ~low-single-digit %/yr; SURVIVORS bull-panel +11-19% SUPERSEDED).
## NEXT VALIDATION TASKS (for next tick — NOT new factor families; STOP: MA sweeps, overlay variants, 1M, per-stock):
1. 21yr net-of-cost EQUITY CURVE of the final 1Y composite through 2008/2011/2020 (pin the real net figure).
2. PER-SECTOR IC of the composite (confirm not a concealed sector bet).
3. Pre-register the p_bear regime-SIZING rule (continuous, floored-at-0) + apply breadth+VIX exposure scalars to the equity curve.
4. Wave-3 REJECTED-SOURCES pass, capped ~6 (event-time PEAD, quality-in-bear gate) — per AUTONOMOUS_PLAN, due now.
5. Then pre-IC packaging: run `sensitivity` + `lookahead-audit` firm skills on the composite; draft IC-memo candidate set. Calibration (score→p_up/E[ret]) stays deferred per Principal.
## FINAL MODEL WRITTEN: rnd/FINAL_MODEL.md — orthogonality-pruned (~7 independent legs, value block collapsed to EY, BAB absorbed by QMJ); 1Y composite IC_IR 0.91/mono 0.976/lag-clean; regime = SIZING not blending (breadth+VIX exposure scalars, blend-overlay rejected); modest honest magnitudes; gates = calibration+IC-memo before production. Wave-B (8 agents) + capstone COMPLETE. Crons continue backlog + wave-3 rejected-sources pass.
## RESTART LOG: session restarted (prev process exited). Crons are SESSION-ONLY → re-armed both (hourly tick :17, Fable :43). Transcripts: 1972 dirs downloaded + _coverage.csv (largely done pre-restart). 331 cards. Resumed grind = Wave-B: 8 agents dispatched on top overlay-rank-band fix + 24 of the 51 queued ideas (issuance/asset-growth/accruals, profitability/QMJ, low-risk BAB/idio-vol/MAX, momentum-quality frog-in-pan, India deleveraging/under-owned/CFO-PAT/ROCE-longevity, breadth overlays, seasonality/composites). Confirmed durable core unchanged: EY+DCF value backbone, sector-rel momentum + MA-65 (regime-gated), regime overlay (needs rank-band to beat static net-of-cost). ON RESTART: re-arm crons, resume from CONSOLIDATION.md + SURVIVORS.md.
## STATUS: WAVE-2 LIVE (money-first). Wave-1 (10 workers) produced 96 cards. PBO demoted to ADVISORY (Principal: don't be so strict we never find money-makers). Money-first scoreboard built: `rnd/pragmatic_score.py` -> `rnd/scoreboard.csv`.

## MONEY-FIRST CALIBRATION (Principal directive)
Hard gates = ONLY lookahead(lag_test_delta>0.25) + placebo(|ic|>0.02). Rank by net-of-cost LS return, IC_IR, monotonicity, hit-rate; PBO/DSR are advisory flags (structurally ~1 on our 36-month sample — not kills). Verdict_v2 in scoreboard.csv.

## WAVE-1 WINNERS (1Y, residual, lag+placebo clean) — needs 21yr confirmation
- **65-DMA THESIS CONFIRMED**: H001 stack65 IC_IR 0.947 > stack50 0.912; slope65 0.717>slope50 0.669; dist65>dist55. 65 beats 50 on dist/slope/stack.
- H002 MA plateau: dist/slope robust across lengths (NOT one lucky number).
- H004 vol-scaled momentum 12m: IC_IR 0.79, mono 0.98, hit 75% (top practical).
- H003 resid momentum 0.72; H005 residual>raw (0.72 vs 0.58 — momentum not pure closet-beta); H009 stage-2 (best LS, selective gate).
- Low-vol INVERTED in this bull sample (regime-dependent). Value/quality/growth cards still landing.
CAVEAT: bull/smallcap-heavy 5yr sample; net-LS = decile spread not portfolio return. Ranking trustworthy; magnitude+durability need panel_long.

## WAVE-2 (15 agents, staggered as wave-1 frees slots) — money-first
Live: SCOUT (backtestable money-makers -> SCOUT_OPPORTUNITIES.md + backlog_scout.json), 21yr-validator (confirm winners on panel_long across bears), composite-builder (winners -> improved model), 65DMA-deepdive (+crowding proxy), vol-mom-refine (cut turnover). QUEUED (release as slots free): event/PEAD, options-flow(PCR/OI/IV), seasonality/expiry, RS sector-rotation, corp-events(bulk/index), delivery-flow, value money-first, quality-momentum, microcap-specific, prioritizer/wave-3.

## WAVE-1 COMPLETE — verdict map (money-first, this 2021-26 bull sample; needs 21yr confirm)
WINNERS (lag+placebo clean, strong money-first): 
- Trend: **65DMA STACK** (close>MA65>MA150>MA200) IC_IR 0.95 @1Y — stack beats dist/slope by 20-30 IC_IR pts; 65>50 confirmed but crowding-reason NOT supported (generic longer-MA effect, plateau 55-75). NO tradeable MA signal @1M.
- Momentum: **vol-scaled 12m + rankband_b10** IC_IR 0.80, turnover 0.167 (refined, deployable); residual 12-1 (0.72); momentum ~87.5% real alpha not closet-beta (H032).
- Value: **earnings yield** IC_IR 1.52 @1Y (star). FCF-yield borderline.
- 52w-high: strong in HIGH-VOL only.
REGIME-CONDITIONAL GOLD (Principal's thesis, confirmed): 
- Quality (ROIC/gross-prof) STRONGLY negative in this junk-bull (mono -0.8/-0.9) → classic (+) expected in bears (21yr will test). Piotroski/accruals correct-sign, PBO-only kills.
- Low-vol/idio-vol/low-beta: negative pooled, POSITIVE in bear & high-vol.
- Momentum/trend: crash in bear (IC -0.09..-0.17). → regime-SWITCH (momentum in bull/calm, defensive in bear/hi-vol) = the model.
TRAPS/DEAD (this sample): raw growth CAGR NEGATIVE (growth-trap, needs quality/val gate); forced interactions (QARP/GARP/qual×mom) destroy strong single legs — use SIMPLE RANK-AVERAGE (H050: ML/ridge overfits); short-term mean-reversion (K confirmed); size (smallcap-rally); PEAD (monthly too coarse — redesign for event-time).
COMBINATION RULE: simple rank-average of strong orthogonal factors; do NOT force interactions or learn weights (overfit).
HARNESS ISSUES to fix (advisory, non-blocking): PBO/CSCV structurally ~1 on 36-53 monthly obs (demoted to advisory — Principal directive); verdict() uses UNSIGNED IC_IR (auto-kills neg-sign factors); DSR uses global trial count (~0 for all); 1Y net-return annualized x12 (magnitudes inflated, ranking OK); lag-test full-period shift mismatched for event-window factors.

## WAVE-2 (money-first) IN FLIGHT: composite-builder, regime-switch model, sector-map+analytics, options-flow, 21yr-validator. Scout DONE (25 ideas, backlog_scout.json W2S-01..15 for wave-3). vol-mom-refine DONE (rankband_b10). 65DMA-deepdive DONE (stack@65).
## WAVE-3 QUEUE (backlog_scout.json + redesigns): FII/DII & promoter-buying drift, max-pain/expiry seasonality, sector relative-PE rotation, event-time PEAD (daily), quality-in-bear gate, regime-switched composite tuning.

## DEFERRED (after fundamental workers stop reading consolidated/ — now DONE, all wave-1 fundamental workers finished): re-run consolidate_screener (2180 JSONs) + build_master -> fresh FY24-26 for ~2079 co. SAFE TO RUN NOW.

## FOUNDATION (built + validated this session)
- `rnd/RESEARCH_PROTOCOL.md` — anti-overfit spine (pre-registration, train/val/OOS-once, purge+embargo WF, market+FF6 neutralization → residual returns, DSR + FDR honest-trials, lag-test, placebo, replace-don't-add, red-team gate).
- `rnd/backlog.json` — 50 pre-registered hypotheses, prioritized, all themes (65DMA-vs-50DMA H001, momentum, low-vol, value, quality, growth, O'Neil/Minervini, interactions, neutralization diagnostics, regime, ensemble).
- `rnd/FRAMEWORK_CATALOG.md` (librarian) — 67 factor defs + 17 anti-overfit lessons + KILLED ideas (RSI/z-score meanrev, ADX/ATR entries, K-015 regime overlay, K-014 semiannual) the loop must not re-walk.
- `rnd/panel/panel.parquet` — PIT labeled panel, 40,201 rows (751×61 month-ends, 2021-07→2026-07). Labels fwd_ret_{1M,1Y,5Y}_{raw,excess,resid}; beta_252, FF6 betas, vol term-structure, regime, sector, mktcap. NO-LOOKAHEAD verified. CAVEAT: 1M cover 96%, 1Y 76%, **5Y 0%** (only 5y history) → 5Y needs panel_long.
- `rnd/panel/panel_long.parquet` — IN FLIGHT (21yr Nifty500_Master price panel → real 1Y/5Y forward returns, less survivorship).
- `rnd/lib/harness.py` — shared gate. VALIDATED: +control (injected) IC 0.29/mono 0.98; −control (noise) correctly KILLed; demo 12-1 momentum lag/placebo clean. CAVEAT: PBO/CSCV is a single-factor adaptation, may be over-harsh (12-1 mom got PBO 0.97) — REVIEW calibration once cards accumulate before trusting KILLs.
- `rnd/panel/cube_close|volume|bench.parquet` — shared price cube (1238×751) so workers don't reload 751 parquets.

## WAVE-1 WORKERS (10, each writes rnd/cards/<Hxxx>.json + rnd/lib/builders_<bucket>.py)
ma · mom · oneil · vol · value · quality · growth · interact · neutral · regime. Horizons 1M & 1Y (5Y deferred to panel_long). trials_counter.json tracks honest trials (may race under concurrency — reconcile).

## NEXT (the intelligent loop continues)
> 1. Collect wave-1 cards → build `rnd/scoreboard.csv` (id, horizon, IC_IR, DSR, PBO, verdict).
> 2. RED-TEAM/overfit review of PBO calibration + any PROMOTE-grade survivors (placebo/lag re-check).
> 3. PRIORITIZER pass: read cards+KILLED+CATALOG → spawn CHILD hypotheses of winners (interactions, refinements, plateau neighbours), prune dead branches, append to backlog → WAVE-2 (10 workers). Repeat to budget.
> 4. When panel_long lands: re-run 1Y + all 5Y hypotheses on it.
> 5. Only OOS-surviving + red-team-passed factors → weight-book update via IC memo (never on in-sample shine).

## ALSO IN FLIGHT
- 1,606-symbol screener scrape (master-file freshness) — 6 procs, background.
- panel_long builder.
