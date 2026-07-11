# RED-TEAM — MidSmall Momentum Rotation, Variant B (in the stacked paper book, 50L equity)
Nikhil Bose (E-014, Red Team) · 2026-07-13 · reports to CIO
Target: `04_RND_LAB/results/MIDSMALL_MOM_ROTATION_20260707/` (engine `midsmall_mom_rotation.py`, VarB = full-N500)
Scripts + raw outputs banked in the target dir: `varb_rt_1_placebo.py` (+`_dist.csv`,`_summary.json`,`_LOG.txt`), `varb_rt_2_robust.py` (+`.json`), `varb_rt_3_beta_corr.py` (+`.json`).

## VERDICT: **SURVIVES-AS-BETA**
Real, non-lookahead, tradeable **risk-managed midcap-momentum BETA** sleeve. **It is NOT alpha.** Stays in the paper book ONLY relabelled as equity/midcap beta with a sizing haircut, and MUST NOT be counted as an independent alpha toward the "6-8 uncorrelated sleeves → 30/10" frontier.

## The ONE attack chosen & why
The author (Arjun Rao) already ran lag-1, 2x-cost, degenerate detectors, fills — all passed — and self-labelled the sleeve "regime-timing, not selection." That label was **asserted from an index comparison, never proven with a statistic.** My focused attack: **prove or disprove that the pick is beta-in-costume** via (a) a **random-selection placebo (D-029)** that holds the regime overlay constant and varies only the stock pick, and (b) an **invested-days beta/alpha regression with a t-stat**. Supporting: extended lag-decay, year-exclusion, corr-horizon.

Harness integrity: my rig feeds RANDOMISED cross-sectional scores into the FROZEN engine (NaN/eligibility mask kept byte-identical); it reproduces banked VarB **exactly** (CAGR 0.2277, Sharpe 1.142, MaxDD −0.2462, finalV 6.2327, turn 22.1). So every perturbation below runs through the real cost/fill/regime machinery. Engine and stacked book were NOT modified (D-030 respected).

## Evidence

### 1. Invested-days beta/alpha — THE kill on the "alpha" claim
| Regression | Beta | Ann. alpha | t(alpha) | corr (R²) |
|---|---|---|---|---|
| VarB vs MSS400, **full sample** | 0.58 | **+12.4%** | 2.20 | 0.52 (0.28) |
| VarB vs MSS400, **invested days only** | **1.13** | **+0.9%** | **0.16** | 0.79 (0.63) |
| VarB vs N500, invested days only | 1.20 | +5.1% | 0.79 | 0.70 (0.49) |

The headline full-sample alpha (+12.4%, t=2.20) is a **mechanical artifact of sitting in cash/gold ~31% of the time** (regime overlay lowers full-sample beta to 0.58, inflating the intercept). Condition on the days it actually holds stocks and beta = **1.13× midcap** with alpha **+0.9%, t=0.16 → statistically indistinguishable from zero.** The stock PICK adds no risk-adjusted alpha; the value is 100% regime-timing (being out during drawdowns).

### 2. Random-selection placebo, N=200 (D-029 cap-matched: random 15 from same N500-as-of pool, identical overlay+fills)
| | Momentum | Random median | Random p90 | Random max | Momentum sits at |
|---|---|---|---|---|---|
| **GROSS** CAGR (cost=0) | 32.1% | 19.6% | 23.3% | 26.3% | 100th pct |
| **GROSS** Sharpe | 1.554 | 1.207 | 1.415 | **1.546** | 100th pct (≈ tied w/ best random) |
| **NET** CAGR (cost=1x) | 22.8% | −0.1% | 3.3% | 6.5% | 100th pct |
| Turnover (x/yr) | **22** | **42–44** | | | 0th pct |

Reading:
- **Gross selection IS real vs random (+12.5pp CAGR, 100th pct)** — that is the **momentum FACTOR premium**, not idiosyncratic alpha. Note on **Sharpe** the momentum pick (1.554) barely edges the BEST random draw (1.546) and sits inside the random envelope — the edge is a return/vol *tilt* (concentration into higher-beta trending names), not risk-adjusted skill. Consistent with §1 (no alpha vs the index).
- **The enormous NET gap (22.8% vs ~0%) is a TURNOVER artifact, not pick quality.** Random fully churns each rebalance (42–44x turnover) and is annihilated by cost; momentum names persist (22x) so they keep the gross. ~Half the net "edge over random" is *"momentum is cheaper to trade,"* not *"momentum picks better stocks."*

