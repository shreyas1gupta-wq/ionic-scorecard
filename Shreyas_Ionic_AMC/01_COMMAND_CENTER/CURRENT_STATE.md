# CURRENT STATE — read me first (updated every session end)
**As of: 2026-07-04 late-night WINDUP (token limit), by DESK-100 — sleeves ledger COMPLETE; D-028 lookahead controls LIVE**

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
- **Track-2 SIG-11 BUILT** (8-criteria Minervini + 12-1 mom + RS pct + breakout-vol; 10/10 PIT tests). Next: BT-11/COST-11.
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
**In flight/scheduled:** ~~D-M1 S-04 2x-cost certification~~ DONE 2026-07-04 ahead of schedule — SURVIVES 12/12 → paper-watch · ~~D-M2 S-03 IC~~ CANCELLED — S-03 killed pre-IC 2026-07-04 (K-012; honesty-probe #1 needs new vehicle) · ~~D-M3 Track-2 SIG-11~~ SIGNAL LAYER DONE 2026-07-04 (BT-11/COST-11 remain, Jul-31) · D-M4 factor-replication flagship (/prior-art → home-net pull → NIFTY200MOMENTM30, Aug-15) · D-M5 Sanjay screen v1 after Kavya's PIT-stamping ruling (Jul-31) · ~~D-M6 openalgo scoped eval (Manoj, Jul-18~~ DONE 2026-07-04, ahead of schedule: verdict PILOT-ONE-STRATEGY, see `Shreyas_Ionic_AMC/04_RND_LAB/openalgo_eval.md`; purgedcv INSTALLED 0.1.2 — acceptance test vs Arjun's S-01 numbers pending) · D-M7 home-net list + token-hacks rollout (Jul-11) · D-M8 compliance-audit #1 (Farhan, Jul-25) · D-M9 board meet + pack (CEO, Jul-31).
**Outstanding small items (unowned until now — assigned):** lastmonth_IVRV.csv regen post-IV-cap (Manoj — regenerate via build_final_docs) · Kavya's ETF independent cross-check completion · ~~23 Angel daily stragglers retry (Manoj, rate-limit aware)~~ DONE 2026-07-04, 23/23 recovered, 500/500 Nifty 500 · S-01 resurrection HF-hunt (time-boxed ≤3 days, Arjun/Kavya — CIO ruling 2e) · pandas-ta/alphalens dead-import audit (Manoj) · ~~deterministic risk ceiling in scanner (Manoj)~~ DONE 2026-07-04, `enforce_risk_ceiling()` in execution_scanner.py, --dry-run validated · Optiver-RV/JPX-metric/LGBMRanker/MiniLM method adoptions (owners: Arjun/Devika/Ishaan, post-SIG-11) · VRP 9-filter replication weekend job (Arjun) · FinCon retro-routing = already implemented via propagation-check (verified).
**Home-network day (location-blocked, NOT skipped):** /factor-indices pull (script ready) · index factsheets/constituents · FII/DII flows · broader constituents · 217 quarterly symbols.
**Awaiting Principal (only these):** LIVE-capital steps · RISK_LIMITS loosening · DhanHQ-paid data if the HF-hunt fails · tie-breaks under D-025.

## NEW FLAGSHIP DATA TASK (from forensics, 2026-07-04): PIT UNION PANEL v1
Build ONE survivorship-complete daily close panel 2005->today from: HF panel (deep, adjusted, survivors) + Master xlsx (13/14 adjusted; LT-2006 bad print) + Delisted xlsx + raw/nifty500 239 csvs + swing_momentum/processed/eq_close.parquet + screener-dump names. Owner: Kavya+Manoj. Then: re-run BT-11 early slices + replication early era on it. ~95% of missing early names are recoverable ON-DISK (bucket proof: taskA_bucket_counts.csv). Only ~3 names/rebalance + PIT free-float need external data.

## Blockers
- Some NSE `/api` endpoints 403 on proxy (archives + board-meeting/event-calendar APIs DO work — see CLAUDE.md).
- Angel rate limit AB1021: ≥1.2s/req; 23 daily-OHLCV stragglers pending cooldown.
- S-01 resurrection needs 2018+2020 option data (DhanHQ paid or HF alternates — D-009 gate).
