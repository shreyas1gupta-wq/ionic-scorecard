# CURRENT STATE — read me first (updated every session end)
**As of: 2026-07-05 00:00 session close, by DESK-100 — the densest research day complete; all agents landed, all filed, backup #3 taken**
**NEXT SESSION STARTS WITH:** (1) re-arm cadence crons (CLAUDE.md protocol #4); (2) first /weekly-meet Mon 07-07; (3) I-016 diversifier stress-corr deliverable (binding pre-IC); (4) BT-11 v1.5 spec (entry/exit-only + two-stage stops + circuit fills); (5) D-028 retro-audit workflow resume; (6) S-04/S-05 paper first entries (~Jul-14 cycle).

## IN FLIGHT AT WINDUP (harvest these FIRST next session)
1. **Sameer — S-04 Gate-4 sensitivity**: background compute checkpoints to `results/S-04/20260704_sensitivity/` (grid CSV first, then SENSITIVITY_REPORT.md). If report absent: re-run sensitivity_S04.py there or re-summon Sameer (agent now registered).
2. **Devika — Track-2 BT-11**: `results/T2-SIG11/20260704_bt11/` — bt11.py + **VERDICT.md landed at windup, UNREAD/UNFILED** — read, verify shuffle percentile honesty, file into pipeline/register.
3. **D-028 retro-audit workflow STOPPED to save tokens (no work lost)**: 4 sequential lookahead audits (S-01, factor-repl, scanner-chain, SIG-11). Resume via Workflow scriptPath+resumeFromRunId wf_b38e4890-f94 (script under .claude/projects/<slug>/d096bfac.../workflows/scripts/d028-lookahead-retro-audit-wf_b38e4890-f94.js) — or simpler: /lookahead-audit per target (skill exists). S-04's own lookahead audit deliberately excluded → assign to Sameer AFTER his sensitivity lands.

## Right now
- **FIRM FULLY OPERATIONAL.** Team 27 (E-001..E-027 incl. CEO Meher, Product Tanvi, Overfit Dr. Bhat), 49 skills, 60 prompts approved, WORK_LOG + LEADERBOARD live. **BACKUP VAULT live** (`C:\Users\Shreyas.1Gupta\ShreyasIonicAMC_BACKUP`, weekly task, keeps 5, outside OneDrive — `99_OPS/backup_firm.py`).
- **QUARTERLY_PLAN_2026Q3.md BINDING** + leaders'-meeting decisions D-M1..M10 (minutes in 08_BOARD_ROOM). Paper BOOK_EQUITY = **₹1 crore (D-026)**; deterministic risk ceiling live in execution_scanner (median 5 lots).
- **Strategy truth (STRATEGY_REGISTER) — the honest ledger of the four original sleeves is COMPLETE:**
  - S-01 IV/RV — SEND-BACK, paper-only FIREWALLED (+11.4pts incremental; DSR 0.687/PBO 55% FAIL via purgedcv)
  - S-02 earnings short-vol — **KILLED pre-IC** (denominator artifact #2; resurrection conditions registered)
  - S-03 FF calendar CE — **KILLED (K-012, 2026-07-04)** — denominator artifact #3 (pnl/back-premium); rupee-points truth: build +5.85 → **forward −9.30 (loses money 2024+2025)**. D-M2 IC CANCELLED. Honesty-probe #1 needs a new vehicle.
  - S-04 strangle — **THE ONLY SURVIVOR**: corruption purged, honest +0.22%/spot managed, **2×-cost CERTIFIED 12/12 cells → PAPER-WATCH** (watch managed-exit fill optimism first)
  - S-05 Track-1 straddle — paper-ready (P1 clear); openalgo pilot vehicle
  - S-06 momentum blend — re-run w/ PIT universe + approved costs pending
- **Track-2 honest status (2026-07-04 night):** SIG-11 built (10/10 PIT tests). BT-11 run TWICE — HF panel then UNION panel (survivorship-corrected): real selection edge +5-6.3pp/yr over honest null (shuffle pct 86/88), survivorship was ~4pp/yr (all in 2016). **BINDING CONSTRAINT: fails 2x COST_STANDARDS (N20 +1.03%)** — v1.5 path: trade only entries/exits (50% monthly overlap wasted as churn) + two-stage stops (KB lesson 10). Track-2 IC to rule on register status.
- **Factor replication first cut DONE**: LOWVOL30 via Angel data — corr 0.90/TE 5.9% in 2024 (13.4% overall = methodology gap) → data pipeline VALIDATED; D-M4 exact-methodology build targets TE<3%. Index data live: INDIA VIX 2016→, LOWVOL30/ALPHA50/VALUE20, 5 momentum ETFs (`datasets/index_daily/`).
- **HARD RULE (new)**: every per-trade edge reported in denominator-free RUPEE POINTS + %spot (3 sleeves died of denominator disease). purgedcv = canonical DSR/PBO (bars_per_year units guard).
- `AngelDailyOptionCapture` healthy. Execution-Sheet v2 live (258 trades, TRADE/DISCRETIONARY/BLOCKED blocks); 8 blank 25AUG-PE prices pending backfill.

## Approvals
**D-027 STANDING APPROVAL in force** (+ D-024/D-025): CEO+CIO jointly approve everything; Principal = tie-breaks + LIVE-capital + RISK_LIMITS-loosening ONLY. Permissions dontAsk. D-021/D-022 remain.

## ADOPTION QUEUE (from 3 scouts, 2026-07-04 — Manoj/Ops owns installs, ≤3 parallel, /prior-art first)
1. `pip install purgedcv` (proxy: truststore) → replace hand-rolled DSR/PBO in the validation battery (test vs Arjun's S-01 numbers first).
2. Evaluate **openalgo** (Angel-native paper-trading sandbox w/ margin sim) as the S-05/S-01 paper engine — biggest paper-desk upgrade candidate.
3. Swap any pandas-ta imports → pandas-ta-classic (original hijacked/abandoned); AUDIT for dead alphalens/pyfolio originals.
4. /retro refinement (FinCon): lessons route to the IMPLICATED persona only, broadcast only via propagation-check.
5. Deterministic risk ceiling (ai-hedge-fund pattern): hard non-overridable cap in execution_scanner (formalizes RISK_LIMITS 1%).
6. NOW-methods: Optiver RV features (IV/RV sleeve), JPX top-minus-bottom metric + LGBMRanker (Track-2), MiniLM embeddings (memo search).
7. KNOWLEDGE_BASE ref fix: mlfinlab is PAYWALLED since 2019 (keep-out); nsepy dead.

## COMPLETE TASK LEDGER (recheck 2026-07-04 — nothing skipped; owners per leaders' meeting)
**In flight/scheduled:** ~~D-M1 S-04 2x-cost certification~~ DONE 2026-07-04 ahead of schedule — SURVIVES 12/12 → paper-watch · ~~D-M2 S-03 IC~~ CANCELLED — S-03 killed pre-IC 2026-07-04 (K-012; honesty-probe #1 needs new vehicle) · ~~D-M3 Track-2 SIG-11~~ SIGNAL LAYER DONE 2026-07-04 (BT-11/COST-11 remain, Jul-31) · ~~D-M4 factor-replication flagship~~ **DATA-VALIDATION COMPLETE 2026-07-04 (6wk early): LOWVOL30 TE 4.58%/corr 0.956 (<=6% all eras) on union price panel; MOMENTM30 8.48% (floor = float-weights+constituents, home-net factsheets to close)** · D-M5 Sanjay screen v1 after Kavya's PIT-stamping ruling (Jul-31) · ~~D-M6 openalgo scoped eval (Manoj, Jul-18~~ DONE 2026-07-04, ahead of schedule: verdict PILOT-ONE-STRATEGY, see `Shreyas_Ionic_AMC/04_RND_LAB/openalgo_eval.md`; purgedcv INSTALLED 0.1.2 — acceptance test vs Arjun's S-01 numbers pending) · D-M7 home-net list + token-hacks rollout (Jul-11) · D-M8 compliance-audit #1 (Farhan, Jul-25) · D-M9 board meet + pack (CEO, Jul-31).
**Outstanding small items (unowned until now — assigned):** lastmonth_IVRV.csv regen post-IV-cap (Manoj — regenerate via build_final_docs) · Kavya's ETF independent cross-check completion · ~~23 Angel daily stragglers retry (Manoj, rate-limit aware)~~ DONE 2026-07-04, 23/23 recovered, 500/500 Nifty 500 · S-01 resurrection HF-hunt (time-boxed ≤3 days, Arjun/Kavya — CIO ruling 2e) · pandas-ta/alphalens dead-import audit (Manoj) · ~~deterministic risk ceiling in scanner (Manoj)~~ DONE 2026-07-04, `enforce_risk_ceiling()` in execution_scanner.py, --dry-run validated · Optiver-RV/JPX-metric/LGBMRanker/MiniLM method adoptions (owners: Arjun/Devika/Ishaan, post-SIG-11) · VRP 9-filter replication weekend job (Arjun) · FinCon retro-routing = already implemented via propagation-check (verified).
**Home-network day (location-blocked, NOT skipped):** /factor-indices pull (script ready) · index factsheets/constituents · FII/DII flows · broader constituents · 217 quarterly symbols.
**Awaiting Principal (only these):** LIVE-capital steps · RISK_LIMITS loosening · DhanHQ-paid data if the HF-hunt fails · tie-breaks under D-025.

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
- Some NSE `/api` endpoints 403 on proxy (archives + board-meeting/event-calendar APIs DO work — see CLAUDE.md).
- Angel rate limit AB1021: ≥1.2s/req; 23 daily-OHLCV stragglers pending cooldown.
- S-01 resurrection needs 2018+2020 option data (DhanHQ paid or HF alternates — D-009 gate).