### 3. Lag-decay (VarB, enter 0/1/2/3/5 td late)
CAGR retained: 100% / 102% / 90% / 95% / **83%**; Sharpe retained down to 87% at lag-5. **No collapse → no lookahead** (a leak collapses >50%), AND confirms a **slow signal** (drift/regime), not a fast alpha — you cannot lose it by being a day late, which is exactly the beta-signature.

### 4. Year-exclusion (drop each CY from the daily chain)
| Drop | CY ret | CAGR ex | finalV ex |
|---|---|---|---|
| 2021 | +86.1% | 16.5% | 3.35 |
| 2023 | +68.2% | 17.9% | 3.71 |
| **2021 + 2023** | — | **10.4%** | **1.99** |
Full = 22.8% / 6.23. **Strip the two midcap-bull years and CAGR (10.4%) falls below Nifty500 buy-hold (14.3%).** Classic small/mid-beta payoff profile — it earns in trending bull years and is otherwise unremarkable. Not fake; just not a steady-state 22.8%.

### 5. Corr-horizon vs other book sleeves (book_daily_pnl.csv, 2022-2025)
| Horizon | vs breakout | vs s1f | vs b1b | max |
|---|---|---|---|---|
| daily | 0.08 | −0.01 | −0.01 | 0.08 |
| monthly | 0.27 | 0.07 | 0.18 | 0.27 |
| quarterly | 0.41 | 0.38 | **0.53** | **0.53** |
The "max pairwise 0.08 → uncorrelated" book claim is a **daily-sampling illusion**. At the horizon that governs drawdowns (quarterly) midsmall shares **0.53 with b1b, 0.41 with breakout, 0.38 with s1f** — it is substantially the **same equity factor** already owned by breakout+b1b (worst-month clustering already documented in the STACKED_BOOK addenda: Feb-2022 and Mar-2024 all-equity-sleeves-down-together).

## What was ESTABLISHED vs previously ASSUMED
- Previously ASSERTED (no stat): "regime-timing not selection." **Now ESTABLISHED**: invested-days alpha +0.9%, **t=0.16** vs MSS400; beta 1.13. The pick is factor beta.
- NEWLY ESTABLISHED: (a) momentum's net advantage over random is **half turnover/persistence, not selection**; (b) the sleeve is **2-year-dependent** (2021+2023); (c) it is **not a diversifier at drawdown horizon** (0.53 quarterly vs b1b).

## Conditions attached to SURVIVES-AS-BETA (hard)
1. **Relabel** in STRATEGY_REGISTER / book from "alpha sleeve" to **"equity — risk-managed midcap-momentum BETA (invested β≈1.1–1.2× midcap + momentum factor tilt + 200-EMA regime overlay that halves index maxDD)."**
2. **Do NOT count it as an independent alpha** in the frontier math. It belongs in the **equity-beta bucket** alongside breakout+b1b, correlated 0.38–0.53 quarterly. If breakout+b1b already fill the equity-momentum allocation, midsmall is **largely redundant** — a portfolio-construction call for CIO/FM (pick one, don't triple-count the factor).
3. **Sizing haircut**: size on quarterly (not daily) correlation; its diversification benefit at book level is ~nil at drawdown horizon.
4. **Net-of-cost expectation** is ~13-14% (2x-cost stress = 13.6%), not 22.8%; the 22.8% is turnover-fragile and 2-year-loaded.

## What would change the verdict
- **→ SURVIVES (genuine alpha)**: an **invested-days alpha vs a passive midcap-MOMENTUM index** (Nifty Midcap150 Momentum50 TR or BSE Midcap150 Momentum30, net of cost) that is **positive with t>2**. Current invested alpha vs MSS400 is t=0.16 — nowhere near. A cheap passive momentum/midcap ETF captures the same factor without the 22x turnover.
- **→ KILL (must exit)**: if the book continues to present it as an **independent/uncorrelated alpha** (frontier math), it is actively misleading on diversification and drawdown-clustering and should be removed rather than laundered.

## AP-relevant catches
- Hardened a previously-unproven "beta not alpha" label into a t-stat (invested alpha t=0.16).
- Exposed the placebo's own turnover confound and split gross-selection (real momentum factor, +12.5pp) from net-persistence (the thing actually driving the vs-random gap) — did not let my own kill-test overstate.
- Independently reproduced the book's daily→quarterly correlation inflation (0.08→0.53) on the midsmall sleeve, confirming it is not a diversifier at drawdown horizon.
- Lookahead battery (D-028): lag 0→5 retains 83-102% → clean.
