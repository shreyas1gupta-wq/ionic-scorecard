# S1-F DSR baseline + trials ledger (Phase-0 #9, 2026-07-11)

```
S1-F daily series: T=259, SR_hat(per expiry)=0.243 (~1.75 annualized at 52 exp/yr), skew=-0.00, kurt=4.2
Total trials on ledger: 229 (upper bound for N); sell-side family only: ~157

DSR grid (prob. the edge is real after deflating for the search):
  N trials       V[SR] assumption      DSR
        50         tight (SR^2/4)   0.2990
        50            wide (SR^2)   0.0000
       157         tight (SR^2/4)   0.0954
       157            wide (SR^2)   0.0000
       229         tight (SR^2/4)   0.0612
       229            wide (SR^2)   0.0000

Reading: DSR > 0.95 = edge survives deflation at that assumption. V[SR] (cross-trial SR variance)
is UNKNOWN for historical cells (not individually recorded) - hence the declared grid, not one number.
From now on RUN_CARDs record per-trial stats so V[SR] becomes measurable. Sameer to refine at Gate-4.
```

## Interpretation (CIO/Sameer read this before quoting the grid)
1. **The grid treats all trials as INDEPENDENT draws aimed at one target — that overstates deflation.** The 84-cell sensitivity surface is highly correlated neighboring parameters (~5-10 effective independent trials, not 84); buying/momentum/PEAD campaigns were different hypothesis families on different constructions. Effective-N for the S1 discovery is plausibly ~20-40, not 157-229. Cross-check: naive Bonferroni on the headline p~1e-4 x 157 ~ 0.016 — still under 0.05.
2. **Verdict: AMBER, not red.** Under strict independence the in-sample edge does not survive deflation; under effective-N it plausibly does. In-sample statistics CANNOT settle this after this much search — which is exactly why S1-F is in a pre-registered paper forward test with frozen kill bars. The forward test is the only exit from this ambiguity. No amount of further in-sample analysis changes it.
3. **Binding discipline consequence:** every additional sell-side variant tested on the SAME 2021-26 sample deflates S1-F further. The sample is close to spent. New research must target NEW data (forward paper data, the 2011-21 backfill era, other streams/instruments — e.g., B1b runs on a different dataset family entirely).
4. Sameer's Gate-4 refinement: compute effective-N via trial-correlation clustering (RUN_CARDs now record per-trial stats so V[SR] becomes measurable going forward), and re-run this DSR with measured inputs instead of the assumption grid.
