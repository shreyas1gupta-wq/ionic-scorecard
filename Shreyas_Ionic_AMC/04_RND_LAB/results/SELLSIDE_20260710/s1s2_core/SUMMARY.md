# S1/S2 sell-side core results (frozen bars in script docstring; NO COVID in sample)

S1 09:20/30: n=259 net=+8.02 stress=+1.73 pts | t=2.94 PF=1.56 win=69% | maxDD=-231 conc=3% | era21-23=+5.35 era24-26=+10.92 | ROM/trade=+0.50% | electionday=nan | worst5={'2026-03-30': -102.0, '2025-02-13': -101.4, '2024-08-08': -94.1, '2024-12-05': -86.5, '2026-03-24': -84.9} | **PASS**

S1 09:20/50: n=259 net=+7.02 stress=+0.90 pts | t=2.22 PF=1.48 win=68% | maxDD=-323 conc=3% | era21-23=+5.21 era24-26=+8.99 | ROM/trade=+0.44% | electionday=nan | worst5={'2026-03-24': -148.0, '2026-03-30': -139.2, '2024-12-05': -137.6, '2025-02-13': -130.2, '2025-05-15': -107.4} | **PASS**

S1 09:20/none: n=259 net=-2.63 stress=-8.63 pts | t=-0.46 PF=0.92 win=56% | maxDD=-1621 conc=nan% | era21-23=-6.88 era24-26=+2.00 | ROM/trade=-0.16% | electionday=nan | worst5={'2025-04-17': -413.0, '2022-06-16': -384.0, '2025-05-15': -312.4, '2024-09-12': -291.1, '2022-02-24': -247.6} | **KILL**

S1 10:00/30: n=259 net=+4.88 stress=+0.88 pts | t=2.09 PF=1.37 win=68% | maxDD=-363 conc=2% | era21-23=+7.19 era24-26=+2.36 | ROM/trade=+0.30% | electionday=nan | worst5={'2024-12-05': -124.6, '2026-03-24': -109.4, '2022-05-26': -107.0, '2024-08-29': -94.4, '2024-08-08': -88.4} | **PASS**

S1 10:00/50: n=259 net=+6.19 stress=+2.19 pts | t=2.44 PF=1.50 win=70% | maxDD=-279 conc=2% | era21-23=+4.53 era24-26=+7.99 | ROM/trade=+0.39% | electionday=nan | worst5={'2026-03-24': -158.4, '2026-03-17': -120.9, '2024-08-29': -114.2, '2022-02-24': -106.9, '2022-05-26': -103.3} | **PASS**

S1 10:00/none: n=259 net=+3.09 stress=-0.91 pts | t=0.63 PF=1.11 win=57% | maxDD=-981 conc=2% | era21-23=+0.69 era24-26=+5.70 | ROM/trade=+0.19% | electionday=nan | worst5={'2025-04-17': -372.6, '2025-05-15': -345.3, '2022-06-16': -337.3, '2024-09-12': -274.1, '2024-11-28': -252.5} | **KILL**

S1 PRIMARY weekday split:
            mean  count
w                      
Monday     11.85      3
Thursday    6.72    213
Tuesday     9.02     34
Wednesday  33.56      9

S2 biweekly/hold: n=206 net=+0.18 stress=-3.82 pts | t=0.01 PF=1.00 win=69% | maxDD=-2374 conc=1% | era21-23=-15.27 era24-26=+25.02 | ROM/trade=+0.01% | electionday=nan | worst5={'2023-11-28': -732.4, '2025-04-07': -708.9, '2022-01-17': -633.8, '2024-09-30': -559.3, '2023-10-16': -526.2} | **KILL**

S2 weekly/hold: n=244 net=+7.03 stress=+3.03 pts | t=0.67 PF=1.11 win=67% | maxDD=-2350 conc=1% | era21-23=+4.17 era24-26=+10.13 | ROM/trade=+0.44% | electionday=nan | worst5={'2024-09-27': -654.5, '2024-05-03': -549.6, '2022-06-10': -494.8, '2023-10-20': -483.7, '2025-04-11': -467.6} | **KILL**

S2 weekly/stop3x: n=244 net=+5.73 stress=+1.73 pts | t=0.62 PF=1.10 win=60% | maxDD=-1456 conc=1% | era21-23=+6.76 era24-26=+4.62 | ROM/trade=+0.36% | electionday=nan | worst5={'2025-04-03': -654.6, '2025-04-11': -466.4, '2024-08-02': -409.4, '2025-05-09': -393.2, '2026-03-11': -383.6} | **KILL**

S2 weekly/tp50: n=244 net=+1.70 stress=-2.30 pts | t=0.18 PF=1.03 win=75% | maxDD=-2888 conc=1% | era21-23=+3.61 era24-26=-0.38 | ROM/trade=+0.11% | electionday=nan | worst5={'2024-09-27': -654.5, '2024-05-03': -549.6, '2022-06-10': -494.8, '2023-10-20': -483.7, '2025-04-11': -467.6} | **KILL**

## VERDICT NOTES (2026-07-10)
S1 PRIMARY (09:20 entry, 30% per-leg SL) = **FIRST PASS of the campaign**: pre-registered primary cell, not cherry-picked; survives stress costs (+1.73); both eras positive and strengthening; concentration 3%. SL grid confirms the SL IS the edge-preserver (no-SL cell = KILL, worst days -413/-384). S2 weekly strangle: positive expectancy but t<=0.67 -> KILL on significance; tails (-650pt cycles) eat it.
Trials ledger: +9 cells. NO COVID IN SAMPLE. Next gate: Gate-4 (sensitivity/overfit/red-team/lookahead + tick-granularity SL check) before any register entry.
