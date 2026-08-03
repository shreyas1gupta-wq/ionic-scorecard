# FINDINGS — PLEDGE_SAFE_20260802
Rs 50L G-sec (8%) + Rs 50L equity MF (12% assumed), both pledged, margin run through S1-F
(frozen spec) as a yield overlay, +/- a partial protective-put hedge. Red-teamed
(`07_RISK_OFFICE/ADVERSARIAL_REVIEWS.md`, 2026-08-02 entry, verdict FRAGILE with a stated
flip-to-REAL condition) — the flip condition (F1/F2 veto applied + D-1-lagged sizing in the COVID
rerun) has been met; see corrected numbers below.

## Headline
| Scenario | Combined CAGR | Combined MaxDD | vs bond+MF-only baseline | vs RISK_LIMITS 20% COVID bar |
|---|---|---|---|---|
| Calm 2021-2026, flat 8%/12% assumption | +15.14% | -1.51% | degenerate baseline (0.00% DD) — not informative | n/a |
| Calm 2021-2026, REAL NIFTY500 for MF | +15.08% | **-6.96%** | baseline -9.81% (yield HELPS) | n/a |
| COVID 2020-21, yield overlay only, **corrected** | — | **-20.17%** | baseline -18.57% (yield HURTS) | **FAILS** (barely) |
| COVID 2020-21, yield + 50%-notional protective put, **corrected** | — | **-17.53%** | baseline -18.57% (BEATS baseline) | **PASSES** |
| Calm 2021-2026, yield + hedge | +14.59% | -7.09% | mild cost vs yield-only (~-0.5pt/yr, ~+0.1pt MaxDD) | n/a |

## The corrected-vs-original story (why the correction mattered)
First COVID pass (`run_covid_stress_rerun.py`) reused an existing S1-F COVID backcast
(`SELLSIDE_20260710/covid_backcast`, model-validated corr=0.64) that runs every Thursday
unconditionally — it does NOT apply the frozen spec's F1/F2 vetoes. Red-team checked the two
worst days behind the original -23.34% headline (2020-03-19 -Rs454,388; 2020-03-26 -Rs436,312)
directly against the same 1-min spot series and confirmed BOTH would be vetoed live (D-1 RSI5=11.4
and D-1 ret -4.75%/+5.71%). 76% of the 20Feb-10Apr-2020 window's scheduled days would veto.
Red-team also caught a real (if modest) same-day sizing lookahead: `book_now` used that day's
already-known MF close rather than D-1's — a T3-class leak, biased toward UNDERSTATING lots
(hence losses) through the selloff.

`run_covid_stress_rerun_v2_corrected.py` fixes both (veto computed from the same 1-min data,
D-1-lagged book_now for margin_budget). Corrected result: yield-only MaxDD improves from -23.34%
to **-20.17%** — still a real, if narrow, breach of RISK_LIMITS.md's own pre-existing COVID-stress
bar ("book survives if drawdown <20%", line 17) and still worse than simply holding bond+MF. Adding
the protective-put hedge (same correction applied) brings it to **-17.53%** — passes the bar
comfortably and now beats the passive baseline outright.

## Verdict
**Yield-only does not meet "very very safe" by the firm's own pre-existing bar** — real in calm
markets (-6.96% MaxDD, options overlay net-additive vs baseline), but in a corrected COVID
reconstruction it modestly breaches RISK_LIMITS.md's 20% line and underperforms just holding the
pledged assets. **Yield + a 50%-notional rolling protective put (5% OTM, ~30D, roll T-5) does meet
it** — passes the firm's bar in the corrected crash scenario, beats the passive baseline there, and
only costs ~0.5pt/yr of CAGR and ~0.1pt of MaxDD in calm markets. Recommended structure if
"protect capital" is the binding mandate.

## Standing caveats (disclosed, not resolved this session)
1. **Settlement/liquidity channel not modeled**: a bad expiry-day options loss is booked as a cash
   ledger entry; the model never asks whether covering it in practice requires posting fresh cash
   or partially de-pledging collateral — a liquidity/forced-sale question distinct from "margin cap
   breach" (0 cap breaches were verified, but that is close to tautological given lots is
   floor-computed from the cap by construction).
2. **No GFC-class scenario tested** — `nifty500.parquet` starts 2016-01-04, `NIFTY 50_minute.csv`
   starts 2015-01-09; a prolonged multi-year grinding bear (2008-style) is untested, not ruled
   favorable or unfavorable.
3. **Haircuts are labeled assumptions** (10% G-sec / 30% equity MF) — no single citable current
   NSE/CDSL rate exists for either (scheme-specific, published only in the live approved-securities
   list); verify against the actual bond/fund's ISIN on Angel's pledge calculator before treating
   any margin number here as actionable. Red-team separately checked the haircut-tightening-in-
   crisis mechanism specifically and found the 40%-of-book cap has ample structural buffer against
   it (would need an implausible ~60% blended haircut to bind) — this part is not a live concern.
4. **Put-calendar family (separate side-thread, `PUTCAL_LADDER_20260802`) is dead/inconclusive, not
   usable for this portfolio**: 45D/15D calendars lose money regardless of roll timing (T-5:
   t=-3.41, clearly dead; T-2: t=-1.87, indistinguishable from random-timing noise). 90D/30D is
   mildly positive (+5.4pts/rung, beats 63% of random-timing draws) but t=0.69 — underpowered, not
   proven, flagged as a forward-test candidate only, not a component of the recommended structure.
