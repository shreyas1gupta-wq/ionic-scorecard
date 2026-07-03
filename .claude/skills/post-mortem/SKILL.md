---
name: post-mortem
description: Decompose a paper/live-vs-sim divergence or a big unexpected loss into causes and ONE fix. Use for /post-mortem <trade|week>, after any trade >2x modeled worst-case, or when paper diverges from sim.
---
# /post-mortem — RP-08
1. Pull the trade(s) from PAPER_LEDGER + the sim expectation from the strategy's results run.
2. Spawn `execution-tca-tara-singh`: decompose the gap → slippage / fill-rate / timing / signal-decay, with numbers.
3. Propose ONE fix. If costs were optimistic → draft COST_STANDARDS amendment (Principal approves). If signal decayed → flag edge-decay review. Log in PAPER_LEDGER reconciliation + journal. RISK_LIMITS escalation rule applies (>2x worst-case = mandatory).
