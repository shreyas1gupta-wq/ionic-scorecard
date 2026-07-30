# KILLED IDEAS — graveyard with resurrection conditions (D-012)
Append-only. Every kill: what, when, WHY (evidence), and the SPECIFIC condition that would reopen it. Kills are conditional, never dogma — count them in the family trials ledger.

| # | Idea family | Killed | Evidence | Resurrection condition |
|---|---|---|---|---|
| K-001 | Intraday NIFTY option BUYING (~14 variants: ORB, mean-rev, shakeout, doji, gap-fade, regime-gated, 0.7Δ/0.3Δ combos, expiry-vol-breakout, Europe-open, RSI/MACD/S-R timing...) | 2026-06 | ALL net-negative after costs across 2021-26; VRP means buyers structurally overpay; theta+slippage eat every timing edge tested | A sniper-entry variant with <5 trades/mo showing net-positive after 2× COST_STANDARDS on a fresh OOS window |
| K-002 | Reverse calendar (BUY near / SELL far) | 2026-07 | −174% cumulative; structurally short theta-of-term-structure the wrong way | None foreseseen — structural (would need persistent term-structure INVERSION regime detector) |
| K-003 | Double calendar (CE+PE both legs) | 2026-07 | Forward-NEGATIVE on both 88 and 210 universes (−4..−8% fwd at every FF threshold, both slippage tiers) while single-CE positive — PE leg is dead weight (put skew keeps back PEs rich) | PE-leg variant profitable on its own forward window |
| K-004 | Long far-OTM options at high IV (IV>60%, IV/RV>2 "cheap convexity") | 2026-07 | Loses at every distance (−12..−39%); high IV = wings expensive; buying pre-earnings IV = eating the crush; n small and IV prints partly bad | LOW-IV pre-catalyst long-vol variant (buy cheap vol BEFORE the market prices the event) — untested, legitimate |
| K-005 | 0DTE NIFTY iron condor (all configs) | 2026-06 | Negative all parameter cells | Regime-gated variant if intraday IV-crush regime detector built |
| K-006 | Naked-PE-below-50DMA & other regime-gated naked selling variants | 2026-06 | No robust improvement over unconditional; several negative | New regime feature with WALK-FORWARD proof |
| K-007 | Gap-fade CE/PE selling (0.3/0.6/0.9% gates, SL grid) | 2026-07 | Not robust across build/forward after the pre-open-auction bug fix | Re-test post-2026 only if gap-frequency regime returns |
| K-008 | Stop-losses on FF calendars | 2026-07 | Gaps jump through stops (worst only −249%→−182%); loose stops INCREASE blowups 7→11 via whipsaw of recoverable trades | Intraday (not EOD) stop engine with real fill modeling |
| K-009 | Pre-bought both-wing hedges on FF calendars | 2026-07 | Theta bleed kills mean (+16.7%→+1..14%); far-OTM single-stock wings unpriceable (stale prints → −883% artifact) | Index-wing overlay (liquid) hedging a single-stock calendar BOOK, not per-trade wings |
| K-010 | Retro-fit "landmine blacklist" for strangle stocks | 2026-07 | LOOKAHEAD — picked by realized outcomes; only modest persistence (fwd worst −6.2% vs −3.8%) | N/A — replaced by ex-ante inverse-IV sizing + liquidity gate + adaptive stop-list (see KNOWLEDGE_BASE) |

| K-011 | Gold/Silver ETF as SAME-DAY crash hedge | 2026-07-04 | Pre-registered kill tripped: gold mean on worst equity-decile days −0.017% (<0), 39% hit; 2021-23 −0.05%. Uncorrelated (tail corr −0.05) but NOT reliably positive when equities bleed; 85/15 overlay worsened worst-month (−1.83%→−2.40%) despite raising ann. return (+5.1%→+7.6%). No true crash in window; equal-weight proxy smooths stress days. results/gold_silver/20260704_cheaptest | (a) retest vs TRUE NIFTY index incl. a real crash (extend GOLDBEES pre-2021 via NSE bhavcopy/second source, cover 2020 COVID); (b) the DIFFERENT hypothesis "strategic low-corr return sleeve" (corr +0.07, gold rallying) needs its own one-pager — not killed, not claimed |

