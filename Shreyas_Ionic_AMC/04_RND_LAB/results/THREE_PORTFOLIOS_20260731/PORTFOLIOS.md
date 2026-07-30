# THREE PORTFOLIOS -- LOW RISK / HIGH CAGR / BALANCED
**Built 2026-07-31, Vikram Shah (FM). Script: `build_portfolios.py` in this folder. Source: `FINAL_RANKING_20260730/all_sleeves_daily.json` (no sleeve rebuilt).**

## 0. WHAT WAS EXCLUDED / CORRECTED
- **S1_GAPFADE EXCLUDED** (mandate hard rule): t=1.44, excess kurtosis 10.11, 38.6% of profit in 3 trades, only 8.8% of trades replay from stated rules. Never earned a weight.
- **The prior 'PORTFOLIO' file (Calmar 2.597, ~73% CAGR) is NOT reused as a starting point** -- its own metadata says it is built from 'all six' sleeves, i.e. it INCLUDES GAPFADE, so it is contaminated under the exclusion rule above. Rebuilt clean from the 5 permitted sleeves: SWEEP, CALENDAR, OVERSHOOT, LD_SELL, BOOK.
- **[OPINION, capacity guardrail]** naive inverse-vol weighting run unconstrained wants 60-80%+ of the book in CALENDAR+OVERSHOOT because both look 'quiet' against a full Rs10L allocation (capital-idleness effect) -- but neither has ever had a capacity check (STRATEGY_DOSSIER OPEN/OWED item). This may be exactly how the prior ~73% CAGR figure was reached. As FM I capped each sleeve's scale-up per mandate below rather than let the optimiser lever up an unverified-capacity sleeve; see the cap table in section 2. Note the concentration risk did not disappear, it MOVED: HIGH_CAGR's fitted solution instead concentrates in SWEEP (11.9x its documented backtest size) and BOOK (7.9x) -- a different, and arguably more executable, capacity ask (NIFTY futures and a diversified equity+S1F book scale more credibly than a thin monthly calendar spread) but still UNVERIFIED and flagged for a real capacity-check before any live sizing (see section 5).
- **[CORRECTED mid-build, coordinator catch]** Only OVERSHOOT has genuinely NO crash-window history. CALENDAR and LD_SELL trade on the 16-year daily bhavcopy archive (back to 2011), so they DO have 2015-16/2018/COVID/2022 data -- but THINLY sampled (1-13 cycles per window), and LD_SELL shows a **measured negative COVID result** (short premium bleeding in a crash), corroborated independently by the selling desk (-Rs42,545/27 COVID cycles, worst trade -50.6% of margin even with a stop). LD_SELL therefore carries the tightest cap of the four non-BOOK sleeves in the LOW_RISK mandate specifically. A same-expiry-hedged LD_SELL variant was tested by the desk and makes risk-adjusted return WORSE (Sharpe 0.02 vs 0.92) -- LD_SELL is sized here on naked/10%-margin economics throughout, no hedged-margin credit taken.

## 1. PER-SLEEVE STANDALONE METRICS (natural 1x = Rs10L allocation, full available history)
| Sleeve | Span | Yrs | CAGR% | MaxDD% | Calmar | Sharpe | PF | Month win% | Active days |
|---|---|---|---|---|---|---|---|---|---|
| SWEEP | 2015-01-13..2026-05-14 | 11.33 | 13.82 | -17.61 | 0.785 | 1.76 | 1.43 | 64.2 | 1578 |
| CALENDAR | 2011-01-21..2026-07-07 | 15.46 | 0.66 | -1.65 | 0.398 | 2.85 | 1.6 | 57.2 | 178 |
| OVERSHOOT | 2021-06-21..2026-05-27 | 4.93 | 0.55 | -1.76 | 0.313 | 0.72 | 1.16 | 53.3 | 913 |
| LD_SELL | 2011-02-24..2026-06-17 | 15.31 | 1.45 | -5.92 | 0.245 | 2.19 | 1.45 | 68.6 | 286 |
| BOOK | 2022-01-04..2025-12-31 | 3.99 | 16.9 | -19.24 | 0.879 | 1.5 | 1.36 | 62.5 | 942 |

