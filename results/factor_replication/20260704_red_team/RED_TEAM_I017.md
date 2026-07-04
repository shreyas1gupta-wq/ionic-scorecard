# RED TEAM — I-017 Pure N500 Momentum Top-50 Monthly (pre-intake gate)
**Nikhil Bose (E-014), Red Team. 2026-07-04.** Reports to CIO only.
Target: `results/factor_replication/20260704_dynamic_basket/nav_control_momentum.csv` (26.38%/23.10% net 1x/2x,
maxDD -67%, ann turnover 370%). Discovered POST-HOC as a control in K-015's dynamic-basket kill.

## VERDICT: **ADVANCE-TO-INTAKE — but the headline is a HIGH-BETA SMALLCAP-MOMENTUM tilt, not a "momentum factor," and its live case is a CAPACITY question the CAGR does not answer.**

**Single decisive number:** under an honest ADV-based slippage tier (mean **27.1 bps**, not the 22 bps
flat tier as built — because **59.8% of book weight sits in SMALL-ADV names <Rs25cr/day**), net-2x falls
23.10% → **22.05%**; under a pessimistic 35 bps small-cap floor it is **20.46%**. The return is REAL (not a
cost/data-path artifact), but it is earned in the thinnest tercile of the tape at 370% turnover with a
**-68% drawdown** — so the kill that matters is CAPACITY, not CAGR.

---

## ATTACK CHOSEN & WHY
Three candidate attacks in the brief. I ran all three cheaply; (c) was the decisive one to actually
compute, (a) and (b) are resolved by counting/reconciliation.

### (a) Selection-after-the-fact — HONEST TRIAL COUNT [INFERENCE]
The number was NOT pre-registered as a strategy — it fell out of K-015's dynamic-basket run as one of two
static controls. So the correct question: how many implicit variants existed tonight such that ONE control
looking spectacular is expected by chance?

Tonight's D-029 factor wave, honest enumeration:
- Factor family (Arjun): **6 sleeves** (smallcap_MQ100/25, n500_MQ50, n500_lowvol50, smallcap_lowvol25, midsmall_MQ30).
- Cadence test (Devika, I-016): **2 variants** (LowVol50-Q, MQ50-semiannual).
- Dynamic basket (Ishaan): **3 configs** (dynamic, control-momentum, control-lowvol) + turnover-banded = 4th.
- Sameer's I-016 sensitivity grid: **36 cells**.
- Random-benchmark suite: 8 specs (benchmark construction, not strategy trials).