| K-012 | FF calendar single-CE (FF≥0.25, the last original sleeve) | 2026-07-04 | THIRD denominator artifact (pnl/CE_be back-premium); denominator-free RUPEE POINTS, large-cap gate: build +5.85pts → forward **−9.30pts** (2024 −2.2, 2025 −10.8 — loses real money); confirms the FF-decay observation from pre-firm memory; honest trials ≥20 | **RESURRECTION REVIEW CLOSED 2026-07-05 (CIO ruling): STAYS-KILLED-WITH-NEW-INTAKE.** Signal REAL (Nikhil: 100th pctile vs turnover- AND premium-matched placebos) but VEHICLE DEAD: pre-registered causal gate (Arjun) fwd -0.03/Rs100 @1x, -2.36 @2x, BUILD -0.51 (negative in-sample too); 61% of fwd back-leg markets dead (Tara). Calendar vehicle NOT resurrectable. REVISED CONDITION: only via a NEW liquidity-native vehicle (index / liquid-underlier / short near-next serial calendar) meeting 5 pre-registered kills -- see K-012 review trail below + CIO_RULING.md. NO paper signal-tracking (EXPLORATORY +0.99 same-day dies at 2x). Trail: results/S-03/20260705_resurrection/ |

| K-013 **RESURRECTED same day** (condition met: corrected frictionless terminal p75 = 17.13%; LowVol50-Q 17.46% clears +0.33pp -> Gate-4 per pre-registration) | N500 LowVol50 sleeve — QUARTERLY | 2026-07-04 | KNIFE-EDGE/BAR-ARTIFACT kill: passes (a) +2.88pp at 2x, (b1) mean +3.8pp, (c), (d) -44.2%; misses ONLY pre-registered (b2) "beat p75 frictionless" — but no frictionless p75 exists on disk AND the p75 is a chained path-of-percentiles (fictional always-lucky path, inflated bar). Pre-registration honored, goalposts not moved. Quarterly beat monthly on EVERY axis (turnover 173->110%) | Ishaan ships a proper per-path FRICTIONLESS p75 (percentile of terminal-path CAGRs); if LowVol50-Q 17.46% fric beats it -> straight to Gate-4. Diversifier one-pager (orthogonality to short-vol book) stands for IC independent of p75 |
| K-014 | N500 MQ50 sleeve — SEMIANNUAL | 2026-07-04 | CLEAN STRUCTURAL kill: fails a/b/c/d (2x 10.10% vs 12.74% hurdle; maxDD -74.6%). Semiannual holds let momentum winners round-trip — frictionless collapsed 18.94->12.34%; the edge decays faster than the cost saved. Quality-leg coverage 23% (momentum-fallback majority) | Only a QUARTERLY MQ50 variant beating hurdle+0.5pp at 2x with maxDD > -50%; semiannual MQ = structurally dead |

| K-015 | N500 mom-lowvol dynamic-regime basket (monthly, VIX-median switch) | 2026-07-04 | KILLED on pre-registered K2a: dynamic net-1x 21.54% LOSES to its own pure-momentum parent 26.38% — the regime layer DILUTED a stronger static factor (classic vol-timing noise), though it did cut vol (15.0 vs 20.7%) and maxDD (-46 vs -67%). Turnover-banded variant didn't rescue. Self-red-team catch: pre-2016 regime proxy was poisoned by a stale-print unfreeze (VAIBHAVGBL +400% fake print) — fixed via stale-mask + sanity cap BEFORE verdict | Only as a RISK-TARGETING overlay judged on risk-adjusted terms (Sharpe/DD budget), never on raw CAGR vs parents; or with a demonstrably predictive regime signal (not trailing-median VIX) |

