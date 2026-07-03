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

## Next actions (RESUME HERE next session — any desk; D-023: max 3 parallel)
1. **S-04 pipeline rebuild** (spec ready, never started): fix `intraday_options_strategy/buying/shortlist_shortvol.py` — spot source = HF daily UNION Angel-2026 daily bulk (find under datasets/); import guards L7 (`assert_no_future_settlement`) + L7b (`assert_physical_bounds` ≤6%); regenerate parquet; validate 2026 months normalize; then Arjun re-shuffles.
2. **Gold/silver cheap-test** (data D-009-PASSED, never started): run Devika's pre-registered kill test (one-pager `ideas/20260703_gold_silver_sleeve.md`) on `datasets/etf_gold_silver/*.parquet`; NIFTY proxy caveat: daily panel ends 2026-01-22.
3. **S-05 paper setup** (Vikram) + Track-2 DATA-11 start (corp-action check FIRST) + S-03 shuffle (last priority).
4. **Board prep**: RESEARCH_ORG_PRACTICES adoption votes + P-13/P-14 drafts → Principal.
5. Re-verify the unverified research leads (cheap re-checks listed in the board pack).

## Blockers
- Some NSE `/api` endpoints 403 on proxy (archives + board-meeting/event-calendar APIs DO work — see CLAUDE.md).
- Angel rate limit AB1021: ≥1.2s/req; 23 daily-OHLCV stragglers pending cooldown.
- S-01 resurrection needs 2018+2020 option data (DhanHQ paid or HF alternates — D-009 gate).
