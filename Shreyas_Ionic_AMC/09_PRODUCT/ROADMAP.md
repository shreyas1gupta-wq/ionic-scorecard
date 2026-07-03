# Product Roadmap — Shreyas_Ionic_AMC
Owner: Tanvi Desai (E-026, Head of Product). Version: v0.1. Client: the Principal (today); the Principal's own retail account (future, gated).

Purpose: sequence the firm's PRODUCT surface — everything the Principal actually reads or touches — the same way any AMC would sequence investor-facing deliverables. This is packaging and UX, not investment decisions.

## Q3 2026 — ranked

| # | Product | What it is | Target | Depends on | Owner |
|---|---|---|---|---|---|
| 1 | Monthly Investor Letter #1 | Plain-language account of what the books did, honest edges, kills, next month's plan — bundled with the board pack | Jul-31 | Board-meet minutes, attribution (Neel Basu), STRATEGY_REGISTER kills | Tanvi Desai |
| 2 | Execution-sheet v2 | **DONE 2026-07-04.** One decision-ready view: conviction + sizing + gates together, no data dumps. Consumes `execution_scored.csv` (516 legs -> 258 trades, 3 decision blocks). Builder: `09_PRODUCT/execution_sheet_v2.py`; output: `08_Execution/EXECUTION_SHEET_V2.md` | Aug (shipped early) | `execution_scored.csv` (Quant/Trading Desk to produce), pre-trade-check gate fields | Tanvi Desai + Tara Singh |
| 3 | Firm dashboard v1 | Single lightweight HTML page: books, pipeline status, AP league, spend — built by Manoj Pillai to Tanvi's spec | Aug | Manoj Pillai (build), TEAM_ROSTER/WORK_LOG/IDEA_PIPELINE as data sources | Tanvi Desai (spec) / Manoj Pillai (build) |
| 4 | Strategy product-spec template | Template for packaging a sleeve once it reaches paper/DoD: minimum capital, expected drawdowns in plain language, operational run-steps for a retail investor | Aug-Sep | First sleeve to actually reach DoD (STRATEGY_REGISTER) | Tanvi Desai |
| 5 | [FUTURE, gated on Principal] Retail-account runbook | Step-by-step guide for running a validated sleeve on the Principal's own small account — the eventual "client" this whole roadmap serves | Not scheduled — opens only when Principal explicitly authorizes moving a strategy toward his own capital | Item 4 (product-spec template) must exist first; Principal gate | Tanvi Desai |

## Sequencing logic
- Items 1–2 are pure packaging of work other desks already produce — no new dependencies, ship first.
- Item 3 needs Manoj's build time; spec can start in parallel with 1–2.
- Item 4 is templating ahead of need — first real use waits on a sleeve actually reaching DoD.
- Item 5 is explicitly gated: do not start scoping until the Principal says so (D-025/Principal-only gate on anything touching his real capital path).

## Review cadence
Reviewed monthly alongside the board meeting (`/board-meet`); re-ranked whenever a new sleeve reaches paper/DoD or the Principal flags a usability gap.
