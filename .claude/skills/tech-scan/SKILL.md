---
name: tech-scan
description: Minervini trend-template scan over a universe — stages, pivots, VCP, RS ranks. Use for /tech-scan <universe|watchlist>, "which names pass the trend template".
---
# /tech-scan — technical desk (RP-10)
1. Spawn `technical-head-dhruv-kapoor`. Data: daily prices (mind CATALOG staleness note) + 42 PIT snapshots for the universe.
2. Apply ALL 9 template criteria (ANALYST_CHECKLISTS §Minervini) — no partial passes. RS percentile vs Nifty-500.
3. Return ONLY passing names: stage, pivot, stop, risk-per-share, VCP note. Feed Track-2 watchlist (`swing_momentum/FORWARD_WATCHLIST.md`).
