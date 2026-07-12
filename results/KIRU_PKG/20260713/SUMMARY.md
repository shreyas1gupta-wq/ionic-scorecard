# KIRU PACKAGE — VERDICTS (2026-07-13, DESK-20)
Card: `04_RND_LAB/ideas/20260713_kiru_rotation_0dte_package.md` (FROZEN pre-run @ commit before this run). Scripts-only (spend-limit law). Data: real NIFTYBEES+GOLDBEES 2013→2026 (Angel, continuity guards PASS — window includes COVID), NIFTY weekly options 1-min 259 expiries 2021-05→2026-06.

## Component A — NIFTYBEES↔GOLDBEES ratio-Donchian(20) rotation → **NOT ADOPTED (1/3 core bars)**
| Config (net of 0.426%/switch) | CAGR% | Vol% | MaxDD% | Switches/yr | Cost drag pp/yr |
|---|---|---|---|---|---|
| **Primary: N20, t+1 OPEN exec** | **9.79** | 16.08 | **−32.96** | 7.4 | 3.16 |
| N20, execute AT signal close (needs 15:25 calc) | 12.44 | 15.52 | −25.26 | 7.4 | 3.16 |
| N20, SAME-BAR (lookahead demo — inadmissible) | 29.41 | 15.07 | −20.45 | 7.4 | 3.16 |
| Neighbors N15 / N25 / N30 (t+1 open) | 12.9 / 14.9 / 14.1 | ~16-17 | −27 to −29 | 9.8 / 5.6 / 4.9 | 4.2 / 2.4 / 2.1 |
| NIFTYBEES buy & hold | 11.93 | 14.71 | −36.34 | — | — |
| GOLDBEES buy & hold | 11.09 | 15.32 | −25.46 | — | — |
| **50/50 monthly rebal (benchmark)** | **12.29** | **10.47** | **−21.49** | ~12 tiny | ~0.1 (est, not modeled) |

- **KR-R1 FAIL** (CAGR 9.79 < 10.93 bar; MaxDD −32.96 vs ≤ −21.8 bar). **KR-R3 FAIL** (3.16pp > 2pp). **KR-R2 PASS** — but N20 is the WORST neighbor: the podcast's exact parameter is a fragile draw.
- **The claimed "18%" is an execution illusion [INFERENCE]:** same-bar execution shows 29.4%; one honest day of lag destroys 17-20pp/yr — the edge is concentrated in the breakout bar itself, which retail cannot capture. Claimed vol/DD reduction: vol is HIGHER than B&H (16.1 vs 14.7); worst rotation drawdown (−33%) happened 2024-26, exactly when protection was expected.
- Era truth: 2013-16 rot −21.5% vs B&H +38.6% (whipsaw hell); 2020 COVID rot +27.7%/−21.6%DD vs B&H +15.4%/−36.3%DD (the one shining era, likely the demo window).
- **COMPONENT-BANK (the real finding): static 50/50 NIFTY-gold with monthly rebalancing dominates the strategy** — better CAGR than B&H, 29% less vol, 41% less MaxDD, near-zero cost. This is direct evidence FOR K-011's explicitly-unclaimed "strategic gold sleeve" hypothesis → route to Devika (different-FACTOR roadmap fit). Caveat: 50/50 rebal costs not modeled (~0.1pp/yr est); NIFTYBEES dividends ignored (hurts B&H and rotation equally).
- Kill filed as **K-016** with resurrection conditions (overlay-on-50/50 base · monthly-frequency low-whipsaw version · VIX-percentile regime gate) — any retest must beat the 50/50 benchmark, not B&H.

## Component B — 0DTE ATM short straddle 09:16, combined-premium SL +30% → **BARS PASS, but claim off by ~7×; → S1-F-family VARIANT note (no register row)**
| Variant (n=259 expiries, % of spot notional) | mean/expiry | win% | p5 | min | ann (×52) |
|---|---|---|---|---|---|
| **SL30 (his spec)** | **+0.0328** | 43.6 | −0.288 | −0.537 | **+1.71%** |
| SL20 / SL40 | +0.031 / +0.037 | 37 / 49 | −0.23 / −0.35 | | +1.6 / +1.9% |
| No SL (baseline) | +0.0218 | 58.7 | **−0.762** | −2.348 | +1.13% |
| SL30 + exit 15:20 | +0.0312 | 43.6 | −0.288 | | +1.62% |
| **SL30 + firm ≥0.45% filter (n=167)** | **+0.0597** | 47.3 | −0.318 | | **+3.10%** |
| SL30 below-filter days (n=92) | **−0.0159** | 37.0 | | | −0.83% |

- **KR-S1 PASS** (mean>0, n=259). **KR-S2 PASS** — the 30% SL is the genuinely good part of his spec: cuts tail p5 2.6× AND improves the mean. **KR-S3 PASS** (trailing-12m +0.033).
- **Honest annualized edge: +1.7%/yr of notional unlevered** (his claim: 12%/yr — requires ~7× leverage, or ~4× margin-max WITH an IV filter he doesn't use). 2023 was a NEGATIVE year (−0.6%). SL fires on 52.5% of days; median trade is −0.135% — the "consistent theta income" narrative is false in practice: most days lose small, a minority of full-decay days carry the P&L.
- **KR-S4:** our existing ≥0.45%-of-spot deploy rule nearly doubles the edge and the excluded 36% of days are net-NEGATIVE — his unfiltered spec is strictly dominated by the firm's known rule. Same trade family as S1-F (paper, Tue engine) — this is independent re-confirmation that the family edge is real but thin; NOT a new strategy.

## Component C — combined "30%/yr" claim → **NOT REPRODUCED**
Honest stack: rotation 9.8-12.4% + straddle overlay at 1-2× notional +1.7 to +3.4pp (filtered: +3.1 to +6.2pp) ≈ **11.5-18.6%/yr**, with correlated drawdowns (2024-26 rotation DD −33% while straddle SL days cluster in the same vol spikes; pledge haircut + margin calls compound in stress). The 30% needs the same-bar rotation illusion AND ~7× options leverage simultaneously.

## Trials: +12 (rotation 6, straddle 6) — for family ledgers; DESK-100 regenerate build_trials_ledger.
Artifacts: `rotation/{metrics.json,equity_curves.csv,rotation_monthly_returns.csv}` · `straddle/{metrics.json,trades.csv}`. Sleeve-corr join (KR-R4): monthly series banked; no *daily_returns*.csv matched in results/ glob — pending Neel/DESK-100 join.