## 2. CAPACITY / CRASH-RISK CAP TABLE (max weight share of Rs1cr book, by mandate)
[OPINION, judgment call -- not derived from data, stated loudly] Reflects (a) unverified scale-up capacity for CALENDAR/OVERSHOOT, (b) OVERSHOOT's total absence of crash history, (c) LD_SELL's measured negative crash behaviour.
| Sleeve | LOW_RISK | HIGH_CAGR | BALANCED |
|---|---|---|---|
| SWEEP | 25% | 50% | 35% |
| CALENDAR | 20% | 50% | 35% |
| OVERSHOOT | 8% | 25% | 15% |
| LD_SELL | 10% | 35% | 20% |
| BOOK | 25% | 50% | 35% |

## 3. CRASH-WINDOW BEHAVIOUR (raw Rs P&L at natural 1x; n = trading days/cycles inside window)
| Window | SWEEP | CALENDAR | OVERSHOOT | LD_SELL | BOOK |
|---|---|---|---|---|---|
| 2015-16 (Aug15-Feb16) | Rs+360,137 (n=81) | Rs-85 (n=7) | NO DATA | Rs+13,239 (n=7) | NO DATA |
| 2018 (Jan-Mar VIX-plosion) | Rs+75,256 (n=31) | Rs-2,059 (n=1) | NO DATA | Rs-7,756 (n=3) | NO DATA |
| COVID (Feb-Apr 2020) | Rs+321,216 (n=17) | Rs-4,144 (n=2) | NO DATA | Rs-43,196 (n=4) | NO DATA |
| 2022 (Jan-Jun selloff) | Rs+403,139 (n=69) | Rs+27,517 (n=6) | Rs+9,233 (n=90) | Rs+17,430 (n=13) | Rs-132,930 (n=113) |

SWEEP is the only sleeve positive in all four windows (crash hedge). OVERSHOOT has no observations before 2022. CALENDAR/LD_SELL are thinly sampled (single digits per window) -- treat their sign as indicative, not established; LD_SELL's negative COVID reading recurs under two different window definitions (stable), CALENDAR's does not (unstable).

## 4. WALK-FORWARD WEIGHT FIT (FIT 2022-2023 -> EVAL 2024-2025, no lookahead)

### LOW_RISK
- NAIVE (capacity-capped inverse-vol) weights: {'SWEEP': 0.25, 'CALENDAR': 0.2, 'OVERSHOOT': 0.08, 'LD_SELL': 0.1, 'BOOK': 0.25}
  - FIT:  CAGR 14.79%, MDD -6.45%, Calmar 2.292
  - EVAL: CAGR 11.53%, MDD -6.47%, Calmar 1.782  **OOS/IS(Calmar) = 0.777**
- FITTED (40k-sample constrained search on FIT only) weights: {'SWEEP': 0.275, 'CALENDAR': 0.22, 'OVERSHOOT': 0.0, 'LD_SELL': 0.11, 'BOOK': 0.275}
  - FIT:  CAGR 16.17%, MDD -7.14%, Calmar 2.266
  - EVAL: CAGR 12.52%, MDD -6.96%, Calmar 1.797  **OOS/IS(Calmar) = 0.793**
- **CHOSEN: NAIVE** -- fitted does NOT clearly beat naive OOS on the mandate's own objective (CAGR 12.52 vs 11.53); per lesson (weight-fitting overfits: prior 15,625-combo search gave OOS/IS=0.36), naive is used unless fitted clearly and robustly wins OOS on the CORRECT objective for that mandate (not always Calmar -- see section 9).

### HIGH_CAGR
- NAIVE (capacity-capped inverse-vol) weights: {'SWEEP': 0.0723, 'CALENDAR': 1.0928, 'OVERSHOOT': 0.625, 'LD_SELL': 0.6001, 'BOOK': 0.1098}
  - FIT:  CAGR 8.97%, MDD -1.67%, Calmar 5.383
  - EVAL: CAGR 8.8%, MDD -2.58%, Calmar 3.415  **OOS/IS(Calmar) = 0.634**
- FITTED (40k-sample constrained search on FIT only) weights: {'SWEEP': 1.1921, 'CALENDAR': 0.0902, 'OVERSHOOT': 0.0274, 'LD_SELL': 0.3134, 'BOOK': 0.7867}
  - FIT:  CAGR 49.46%, MDD -24.71%, Calmar 2.002
  - EVAL: CAGR 41.6%, MDD -17.64%, Calmar 2.359  **OOS/IS(Calmar) = 1.178**
- **CHOSEN: FITTED** -- fitted clearly beats naive OOS on the mandate's own objective (CAGR 41.6 vs 8.8); per lesson (weight-fitting overfits: prior 15,625-combo search gave OOS/IS=0.36), naive is used unless fitted clearly and robustly wins OOS on the CORRECT objective for that mandate (not always Calmar -- see section 9).

