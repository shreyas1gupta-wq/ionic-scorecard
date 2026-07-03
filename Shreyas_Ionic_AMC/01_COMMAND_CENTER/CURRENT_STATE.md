# CURRENT STATE — read me first (updated every session end)
**As of: 2026-07-04 (early), by DESK-100**

## Right now
- **FIRM BUILD COMPLETE.** All of WORK_ORDER_DESK100_BUILD executed: git repo live (command layer, data ignored), 15 agents in `.claude/agents/`, 5 skills (`/ic-memo /red-team /data-check /idea-log /eod`), folders 03–07+99 fully seeded, FACTOR_LIBRARY, RESEARCH_SOP, CODE_CHECKS + `lib/guards.py` (smoke-tested on real data), RP-01..10 drafts, ANALYST_CHECKLISTS.
- **Data milestone (DESK-100): the 17-month option gap is FILLED** (NSE bhavcopy, daily granularity) and the option universe is **210 F&O names** (was 88; +122 incl. PAYTM/KAYNES/DIXON/HAL, 2-yr history). `stocks_options/` is now DUAL-SCHEMA — see DATA_QUALITY_RULES.
- **All 4 option strategies re-validated on 210 universe, forward-stable** (full-2025+H1-26 OOS): IV/RV +36.7%/trade 90% fwd · earnings-thru +21.6%/60% · FF-CE +6-9%/70% (large-cap only) · strangle-managed +1.75%/spot 88%. Registered as S-01..S-04 with gates; S-05 Track-1 paper-ready; S-06 momentum blend diversifier.
- Live execution machinery: conviction+news-scored sheets in `FINAL_STRATEGY_FORWARD_CHECK/08_Execution/` (516 legs, 210 stocks, Jul-2026 cycle); NSE earnings calendar refreshed (27 Q1-FY27 dates).
- `AngelDailyOptionCapture` healthy: 15:45/20:00/23:00 + wake-catch-up, idempotent. DESK-100 owns.

## Approvals — ALL GRANTED (D-021, 2026-07-03: "my approval on everything okay continue")
P-01..P-12 + RP-01..RP-10 in `02_PROMPT_LIBRARY/approved/`; COST_STANDARDS + RISK_LIMITS banners APPROVED and binding. Team now 16 (E-016 Devika Menon, FM-Equities) + 20 skills (SKILLS_INDEX.md).

## IC-1 outcome (read the memo: 03_RESEARCH_DESK/memos/20260703_S01_ivrv_short_straddle.md)
- S-01 IV/RV: **SEND-BACK, no capital** (DSR 0.687/PBO 55.3%; headline = 71% regime beta; true edge +11.4pts incremental). Paper-tracking approved, firewalled. Resurrection conditions registered.
- D-021: everything approved (P/RP clauses, COST_STANDARDS, RISK_LIMITS all binding).
- Board: Track-2 at CHEAP-TEST (Devika spec), Track-3 + 4 new ideas at INTAKE, S-02..S-04 await their ICs.

## Next actions
- **Either desk:** IC memos for S-02/S-03/S-04 via `/ic-memo` (expect Red-Team regime-beta decomposition on each — IC-1 set the standard; the strangle's +1.75%/spot likely has the same beta component).
- **DESK-100:** Track-2 build DATA-11→GATE-11 per Devika's spec (FIRST: corp-action adjustment check on the daily panel); fix live-feed IV-cap (Tara's catch — INFY 132.7% must be impossible in the live scanner); re-run S-06 with PIT universe + approved costs; retry 23 Angel stragglers; scanner risk-wiring agent in flight (check journal for landing).
- **DESK-20 / R&D:** cheap-tests for the 4 INTAKE ideas (sentiment lexicon quintile first — cheapest); S-01 resurrection work needs 2018+2020 option data (source: DhanHQ paid, or HF alternates — D-009 gate).
- **Data Officer:** OI-surface cadence fix + spot/IV join (Track-3 blocker); GOLDBEES/SILVERBEES daily price series fetch.
- **Home-network day:** NSE-blocked items (FII/DII flows, broader constituents, 217 missing quarterly symbols).

## Blockers
- Some NSE `/api` endpoints 403 on proxy (archives + board-meeting APIs DO work — see CLAUDE.md).
- Angel rate limit AB1021: ≥1.2s/req; 23 daily-OHLCV stragglers pending cooldown.
