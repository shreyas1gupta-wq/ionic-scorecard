# RED TEAM — I-016 N500 LowVol50 QUARTERLY (post-Gate-4)
**Nikhil Bose (E-014), Red Team. 2026-07-04.** Reports to CIO only.
Target: `results/factor_replication/20260704_i016_cadence/` (certified 17.46% fric / 16.54% 1x / **15.62% 2x**,
vol ~12.6%, maxDD -44.2%, turnover 109.6%; DSR 0.9995 / PBO 19.8%; lookahead 0-FAIL; resurrected same-day from K-013).

## VERDICT: **FRAGILE — bordering FAKE-as-an-edge.** The headline "+2.88pp over the 12.74% hurdle" is
## overwhelmingly a LOW-TURNOVER cost saving, not low-vol SELECTION skill. It is a real, low-cost, low-DD
## beta-delivery vehicle; it is NOT a demonstrated alpha over a turnover-matched dart-throw.

**Single decisive number:** a **RANDOM 50-name inverse-vol basket, turnover-matched to LowVol50-Q, run through
the IDENTICAL cost engine, earns median net-2x ≈ 13.8% at 133%/yr turnover (60 seeds, confirmed) and ≈ 15.0%
at 119%/yr turnover (nearest match to LowVol's 109.6%)** — versus LowVol's certified **15.62%**. Extrapolated
to LowVol's exact 109.6% turnover, a skill-less random invvol basket lands **~15.0-15.4%**, so the low-vol
*selection* margin over an equally-low-churn random basket is **≤~0.6pp**, not the +2.88pp the strategy claims
over the firm's (full-churn, ~200-355% turnover) 12.74% hurdle. **~2.3 of the 2.88pp headline edge is a
turnover/cost artifact; only ~0.6pp is attributable to low-vol name selection.** (Full 60-seed sweep at the
0.72/0.75/0.78 keep-fracs `placebo_summary.json`; smoke n=6 and 60-seed confirm each other.)

---

## ATTACK CHOSEN & WHY
Three candidates in the brief. Sameer's Gate-4 already established the regime-carry weakness (attack c:
2016-26 half 11.74% < hurdle, 48% of years below) — but that is a FRAGILE flag on generalization, not proof
the full-sample edge is fake. The **unexamined, load-bearing** question is attack **(b): is the +2.88pp margin
over the hurdle a low-VOL effect, or a low-TURNOVER effect wearing a low-vol costume?** This is the cheapest
decisive test AND it attacks the number the diversifier case actually rests on. I ran it.

