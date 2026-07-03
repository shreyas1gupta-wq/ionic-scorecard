# openalgo scoped evaluation (D-M6) — eval only, NOT installed

**Repo:** github.com/marketcalls/openalgo · **Date:** 2026-07-04 · **Owner:** Manoj Pillai (Ops)
**Scope:** eval only per task order — nothing installed into the firm stack.

## Fact 1 — Angel adapter + options sandbox
Sandbox/"Analyzer" mode is a platform-level layer (not per-broker): ₹1 Cr sandbox capital, real
margin calc via a `FundManager.calculate_margin_required`, MIS vs NRML product types for F&O,
auto square-off + T+1 settlement simulation. Options ARE covered (not equity-only) — CNC is
explicitly *not* supported for options, MIS/NRML are. Angel One's own doc page covers only
broker auth (TOTP/API key), not sandbox specifics, but sandbox is broker-agnostic so it rides on
top of any connected broker including Angel.
[DATA, sourced: docs.openalgo.in "07 - Sandbox Architecture (Analyzer Mode)"; Rajandran R (creator)
Medium post "Understanding OpenAlgo Sandbox Mode"; docs.openalgo.in OptionsOrder API page]

## Fact 2 — Windows deployment footprint
Native path wants Python 3.10/3.11, Node.js (CSS build), Git; standard prod deploy is
Linux+Nginx+Gunicorn(eventlet). Docker path (recommended for a Windows desktop) runs one
container, SQLite by default (`sqlite:///db/openalgo.db`), no separate DB server, but needs
2GB shared memory reserved for scipy/numba and binds a web UI port (Flask/Gunicorn, default
5000). No Redis/Celery/queue mentioned for the base install. Moving parts: 1 container + SQLite
file — closer to "one more service" than "new stack", but it IS a persistent background web
server process, which today we have zero of. [DATA, sourced: INSTALL.md; docs.openalgo.in Docker
Development + Docker+Custom Domain pages]

## Fact 3 — Order-flow / logging architecture
openalgo owns its own strategy/order pipeline: webhook-driven Strategy module, its own order
queue + rate limiting (100/min webhook, 200/min strategy), its own order/trade/position book
tables, an internal event bus for order side-effects (notifications/logging). Our PAPER_LEDGER
discipline would either (a) sit outside it entirely, treating openalgo purely as a sandboxed
execution/margin backend called via its REST API — feasible, no forced migration — or (b) if we
want its order book as source of truth, we inherit ITS schema, not ours. Woven-in coexistence,
not a clean bolt-on. [DATA, sourced: docs.openalgo.in Strategy Management page]

## Verdict: PILOT-ONE-STRATEGY

Three facts that decide it: (1) options margin sim is real, not a stub — worth having; (2)
footprint is one Docker container + SQLite, not a multi-service buildout — tolerable on a
laptop; (3) but it brings its own order/webhook pipeline that our PAPER_LEDGER would have to
sit beside (via REST) rather than feed directly, so full adoption changes our signal-logging
flow more than "boring reliability" wants on day one. Pilot it on ONE low-stakes sleeve (e.g.
S-05 Track-1 straddle paper track) calling openalgo's margin/sandbox API only, PAPER_LEDGER
staying the system of record — validate margin-sim accuracy against our own numbers for one
month before considering it for S-01/wider adoption.
