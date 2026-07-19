# WAVE-4 Technical Patterns — CONFIRMATION/TIMING OVERLAY TEST
2026-07-17, Dhruv Kapoor (Technical Head). Task: test whether chart/technical patterns
add value to ALPHA_RANKER's frozen 7-leg composite — Principal's frame: only worth
adopting if they help CLUBBED with the fundamental/momentum score, tested ERA-AWARE
(patterns are increasingly manipulated 2010→2025). Prior art already killed ADX-entry,
Weinstein stage-2, mean-reversion-entry, ORB as STANDALONE technical entries (`rnd/KILLED.md`,
`FRAMEWORK_CATALOG.md` PRIOR-ART table) — only MA-65 slope (already IN the 7-leg composite)
and ATR-based exits survived. This wave does not expect standalone alpha and tests
each pattern as a confirmation/timing overlay, not a rediscovery of a killed vehicle.

**Code, harness, cards**: `rnd/run_w4tech_dhruv.py` (all 6 builders + clubbing-test +
era-split logic); harness cards `rnd/cards/W4TECH_*.json`; declined-pattern stubs
`rnd/cards/W4TECH_{elliott,cupandhandle,ladder}_DECLINED.json`; raw results
`rnd/reports/W4TECH_patterns_results.json`. Evaluated at 1Y/resid on `panel_long.parquet`
(2005-2025, 249 monthly dates, `disc_event_in_window_1Y`-guarded), through the SAME
`harness.evaluate()` every other factor in this program goes through — no separate math.

## HARD DATA LANDMINE — read before the era-split numbers below
`cube_volume.parquet` and `data/prices/*.parquet`'s `Volume` column **start 2021-07-16**,
not 2005. There is **no daily volume history pre-2015** anywhere in this repo. Any pattern
whose definition requires volume (VCP, volume-profile) can only be evaluated **2021-2025**
— entirely the POST-2015 "manipulation era" by the Principal's own framing. The question
"does it survive into the manipulation era, or only work in old low-float small-caps" is
therefore **structurally unanswerable with current data** for volume-dependent patterns —
reported as a gap, not silently worked around or faked. Price-only patterns use
`cube_close_long.parquet` (2005-2025) and get a genuine era split.
Cap-segment note: `cube_volume` covers 751 symbols vs `cube_close_long`'s 976 — a real
but modest coverage gap tilting the volume-pattern sample away from the most illiquid/
delisted micro-caps; no separate cap-tier cut was run (out of scope for this pass), flagged
not fabricated.

---

## Pattern-by-pattern

### 1. VCP (volatility contraction pattern) — buildable, volume-dependent (2021-2025 only)
Mechanical rule: 21d/63d realized-vol ratio <0.7 AND 21d/63d avg-volume ratio <0.7
(contraction+dry-up), followed within 10 sessions by a close above the trailing 20d high
on ≥1.3x volume expansion. Binary flag.
- **Standalone**: IC_IR 0.104 (below 0.20 floor), mono 0.45, **lag_test_delta 1.484**
  (>>0.25 hard gate — the signal is wildly unstable under a 1-period lag shift, a red
  flag for a rare/bursty binary flag with only 36 IC dates). PBO 0.952. **KILL.**