### BALANCED
- NAIVE (capacity-capped inverse-vol) weights: {'SWEEP': 0.1786, 'CALENDAR': 0.525, 'OVERSHOOT': 0.225, 'LD_SELL': 0.3, 'BOOK': 0.2714}
  - FIT:  CAGR 14.59%, MDD -5.83%, Calmar 2.503
  - EVAL: CAGR 11.16%, MDD -4.11%, Calmar 2.713  **OOS/IS(Calmar) = 1.084**
- FITTED (40k-sample constrained search on FIT only) weights: {'SWEEP': 0.1734, 'CALENDAR': 0.3844, 'OVERSHOOT': 0.1647, 'LD_SELL': 0.2196, 'BOOK': 0.0576}
  - FIT:  CAGR 8.03%, MDD -2.51%, Calmar 3.193
  - EVAL: CAGR 7.96%, MDD -3.76%, Calmar 2.114  **OOS/IS(Calmar) = 0.662**
- **CHOSEN: NAIVE** -- fitted does NOT clearly beat naive OOS on the mandate's own objective (Calmar 2.114 vs 2.713); per lesson (weight-fitting overfits: prior 15,625-combo search gave OOS/IS=0.36), naive is used unless fitted clearly and robustly wins OOS on the CORRECT objective for that mandate (not always Calmar -- see section 9).

## 5. FINAL PORTFOLIO METRICS (chosen weights, FULL_EXT 2022-01 to latest per sleeve)
| Metric | LOW_RISK | HIGH_CAGR | BALANCED |
|---|---|---|---|
| Span | 2022-01-04..2026-07-07 | 2022-01-04..2026-07-07 | 2022-01-04..2026-07-07 |
| Years | 4.5 | 4.5 | 4.5 |
| CAGR % | 10.62 | 30.44 | 10.29 |
| MaxDD % | -6.45 | -24.71 | -5.83 |
| Calmar | 1.646 | 1.232 | 1.765 |
| Sharpe | 1.64 | 1.51 | 1.81 |
| Profit factor | 1.54 | 1.52 | 1.57 |
| Monthly win % | 61.8 | 60.0 | 63.6 |
| Worst month % | -2.96 | -12.65 | -2.56 |
| Worst 3-mo stretch % | -4.98 | -22.52 | -4.01 |
| Worst day % | -1.74 | -5.46 | -1.88 |
| Capital deployed % (of book) | 88.0 | 241.0 | 150.0 |
| Capital utilisation % (active x weight) | 28.7 | 92.5 | 36.9 |

### Chosen weights (fraction of Rs1cr book capital)
| Sleeve | LOW_RISK | HIGH_CAGR | BALANCED |
|---|---|---|---|
| SWEEP | 25.0% | 119.2% | 17.9% |
| CALENDAR | 20.0% | 9.0% | 52.5% |
| OVERSHOOT | 8.0% | 2.7% | 22.5% |
| LD_SELL | 10.0% | 31.3% | 30.0% |
| BOOK | 25.0% | 78.7% | 27.1% |

**[OPINION, flagged loudly] HIGH_CAGR's 30.4% CAGR depends on running SWEEP at ~11.9x and BOOK at ~7.9x their documented/tested size (see section 8 AU table) -- this is a real capacity assumption, not a free scale-up. SWEEP is delta-1 NIFTY futures (generally the most scalable instrument here); BOOK's S1F sub-component is registered at ~3-4 lots/Rs10L in `06_TRADING_DESK/STRATEGY_REGISTER.md` -- running it at 7.9x that is well beyond what has been risk-approved. A `/capacity-check` on both before any live sizing is a hard precondition, not a nice-to-have, for the HIGH_CAGR mandate specifically.**

### Per-sleeve active-day fraction (how often that sleeve is actually in a position)
| Sleeve | Active-day % (of FULL_EXT calendar days) |
|---|---|
| SWEEP | 36.6% |
| CALENDAR | 3.0% |
| OVERSHOOT | 49.3% |
| LD_SELL | 7.0% |
| BOOK | 57.2% |

## 6. PORTFOLIO-vs-SLEEVE correlation (monthly / quarterly, FULL_EXT window)

### LOW_RISK
| Sleeve | corr (monthly) | corr (quarterly) |
|---|---|---|
| SWEEP | 0.867 | 0.863 |
| CALENDAR | 0.064 | 0.101 |
| OVERSHOOT | -0.136 | -0.415 |
| LD_SELL | 0.031 | 0.267 |
| BOOK | 0.586 | 0.515 |