### K-012 -- FF calendar resurrection review CLOSED 2026-07-05 (CIO ruling: STAYS-KILLED-WITH-NEW-INTAKE)
Principal-triggered review ("check once again if we were too hard on them"). Four evidence legs, `results/S-03/20260705_resurrection/`:
- **Sameer (sensitivity): PLATEAU** -- 30/30 cap x FF cells forward-positive, chosen cell dead-center (+0.99% vs neighborhood median); BUT conditional on the non-causal engine -- every absolute number an optimistic ceiling. Equal-premium sizing basis is load-bearing, cap second-order. +30 family trials.
- **Nikhil (red team): EDGE-BEYOND-SIZING, overall FRAGILE** -- FF signal REAL at 100th pctile vs BOTH turnover-matched and CE_be-matched (same-premium) placebos (sizing-alone ~0; trade-everything fwd -0.45; inverted FF flips sign to -4.76). Caught a NEW T9 argmax-FF entry lookahead in forward_factor_v2.py (v1 was causal, v2 silently non-causal). Dies at ~3.3x costs.
- **Tara (fill audit): MARGINAL +3.88/Rs100** -- 61.3% of fwd signals fire into DEAD back-leg markets (zero volume, mostly zero OI); even mega-caps (APOLLOHOSP/SUNPHARMA/BRITANNIA/COLPAL) show 100% fwd drop; drop-rate is 95% of the gap, slippage only 5%; the headline worst trade -464% (BOSCHLTD) was itself unfillable.
- **Arjun (PRE-REGISTERED FINAL GATE): FAILS** -- causal entry + ex-ante gate + D+1 fills + tiered 1x -> fwd **-0.03/Rs100 (-0.07 deploy-wtd)**, **-2.36 at 2x**, **BUILD -0.51** (never honestly positive, in or out of sample), survivor PF 0.99. Ex-ante liquidity gate is COUNTER-PRODUCTIVE: it admits weaker fillable trades (gating +0.99 < dropping +3.88). Vehicle death, not signal death.

**CIO ruling (Rajan Mehta):** the CALENDAR VEHICLE is CONFIRMED KILLED (both the edge <=0 AND an exitability tail-veto: 61% dead markets = un-exitable inventory). The FF term-structure SIGNAL graduates to a NEW, DISTINCT intake (Structurer/Aakash) with 5 pre-registered kills -- this is NOT a resurrection of K-012. DSR/PBO recompute is MOOT (edge <=0 before any multiple-testing correction). NO paper-desk signal-tracking (rejected as scope creep against the pre-registered FAIL; EXPLORATORY same-day +0.99 dies at 2x and is fenced out of the verdict). Full reasoning + tail-risk section + dissents-by-name: `results/S-03/20260705_resurrection/CIO_RULING.md`.

## Watch-list (not killed, demoted pending proof)
- FF calendar on MID-CAPS: fwd edge thins (+6-7%) and single trades hit −141% (KAYNES) — demoted to large-cap-only until liquid-back-month gate is coded.
- Mid-cap earnings short-vol: lottery-like (+150%/−31% swings) — large-cap gate + DTE≥7-to-expiry rule pending codification.

## K-air-pocket-overlay (2026-07-11) — air-pocket leg-buyback on S1
**Killed by:** B2-CARD pre-registered variant test (frozen @ 9e82e72), all 3 bars failed (delta -0.23 pts/day; worst-10 +5.9 vs +15 bar; SL-day -0.16). Source lead was T6 CONTROL-group find (+4.4 pts/30min t=3.94, low-OI strike crossings) — explicitly flagged full data-mining risk at intake; the required variant test did not confirm monetization.
**Mechanism of failure:** early buyback surrenders decay on false triggers (-1.87 pts/day on no-SL days) and saves little on true ones (trigger fires when leg already >=10% underwater, i.e., close to the 30% SL anyway).
**Resurrection conditions:** (a) futures-MFT construction (trade the traverse directly at 2-pt hurdle, NOT as an S1 exit) — own frozen card, weakened prior declared; or (b) A-family timing variant — own frozen card. NO re-tuning of trigger thresholds/OI deciles on this dataset (that would be fishing the same sample).

## K-stock-meanrev-standalone (2026-07-11) — RSI3/zscore pullback buying in stage-2 uptrends
**Killed by:** T-B-CARD (frozen @ e4de961), both cells: net -0.15%/-0.19% per trade, t=-4.8/-7.2, n=21k/30k, both eras negative, 2015-2026, PIT universe, 25bps/side. Short-hold (2-5d) mean reversion cannot cover retail swing costs in NIFTY500 names.
**Residual:** +0.28% relative edge vs placebo (random stage-2 days, same exit) - the timing information is real, the standalone vehicle is dead (same class as ORB kills: signal real, vehicle dead on friction).
**Resurrection:** entry-timing overlay on trades/investments already being made (zero marginal cost context) as a NEW pre-registered card. NO standalone re-tests at different RSI/z thresholds (t=-5 to -7 is not a tuning problem).

