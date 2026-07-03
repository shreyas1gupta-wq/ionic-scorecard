---
name: capacity-check
description: Estimate a strategy's capacity — ADV participation, impact, edge-vs-size curve (RP-14). Use for /capacity-check <strategy> at gate-4/6 or before any size increase.
---
# /capacity-check — owner: Quant + Tara
1. Spawn quant-head-arjun-rao (or run main-loop if trivial): RP-14 on the strategy's instruments — ADVs, participation caps (10%/5% micro), impact estimate, the size at which edge halves.
2. Verdict vs intended book size; file with the register row. Composes with /structure-trade.