### The rigged comparison [DATA]
The firm's 12.74% hurdle (`datasets/derived/benchmarks_random/summary.csv`, `n500_50`) is a **full-churn**
quarterly random basket: it redraws 50 random names every quarter, so ~all 50 turn over each quarter
(cost drag **3.31 pp/yr**, BENCHMARKS_README §headline). LowVol50-Q runs at only **109.6%** turnover because
low-vol names persist across quarters (cost drag only **1.84 pp/yr**, 17.46→15.62). **The strategy is being
credited for a +2.88pp margin, ~1.5pp of which is simply that it TRADES LESS than the benchmark it is
measured against.** That is a measurement artifact (my charter priority #2: denominators/comparators), not skill.

### DECISIVE TEST — turnover-matched random placebo [DATA]
I built random 50-name baskets with a persistence knob (`keep_frac`) tuned to hit LowVol's turnover, weighted
inverse-vol (identical scheme) and equal-weight, and ran them through the **certified engine's exact cost/P&L
code** (copied verbatim; validated by re-running the real LowVol50-Q through my harness → reproduced
**fric 17.46% / 1x 16.54% / 2x 15.62% / turn 109.6%** to the decimal, so this is true apples-to-apples).
Distribution of net-2x CAGR by turnover level (smoke n=6/cell; 60-seed confirmation `placebo_summary.json`):

| Random basket | ann turnover | net-2x median | %seeds > 12.74% hurdle | %seeds > LowVol 15.62% |
|---|---|---|---|---|
| invvol, full churn (keep 0) | ~354% | **9.93%** | 0% | 0% |
| invvol, keep 0.55 | ~186% | 13.51% | 83% | 0% |
| invvol, keep 0.70 | ~139% | 14.46% | 100% | 0% |
| **invvol, keep 0.75 (≈LowVol turnover)** | **~119%** | **15.04%** | 83% | 17% |
| equal-wt, keep 0.70 | ~137% | 14.47% | 100% | 17% |
| **— LowVol50-Q (certified, via same engine) —** | **109.6%** | **15.62%** | — | — |

**The mechanism is laid bare: a skill-LESS random basket's net-2x climbs monotonically from 9.9% (full churn)
to ~15.0% purely by trading LESS.** At LowVol's own turnover, a random inverse-vol dart-throw is within
~0.6pp of the "certified low-vol edge," and ~1-in-6 random seeds BEAT it outright. **The low-vol anomaly is
NOT the source of the +2.88pp headline margin — the turnover differential vs the benchmark is.**

### What this means for the pre-registered kill (attack a — the resurrection) [INFERENCE]
K-013 was killed on a fictional bar (chained-p75) and resurrected on the corrected per-path frictionless
terminal p75 (17.13%; LowVol 17.46% clears +0.33pp). I checked whether that was bar-shopping: **it was NOT** —
the correction (percentile-of-terminal-paths vs path-of-percentiles) is the *methodologically correct* bar per
Ishaan's own README §NAV-construction (KB lesson 18), not the convenient one, and the +0.33pp clearance is
honest. **But note how thin the true skill margin is:** the strategy clears the corrected p75 by 0.33pp, and
clears a turnover-matched random invvol basket by ~0.6pp. Both "wins" are inside the seed-to-seed noise of a
random basket (p05-p95 of the matched random cell spans ~12.4-16.8%). **The resurrection is procedurally
clean; the edge it resurrects is a rounding error once you strip the turnover advantage.**

### Regime-carry (attack c) — I concur with Sameer, and it compounds my finding
2016-26 half 11.74% (below hurdle), 2022-26 rate-era 12.08% (below hurdle), 48% of years below hurdle, post-2020
excess front-loaded into 2020-21 recovery. Combined with the turnover finding: the **only** era where LowVol
clearly beats a turnover-matched random basket is 2005-2015 (pre-institutional-lowvol-crowding), which is
exactly the era the factor's own popularity has since arbitraged. Forward expectation should anchor near the
post-crowding 11.7% — **below the hurdle, and below a turnover-matched random basket.**

---

## PLACEBO BATTERY (charter requirement)
- **lag+1 degrades:** PASS (Sameer's audit: +1-day-lag collapse 2.0% — real slow signal). Not the weak point.
- **cross-sectional / turnover-matched random benchmark:** **FAIL of the edge claim** — a turnover-matched
  random basket ties LowVol within 0.6pp (this review's decisive test). The strategy does NOT decisively beat
  a like-for-like random benchmark; it beats a HIGHER-turnover one.
- **2x costs survive:** PASS at the CAGR level (15.62% > 12.74%) — but that "survival" is the turnover artifact.
- **DSR/PBO bootstrap:** PASS (DSR 0.9995, PBO 19.8%) — these measure "is the parameter cell overfit," which it
  is not; they do NOT test "is the benchmark a fair, turnover-matched comparator," which is where it fails.

The DSR/PBO/plateau/stale-mask all being clean is exactly why this is FRAGILE not FAKE: the *number* 15.62% is
real and reproducible. It is the *interpretation* ("+2.88pp of low-vol selection alpha over the market") that is
fake. The strategy is a genuine low-cost, low-drawdown, low-vol-BETA vehicle — not an alpha source.

## DIVERSIFIER CASE — assessed separately (its actual IC claim)
Devika/Sameer both (correctly) argue the IC case is **orthogonality to the short-vol book**, NOT raw CAGR.
I concede the CAGR attack does not touch that claim — a low-cost, -44%-DD, ~12-13% vol long-only equity sleeve
IS structurally the firm's only non-short-vol exposure, and that has value regardless of the turnover finding.
**BUT** the orthogonality case has its own untested tail: **does LowVol50-Q actually decorrelate from a
short-strangle proxy in STRESS months, or only in calm ones?** Low-vol is a bond-proxy/defensive factor; short
vol is short-gamma. In a sharp equity selloff BOTH lose (low-vol equity still falls; short strangles get run
over) — the diversification can evaporate in the exact months it is bought for. **This correlation-in-stress
test was NOT in tonight's package and I did not have a short-strangle NAV series on disk to run it.**
→ **Registered as the binding pre-IC deliverable for the diversifier case** (see flip condition).

## VERDICT: **FRAGILE** — and the diversifier framing is the ONLY surviving case, contingent on stress-corr proof.
**What would flip it to REAL (as an EDGE):** a turnover-matched random invvol basket must FAIL to reach
LowVol's net-2x by a decisive, seed-stable margin (e.g. LowVol beats the random-matched p75, not just the
median) — i.e. show the selection adds >~2pp over like-for-like random churn. Current evidence: it adds ~0.6pp.
**What would flip the DIVERSIFIER case to fundable:** monthly-return correlation of LowVol50-Q vs a
short-strangle-proxy NAV, computed IN the worst decile of equity-drawdown months, must be materially negative
(not just full-sample near-zero). Until then the "diversifier" is unproven precisely where it must hold.

## RECOMMENDATION TO CIO/IC
Do **not** advance this as a return/alpha sleeve. If it advances at all, advance it **only** as a
capital-efficient low-vol-BETA diversifier at MODEST size, with (1) the turnover-artifact finding attached
verbatim (the +2.88pp is ~0.6pp skill + ~2.3pp cost-differential), (2) a mandatory stress-correlation proof vs
the short-vol book BEFORE sizing, (3) forward return anchored at the post-crowding ~11.7%, not the 15.62%
full-sample number, and (4) a rate-regime monitor per Sameer. This is a beta vehicle, not an edge.

## AP-relevant catch
Isolated that **~80% of I-016's headline margin over the firm's own random-basket hurdle is a turnover/cost
differential, not low-vol selection** — a comparator/denominator artifact the full Gate-4 battery (DSR/PBO/
plateau/lookahead, all clean) is structurally blind to. Prevents the firm's FIRST double-gate-passing strategy
from being sized to a ~0.6pp real edge dressed as +2.88pp alpha.

---
*Nikhil Bose (E-014), Red Team. Signed 2026-07-04. Evidence: `placebo_summary.json`, `placebo_randInvVol_*.csv`
(this dir); certified engine reproduced exactly via local harness; `20260704_i016_cadence/VERDICT.md` +
`SENSITIVITY_REPORT.md`; `datasets/derived/benchmarks_random/BENCHMARKS_README.md` §headline cost-drag.*
