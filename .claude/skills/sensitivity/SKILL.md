---
name: sensitivity
description: Gate-4 overfit & sensitivity battery — parameter surfaces, perturbation, subsample stability, DSR/PBO (owner: Dr. Sameer Bhat). Use for /sensitivity <strategy>, mandatory before any certification/IC.
---
# /sensitivity — owner: overfit-analyst-sameer-bhat
1. Spawn Sameer with the strategy's data + results dir + family trials count (from IDEA_PIPELINE/oos-audit).
2. He runs: param surface (±20-50%/param, plateau verdict) · perturbation (entry jitter, cost ±50%, universe drop-10%) · subsample halves/thirds · bootstrap CI · DSR/PBO (purgedcv).
3. Verdict ROBUST/FRAGILE-AT/OVERFIT filed to 07_RISK_OFFICE/SENSITIVITY_REPORTS/<strategy>_<date>.md; Gate-4 cannot pass without it; feeds /ic-memo evidence pack.
