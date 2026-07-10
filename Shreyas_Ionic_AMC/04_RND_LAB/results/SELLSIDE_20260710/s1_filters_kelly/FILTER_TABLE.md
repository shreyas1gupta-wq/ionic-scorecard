# S1 exploratory filter terciles (in-sample - adopt nothing without re-test)
pcr (n=222): | low: n=74 net=+4.56 t=0.95 | mid: n=74 net=+14.63 t=3.08 | high: n=74 net=+6.11 t=1.31 | high-low=+1.55 t=0.23
prior_ret (n=259): | low: n=87 net=+4.40 t=0.94 | mid: n=86 net=+7.59 t=1.91 | high: n=86 net=+12.11 t=2.23 | high-low=+7.71 t=1.08
gap (n=259): | low: n=87 net=+11.01 t=2.17 | mid: n=86 net=+6.34 t=1.39 | high: n=86 net=+6.67 t=1.48 | high-low=-4.34 t=-0.64
r5rng (n=259): | low: n=87 net=+5.24 t=1.39 | mid: n=86 net=+6.33 t=1.43 | high: n=86 net=+12.51 t=2.17 | high-low=+7.27 t=1.05
trend920 (n=259): | low: n=87 net=+13.08 t=2.56 | mid: n=86 net=+6.57 t=1.33 | high: n=86 net=+4.35 t=1.08 | high-low=-8.73 t=-1.34

## PRINCIPAL VETO RULES (2026-07-10, exploratory, old-cost-model basis +8.02)
- PCR 0.7-1.3 band: HURTS (-2.04; vetoed days earned +11.06)
- RSI(D-1) 90/10: never fires in 5 yrs (0 days) - inert rule
- RSI(D-1) 80/20: +0.35 (only 4 veto days at -14.45 avg; n too small to trust)
- RSI(D-1) 70/30: +0.89
- Skip LOW-premium proxy days (RV3 bottom decile): +1.14 (vetoed days -1.79 = "no cushion" intuition is real)
- Skip HIGH-premium days: +0.10 (rich days pay fine)
- Skip BOTH RV3 extremes: +1.38, t 3.31 (best; candidate forward-test FLAG only)
- Skip high open-vol decile: HURTS (-1.28; those mornings earned +19.45)
VERDICT: no adoption; big-premium "scary" days are where selling pays. Ledger +8.