- **Clubbed**: among top-quintile-composite names, pattern-present forward return +18.1pp
  vs pattern-absent (n=12,632 obs across the pattern's coverage window), Welch t=2.10,
  p=0.037 — nominally "significant" in isolation, **but disqualified by the pattern's own
  lag-test failure above** (task's rule: "keep lag+placebo hard" — a factor that fails its
  own stability check does not get credit for a clubbed p-value built on the same noisy
  ranking). Not trusted.
- **Era-split**: pre-2015 N/A (no volume data); post-2015 IC_IR 0.104 (same as standalone,
  since 100% of the sample is post-2015 by construction).
- **Verdict: standalone weak/unstable, clubbed reading not trustworthy. Does NOT earn a
  confirmation-overlay slot.**

### 2. Breakout + retest-hold — buildable, price-only (full 2005-2025)
Mechanical rule: 50d-high breakout 5–20 sessions ago, current close 0–8% above that level
(near it, holding above — approximation, does not verify the actual intraday pullback touch,
disclosed [INFERENCE]).
- **Standalone**: the BEST-behaved gates of all six patterns — IC_IR 0.419, Newey-West
  t=4.5, lag_test_delta 0.077 (clean), placebo_ic -0.0001 (clean). Mono only 0.20 (weak
  decile monotonicity despite the decent IC — a real tension, not glossed over). **KILL on
  PBO=1.00/DSR=0** — consistent with this harness's own disclosed sensitivity issue
  (`KILLED.md` H002: PBO fires 0.85–1.00 on "literally every one of the 62 cards" at the
  current global trial count; not unique to this factor).
- **Clubbed**: delta_mean +2.5pp, Welch t=0.72, p=0.47 — **not significant**. This is the
  factor with the cleanest standalone stats, and it STILL shows no real incremental value
  on top of the composite.
- **Era-split**: pre-2015 IC_IR 0.446, post-2015 IC_IR 0.394 — stable across eras, no
  decay (rare survivor of the "manipulation" concern on this specific metric), but moot
  given the clubbed test is null.
- **Verdict: standalone-cleanest, clubbed-null. Does NOT earn a confirmation-overlay slot** —
  directly reproduces the prior-art lesson (same-exit/incremental-value placebo, not raw
  backtest, is the real arbiter).

### 3. Down-channel breakout — buildable, price-only (full 2005-2025)
Mechanical rule: 120d rolling-regression channel (closed-form cov/var slope vs a time
index; channel width proxied by rolling price std, disclosed [INFERENCE] vs a true
OLS-residual std), breakout = close > upper band while the trailing channel itself sloped
down.
- **Standalone**: IC_IR -0.068 (negative), lag_test_delta 0.539 (fails), PBO 1.00, DSR 0.
  **Clean KILL**, no ambiguity.
- **Clubbed**: delta_mean -1.5pp, t=-0.36, n.s.
- **Era-split**: pre-2015 IC_IR -0.141, post-2015 +0.012 — sign-flips between eras, no
  stable edge in either.
- **Verdict: dead on every cut. Does NOT earn a slot.**

### 4. Flag (thrust → low-vol consolidation → continuation) — buildable, price-only (full 2005-2025)
Mechanical rule: ≥15% thrust over a 20d window ending 15 sessions ago, trailing-15d vol
<50% of the thrust window's vol, continuation breakout above the 15d consolidation high.
- **Standalone**: IC_IR 0.147 (below floor), **monotonicity 0.09 — essentially flat/
  non-monotonic decile ranking**, a real warning that the positive mean IC isn't a clean
  ranking. lag_test_delta 0.20 (passes the 0.25 gate but close to it), placebo clean.
  PBO 0.99, DSR 0. **KILL.**
- **Clubbed**: the largest raw effect of all six — delta_mean **+43.3pp**, Welch t=1.92,
  **p=0.060** (misses conventional 0.05, single uncorrected test — with 6 patterns tested
  this session a naive Bonferroni puts the effective p near 0.36). Per the task's low-t
  rule ("logic+effect+drop-one"), a borderline single-test result with near-zero standalone
  monotonicity does **not** clear the bar for acceptance without a drop-one/out-of-sample
  confirmation pass, which was not run this cycle.
- **Era-split**: pre-2015 IC_IR 0.133, post-2015 0.162 — stable, no decay, for what is
  otherwise a very weak signal.
- **Verdict: the single most interesting (largest, marginally-significant) clubbed reading
  in this batch, but NOT confirmed — flagged as a candidate for a dedicated drop-one/
  robustness re-test, not adopted.**

### 5. Choppy/range regime (efficiency ratio, NEGATIVE FILTER) — buildable, price-only (full 2005-2025)
Kaufman efficiency ratio (|net 20d change| / sum|daily changes|), tested by design as a
suppression gate, not a directional score.
- **Standalone**: IC_IR 0.034 (~0, as expected for a non-directional filter), mono 0.53
  (moderate — chop level does correlate somewhat with return magnitude/dispersion, as
  intended), lag_test_delta 0.255 (marginal fail). KILL as a standalone factor (expected;
  it was never meant to be one).
- **Clubbed** (trending/high-ER vs choppy/low-ER among top-quintile-composite names):
  delta_mean +2.1pp (trending better), t=1.04, p=0.30 — **directionally consistent** with
  "the composite works better outside chop" but **not significant**.
- **Era-split**: pre-2015 IC_IR 0.019, post-2015 0.054 — both near zero, no era story.
- **Verdict: directionally plausible as a suppressor, not statistically confirmed. Weak
  candidate, not a slot-earner on this evidence.**

### 6. Volume-profile approximation — buildable-as-approximation, volume-dependent (2021-2025 only)
Disclosed approximation: true tick-level POC/value-area is not buildable from daily
Close+Volume; proxy = 60d volume-weighted-average-price (VWAP), factor = (close−VWAP60)/
60d price-std.
- **Standalone**: IC_IR 0.385 (second-best of the six), mono 0.6 (best of the six), lag
  clean (0.053), placebo clean. **KILL only on PBO=0.983** (39 IC dates — thin sample,
  volume-floor-limited).
- **Clubbed**: delta_mean **-4.2pp — wrong sign** (adding this on top of a strong
  composite score REDUCES forward return, though n.s., p=0.19). [INFERENCE] plausible
  explanation: the VWAP-distance proxy may be partially anti-correlated with the
  composite's own momentum leg (buying INTO recent strength vs this factor rewarding
  cheapness-vs-recent-volume-weighted-price) — not confirmed, flagged as a hypothesis only.
