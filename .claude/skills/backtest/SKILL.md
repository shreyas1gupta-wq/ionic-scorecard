---
name: backtest
description: Gate-4 full backtest — spec first, guards imported, validation battery, results engineering. Use for /backtest <idea>, "full backtest this".
---
# /backtest — gate 4 (RESEARCH_SOP)
1. Spec BEFORE code (RP-03): universe, PIT joins, signal, sizing, costs per COST_STANDARDS, walk-forward windows, every free parameter justified (≤5).
2. Code with `import guards as G` from `04_RND_LAB/lib/`; run; results to `results/<strategy>/<run_id>/` (config.json w/ data snapshot, metrics.json, trades.csv, equity.png) — never overwrite a run dir.
3. Validation battery: walk-forward, plateau, DSR (honest family trials), PBO, regime slices, degenerate detectors (G.degenerate_flags).
4. Auto-advance on pass → /red-team next (gate 5). Fail → KILLED_IDEAS + resurrection condition. Journal one line. DESK-100 work by default (heavy).
