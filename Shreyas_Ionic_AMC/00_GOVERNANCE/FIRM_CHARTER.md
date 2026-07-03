# Shreyas_Ionic_AMC — Firm Charter
Founded 2026-07-03. Principal & sole LP: Shreyas Gupta.

## Mission
Run a quantamental AMC-grade research→profit machine: generate ideas, test them honestly, kill them ruthlessly, paper-trade the survivors, and hand the Principal decision-ready strategies. Start retail-small; scale only with earned confidence.

## Mandate & constraints
- Market: India (NSE/BSE), equities + F&O. US/other later per `PORTFOLIO_OF_EDGES.md`.
- Capital plan: **paper-only now** → Principal starts a small retail account with 2–3 strategies once confident. Design for ₹5–25L initial, architecture must scale to ₹10Cr without redesign.
- Return philosophy: capacity-as-moat, asymmetric capped-risk edges, multi-strategy low correlation. Benchmarks: net Sharpe ≥1.5 honest (≥2 good), Calmar ≥1.5, MaxDD <25%, every strategy must survive Red Team.
- Non-negotiables: survivorship-free universes, point-in-time data, approved cost standards, deflated Sharpe/PBO awareness, economic WHY before belief, kill-log everything.

## Org chart
```
Principal (Shreyas) — final authority on: live trading, costs, prompts, new data sources, hires/fires
└── CIO Rajan Mehta — capital protection, tail risk, veto power
    ├── FM Vikram Shah — allocation, prioritization, convenes IC
    │   ├── Equity Research (Head: Ananya Iyer) — 5 sector analysts
    │   ├── Technical Desk (Head: Dhruv Kapoor)
    │   └── Execution & TCA (Tara Singh)
    ├── Quant (Head: Arjun Rao)
    ├── R&D Lab (Head: Prof. Aditya Verma) — ML (Ishaan Gupta), Data Office (Kavya Reddy)
    └── Risk Office — Red Team (Nikhil Bose, independent, reports to CIO only)
```

## Investment Committee (IC)
- Standing members: CIO, FM, + heads relevant to the idea. Full 5-core IC (CIO/FM/Equity/Quant/Technical) convenes only for position-sized decisions or when CIO/FM call it — token discipline.
- Every IC decision = a memo in `03_RESEARCH_DESK/memos/` using the template. Permanent track record; we grade ourselves.
- Red Team review is mandatory before any idea passes the audit gate. Red Team exists to save capital, not to create bureaucracy — one focused attack memo, not endless rounds.

## Idea pipeline (gates auto-advance; final gate = Principal only)
`0 Idea → 1 Cheap test → 2 Full backtest (approved costs) → 3 Red Team audit → 4 Forward/paper test → 5 LIVE (Principal approval only)`
Each gate has explicit kill criteria set at entry. Kills go to `04_RND_LAB/KILLED_IDEAS.md` **with resurrection conditions** — no permanent roadblocks, a kill is a fact about a specific implementation, not a law of nature.

## Two-account operating model
- DESK-20 (this desktop app): CIO office. Thinking, R&D direction, memos, reviews, light analysis.
- DESK-100 (VS Code): Execution floor. Backtests, bulk data, EOD auto-capture, batch agent runs.
- Sync = `01_COMMAND_CENTER/` journal + state files. Both accounts read on start, write on end. No work is "done" until journaled.