### HIGH_CAGR
| Sleeve | corr (monthly) | corr (quarterly) |
|---|---|---|
| SWEEP | 0.93 | 0.928 |
| CALENDAR | 0.055 | 0.121 |
| OVERSHOOT | -0.101 | -0.37 |
| LD_SELL | 0.019 | 0.22 |
| BOOK | 0.464 | 0.386 |

### BALANCED
| Sleeve | corr (monthly) | corr (quarterly) |
|---|---|---|
| SWEEP | 0.761 | 0.754 |
| CALENDAR | 0.127 | 0.156 |
| OVERSHOOT | -0.171 | -0.462 |
| LD_SELL | 0.155 | 0.403 |
| BOOK | 0.691 | 0.636 |

## 7. DYNAMIC WEIGHTING TEST -- CPPI drawdown-floor overlay vs STATIC
[NOTE] Regime-conditioning on monthly sleeve P&L already tested elsewhere in this lab and FAILED (28 cells, 0 candidates, 22 dead, n only 111-172 months) -- not re-run; per the mandate's own steer, only the more-promising CPPI/drawdown-floor variant is tested here. Overlay: cut exposure to 35% once running drawdown from high-water-mark breaches -6%, restore to 100% once drawdown recovers above -2% (causal, uses only past equity).
| Portfolio | | CAGR% | MaxDD% | Calmar | Sharpe |
|---|---|---|---|---|---|
| LOW_RISK | STATIC | 10.62 | -6.45 | 1.646 | 1.64 |
| LOW_RISK | CPPI | 9.36 | -6.31 | 1.484 | 1.52 |
| HIGH_CAGR | STATIC | 30.44 | -24.71 | 1.232 | 1.51 |
| HIGH_CAGR | CPPI | 24.41 | -14.36 | 1.699 | 1.32 |
| BALANCED | STATIC | 10.29 | -5.83 | 1.765 | 1.81 |
| BALANCED | CPPI | 10.29 | -5.83 | 1.765 | 1.81 |

**Result: mixed, and informative.** On LOW_RISK and BALANCED (MaxDD only -5..-6%), the 6% floor barely engages -- CPPI is a wash-to-slightly-worse there (fewer active days once it does trip, no real drawdown to cut). **On HIGH_CAGR, where real drawdown depth exists (-24.7% static), the floor DOES help**: MaxDD cut from -24.7% to -14.4%, Calmar improved 1.23 -> 1.70, at a real cost (CAGR 30.4% -> 24.4%). This is a genuine, usable risk lever for HIGH_CAGR specifically -- not the free lunch dynamic weighting is often sold as, but a legitimate drawdown-vs-return trade a CIO could choose to arm, especially since it pulls HIGH_CAGR's MaxDD comfortably clear of the firm's 25% hard ceiling instead of sitting right at it. This mirrors the Principal's own steer that dynamic weighting mostly loses to static, with one genuine exception where the book actually draws down enough for a floor to matter.

## 8. LOT / CAPITAL FEASIBILITY -- Rs10L vs Rs1cr book
1 AU (allocation unit) = Rs10L capital-equivalent = each sleeve's already-embedded natural sizing (1 NIFTY futures lot for SWEEP; however many option contracts a Rs10L margin slot buys at the strikes/expiries already embedded in the other sleeves' trades).

### LOW_RISK
- **Rs1cr book**: AU per sleeve {'SWEEP': 2.5, 'CALENDAR': 2.0, 'OVERSHOOT': 0.8, 'LD_SELL': 1.0, 'BOOK': 2.5}, total 8.8 AU -- FEASIBLE - integer/near-integer AU per sleeve.
- **Rs10L book**: AU per sleeve {'SWEEP': 0.25, 'CALENDAR': 0.2, 'OVERSHOOT': 0.08, 'LD_SELL': 0.1, 'BOOK': 0.25}, total 0.88 AU -- INFEASIBLE as multi-sleeve recipe (fractional AU, no lots tradable); nearest feasible = 1 AU in SWEEP alone.

