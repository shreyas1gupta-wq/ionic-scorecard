---
name: structure-trade
description: Pick the best options VEHICLE for a validated edge — structure, strikes, expiry, margin, liquidity honesty. Use for /structure-trade <signal/strategy> at gate-6 or before paper entries.
---
# /structure-trade — owner: Aakash Jain (structurer-aakash-jain)
1. Spawn Aakash with the signal + registered edge + universe.
2. He returns 2-3 candidate structures: legs/strikes/expiry, SPAN margin, max-loss, liquidity check (far-OTM single-stock = auto-reject), cost stack; recommendation + why others lose.
3. Composes with /pre-trade-check (risk) + Tara (fills). Verdict filed with the strategy's register row.
