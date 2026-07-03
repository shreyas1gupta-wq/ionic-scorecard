---
name: fill-audit
description: Audit a backtest's fill assumptions against bar ranges/volumes — optimistic-fill bias in bps (RP-39). Use for /fill-audit <backtest> at gate-4/5.
---
# /fill-audit — owner: Tara Singh
1. RP-39: 10 random trades vs actual bar ranges + volumes; limit-at-touch and market-at-mid assumptions exposed; bias in bps; does it flip the verdict?
2. Attach to the run dir; feeds Red Team's cost-fiction attack surface.
