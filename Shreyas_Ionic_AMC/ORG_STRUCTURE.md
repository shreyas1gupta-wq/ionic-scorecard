# ORG STRUCTURE — Shreyas_Ionic_AMC (master map; update on any structural change)

## Governance chart
```
PRINCIPAL (Shreyas) — owner, board chair, LIVE gate, approvals (D-series)
└── BOARD (monthly, 08_BOARD_ROOM): Principal chairs; CIO presents; FMs report books
    ├── Meher Kapadia — CEO (E-018): OPERATIONS — cadence (master schedule: 01_COMMAND_CENTER/OPERATING_CALENDAR.md), budget/tokens, HR/AP, board secretary
    │    ├── Farhan Qureshi (E-019) Compliance · Manoj Pillai (E-023) Ops-Eng · Lakshmi N. (E-024) Librarian
    │    └── Tanvi Desai (E-026) Head of Product — investor letter, dashboards, execution-sheet UX, strategy packaging (09_PRODUCT/)
    └── Rajan Mehta — CIO (E-001): INVESTMENTS — capital protection, tail-risk veto, arbitrates the 3 books
        ├── Ritika Sharma (E-020) Portfolio Risk Mgr · Dr. Sameer Bhat (E-027) Overfit/Sensitivity · Cyrus Daruwalla (E-021) Macro · Aakash Jain (E-022) Structurer · Neel Basu (E-025) Attribution
        ├── Vikram Shah (E-002) — FM DERIVATIVES & SHORT-VOL book (S-01..S-05)
        ├── Devika Menon (E-016) — FM EQUITIES & MOMENTUM book (Track-2, factor sleeves, gold/silver)
        ├── Sanjay Kulkarni (E-017) — FM FUNDAMENTAL QUALITY & VALUE book (screens→coverage→watchlist)
        ├── Ananya Iyer (E-003) — Equity Research Head → Meera/Karan/Sneha/Rohan/Priya (5 sector analysts)
        ├── Arjun Rao (E-004) — Quant Head (validation authority) · Dhruv Kapoor (E-005) — Technical Head
        ├── Prof. Aditya Verma (E-011) — R&D Head · Ishaan Gupta (E-012) — ML
        ├── Kavya Reddy (E-013) — Data Officer · Tara Singh (E-015) — Execution/TCA
        └── Nikhil Bose (E-014) — RED TEAM (reports to CIO ONLY — independence by design)
DESKS: DESK-20 (CIO office/light R&D, ≤2 parallel) · DESK-100 (execution floor, ≤3 parallel per D-023)
D-022: CIO + 3 FMs may create new agents/skills (journal + EVOLUTION_LOG mandatory).
```

## Folder map (what lives where — file-placement RULES)
| Folder | Purpose | Placement rule |
|---|---|---|
| `00_GOVERNANCE/` | charter, roster+AP, token policy, models, LEADERBOARD, SELF_IMPROVEMENT, evolution log | anything about WHO we are and how we're measured |
| `01_COMMAND_CENTER/` | SESSION_JOURNAL, CURRENT_STATE, DECISIONS_LOG, WORK_LOG, QUARTERLY_PLAN, WAR_ROOM, SKILLS_INDEX, `archive/` (completed orders) | anything about WHAT is happening now/next |
| `02_PROMPT_LIBRARY/` | `approved/` (binding) · `drafts/` | every reusable prompt |
| `03_RESEARCH_DESK/` | IC_MEMO_TEMPLATE, EVALUATION_FRAMEWORK (master NAV/product/manager/idea/strategy analysis protocol — 6 modules + scoring rubric + red-flag library), `memos/` (permanent decisions), ANALYST_CHECKLISTS, `forward_tests/` (paper-strategy weekly marks) | anything an IC will judge |
| `04_RND_LAB/` | IDEA_PIPELINE, `ideas/` (one-pagers), KILLED_IDEAS, KNOWLEDGE_BASE, FACTOR_LIBRARY, RESEARCH_SOP, CODE_CHECKS, `lib/guards.py` | anything pre-IC research |
| `05_DATA_OFFICE/` | DATA_CATALOG, DATA_QUALITY_RULES, `scripts/` (canonical data/exec code) | anything about data truth |
| `06_TRADING_DESK/` | COST_STANDARDS, STRATEGY_REGISTER, PAPER_LEDGER | anything about live/paper execution |
| `07_RISK_OFFICE/` | RISK_LIMITS, ADVERSARIAL_REVIEWS | anything Red Team / limits |
| `08_BOARD_ROOM/` | BOARD_CHARTER, `minutes/`, `month_end/` (checkpoints + next-month plans) | governance cadence artifacts |
| `09_PRODUCT/` | ROADMAP, BACKLOG, Investor Letters, dashboard specs, strategy product-specs | anything the Principal (or future retail-account client) actually reads/touches |
| `90_PRINCIPALS_DESK/` | INBOX, `active/`, `done/` | **Principal's NON-FIRM tasks (his job, general asks)** — firewalled from research books; still WORK_LOG'd |
| `99_OPS/` | EOD_ROUTINE, BACKUP_POLICY | plumbing |
| root `results/` | `<strategy>/<run_id>/` immutable run outputs | every backtest run |
| root legacy (`intraday_options_strategy/`, `swing_momentum/`, `datasets/`, `FINAL_STRATEGY_FORWARD_CHECK/`...) | READ-ONLY legacy (D-002) | never move/rename; copy INTO firm if needed |

## Cadences (who runs what, when)
- **Daily (auto):** AngelDailyOptionCapture (15:45/20:00/23:00) · EOD freshness ping (/eod) · /desk-open at session start.
- **Weekly:** paper reconcile (Tara) · pipeline triage (FMs) · WAR_ROOM wipe (journal first).
- **Monthly:** **BOARD MEETING** (/board-meet → 08_BOARD_ROOM) — month-end checkpoint + next-month plan + edge-decay review + AP posting.
- **Quarterly:** binding plan refresh (CIO+FMs) · /review-team (leaderboard settlement, PIP, persona rewrites) · red-team the PROCESS · KILLED_IDEAS resurrection review.

## Self-improvement (full protocol: 00_GOVERNANCE/SELF_IMPROVEMENT.md)
Per-task /retro → persona Lessons · per-session leaderboard coaching · monthly board review → quarterly persona evolution. Lessons are institutional: they survive agent replacement (roster PIP rule).