## K-postbreakout-orb (2026-07-11) — ORB 5/15min in stocks during post-breakout weeks (Principal idea)
**Killed by:** T-C-CARD (frozen @ 4692e17): gross -11.1 bps/trade BEFORE costs (t=-16.3 net, n=6,646, 2022-2026 minute data, PIT breakout events from audited scan). Overnight-hold variant noise (t=0.54, era-flip). The hypothesis (breakout stocks trend harder intraday) is BACKWARDS in the data: they fade opening-range triggers during the post-breakout weeks.
**Family closure:** with the 07-07 basket kills + puts vehicle + this, intraday ORB on Indian stocks is killed across universes, windows, stops, vehicles, and event-conditioning. Resurrection bar: a construction with POSITIVE GROSS edge >= 40bps demonstrated first on new data (not parameter reshuffles).

## K-AF07-stage-turn (2026-07-12) — the red-team killing its own discovery
**Killed by:** AF-07 certification battery. Honest episode-level re-measurement: -0.28%/trade (n=348, ALL signals) vs stock-shuffle placebo +1.64% and date-shuffle placebo +4.05% — the turn signal is WORSE than random entries with the same exits. 3/8 years positive. 
**Root cause of the false +24.1%/Sharpe 1.26:** forge_engine methodology defects — (1) max_conc slot queue arbitrarily SELECTED a favorable trade subset; (2) stat_windows computed Sharpe on active-days-only (inflates sparse sleeves). BOTH now deprecated: all sleeve claims must use episode-level measurement + the 5-test battery.
**Propagation:** ALL ALPHA_FORGE wave-A numbers carry the same defects — AF01 Sharpe 3.83 etc. are UNTRUSTED until episode-level re-measurement. Wave-A table demoted to leads-only.
**Lesson (KB-grade):** the placebo-with-same-exits test is the ONLY reliable arbiter in drifting markets; engine-level portfolio simulations can manufacture edges from queue mechanics alone.

## K-B1c-DII-flow (2026-07-12) — killed by 0.07 t on a certify-or-kill card
**Killed by:** B1c-CARD (frozen @ 83259ac): t=2.43 vs 2.5 bar. 4/5 bars passed: +26.5 bps/trade (n=374), beat shuffle95 (+24.3), lag-decay present, beat random-days t-null (2.31), eras strengthening +11.7 -> +44.4. The single-shot card had no park by design (lattice family budget spent) - honored.
**Resurrection condition (FORWARD DATA ONLY):** zero-size shadow ledger of the signal (daily DII 5d-flow rank, q>=0.8 -> 3d hold) accruing from now; re-decision after 60 forward signals. NO in-sample re-tests, NO threshold changes. The signal's t at n=374 is sample-limited; only new data can settle it.

## K-adx-atr-family (2026-07-12) — 8 constructions, 0 pass
**Killed by:** ADX-ATR battery (frozen @ de0cc36), literature-standard Wilder-14/chandelier params, same-exit placebos x100-200. Indices/gold/short/squeeze/compression at-or-below placebo; stocks long-hold (n=14,666) shows ADX-confirmation entries earn HALF of random stage-2 entries with identical exits.
**Mechanism:** ATR trails are good EXITS (credit belongs to the exit); ADX entry gating buys extended and is negative selection. **Reusable lesson: any "trend confirmation" entry filter must beat the same-exit placebo, and this one never has.**
**Resurrection:** none for ADX-entry constructions; ATR-exit components remain free to use inside other systems (no re-test needed - they are exits, not signals).

