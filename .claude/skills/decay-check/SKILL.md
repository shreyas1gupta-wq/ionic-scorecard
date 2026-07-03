---
name: decay-check
description: Era-split decay analysis of a backtest/sleeve — stable, decaying, or regime-dependent (RP-16). Use for /decay-check <target>, monthly edge-decay cadence input.
---
# /decay-check — owner: Quant
1. RP-16: 3 equal eras + trailing 12m; edge per era with counts; breakpoints; honest FORWARD expectation (never the full-sample mean).
2. Feeds /edge-decay demotion decisions. S-04's build +0.31 → fwd +0.17 is the current template of a decaying verdict.
