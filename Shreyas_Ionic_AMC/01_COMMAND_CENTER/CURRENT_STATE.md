# CURRENT STATE — read me first (updated every session end)
**As of: 2026-07-04 (early), by DESK-100**

## Right now
- **FIRM BUILD COMPLETE.** All of WORK_ORDER_DESK100_BUILD executed: git repo live (command layer, data ignored), 15 agents in `.claude/agents/`, 5 skills (`/ic-memo /red-team /data-check /idea-log /eod`), folders 03–07+99 fully seeded, FACTOR_LIBRARY, RESEARCH_SOP, CODE_CHECKS + `lib/guards.py` (smoke-tested on real data), RP-01..10 drafts, ANALYST_CHECKLISTS.
- **Data milestone (DESK-100): the 17-month option gap is FILLED** (NSE bhavcopy, daily granularity) and the option universe is **210 F&O names** (was 88; +122 incl. PAYTM/KAYNES/DIXON/HAL, 2-yr history). `stocks_options/` is now DUAL-SCHEMA — see DATA_QUALITY_RULES.
- **All 4 option strategies re-validated on 210 universe, forward-stable** (full-2025+H1-26 OOS): IV/RV +36.7%/trade 90% fwd · earnings-thru +21.6%/60% · FF-CE +6-9%/70% (large-cap only) · strangle-managed +1.75%/spot 88%. Registered as S-01..S-04 with gates; S-05 Track-1 paper-ready; S-06 momentum blend diversifier.
- Live execution machinery: conviction+news-scored sheets in `FINAL_STRATEGY_FORWARD_CHECK/08_Execution/` (516 legs, 210 stocks, Jul-2026 cycle); NSE earnings calendar refreshed (27 Q1-FY27 dates).
- `AngelDailyOptionCapture` healthy: 15:45/20:00/23:00 + wake-catch-up, idempotent. DESK-100 owns.

## Awaiting PRINCIPAL approval (nothing binding yet — D-020)
1. Prompt clauses P-01..P-12 (`BUILD_ADDENDUM_v1.md §2`) — one by one → then `approved/`.
2. Research prompts RP-01..RP-10 (drafts/) — one by one.
3. `06_TRADING_DESK/COST_STANDARDS.md` (DRAFT) and `07_RISK_OFFICE/RISK_LIMITS.md` (DRAFT).

## IC-1 outcome (read the memo: 03_RESEARCH_DESK/memos/20260703_S01_ivrv_short_straddle.md)
- S-01 IV/RV: **SEND-BACK, no capital** (DSR 0.687/PBO 55.3%; headline = 71% regime beta; true edge +11.4pts incremental). Paper-tracking approved, firewalled. Resurrection conditions registered.
- D-021: everything approved (P/RP clauses, COST_STANDARDS, RISK_LIMITS all binding).
- Board: Track-2 at CHEAP-TEST (Devika spec), Track-3 + 4 new ideas at INTAKE, S-02..S-04 await their ICs.

## Next actions
- **Either desk:** IC memos for S-01..S-04 via `/ic-memo` (owners + kill criteria formalized) — first real committee run.
- **DESK-100:** wire ex-ante inverse-IV sizing + event-gate into the execution scanner (S-04 gate); re-run S-06 momentum blend with PIT universe + draft costs; retry 23 Angel stragglers post-cooldown.
- **DESK-20:** R&D one-pagers for the intake queue (sentiment/PEAD/gold-silver/expiry-seasonality) via `/idea-log`.
- **Home-network day:** NSE-blocked items (FII/DII flows, broader constituents, 217 missing quarterly symbols).

## Blockers
- Some NSE `/api` endpoints 403 on proxy (archives + board-meeting APIs DO work — see CLAUDE.md).
- Angel rate limit AB1021: ≥1.2s/req; 23 daily-OHLCV stragglers pending cooldown.
