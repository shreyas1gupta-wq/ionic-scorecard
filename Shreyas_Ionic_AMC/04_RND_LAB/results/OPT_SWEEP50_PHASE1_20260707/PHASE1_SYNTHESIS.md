# CAMPAIGN OPT-SWEEP-50 — Phase-1 synthesis (closed 2026-07-07)
Closed early by org monthly API spend limit: 13/25 groups (26/49 setups) completed; 12 groups (23 setups)
did not finish and are marked INCOMPLETE below, not killed. Do not treat an incomplete setup as a negative
result. Resume via the same group prompts in `20260707_nifty_option_sweep_50.md` section 3 if/when budget allows.

## Bottom line
**Nothing tested — across this 50-setup sweep, the 4 Principal-specified concrete tests (Arjun's separate
track), or the literature (Lakshmi's scan) — clears Sharpe>2 / XIRR>50% post-cost.** Best honest annualized
Sharpe seen anywhere in the firm's data is ~1.0. This matches Lakshmi's literature verdict: realistic net
Sharpe for index option-selling caps out ~0.9-1.2; XIRR>50% sustained is not documented anywhere credible.

## Completed verdicts (13 groups / 26 setups)
| Setup | Verdict | Ann. Sharpe | Edge (Rs-pts / %spot) | Note |
|---|---|---|---|---|
| OS-01 weekly strangle (baseline) | reference | ~0.8-1.0 | +7.68 / +0.043% | the VRP benchmark everything else must beat |
| OS-03 monthly strangle (baseline) | UNFILLABLE | - | - | 0/62 cycles have real 12-15delta strikes at 30DTE in this dataset |
| OS-04 VIX-gated strangle | SURVIVE-fragile | 0.67 | +14.4 / +0.070% | uplift concentrated in >80th VIX pctile, eff. N=47 |
| OS-05 inverse-IV sizing | KILL | - | = baseline by construction | fails risk-adjusted vs OS-01, worsens tail |
| OS-06 delta-hedged strangle | KILL | -0.05 | -4.98 / -0.020% | hedging realizes negative gamma P&L |
| OS-08 0DTE straddle | KILL | 0.69 | +6.69 / +0.030% | lost money 2022 & 2023; worst day -2.0sigma |
| OS-09 0DTE strangle | KILL | 1.72 | +3.68 / +0.017% | textbook tail-seller, -4.8sigma day, stop gapped through |
| OS-15 0DTE IC regime-gated | KILL | - | - | honest IV-crush detector built; gated worse than ungated; K-005 stays killed |
| OS-19 term-structure vega-neutral | DATA-BLOCKED | - | - | ~30DTE back leg missing in 61.6% of cycles; route to Aakash |
| OS-20 short put after down-day | SURVIVE-marginal | 0.37 | +24.85 / +0.127% | positive both regimes, 5/6 yrs; negative skew |
| OS-21 short call after up-day | KILL | 0.08 | +4.00 / +0.025% | edge only in pre-2022 up-grind, negative post-Sept-2025 |
| OS-22 covered call overlay | KILL-as-overlay | - | - | fill-starved + economically negative (BXM drag) |
| OS-23 collar overlay | KILL-as-overlay | - | - | 0/59 fills, larger drag than OS-22 |
| OS-26 bear-call spread, regime-gated | SURVIVE-fragile | ~1.0 | +12.48 / +0.062% | only 34 trades/5yr, beats unconditional (K-006 test passes) |
| OS-27 put ratio spread | KILL | - | - | regime-only edge, -73% under realistic fill |
| OS-29 jade lizard | KILL | 0.46 | +8.1 / +0.038% | W/L 0.325 degenerate flag; fails post-Sept-2025 |
| OS-32 pre-event straddle | KILL-CONFIRMED | - | - | = S-02 ported to index; event increment insignificant |
| OS-33 post-event vol-reset | KILL-non-distinct | - | - | statistically identical to generic weekly strangle |
| OS-34 turn-of-month strangle | KILL | - | - | pre-break negative selection; 47% no-fill drop |
| OS-35 0DTE expiry pin | SURVIVE-marginal, do-not-advance | insig. (t=1.21) | +17.33 / +0.066% (post-regime only) | tail barely sampled, 3 steamroller days already |
| OS-36 results-cluster strangle | KILL | - | +15.52 / worse than parent +16.76 | zero incremental over existing VRP book |
| OS-38 VIX-sizing overlay | KILL | - | - | fails A.19 vs both parents |
| OS-44 gamma scalping | KILL | -0.71 | -18.83 / -0.097% | gross negative before costs = confirms VRP |
| OS-47 conversion/parity arb | KILL | - | - | no futures for synthetic leg; spread swamps gross edge |
| OS-48 dispersion | KILL | - | - | NOT blocked by exitability wall (only 2.6% dead legs) but no bid/ask + margin/tail |
| OS-49 trend debit spread | KILL | -0.90 | -18.38 / -0.071% | negative both regimes |
| OS-50 momentum breakout buying | KILL | - | -33.7 / -0.120% | negative pre-Sept-2025 too, not a regime artifact |
| OS-43 ORB buying | EXCLUDED | - | - | flat duplicate of killed K-001, not run |

Plus Arjun's 4 Principal-specified concrete tests (separate track, 6 variants — 30m z-score mean-reversion x2 EMA
lookbacks, RSI(5) extreme x2 position types x2 entry styles): 5 of 6 KILL, 1 MARGINAL-hold (30m z-score vs
EMA200, naked short-vol degenerate flag, do not escalate). Full detail: `../MEANREV_RSI_CAMPAIGN_20260707/REPORT.md`.

## Incomplete (12 groups / 23 setups — NOT killed, just not run to completion)
OS-02, OS-07, OS-10, OS-11, OS-12, OS-13, OS-14, OS-16, OS-17, OS-18, OS-24, OS-25, OS-28, OS-30, OS-31,
OS-37, OS-39, OS-40, OS-41, OS-42, OS-45, OS-46. (OS-01 baseline itself also needs a final clean re-run —
the corrected engine was mid-fix when it was cut off.)

## Side-finding, independent of the spend limit (flag to Kavya / Data Officer)
Five separate agents (working on OS-03, OS-10, OS-12, OS-16, OS-17/18) independently hit the same wall:
**the cataloged NIFTY HF options dataset has broken/sparse coverage for ~30-DTE monthly back-month contracts** —
0/62 valid fills in one case, wrong-regime strike contamination in another (liquid-looking strikes 3500pts
away from spot), and a calendar spread showing an impossible "long-vega wins" print that is almost certainly a
stale/bad mark on the far leg rather than real edge. This is distinct from (but consistent with) G17's finding
that OS-19's back leg is missing in 61.6% of cycles. Any monthly-DTE or calendar/diagonal backtest on this
dataset should be treated as unreliable until Kavya's office verifies/patches monthly-contract coverage.

## Recommendation
The four SURVIVE-fragile/marginal setups (OS-04, OS-20, OS-26, OS-35) are legitimate small incremental edges
consistent with the firm's existing VRP book (S-04/S-05) — worth a Gate-4 pass ONLY if the goal shifts from
"find a >50%/>2 strategy" (which none of these are) to "find a modest uplift over the existing short-vol
sleeve." That is a different, smaller ask than what was originally commissioned. Recommend closing this
campaign against its original mandate (bar not cleared, consistent with literature) and treating the four
survivors as a separate, small follow-on decision for the CIO/FM desk if there's interest.
