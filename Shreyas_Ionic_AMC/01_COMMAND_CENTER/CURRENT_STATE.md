# CURRENT STATE — read me first (updated every session end)
**As of: 2026-07-04, by DESK-20 (cross-desk sync audit — all DESK-100 claims disk-verified)**

## Right now
- **FIRM FULLY OPERATIONAL & AUDITED.** 17 agents (three-book structure, D-022), 22 skills (SKILLS_INDEX), ORG_STRUCTURE.md = master map, BOARD_ROOM (monthly cadence) + PRINCIPALS_DESK + WORK_LOG + LEADERBOARD live, git @ 59df9c3.
- **QUARTERLY_PLAN_2026Q3.md is BINDING** (CIO synthesis of blind FM plans): inverse-IV sizing capped 1.0× until a regime gate exists · pre-IC shuffle SOP mandatory · gold via D-009 · S-03 = first-cut if capacity binds · HF-first for backfills.
- **Strategy truth (STRATEGY_REGISTER):**
  - S-01 IV/RV — SEND-BACK, paper-only FIREWALLED; registered edge +11.4pts incremental (headline was 71% regime beta)
  - S-02 earnings short-vol — **FAILS-PRE-IC** (denominator artifact; honest +9.7%/event; −10.1% vs calendar-matched short-vol); resurrection conditions registered
  - S-03 FF calendar CE — **IC-memo PENDING (next up — only untested registered strategy)**
  - S-04 strangle — **FAILS-PRE-IC + DATA CORRUPTION** (future-expiry fabricated wins; guards L7/L7b added; marking pipeline at Data Office for rebuild)
  - S-05 Track-1 straddle — paper-ready; **P1 IV-cap CLEAR → paper track unblocked**
  - S-06 momentum blend — re-run w/ PIT universe + approved costs pending
- Gold/silver ETF series cataloged (D-009 PASS) → Devika's gold-silver cheap-test unblocked.
- `AngelDailyOptionCapture` healthy (15:45/20:00/23:00 + wake catch-up). DESK-100 owns.

## Approvals
D-021 blanket approval in force: P-01..12 + RP-01..10 in `approved/`, COST_STANDARDS + RISK_LIMITS binding. D-022: CIO+FMs may create agents/skills (journal + EVOLUTION_LOG mandatory). Nothing currently awaiting Principal.

## ADOPTION QUEUE (from 3 scouts, 2026-07-04 — Manoj/Ops owns installs, ≤3 parallel, /prior-art first)
1. `pip install purgedcv` (proxy: truststore) → replace hand-rolled DSR/PBO in the validation battery (test vs Arjun's S-01 numbers first).
2. Evaluate **openalgo** (Angel-native paper-trading sandbox w/ margin sim) as the S-05/S-01 paper engine — biggest paper-desk upgrade candidate.
3. Swap any pandas-ta imports → pandas-ta-classic (original hijacked/abandoned); AUDIT for dead alphalens/pyfolio originals.
4. /retro refinement (FinCon): lessons route to the IMPLICATED persona only, broadcast only via propagation-check.
5. Deterministic risk ceiling (ai-hedge-fund pattern): hard non-overridable cap in execution_scanner (formalizes RISK_LIMITS 1%).
6. NOW-methods: Optiver RV features (IV/RV sleeve), JPX top-minus-bottom metric + LGBMRanker (Track-2), MiniLM embeddings (memo search).
7. KNOWLEDGE_BASE ref fix: mlfinlab is PAYWALLED since 2019 (keep-out); nsepy dead.

## COMPLETE TASK LEDGER (recheck 2026-07-04 — nothing skipped; owners per leaders' meeting)
**In flight/scheduled:** D-M1 S-04 2x-cost certification (Arjun, Jul-18) · D-M2 S-03 IC w/ shuffle + seeded honesty-probe (Vikram/Arjun/Nikhil, Jul-25) · D-M3 Track-2 SIG-11 (Devika+DESK-100, Jul-31) · D-M4 factor-replication flagship (/prior-art → home-net pull → NIFTY200MOMENTM30, Aug-15) · D-M5 Sanjay screen v1 after Kavya's PIT-stamping ruling (Jul-31) · D-M6 openalgo scoped eval (Manoj, Jul-18; purgedcv INSTALLED 0.1.2 — acceptance test vs Arjun's S-01 numbers pending) · D-M7 home-net list + token-hacks rollout (Jul-11) · D-M8 compliance-audit #1 (Farhan, Jul-25) · D-M9 board meet + pack (CEO, Jul-31).
**Outstanding small items (unowned until now — assigned):** lastmonth_IVRV.csv regen post-IV-cap (Manoj — regenerate via build_final_docs) · Kavya's ETF independent cross-check completion · ~~23 Angel daily stragglers retry (Manoj, rate-limit aware)~~ DONE 2026-07-04, 23/23 recovered, 500/500 Nifty 500 · S-01 resurrection HF-hunt (time-boxed ≤3 days, Arjun/Kavya — CIO ruling 2e) · pandas-ta/alphalens dead-import audit (Manoj) · ~~deterministic risk ceiling in scanner (Manoj)~~ DONE 2026-07-04, `enforce_risk_ceiling()` in execution_scanner.py, --dry-run validated · Optiver-RV/JPX-metric/LGBMRanker/MiniLM method adoptions (owners: Arjun/Devika/Ishaan, post-SIG-11) · VRP 9-filter replication weekend job (Arjun) · FinCon retro-routing = already implemented via propagation-check (verified).
**Home-network day (location-blocked, NOT skipped):** /factor-indices pull (script ready) · index factsheets/constituents · FII/DII flows · broader constituents · 217 quarterly symbols.
**Awaiting Principal (only these):** LIVE-capital steps · RISK_LIMITS loosening · DhanHQ-paid data if the HF-hunt fails · tie-breaks under D-025.

## Blockers
- Some NSE `/api` endpoints 403 on proxy (archives + board-meeting/event-calendar APIs DO work — see CLAUDE.md).
- Angel rate limit AB1021: ≥1.2s/req; 23 daily-OHLCV stragglers pending cooldown.
- S-01 resurrection needs 2018+2020 option data (DhanHQ paid or HF alternates — D-009 gate).
