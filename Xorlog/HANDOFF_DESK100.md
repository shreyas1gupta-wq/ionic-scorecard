# XORLOG — HANDOFF TO DESK-100 (execution floor)
From: DESK-20 session 2026-07-16 (research + plan complete). Read order: this file → PROGRESS.md → 00_VISION_AND_PLAN.md → 02_FEATURE_BACKLOG.md (skim 01_RESEARCH/ per task).

## Standing rules for ALL Xorlog work (non-negotiable)
1. Regulatory line (plan §3): NOTHING Xorlog-authored may emit a buy/sell/hold on a named security. No performance promises. Pre-RA phase.
2. Max 3 parallel agents (D-023). Scripts-first; agents return conclusions only. Bank every step to disk immediately; update PROGRESS.md after each task step.
3. Data landmines from root CLAUDE.md apply fully (HF timezone, pre-open auction, PIT earnings, T1-T10 lookahead, fill realism).
4. NOTHING gets deployed/published/posted externally — build locally; Principal deploys and posts himself.
5. Epistemic conduct (D-035): estimates labeled, verify before claiming done.
6. Session end: update Xorlog/PROGRESS.md + firm SESSION_JOURNAL.md + CURRENT_STATE.md.

## Task queue (execute in order; each is resumable; outputs under Xorlog/03_BUILD/)

### T1 — Honest-data artifact #1: the survivorship-bias study (Phase-0 distribution asset)
Goal: quantify, on OUR data, how much a simple backtest lies when run on today's NIFTY500 constituents vs the PIT universe (`NIFTY500_TICKER_2005_2025_Final.xlsx`, 42 snapshots).
- Script computes: (a) equal-weight buy-and-hold and (b) a simple 12-1 momentum sort, both ways (current-constituents vs PIT), 2010-2025, with costs from COST_STANDARDS assumptions labeled DRAFT. Deltas in CAGR/Sharpe/DD.
- Output: `03_BUILD/artifact1_survivorship/` — results.csv, 2 charts (PNG), METHODOLOGY.md, and a ~600-word informational draft post (teach-the-concept style per Brand-Desk informational rule; NO stock names in conclusions, factor/universe level only).
- Landmines: lookahead audit pass required (lib/lookahead_audit.py); pre-open/timezone fixes.
- This doubles as Phase-0 content AND the public "honesty benchmark" methodology seed.

### T2 — Journal MVP core: Angel SmartAPI trade-import prototype (Phase-1 product spine)
Goal: CLI proof (no UI): fetch tradebook/orderbook via SmartAPI (creds: data-only account, existing capture-task code patterns; ≥1.2s/req, AB1021 retry), normalize to a canonical trade schema (parquet/JSON): instrument, side, qty, price, timestamps, charges; F&O: leg-level with strike/expiry/right; then GROUP multi-leg option strategies (same underlying+expiry+entry window → spread/strangle/straddle detection).
- Output: `03_BUILD/journal_import/` — schema.md, import script, grouping script, sample anonymized output, LIMITS.md (what SmartAPI can't give us — e.g., historical depth — and the contract-note-parser fallback per backlog A2).
- Compute per-trade analytics stubs: realized P&L incl. charges, holding time, MFE/MAE placeholders (needs price join to our 1-min data — note join keys).

### T3 — Landing page + waitlist (build only, Principal deploys)
Goal: static site (Next.js or plain HTML+Tailwind) per plan §6/§7: hero = one-line thesis, 3 wedges, waitlist email capture (Supabase table or a simple serverless-ready form stub), FAQ with the honest-positioning ("not a broker, not advice — tools").
- Copy tone: teach-first, zero hype, no return claims. Use shadcn/ui if Next.
- Output: `03_BUILD/landing/` runnable locally (`npm run dev`), README with Cloudflare Pages deploy steps FOR PRINCIPAL. Do not deploy.

### T4 — Screener data layer (Phase-1 prep)
Goal: DuckDB views over the existing parquet lake: daily prices (survivorship-aware via PIT membership), fundamentals (`datasets/earnings_pit/unified_quarterly_pit.parquet`, respect available_date), corporate-actions honesty check (splits/bonus adjustment status — VERIFY, don't assume), and 10 benchmark screener queries (<500ms each target).
- Output: `03_BUILD/data_layer/` — build_views.py, QUERIES.md with timings, DATA_GAPS.md (what the lake is missing for a retail screener, e.g., live quotes, shareholding patterns).

### T5 (stretch) — Backlog triage
Score 02_FEATURE_BACKLOG.md §A items on impact×effort×regulatory-risk (1-5 each); propose the Phase-1 cut list. Output: `03_BUILD/backlog_triage.md`. No new features — triage only.

## Paste-ready prompt for DESK-100 (Principal: copy the block below)
```
XORLOG continuation (handoff from DESK-20, 2026-07-16). New venture, folder Xorlog/ at repo root — NOT an AMC workstream, but firm rules apply.
Read in order, then execute: Xorlog/HANDOFF_DESK100.md (the task queue T1→T5 with full specs), Xorlog/PROGRESS.md, Xorlog/00_VISION_AND_PLAN.md.
Work the queue strictly in order T1→T2→T3→T4 (T5 stretch). One task at a time, bank outputs to Xorlog/03_BUILD/<task>/ continuously, update PROGRESS.md after every step so a token cut loses nothing. Max 3 parallel agents, scripts-first, all root-CLAUDE.md data landmines apply, lookahead audit on T1 before any number is quoted. Build only — deploy/publish NOTHING external; flag anything needing my decision in PROGRESS.md §OPEN instead of stopping. Session end: journal + CURRENT_STATE per protocol.
```
