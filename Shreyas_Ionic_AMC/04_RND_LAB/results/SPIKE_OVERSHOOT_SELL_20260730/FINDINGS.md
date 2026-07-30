# SPIKE-OVERSHOOT SELL — MEASURED FINDINGS (2026-07-30)
**Principal's own observation, tested. This is the session's best candidate and the ONLY one that
IMPROVED through the Oct-2024 break AND held up on the untouched 2026 sample.**

His hypothesis: *"0.2-0.4 delta options get too much inflated if a sudden large move come, going over
few points like 3-10 points over the [fair] value, and when mean reversion kicks in we get 10-30 point
pullback + this extra 3-10 points."*

## METHOD
4,903 spike events (`events_raw.csv`); 4,639 had a usable 0.20-0.40 delta option.
Overshoot = actual traded price at t0 minus the same option repriced at its OWN PRE-SPIKE IV using the
POST-SPIKE spot/time. Benchmark is the option's own prior vol, not a model surface.
Capture = the FALL in excess-over-fair, with fair repriced at the spot prevailing at each later moment
=> this isolates VOL decay from DELTA P&L, i.e. it is the DELTA-NEUTRAL capture.
Script: `measure_overshoot.py`. Data: `overshoot_measured.csv`.

## ⚠ TWO OF MY OWN BUGS, FOUND AND FIXED — the first inflated the headline 4.5x
1. **Pre-spike IV was inverted against the POST-spike spot.** For an up-spike on a call this pairs a
   higher spot with a lower (pre-spike) price => understates iv_pre => understates fair value =>
   **INFLATES the measured overshoot.** Corrected to use the actual pre-spike spot.
   **Effect: mean overshoot 9.58 pts -> 2.12 pts. Median +9.40 -> -0.16.** The bias ran in the
   flattering direction; any quote of ~9.6 pts is WRONG and must not be reused.
2. **Decay was measured on raw price change**, which conflates vol decay with delta P&L from continued
   spot movement (it showed -0.18 pts, i.e. apparently NO decay, which would have killed the idea).
   Corrected to excess-over-fair repriced at the prevailing spot.

## RESULT 1 — the overshoot is REAL but far smaller and rarer than observed
| metric | value |
|---|---|
| mean overshoot | **+2.12 pts** |
| **median** | **-0.16 pts (i.e. the TYPICAL spike produces NO overshoot)** |
| share positive | 48.6% (a coin flip) |
| share >= 3 pts | **30.6%** |
| share 3-10 pts | 16.6% |
| mean IV jump | 0.71 vol pts |
| p90 / max / min | +14.22 / +153.33 / -59.52 |
**So the Principal's 3-10 pt figure describes ~31% of events, not the typical one. The mean is carried
entirely by a right tail.** By era: post-Oct-2024 2.50 vs pre 1.92. Held-out 2026 1.99 vs build 2.13.

## RESULT 2 — the excess DOES revert (this is the tradeable part)
| horizon | residual excess | CAPTURED | % of overshoot |
|---|---|---|---|
| +15 min | 1.52 | 0.60 | 28.5% |
| +30 min | 1.04 | 1.08 | 50.9% |
| **+60 min** | 0.35 | **1.77** | **83.7%** |
Unconditionally, 1.77 pts captured vs **~1.45 pts of cost (Rs25/lot/side + ~0.4/side slippage)**
=> **breakeven at best. The pure vol-crush is NOT tradeable unconditionally.**