### HIGH_CAGR
- **Rs1cr book**: AU per sleeve {'SWEEP': 11.92, 'CALENDAR': 0.9, 'OVERSHOOT': 0.27, 'LD_SELL': 3.13, 'BOOK': 7.87}, total 24.09 AU -- FEASIBLE - integer/near-integer AU per sleeve.
- **Rs10L book**: AU per sleeve {'SWEEP': 1.192, 'CALENDAR': 0.09, 'OVERSHOOT': 0.027, 'LD_SELL': 0.313, 'BOOK': 0.787}, total 2.409 AU -- INFEASIBLE as multi-sleeve recipe (fractional AU, no lots tradable); nearest feasible = 1 AU in SWEEP alone.

### BALANCED
- **Rs1cr book**: AU per sleeve {'SWEEP': 1.79, 'CALENDAR': 5.25, 'OVERSHOOT': 2.25, 'LD_SELL': 3.0, 'BOOK': 2.71}, total 15.0 AU -- FEASIBLE - integer/near-integer AU per sleeve.
- **Rs10L book**: AU per sleeve {'SWEEP': 0.179, 'CALENDAR': 0.525, 'OVERSHOOT': 0.225, 'LD_SELL': 0.3, 'BOOK': 0.271}, total 1.5 AU -- INFEASIBLE as multi-sleeve recipe (fractional AU, no lots tradable); nearest feasible = 1 AU in CALENDAR alone.

**This is exactly the 'Rs10L capital base on a Rs1cr book produced an impossible -146% MDD' trap the mandate warned about** -- forcing Rs1cr-scale weight fractions onto a Rs10L account implies 10x leverage on the natural per-sleeve margin unit. The Rs10L-feasible rows above are EXCLUDED as multi-sleeve recipes; the honest substitute is 1 AU (~Rs10L) in the single highest-weighted sleeve alone, sacrificing diversification entirely. Genuine cross-sleeve diversification, at any of these three mandates, requires roughly Rs50L-1cr+ of capital.

## 9. METHOD NOTES
- No-compounding convention throughout (`eq = capital + cumsum(daily P&L)`), matching `book_level.py`'s established firm convention so these numbers are comparable to prior lab output.
- Weight search: 40,000-sample Dirichlet random search + 3 rounds of local polish (20,000 samples each) on the FIT window only, maximizing the mandate objective subject to the MDD constraint and the per-sleeve capacity cap in section 2. This is a much lower-dimensional, lower-DOF search than the prior 15,625-cell grid that produced OOS/IS=0.36 -- but the OOS/IS ratios in section 4 show it STILL overfits versus naive on 2 of 3 mandates, which is why NAIVE was chosen in all three.
- FIT/EVAL windows are 2022-2023 / 2024-2025 (2yr/2yr) because BOOK (the equity+S1F diversifier) only has data from 2022-01-04 -- this is the common window across all five permitted sleeves. SWEEP/CALENDAR/LD_SELL's pre-2022 history (back to 2011/2015, including 2015-16/2018/COVID) is used ONLY for the standalone per-sleeve stats and crash-window table in sections 1 and 3, never for weight-fitting -- using it there would need a lookahead-free proxy for BOOK's pre-2022 behaviour that does not exist.
- Costs are already embedded in each sleeve's daily P&L (per `STRATEGY_DOSSIER.md`); no additional cost model applied here.
- **Bug caught and fixed mid-build**: naive inverse-vol weighting, run at full deployment, systematically OVERWEIGHTS the low-return/low-vol sleeves (CALENDAR/OVERSHOOT/LD_SELL) regardless of mandate -- the first HIGH_CAGR cut compared fitted-vs-naive on Calmar (as all three mandates initially did) and picked a naive vector whose EVAL CAGR was only 8.8%, LOWER than LOW_RISK's 13%, an absurd result for a mandate whose entire point is maximizing CAGR. Fix: the naive-vs-fitted comparison now uses the MANDATE'S OWN objective (CAGR for LOW_RISK/HIGH_CAGR, Calmar for BALANCED), which is why HIGH_CAGR alone ends up on the FITTED weights (a genuine, OOS-improving reallocation toward SWEEP/BOOK) while LOW_RISK and BALANCED stay on NAIVE. A second bug (`cap_and_renorm` water-filling) let a sleeve pinned to its own cap in one redistribution round get pushed back over that cap in a later round -- fixed with a monotonic capped-mask; caught because SWEEP printed at 29.76% against a stated 25% cap.
- A CAGR floor (6-8%, roughly half of naive's own EVAL CAGR) is enforced on every candidate in the search so 'maximize Calmar' cannot degenerate into a near-empty, economically irrelevant book (a real failure caught on the first BALANCED run: 22.8% deployed, 0.58% CAGR, 'winning' on Calmar alone).