## K-016 NIFTYBEES↔GOLDBEES ratio-Donchian rotation (2026-07-13) — external spec (Kiru podcast), Principal-ordered test
**Killed by:** pre-registered card (frozen pre-run) — KR-R1 FAIL (net CAGR 9.79% vs bar 10.93%; MaxDD −32.96% vs bar −21.8%), KR-R3 FAIL (cost drag 3.16pp/yr at 7.4 switches/yr × 0.426%). Real ETFs 2013→2026 incl. COVID, t+1-open exec, approved costs. results/KIRU_PKG/20260713/.
**Mechanism of the illusion:** edge concentrated in the breakout bar itself — same-bar exec shows 29.4% CAGR, honest next-open 9.8% vs B&H 11.9%. Claimed vol/DD reduction false on 13.5yrs (vol HIGHER than B&H; worst DD −33% in 2024-26). N20 = worst neighbor (fragile exact spec).
**Reusable components:** (a) **50/50 monthly-rebal NIFTY-gold BENCHMARK dominates** (12.29% CAGR / 10.47% vol / −21.49% DD) — evidence FOR K-011's unclaimed strategic-gold-sleeve, routed to Devika; (b) any gold-rotation retest must beat the 50/50 benchmark, not B&H.
**Resurrection:** (1) as timing OVERLAY on a 50/50 base (tilt 70/30, not 100/0 switches — halves whipsaw cost); (2) monthly-frequency variant with drag <1pp/yr AND t+1-open CAGR ≥ B&H AND DD ≤ 0.7× B&H; (3) integration with the banked VIX-252d-percentile regime gate. GT-2 signed-corr template applies to any corr claim.
**Addendum 2026-07-13 (Principal: "execute 15:25-15:30"):** that execution = the 12.44%/−25.3%DD variant (recovers ~2.6pp overnight drift vs next-open), NOT the 29.4% same-bar row (unreachable at any clock time — books the day's move in the asset chosen at that day's close). CAGR prong then passes but DD + cost prongs still fail; 50/50 rebal still dominates → kill stands. Resurrection path (2) is the right door if pursued.

## K-017 — Inverse-VRP niche, Niches 2 & 3 (2026-07-29/30) — the ARM's premise survives, two of its four candidate niches don't
**Context:** ARM-level hypothesis (buyer wins only where RV_realized>IV_priced) tested across 4 candidate
niches, real 1-min option P&L via `OPTION_PL_HARNESS_20260729/opt_pl.py`, COST_STANDARDS D-021.
Full detail + scripts + CSVs: `results/INVERSE_VRP_NICHE_20260729/` (PREREG.md pre-registered
before any run).
**Niche 2 — post-compression expansion, pure REALIZED-vol trough (trailing-10d RV percentile≤10),
long ATM straddle, hold to expiry:** KILLED on both pre-registered criteria — net mean **−26.13
pts/straddle** (n=47, t=−1.10), WORSE than the unconditional baseline (−22.93 pts/trade, n=245).
Historical calm alone (independent of whether IV was cheap) does NOT identify a buyable edge —
confirms the ROADMAP's tautology warning: RV mean-reverting off a compressed base does not imply
the buyer wins if IV re-priced concurrently. **Resurrection:** none for pure-RV conditioning alone;
subsumed by Niche 1 (IV-percentile), which DOES show a (weak) effect — see IDEA_PIPELINE.
**Niche 3 — overnight tail BUY, mirror of NS-1 (which killed the SELL side 2026-07-25):** buy 1×CE+1×PE
at 5 strike distances (0/0.5/1.0/1.5/2.0% OTM), D−1 15:25→D0 open, n=258-259/arm, same population as
NS-1. KILLED on the pre-registered criterion — **net pts/night negative at EVERY distance** (−3.2 to
−6.8 pts/night FULL sample, t=−2.2 to −2.6 FULL / −3.3 to −3.9 BUILD-only). The fat right tail IS real
and event-driven (best nights land on 2026-02-03 and 2022-02-24, the Russia-Ukraine invasion — not data
artifacts, skew +5 to +7, best single night +228 to +443 pts) but it is NOT large or frequent enough
(win rate only 6-23%, falling as distance widens) to overcome the frequent small overnight decay losses
plus costs. **The buy-side mirror of NS-1 loses money on average, exactly as the seller's small-positive
edge implies it must** (these are ~complementary, not identical, populations once costs are netted on
each side, but both point the same direction: no exploitable structure in raw overnight NIFTY option
holding, buy or sell, beyond NS-1's already-banked ~5pt gross/night ceiling).
**Resurrection (either niche):** only a construction that changes WHICH nights are entered (a filter,
not unconditional entry) — e.g., an ex-ante flag for scheduled-event eve (see Niche 4/K-pending below)
— tested as a NEW pre-registered cell, not a re-run of the unconditional population.
