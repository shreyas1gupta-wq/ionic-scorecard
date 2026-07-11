# CURRENT STATE â€” read me first (updated every session end)
**As of: 2026-07-11, by DESK-100 â€” citation pass banked (PARTIAL, spend limit), 23 skills installed, crons re-armed; prior states below still current**

## 2026-07-11 snapshot
- **/eod flag (Sat):** earnings `forthcoming_results.csv` MISSING from datasets/earnings_pit -> Kavya: regenerate or correct EOD_ROUTINE path. 23 Angel OHLCV stragglers still queued.
- **INDEX_PROGRAM_2026**: citation pass banked â†’ `04_RND_LAB/INDEX_PROGRAM_2026/RESEARCH_CITATIONS_20260711.md` (8 confirmed/3 refuted/4 leads + 93-claim appendix) + MASTER_PLAN ADDENDUM v1.2. Key: trials-registry is a DSR PREREQUISITE; holdout-touch cap; Stream-A VRP prior +1.1-1.2 net vol pts; NEW C2 card (day-night short-vol P&L decomposition, script-only, cheapest next experiment); weeklies data honesty (NIFTY weeklies only from 2019-02-11); SL-Limit-only order engine.
- **S1-F**: first paper ticket Tue 2026-07-14, cron armed (Tue 09:12); runner still flat-margin â‚¹1.1L â€” sanity-check lots vs ~â‚¹2.7L/lot until hardened (Phase-0 #8).
- **Skills**: 78 total (+23 this session: superpowers suite, scrapling-official, find-skills, task-observer, impeccable, uipro/design suite, karpathy-guidelines). claude-mem BLOCKED (no Node.js). Weekly skill-discovery slot added Sun 19:30 (calendar + prompt spec).
- **Org monthly spend limit hit again** mid-workflow â€” agent-heavy work stays OFF until it resets; scripts-first + sequential rule in force.

## VALUATION-REGIME HEDGING STUDY delivered 2026-07-08 (Principal request)
`04_RND_LAB/results/HEDGING_ANALYSIS_20260708/` â€” NIFTY50 + S&P500, 3 CAPE/PB regimes (25-50-25), best
rollover hedge + overvalued-regime downside play, hist+MC. Deliverable=HEDGING_ANALYSIS_REPORT.docx (human),
SUMMARY.md=agent book. Data: real US Shiller CAPE+S&P500 1871-2026 (multpl) + CBOE VIX 1990- (fetched OK);
India NIFTY50/PE/PB/iVIX 2016- local. Options BS-modeled off VIX+skew (no real chains; Principal-authorized).
FINDINGS: NOW US deep-RICH (CAPE 41.8) but India CHEAP (PB 3.19) -> downside-risk is a US question today.
Best hedge=ANNUAL COLLAR (maxDD -52%->-15% @~3-4pp/yr; annual>>monthly). Best overvalued play=1x2 put
BACKSPREAD/bear put spread (convex, cheap); premium-selling ratios rejected (short the tail). COVID India
iVIX-14 entry: ATM put -37%->-1.5%. Standalone research, NOT a pipeline intake. See journal 2026-07-08.

**As of: 2026-07-07, by DESK-100 â€” CAMPAIGN OPT-SWEEP-50 closed early (org monthly API spend limit hit mid-sweep); prior state below still current**
**NEXT SESSION STARTS WITH:** (0) OPT-SWEEP-50 has 12/25 groups (23/49 setups) INCOMPLETE pending spend-limit reset â€” resume only if Principal wants the full picture, otherwise campaign closed against original mandate (bar not cleared); (0b) Kavya ticket needed: ~30-DTE monthly-contract NIFTY options coverage is broken/sparse (5 independent agents hit this); (1) re-arm cadence crons (CLAUDE.md protocol #4); (2) first /weekly-meet Mon 07-07; (3) I-016 diversifier stress-corr deliverable (binding pre-IC); (4) BT-11 v1.5 spec (entry/exit-only + two-stage stops + circuit fills); (5) D-028 retro-audit workflow resume; (6) S-04/S-05 paper first entries (~Jul-14 cycle); (7) FNO REPLAY GAME P1 build (see below â€” Principal-green-lit, P0 done); (8) FF near-month vehicle (below) -> Arjun Gate-3/4 build + Tara hedge-leg fill audit + Kavya/Arjun live-schema signal-computability check.

## FF SIGNAL NEAR-MONTH VEHICLE â€” SCOPED, not backtested (2026-07-07, Aakash)
K-012 calendar stays killed (CIO ruling 2026-07-05); signal graduated to a new liquidity-native-vehicle
intake owned by Aakash+Arjun. Scoping memo recommends a **near-month bear-call vertical** (SELL ATM CE /
BUY OTM CE, same expiry, liquidity-gated hedge strike) over a naked short call (undefined risk, rejected
on risk-shape) and over a strangle/PE variant (FF is CE-IV-only per the code â€” no validated put-side
signal; parked). Biggest open risk: hedge-leg liquidity is spot-checked only (6 names, encouraging but
not audit-grade) and rhymes with K-009's prior kill (far-OTM wings unpriceable, âˆ’883% artifact) â€” real
fill audit is Tara's next step. Memo + 8-item pre-registration spec: `04_RND_LAB/ideas/20260707_ff_signal_near_month_vehicle.md`.
IDEA_PIPELINE.md row updated (still 1-INTAKE â€” vehicle scoped). Not a Strategy Register row yet.

## CAMPAIGN OPT-SWEEP-50 (2026-07-07) â€” CLOSED EARLY, bar not cleared
Principal-commissioned hunt for a NIFTY option strategy w/ Sharpe>2 & XIRR>50% post-cost (SP500 leg dropped,
no data). 13/25 Phase-1 groups (26/49 setups) + Arjun's 4 concrete tests + Lakshmi's lit scan all completed
before the org hit its monthly API spend limit mid-sweep (10 groups failed on spend limit, 2 on infra
stalls) â€” Principal chose to stop and synthesize rather than wait/raise the limit. **Nothing cleared the bar
anywhere** (best honest ann. Sharpe ~1.0: OS-26 bear-call-spread regime-gated); matches Lakshmi's literature
verdict (realistic net Sharpe caps ~0.9-1.2). Four SURVIVE-fragile/marginal setups (OS-04, OS-20, OS-26, OS-35)
are small legitimate uplifts over the existing S-04/S-05 VRP book, not bar-clearing. Full table + 12 INCOMPLETE
(not killed) setups: `04_RND_LAB/results/OPT_SWEEP50_PHASE1_20260707/PHASE1_SYNTHESIS.md`.

## FNO REPLAY GAME (new Principal product, 2026-07-05) â€” **PLAYABLE** (P0+P1+P2 core done; launch `09_PRODUCT/fno_game/run_game.ps1`)
Intraday NIFTY-weekly-options replay simulator (random hidden day, 1-min bars, persistent â‚¹10L career
bankroll, trade-log analytics). **Build book = `09_PRODUCT/fno_game/ROADMAP.md`** â€” locked Principal
rulings L1â€“L11 (spread-aware fills, lot-65-uniform, hide-date-only, no lockout v1), full mechanics
formulas, phases P0â€“P6. P0 done: FastAPI stack verified, chart lib bundled, eligible pool 1,198/1,242
days built + gap-reviewed, lot history derived from bhavcopy (â€¦â†’65 Jan-26), data_loader smoke-tested.
P1 = replay core (WS tick loop, blinding sanitizer, live chart); P2 = trading engine (needs Tara
spread-calibration vs Angel terminal). Either desk builds; ROADMAP is self-contained.
**2026-07-05 later-3: V1 COMPLETE & DEPLOYED (:8787, detached).** All phases P0-P6 done via 3 agent
rounds + QA (45/45 tests, leak suite, README). Full stack: chain w/ IV+Greeks+OI-percentile, payoff
canvas, margin preview, sizing calc, straddle/strangle presets, MKT/LMT/SL-M orders + cancel,
Orders/Trades/Log tabs, Day-P&L/free-margin/countdown chips, inline TP/SL edit, MAE/MFE+R per trade,
journal tags, Wilson-CI analytics w/ recognized-exclusion, CSV export, sound cues, D-1-continuation
chart w/ VWAP/EMA/RSI/CPR/OR15, unkillable tick loop, pause reasons. QA caught+fixed an export
blinding hole. v1.1 candidates in journal (visual QA, Tara spread calibration, reveal equity/MAE viz).

## REPO STRUCTURE CHANGE (2026-07-05, Manoj/Ops) â€” read before assuming root layout
Root decluttered per Principal order: `other2/` created at repo root, 6 items moved in (`.venv/`,
`working/`, `working101/`, an orphaned `factor_navs (1).xlsx`, and the two pre-firm-structure
planning docs `OPERATING_STANDARD_2026.md`/`PORTFOLIO_OF_EDGES.md` â€” full reasoning + rollback in
`other2/MANIFEST.md`). Root item count 29 -> 24. Nothing cataloged moved; `logs/`,
`stocks_data_cache.pkl`, `build_final_docs.py`, `intraday_options_strategy/` (still LIVE â€” do not
touch) all deliberately kept at root, see manifest for evidence.
**Root RENAME to `Shreyas_project_amc` is STAGED, NOT RUN.** `Shreyas_Ionic_AMC/99_OPS/{migrate_
root_rename.ps1, RENAME_RUNBOOK.md, HARDCODED_PATH_MANIFEST.csv}` are ready but require the WHEN
SAFE checklist (live process finished, cwd outside tree, OneDrive paused, fresh backup) before
anyone passes `-Execute`. Until that runs, every path in every doc is still correct as-is â€” do
NOT assume the folder has been renamed.

## 2026-07-05 NEW CAPABILITY + PRINCIPAL DELIVERABLES (both DONE)
- **EVALUATION_FRAMEWORK.md live** (`03_RESEARCH_DESK/`, Lakshmi +12): 6 modules (NAV forensics/holdings attribution/product-structure-tax/manager forensics/idea gates/live monitoring) + 0-100 rubric + 34 red-flags + verified data map + 60min/1day/IC-grade tiers. Prior-art: QFRA 2.0 (external, `Downloads/Mf_qfra2.../mr_x_framework`, skill qfra2-rerun) wired in for MF names; /attribution skill = extend for external NAVs (build gap, Neel). DATA_CATALOG gap â†’ Kavya: 3 PIT files on disk uncataloged (ratios_pit, yearly_balance_sheet_pit, yearly_profit_loss_pit). Tax module pending Farhan sign-off.
- **AlphaGrep MAAF NFO analysis delivered** (Neel +15): `09_PRODUCT/reports/ALPHAGREP_MAAF_ANALYSIS_2026-07-05.docx` (8 sections, 14 meeting questions, RAG scorecard 4RED/3AMBER/1GREEN). Verified: 78% of claimed 13.9% CAGR = beta; their "NIFTY TRI" = PRICE index (~1.3pp flattery); maxDD mislabeled (COVID not GFC); gold +112.5% NFO-timing. Case-study #1 stub in framework. Pointer in 90_PRINCIPALS_DESK/active/.

## THREE NEW PRINCIPAL RULINGS 2026-07-05 (D-030/031/032 â€” DECISIONS_LOG + CLAUDE.md hard rules)
Forward-test FREEZE (in-test spec changes void the test; new version = new clock) Â· capacity â‚¹10L-10cr +
limit-order-or-skip ACCEPTABLE for exceptional personal-trading strategies (re-read I-017 capacity kill under
this lens; Tara's no-fill=drop convention = the honest limit-or-skip sim) Â· DUAL MANDATE: trading line
(personal, short-term) + investment line (personal/AMC, long-term: multibagger/contrarian/deep-value/quality).
Principal msg truncated "...best and" â€” continuation pending.

## K-012 FF-CALENDAR REVIEW â€” **CLOSED 2026-07-05: STAYS-KILLED-WITH-NEW-INTAKE (CIO ruling)**
Pre-registered v3 final gate FAILED (causal+gate+D+1+tiered 1Ã—: fwd âˆ’0.03/â‚¹100, BUILD âˆ’0.51, 2Ã— âˆ’2.36; survivors PF 0.99). Signal REAL (100th pct vs matched placebos) / vehicle DEAD (61% un-exitable back-leg markets â€” CIO exitability veto). FF signal â†’ NEW INTAKE, owner Aakash (liquidity-native vehicle, 5 pre-reg kills, full ~34-trial family DSR at Gate-4). Paper-tracking REJECTED; sizing ZERO. Full trail: `results/S-03/20260705_resurrection/` (4 legs + CIO_RULING.md); books updated (KILLED_IDEAS, REGISTER, PIPELINE, KB A.14-A.18). Detail below is historical:
### (historical) 3/3 LEGS LANDED 2026-07-05; v3 was the final gate
All in `results/S-03/20260705_resurrection/`. Verdicts:
1. **Nikhil (RED_TEAM_FF_RESURRECTION.md): EDGE-BEYOND-SIZING, overall FRAGILE** â€” FF 100th pct vs turnover-matched AND CE_be-matched placebos (sizing alone â‰ˆ 0, FF adds all of +10.5); **CAUGHT NEW T9 LEAK**: v2 engine enters at argmax-FF day (non-causal; v1 was earliest-cross) â€” logged in LOOKAHEAD_CONTROLS T-log; cost bracket: survives 2Ã— slip, dies ~3.3Ã—.
2. **Sameer (SENSITIVITY_FF_SIZING.md): PLATEAU** â€” 30/30 capÃ—threshold cells forward-positive (+17..+26 per â‚¹100 his convention); equal-premium sizing is load-bearing, cap second-order; +30 family trials declared; recheck-script reproduction gap flagged (canonical sizing to be pinned: qty=min(100/CE_be, 6.0) â€” 3 independent reconstructions converged).
3. **Tara (FILL_AUDIT_FF.md): MARGINAL** â€” honest forward **+â‚¹3.88/â‚¹100 vs +â‚¹10.04 headline (38.6% retained)**; binding constraint = FILL-RATE not cost: 61.3% of fwd signals have DEAD back-leg (zero vol, 82.5% zero OI; slippage only 5% of gap); survivors near-headline (PF 2.05); fix = ex-ante back-leg vol/OI gate.
**NEXT (in flight): Arjun v3 causal re-test** â€” earliest-cross entry (leak fix) + D+1 fills + ex-ante back-leg liquidity gate + canonical sizing + tiered slippage â†’ `CAUSAL_RETEST.md`. THEN CIO synthesis rules on complete evidence (incl. DSR/PBO recompute at ~36+ family trials). Any hard FAIL = K-012 stays killed.

## IN FLIGHT AT WINDUP (harvest these FIRST next session)
1. **Sameer â€” S-04 Gate-4 sensitivity**: background compute checkpoints to `results/S-04/20260704_sensitivity/` (grid CSV first, then SENSITIVITY_REPORT.md). If report absent: re-run sensitivity_S04.py there or re-summon Sameer (agent now registered).
2. **Devika â€” Track-2 BT-11**: `results/T2-SIG11/20260704_bt11/` â€” bt11.py + **VERDICT.md landed at windup, UNREAD/UNFILED** â€” read, verify shuffle percentile honesty, file into pipeline/register.
3. **D-028 retro-audit workflow STOPPED to save tokens (no work lost)**: 4 sequential lookahead audits (S-01, factor-repl, scanner-chain, SIG-11). Resume via Workflow scriptPath+resumeFromRunId wf_b38e4890-f94 (script under .claude/projects/<slug>/d096bfac.../workflows/scripts/d028-lookahead-retro-audit-wf_b38e4890-f94.js) â€” or simpler: /lookahead-audit per target (skill exists). S-04's own lookahead audit deliberately excluded â†’ assign to Sameer AFTER his sensitivity lands.

## Right now
- **FIRM FULLY OPERATIONAL.** Team 27 (E-001..E-027 incl. CEO Meher, Product Tanvi, Overfit Dr. Bhat), 49 skills, 60 prompts approved, WORK_LOG + LEADERBOARD live. **BACKUP VAULT live** (`C:\Users\Shreyas.1Gupta\ShreyasIonicAMC_BACKUP`, weekly task, keeps 5, outside OneDrive â€” `99_OPS/backup_firm.py`).
- **QUARTERLY_PLAN_2026Q3.md BINDING** + leaders'-meeting decisions D-M1..M10 (minutes in 08_BOARD_ROOM). Paper BOOK_EQUITY = **â‚¹1 crore (D-026)**; deterministic risk ceiling live in execution_scanner (median 5 lots).
- **Strategy truth (STRATEGY_REGISTER) â€” the honest ledger of the four original sleeves is COMPLETE:**
  - S-01 IV/RV â€” SEND-BACK, paper-only FIREWALLED (+11.4pts incremental; DSR 0.687/PBO 55% FAIL via purgedcv)
  - S-02 earnings short-vol â€” **KILLED pre-IC** (denominator artifact #2; resurrection conditions registered)
  - S-03 FF calendar CE â€” **KILLED (K-012, 2026-07-04)** â€” denominator artifact #3 (pnl/back-premium); rupee-points truth: build +5.85 â†’ **forward âˆ’9.30 (loses money 2024+2025)**. D-M2 IC CANCELLED. Honesty-probe #1 needs a new vehicle.
  - S-04 strangle â€” **THE ONLY SURVIVOR**: corruption purged, honest +0.22%/spot managed, **2Ã—-cost CERTIFIED 12/12 cells â†’ PAPER-WATCH** (watch managed-exit fill optimism first)
  - S-05 Track-1 straddle â€” paper-ready (P1 clear); openalgo pilot vehicle
  - S-06 momentum blend â€” re-run w/ PIT universe + approved costs pending
- **Track-2 honest status (2026-07-04 night):** SIG-11 built (10/10 PIT tests). BT-11 run TWICE â€” HF panel then UNION panel (survivorship-corrected): real selection edge +5-6.3pp/yr over honest null (shuffle pct 86/88), survivorship was ~4pp/yr (all in 2016). **BINDING CONSTRAINT: fails 2x COST_STANDARDS (N20 +1.03%)** â€” v1.5 path: trade only entries/exits (50% monthly overlap wasted as churn) + two-stage stops (KB lesson 10). Track-2 IC to rule on register status.
- **Factor replication first cut DONE**: LOWVOL30 via Angel data â€” corr 0.90/TE 5.9% in 2024 (13.4% overall = methodology gap) â†’ data pipeline VALIDATED; D-M4 exact-methodology build targets TE<3%. Index data live: INDIA VIX 2016â†’, LOWVOL30/ALPHA50/VALUE20, 5 momentum ETFs (`datasets/index_daily/`).
- **HARD RULE (new)**: every per-trade edge reported in denominator-free RUPEE POINTS + %spot (3 sleeves died of denominator disease). purgedcv = canonical DSR/PBO (bars_per_year units guard).
- `AngelDailyOptionCapture` healthy. Execution-Sheet v2 live (258 trades, TRADE/DISCRETIONARY/BLOCKED blocks); 8 blank 25AUG-PE prices pending backfill.

## Approvals
**D-027 STANDING APPROVAL in force** (+ D-024/D-025): CEO+CIO jointly approve everything; Principal = tie-breaks + LIVE-capital + RISK_LIMITS-loosening ONLY. Permissions dontAsk. D-021/D-022 remain.

## ADOPTION QUEUE (from 3 scouts, 2026-07-04 â€” Manoj/Ops owns installs, â‰¤3 parallel, /prior-art first)
1. `pip install purgedcv` (proxy: truststore) â†’ replace hand-rolled DSR/PBO in the validation battery (test vs Arjun's S-01 numbers first).
2. Evaluate **openalgo** (Angel-native paper-trading sandbox w/ margin sim) as the S-05/S-01 paper engine â€” biggest paper-desk upgrade candidate.
3. Swap any pandas-ta imports â†’ pandas-ta-classic (original hijacked/abandoned); AUDIT for dead alphalens/pyfolio originals.
4. /retro refinement (FinCon): lessons route to the IMPLICATED persona only, broadcast only via propagation-check.
5. Deterministic risk ceiling (ai-hedge-fund pattern): hard non-overridable cap in execution_scanner (formalizes RISK_LIMITS 1%).
6. NOW-methods: Optiver RV features (IV/RV sleeve), JPX top-minus-bottom metric + LGBMRanker (Track-2), MiniLM embeddings (memo search).
7. KNOWLEDGE_BASE ref fix: mlfinlab is PAYWALLED since 2019 (keep-out); nsepy dead.

## COMPLETE TASK LEDGER (recheck 2026-07-04 â€” nothing skipped; owners per leaders' meeting)
**In flight/scheduled:** ~~D-M1 S-04 2x-cost certification~~ DONE 2026-07-04 ahead of schedule â€” SURVIVES 12/12 â†’ paper-watch Â· ~~D-M2 S-03 IC~~ CANCELLED â€” S-03 killed pre-IC 2026-07-04 (K-012; honesty-probe #1 needs new vehicle) Â· ~~D-M3 Track-2 SIG-11~~ SIGNAL LAYER DONE 2026-07-04 (BT-11/COST-11 remain, Jul-31) Â· ~~D-M4 factor-replication flagship~~ **DATA-VALIDATION COMPLETE 2026-07-04 (6wk early): LOWVOL30 TE 4.58%/corr 0.956 (<=6% all eras) on union price panel; MOMENTM30 8.48% (floor = float-weights+constituents, home-net factsheets to close)** Â· D-M5 Sanjay screen v1 after Kavya's PIT-stamping ruling (Jul-31) Â· ~~D-M6 openalgo scoped eval (Manoj, Jul-18~~ DONE 2026-07-04, ahead of schedule: verdict PILOT-ONE-STRATEGY, see `Shreyas_Ionic_AMC/04_RND_LAB/openalgo_eval.md`; purgedcv INSTALLED 0.1.2 â€” acceptance test vs Arjun's S-01 numbers pending) Â· D-M7 home-net list + token-hacks rollout (Jul-11) Â· D-M8 compliance-audit #1 (Farhan, Jul-25) Â· D-M9 board meet + pack (CEO, Jul-31).
**Outstanding small items (unowned until now â€” assigned):** lastmonth_IVRV.csv regen post-IV-cap (Manoj â€” regenerate via build_final_docs) Â· Kavya's ETF independent cross-check completion Â· ~~23 Angel daily stragglers retry (Manoj, rate-limit aware)~~ DONE 2026-07-04, 23/23 recovered, 500/500 Nifty 500 Â· S-01 resurrection HF-hunt (time-boxed â‰¤3 days, Arjun/Kavya â€” CIO ruling 2e) Â· pandas-ta/alphalens dead-import audit (Manoj) Â· ~~deterministic risk ceiling in scanner (Manoj)~~ DONE 2026-07-04, `enforce_risk_ceiling()` in execution_scanner.py, --dry-run validated Â· Optiver-RV/JPX-metric/LGBMRanker/MiniLM method adoptions (owners: Arjun/Devika/Ishaan, post-SIG-11) Â· VRP 9-filter replication weekend job (Arjun) Â· FinCon retro-routing = already implemented via propagation-check (verified).
**Home-network day (location-blocked, NOT skipped):** /factor-indices pull (script ready) Â· index factsheets/constituents Â· FII/DII flows Â· broader constituents Â· 217 quarterly symbols.
**Awaiting Principal (only these):** LIVE-capital steps Â· RISK_LIMITS loosening Â· DhanHQ-paid data if the HF-hunt fails Â· tie-breaks under D-025.

## PIT UNION PANEL v1 -- DONE 2026-07-04 (Manoj). Two panels, not one -- see below.
Original brief asked for ONE union panel; build hit a 73% HF-vs-MASTER conflict rate (stop-rule
fired correctly per spec). Diagnosed against official NSE bhavcopy ground truth
(`datasets/nifty_stock_daily/1_bhavcopy.csv`): **HF/Delisted/Raw500 = PRICE basis** (as-traded,
94.8% exact match to bhavcopy); **Master xlsx = RETURN basis** (dividend-adjusted, 41.4% match,
smooth drift toward 1.0 approaching present -- classic total-return signature). Shipped as TWO
explicit panels instead of one silently-blended column:
- `datasets/derived/pit_union_panel_v1/close_panel_price.parquet` (HF+Delisted+Raw500, 2,511 syms)
- `datasets/derived/pit_union_panel_v1/close_panel_return.parquet` (HF core + Master/Delisted/Raw500
  ratio-spliced gap-fill, 2,556 syms) -- THIS is the one that hits the coverage target.
Coverage (N200 full-252d-history, the headline metric): 2006 59.9%(HF)->71.8%(return panel),
2014 83.6%->95.5%, 2018 87.9%->97.0%. Residual truly-absent names (nowhere on disk): COX&KINGS,
UNKNOWN (data-entry artifact) -- need external data if closed further.
Downstream flags: Arjun's factor-replication is CONSISTENT PRICE basis (no dividend-inflation
artifact -- that hypothesis is retired, his residual TE is coverage/methodology, not this).
BT-11 used HF = correct, PRICE basis is right for P&L backtests, no rework needed.
Full detail + conflict/splice/quarantine audit trail + D-028 self-audit (PASS):
`datasets/derived/pit_union_panel_v1/BUILD_REPORT.md`. Next (unowned): close COX&KINGS/UNKNOWN
via external source if Principal wants it; re-run BT-11 early slices + replication early era on
the return panel now that early-era coverage is fixed.

## Blockers
- Some NSE `/api` endpoints 403 on proxy (archives + board-meeting/event-calendar APIs DO work â€” see CLAUDE.md).
- Angel rate limit AB1021: â‰¥1.2s/req; 23 daily-OHLCV stragglers pending cooldown.
- S-01 resurrection needs 2018+2020 option data (DhanHQ paid or HF alternates â€” D-009 gate).