## ★ RESULT 3 — CONDITIONING ON OVERSHOOT SIZE IS MONOTONIC (dose-response = real mechanism)
| overshoot bucket | n | %evts | mean over | cap@30m | cap@60m | NET (-1.45) | win@60m |
|---|---|---|---|---|---|---|---|
| <=0 | 2384 | 51.4 | -3.99 | 0.44 | 0.90 | **-0.55** | 44.1% |
| 0-3 | 831 | 17.9 | 1.32 | 0.76 | 1.50 | +0.05 | 51.7% |
| 3-7 | 540 | 11.6 | 4.68 | 1.39 | 2.15 | +0.70 | 60.9% |
| 7-14 | 400 | 8.6 | 9.90 | 2.29 | 3.37 | +1.92 | 65.5% |
| **>14** | 478 | 10.3 | 24.60 | 3.48 | **4.87** | **+3.42** | **71.8%** |
Monotonic across ALL five buckets in capture AND win-rate, and the no-overshoot bucket LOSES money —
the correct sanity check. This is a dose-response relationship, not a fitted subset.

## ★ RESULT 4 — THE >=3pt FILTER, and the era result that makes this the session's best candidate
Filtered: **n=1,418 (30.6% of events, ~24/month), mean overshoot 12.87, captured 3.41, NET +1.96 pts.**
| split | n | NET pts |
|---|---|---|
| **post-Oct-2024** | 550 | **+2.74** |
| pre-Oct-2024 | 868 | +1.47 |
| build | 1,283 | +1.86 |
| **held-out 2026** | 135 | **+2.92** |
| 0-1 DTE | 615 | **+2.56** |
| 2-7 DTE | 803 | +1.51 |
**BETTER post-break than pre-break, and BETTER on held-out 2026 than on build.** Every other candidate
this session DEGRADED through Oct-2024 (sweep 1.48->0.99, swing 2.44->0.51, breakout 1.28->0.84).
This is the first and only one that strengthened — consistent with the recency-screen finding that
vol-premium survived while directional died. Short DTE is better (higher gamma => bigger overshoot).

## ⚠ THREE CONSTRAINTS — none of these are resolved
1. **TAIL: worst single trade -75.5 pts vs mean gain 3.41 => 22.1x ratio.** p05 -8.5, p10 -4.8.
   One bad trade erases 22 good ones. Inherent to selling into a move that sometimes keeps going.
   **NOT yet tested on the named crisis dates (Omicron 2021-11-26, Ukraine 2022-02-24, election
   2024-06-04) — that test is OWED before this goes anywhere near capital.**
2. **CONCENTRATION: top 10% of trades = 55% of captured points.** Fails the top-decile-excluded gate.
   Per the Principal's own refinement (cost-stress is the right test at this frequency) the relevant
   number is the cushion: **breakeven at ~2.35x modelled cost** — thinner than SWEEP_E's 4.31x.
3. **CAGR CEILING — this is NOT the 100% CAGR strategy.** At 10% unhedged margin (~Rs187k/lot at
   spot 25000 => ~5 lots on Rs10L): 24 trades/mo x 1.96 pts x 75 ~= **28%/yr**. At 5% hedged margin
   ~**46%/yr**. Real and good, but do not represent it as 100%+.

## ★ THE UNMEASURED HALF — the obvious next test
Everything above is the **DELTA-NEUTRAL vol capture only** — i.e. the Principal's "extra 3-10 points"
BONUS. His main course, the **10-30 point directional retracement**, is stripped out by construction.
**NEXT: run the same >=3pt filter UNHEDGED (sell the inflated option outright, no delta hedge) so both
legs are captured, and compare against (a) the delta-neutral version above and (b) a plain delta-1 fade
of the same spike.** That three-way comparison decides whether this is a genuine vol edge, a
mean-reversion trade in options clothing, or both. Also owed: resting-limit entry (fill iff 1-min HIGH
>= limit, with a 1-tick haircut) vs next-bar entry, and hedged 5% vs unhedged 10% margin on return-on-capital.

## TIER
**FORWARD-TEST CANDIDATE** (not CERTIFIED). Mechanism is stated and dose-response confirmed; holds
out-of-sample and improves post-break; but the tail is unquantified on crisis dates, concentration is
high, and the cost cushion is thin. Trials: this measurement adds ~5 cells to the ledger (firm cumulative
was 466); the conditional buckets are descriptive, not separate strategy trials.