Family strategy-trial total ≈ **11–13 distinct return series** (excluding the 36-cell param grid, which is
all LowVol) OR **47** if you count every computed cell (Sameer's honest count). The pure-momentum control is
**1 of ~2 static controls** deliberately built as the mechanical extremes of the mom/lowvol blend axis.

**Ruling: this is NOT a lucky-draw-from-a-large-search finding.** The pure-momentum-50 is a *structural
control* (the 100/0 corner of the regime-blend weights), not one of N tuned momentum definitions cherry-picked
after seeing results. Its 26% is not "the best of many momentum variants" — it is the ONLY pure-momentum
variant that was run. There is no evidence of a hidden family of momentum definitions (lookback windows,
N, cadences) from which this was the survivor. **BUT** the risk is real going forward: intake would open a
family (N, lookback, cadence, weighting), and the 26% is the number an analyst would anchor on. That anchor
is contaminated by weighting choice (below) and must be re-earned inside a pre-registered momentum family,
not carried in from a control. **Mitigation = pre-registered kills below + honest-trials carried forward.**

### (b) Reconcile 26.38% vs the family's own MQ50-monthly (15.4% at 1x) [DATA]
The delta is NOT quality-leg dilution alone — it is **selection AND weighting both changing**:
- **MQ50 (family):** picks top-50 by 0.5·z(mom)+0.5·z(quality), weights by `mcap`/liquidity tilt (large,
  liquid names). Family `3_n500_MQ50` monthly: 1x **15.41%**, 2x **11.98%**, turnover 419.5%
  (`20260704_factor_family/summary_table.csv`).
- **Pure-momentum-50:** picks top-50 by momentum-z ONLY, weights by `score` (the momentum composite
  itself → concentrates into the HIGHEST-momentum names, which are the smallest/most volatile).

So the +11pp gap (15.41 → 26.38 at 1x) is a **real construct difference, not a data-path bug** — I verified
by reproducing 26.38/23.10 EXACTLY through the identical engine (`i017_liquidity_stress.json` base22 cell =
26.38% 1x / 23.10% 2x / -67-68% maxDD / 370% turnover, matched to the decimal). The gap is
(i) dropping the quality drag + (ii) **momentum-score weighting that tilts the book INTO small high-momentum
names**. This is not fiction; it is a different, higher-beta portfolio. Same panel, same PIT universe, same
costs — the number is a genuine portfolio, but a small-cap-momentum one wearing an "N500 momentum" label.

### (c) DECISIVE TEST — liquidity fiction at N500-tail: is 2x robust to the tier applied at real ADV? [DATA]
The control charges a **flat 22 bps** n500-blend slippage tier (`SLIP_TIER_N500=22.0`, build_dynamic_basket.py
L57) — the tier for a *cap-weighted* N500 basket. But score-weighting concentrates into thin names. I
re-ran the control through the identical engine, classifying every selected name each rebalance by its
**trailing-20d median rupee turnover** (price×volume — the thing that actually drives slippage) into
LARGE(≥Rs100cr, 10bps)/MID(Rs25–100cr, 20bps)/SMALL(<Rs25cr, 35bps), the firm's own benchmark-suite tiers,
and re-costed. `results/factor_replication/20260704_red_team/i017_liquidity_stress.json`:

| Slippage tier | net-1x CAGR | net-2x CAGR | maxDD (2x) |
|---|---|---|---|
| base22 (as built) | 26.38% | **23.10%** | -68.0% |
| **actual ADV-weighted (mean 27.1bps)** | 25.84% | **22.05%** | -68.6% |
| pessimistic small-35bps floor | 25.02% | **20.46%** | -68.9% |
| frictionless | 29.74% | — | — |

**Book composition (the real finding): mean 59.8% of weight in SMALL-ADV names (<Rs25cr/day), only 18.4%
in LARGE (>Rs100cr/day).** The 22bps flat tier IS an understatement — the honest tier is ~27bps — but the
CAGR is not fragile to it: even at a punitive uniform 35bps, net-2x is 20.46%, still +7.7pp over the 12.74%
hurdle. **Attack (c) does NOT kill the return.** It does confirm the strategy lives in the illiquid tail —
which is a CAPACITY problem the CAGR is blind to, not a backtest-realism problem at the CAGR level.

---

## WHAT THE CAGR DOES NOT ANSWER (the real gate)
- **Capacity / market impact.** 59.8% of a top-50 book in <Rs25cr/day names, rebalanced monthly at 370%
  turnover, means the strategy repeatedly buys and sells illiquid names. The 27bps ADV-slippage tier models
  a *fixed bps floor*, NOT the **participation-rate impact** of moving real size through a thin name. At even
  modest AUM this book cannot be filled at modeled prices. **This is the binding constraint, and it is
  unmodelled.** RP-14 capacity-check is mandatory before any sizing.
- **-68% drawdown.** This is a career-ending path for a real book. It fails the firm's own -50% floor that
  I-016 was held to (LowVol -44%). Any intake must carry an explicit drawdown-budget / vol-target overlay.
- **Regime concentration.** Not tested here (out of my one-attack scope) but momentum's return is historically
  front-loaded into trend regimes and suffers violent crashes (2009, 2020 momentum-crash) — the -68% likely
  clusters there. A regime split (2008/2020/2022) is a required intake deliverable.

## PLACEBO NOTE
Full placebo battery not run (this is a pre-intake gate, not Gate-5). The one placebo that matters at intake —
"is the number a construct or an artifact" — is answered: reproduced to the decimal through an independent
harness, cost tier stress-tested, composition decomposed. It is a real (if illiquid, high-beta) construct.

## DECISION: ADVANCE-TO-INTAKE with these PRE-REGISTERED KILLS (fresh, post-hoc discovery → mandatory)
1. **K-a (capacity, BINDING):** RP-14 capacity-check at target AUM with participation-rate impact (not flat
   bps). If <Rs__cr deployable before impact eats >25% of the edge → KILL. Owner: Tara (TCA) + Ishaan.
2. **K-b (honest tier baked in):** rebuild with the ADV-resolved tier (small names get 35bps), not the flat
   22bps. Registered number becomes net-2x **~20-22%**, NOT 23.10%.
3. **K-c (drawdown floor):** must carry a vol-target or drawdown-budget overlay bringing maxDD inside -50%,
   judged on RISK-ADJUSTED terms (Sharpe/DD), never raw CAGR (same rule K-015 imposed on the dynamic basket).
4. **K-d (honest trials carried forward):** DSR/PBO at intake must count the full tonight's family (≈47 cells
   per Sameer) PLUS every momentum-family variant intake spawns — the 26% cannot be re-anchored as "trial 1."
5. **K-e (regime split):** 2008/2020/2022 sub-period CAGR + maxDD; a momentum-crash era below the hurdle with
   a >-60% DD is a demotion trigger.

**Net:** the number is real, not fake. But it is a small-cap high-beta momentum tilt whose live viability is a
capacity/drawdown question, not a return question. Advance to a properly-gated intake; do NOT let the 23.10%
headline travel as a clean "N500 momentum factor" into any IC or investor-facing doc.

## AP-relevant catch
Reproduced the control exactly, then exposed that **60% of the book is in the illiquid tail** and the
slippage tier is understated by ~5bps — a real (if non-fatal-to-CAGR) modeling gap, and identified CAPACITY
(not CAGR) as the true binding kill. Prevents a -68%-DD, unfillable-at-size book from advancing under a clean
"26% momentum" banner.

---
*Nikhil Bose (E-014), Red Team. Signed 2026-07-04. Evidence: `i017_liquidity_stress.json` (this dir);
`20260704_dynamic_basket/summary_table.csv`, `nav_control_momentum.csv`, `turnover_control_momentum.csv`;
`20260704_factor_family/summary_table.csv`.*
