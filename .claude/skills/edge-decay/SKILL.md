---
name: edge-decay
description: Monthly sleeve re-score — recompute recent per-trade edge vs registered edge for every STRATEGY_REGISTER row, auto-demote on 2 consecutive fails. Use for /edge-decay, "re-score the sleeves", "is any strategy decaying", or the monthly RESEARCH_SOP cadence trigger.
---

# /edge-decay — monthly sleeve re-score (RESEARCH_SOP §operating cadence)

1. Read `Shreyas_Ionic_AMC/06_TRADING_DESK/STRATEGY_REGISTER.md` (every row: registered per-trade edge, kill criteria, review cadence) and `PAPER_LEDGER.md` / live fills for trades since the last review.
2. For each row: recompute recent per-trade edge (same metric/window convention as registered) from actual trades since last review; compare vs the registered edge and vs the row's kill criteria threshold.
3. Verdict per row: HOLD (within tolerance) / WATCH (first fail) / DEMOTE (2 consecutive monthly fails vs kill criteria → auto per RISK_LIMITS escalation rule). DEMOTE = flip STRATEGY_REGISTER stage to paper-only + one journal line + AP event (missed edge caught = self-catch, log per TEAM_ROSTER scoring).
4. Ambiguous verdict (edge borderline, regime-slice question, correlated-sleeve confound) → spawn `quant-head-arjun-rao` to rule; otherwise stay cheap tier (mechanical arithmetic).
5. Output a decay table: Strategy ID | registered edge | recent edge | delta | consecutive fails | verdict. File the verdict in STRATEGY_REGISTER + journal; do not touch RISK_LIMITS/COST_STANDARDS (Principal-only amendments).