- **Era-split**: pre-2015 N/A (no volume data), post-2015 = standalone (same reason as VCP).
- **Verdict: best standalone gate profile of the six, but clubbing goes the WRONG direction.
  Does NOT earn a slot.**

### OVERFIT-TRAPS — declined, not tested
- **Elliott wave**: declined. Practitioner wave-counts are re-labelled after the fact
  whenever price violates the prior count; no single canonical rule-set exists (Elliott/
  Prechter/Neely/Frost disagree on alternation/extension/truncation). A rigid, no-relabelling
  counter would be a materially different (and much weaker) object than what "Elliott wave"
  actually means in practice — testing it and calling it "Elliott wave" would misrepresent
  what was tested.
- **Cup-and-handle**: declined. Published definitions (O'Neil/IBD, Bulkowski, Minervini)
  disagree materially on cup depth (12-33% to 50%), duration (7-65 weeks), handle depth
  (<12% vs <15%) and handle-location rules. Any single rigid parameterization is one
  arbitrary choice among many defensible ones — exactly the "too many degrees of freedom"
  trap; a parameter sweep would itself be a fresh multiple-testing problem this program's
  own DSR/PBO machinery already struggles to keep honest at far lower trial counts.
- **"Ladder"**: declined outright. No unambiguous, publicly-agreed definition exists (unlike
  the other three overfit-traps, which at least have multiple published parameterizations
  to choose among) — coding it would mean inventing the rule set from scratch, which is
  fabrication dressed as pattern-recognition, not a test of a known technical concept.

Full rationale + resurrection conditions in `rnd/cards/W4TECH_{elliott,cupandhandle,ladder}_DECLINED.json`.

---

## Overall honest verdict
**No technical pattern tested here earns a confirmation-overlay slot on the current
evidence.** This directly reproduces the prior-art pattern (K-adx-atr-family,
K-stock-meanrev-standalone, K-AF07-stage-turn — `KILLED.md`/`FRAMEWORK_CATALOG.md`):
standalone technical entries show weak-to-no cross-sectional alpha here too, and — the
actual ask — clubbing with the strong 7-leg score does not reliably improve forward
returns for any of the six mechanically-coded patterns once instability (lag test) and
multiple-testing discipline are applied. Two results (`flag`, `VCP`) showed large,
nominally low-p clubbed deltas that a less careful read would have reported as "it works
clubbed" — both are disqualified on closer inspection (VCP's own lag-test failure at
1.48 vs the 0.25 gate; flag's near-zero standalone monotonicity plus lack of multiple-
testing correction across 6 simultaneous tests). This is exactly the failure mode the
task's low-t rule (logic+effect+drop-one, hard lag+placebo) is designed to catch, and it
caught it. The one honestly-flagged candidate for further work is **flag**, ONLY as a
pre-registered drop-one/robustness re-test, not as an adopted overlay.
The 50-DMA-is-non-special / manipulation-tell warning from prior art is not contradicted
or confirmed by this pass — no pattern here reached a trustworthy edge to even ask whether
manipulation decayed it; the closer, more consequential finding is the volume-data floor
(2021-07-16) itself, which makes any future "manipulation decay" claim for VCP/volume-
profile-style patterns untestable until pre-2015 daily volume is sourced.
