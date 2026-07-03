# openalgo scoped evaluation (D-M6) — eval only, NOT installed

**Repo:** github.com/marketcalls/openalgo · **Date:** 2026-07-04 · **Owner:** Manoj Pillai (Ops)

## Fact 1 — Angel adapter + options sandbox
Sandbox/"Analyzer" mode is platform-level (broker-agnostic, rides on any connected broker incl.
Angel): Rs.1 Cr sandbox capital, real margin calc (`FundManager.calculate_margin_required`),
MIS/NRML product types for F&O, auto square-off + T+1 simulation. Options ARE covered (CNC
explicitly unsupported for options; MIS/NRML are) — not an equity-only stub.
[docs.openalgo.in "07 - Sandbox Architecture (Analyzer Mode)"; creator's Medium post; OptionsOrder API page]

## Fact 2 — Windows footprint
Native install wants Python 3.10/3.11 + Node.js + Git; recommended Windows path is one Docker
container, SQLite by default (no DB server), 2GB shared memory for scipy/numba, one web port
(Flask/Gunicorn, default 5000). No Redis/Celery in the base install — but it IS a persistent
background web-server process, which we run zero of today.
[INSTALL.md; docs.openalgo.in Docker Development + Docker+Custom Domain pages]

## Fact 3 — Order-flow / logging
openalgo owns its own pipeline: webhook-driven Strategy module, its own order queue + rate
limits, its own order/trade/position-book tables, an internal event bus for logging. PAPER_LEDGER
could sit outside it (call sandbox/margin only via REST, no migration) but if we ever want ITS
order book as source of truth we inherit its schema, not ours — coexistence, not a clean bolt-on.
[docs.openalgo.in Strategy Management page]

## Verdict: PILOT-ONE-STRATEGY

Deciding facts: (1) options margin sim is real, not a stub; (2) footprint is one container +
SQLite, tolerable on a laptop, but adds our first persistent background service; (3) it brings
its own order/webhook pipeline our PAPER_LEDGER must sit beside via REST rather than feed
directly. Pilot on ONE low-stakes sleeve (S-05 Track-1 straddle paper track), calling only
openalgo's margin/sandbox API, PAPER_LEDGER staying system-of-record — validate margin-sim
accuracy for one month before considering wider adoption.
