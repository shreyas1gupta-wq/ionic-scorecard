# CAMPAIGN OPT-SWEEP-50 — 50 NIFTY option setups, Phase-1 triage queue
_Intake 2026-07-07 · R&D (Aditya Verma) · Principal-commissioned sweep · stage 1-INTAKE (campaign, not a single hypothesis)_

## 0. What this is / two-phase mandate
Principal brief (2026-07-07): sweep 50 "popular or claimed-highly-profitable" NIFTY option-selling/trading
setups, hunting for anything clearing **XIRR > 50% AND Sharpe > 2 POST-cost**.
- **Phase 1 (fast/cheap first pass):** rank all 50 by a light backtest — frictionless-to-1x-cost, index-liquid
  assumption, denominator-free rupee-points + %-spot per trade, ~2016→present where INDIA VIX exists. Rank, don't certify.
- **Phase 2 (Gate-4 certification):** full lookahead audit + 2× COST_STANDARDS + sensitivity/DSR/PBO + red-team
  ONLY on the top 3–5 Phase-1 survivors.
- This file is BOTH the campaign intake one-pager AND the ranked spec list. A separate parallel track (Arjun) runs
  4 Principal-specified concrete tests (zscore mean-reversion, RSI(5) extremes) — **NOT duplicated here** (all my
  conditional entries are return/VIX/skew-based, none RSI- or price-zscore-based).

**Bar realism [OPINION]:** Sharpe>2 AND XIRR>50% post-cost is aggressive. Firm reality: S-04 (our one certified
short-vol sleeve) honest edge is ~+0.22%/spot managed; STRATEGY_RESULTS documents sustained 60% CAGR is not
honestly achievable on Indian equities. High-theta/high-frequency INDEX short-vol (0DTE, weekly) is the only
family with a structural shot at the bar — and it pays for it in left-tail. Rank accordingly.

## 1. Prior-art map (what is EXCLUDED / OWNED — read before queuing)
| Prior-art anchor | Status | Effect on this sweep |
|---|---|---|
| K-001 intraday option BUYING (~14 variants) | KILLED | Any intraday NIFTY option-buying setup = DUPLICATE-DO-NOT-RUN (resurrection only: sniper <5 trades/mo, net-+ after 2× cost) |
| K-002 reverse calendar / K-003 double calendar | KILLED (single-stock) | Calendar-family caution; index variants flagged, not free passes |
| K-004 long far-OTM high-IV | KILLED | Long-vol setups fight VRP; only the LOW-IV pre-catalyst variant is untested (resurrection) |
| K-005 0DTE iron condor (all configs) | KILLED | Plain 0DTE IC = duplicate; only a regime-gated (intraday IV-crush detector) variant is a resurrection |
| K-006 regime-gated naked selling | KILLED | Trend/DMA-gated naked selling caution |
| K-012 / S-03 FF calendar CE | KILLED (stays-killed 2026-07-05) | Do NOT resubmit FF-calendar/event CE-selling. Term-structure SIGNAL already graduated to a NEW liquidity-native intake (Aakash) |
| S-01 IV/RV short straddle (single-stock) | SEND-BACK, paper-only | Index IV/RV variant = OVERLAPS-S-01 (extension, not new family) |
| S-02 earnings/event short-vol | FAILS-PRE-IC | Pre-event IV-crush straddle = OVERLAPS-S-02 (already killed pre-IC) |
| S-04 short strangle 14DTE managed (single-stock) | CERTIFIED → paper-watch | Index strangle variants EXTEND S-04 (new vehicle/underlier), note overlap |
| S-05 delta-hedged 0DTE/1DTE index straddle (0.45% filter) | Paper-ready | 0DTE/1DTE index straddle setups = OVERLAPS-S-05 |
| Track-3 dealer-gamma/GEX gate | 1-INTAKE (Ishaan) | GEX-conditioned setups = OVERLAPS-Track3 (+ GEX data has a cadence gap) |
| expiry_seasonality intake | 1-INTAKE | Expiry-pin / turn-of-month / reconstitution / day-of-week = OVERLAPS-expiry_seasonality |
| VRP 9-filter replication (Agarwal 2025) | Intake queue | VRP-composite short straddle = OVERLAPS-queued replication |

**Governing lessons wired into every spec (KNOWLEDGE_BASE §A):**
- VRP is the meta-edge — selling wins, buying loses. Buying families scored LOW by default (A.1).
- Report edge in denominator-free RUPEE POINTS + %-of-SPOT, never return-on-premium (A.2/A.8 — three sleeves died of this).
- **Exitability wall (A.14):** 61% of the killed calendar's SINGLE-STOCK back-legs fired into dead (zero-vol/OI) markets.
  NIFTY INDEX options are deep → index setups sidestep this; any SINGLE-NAME multi-leg setup (dispersion, single-stock
  conversion) inherits the wall and is scored down. Run a fill-rate/existence check BEFORE sizing/sensitivity.
- Pre-register the entry-fill convention (same-day-close vs D+1) — it alone swings ~1pp/₹100 (A.17).
- Tails are survivable only at portfolio level: small size × staggered entries × inverse-IV × event gates (A.4).
- Stops gap through and bought wings bleed theta on this book (A.4, K-008/K-009).
- **CIO book rule #1:** ALL short-vol setups draw down TOGETHER in a vol spike — this whole sweep is one correlated
  risk cluster; a survivor's real test is incremental Sharpe over the existing short-vol book, not standalone Sharpe.

## 2. RANKED master list (Phase-1 queue order — highest credibility/distinctness first)
Score = rough credibility × distinctness (1–5), used only to ORDER the triage queue. Ties broken by cheapness/breadth-of-information.

| Rank | ID | Setup | Score | Prior-art | One-line thesis |
|---|---|---|---|---|---|
| 1 | OS-04 | VIX-percentile-gated short strangle | 5 | NEW | VRP is fattest when IV-rank is high; only sell when INDIA VIX percentile > 60 → harvest richest premium, skip cheap-vol regimes |
| 2 | OS-01 | Weekly NIFTY short strangle ~16Δ, managed | 5 | NEW-EXTENDS-S-04 | Bread-and-butter VRP harvest on the deepest book; the benchmark every other setup must beat |
| 3 | OS-07 | Laddered / rolling short strangle (staggered DTE) | 5 | NEW | Always ~3 staggered weekly strangles live → smooths carry, de-clusters the April-2026-style correlated blowup (A.4) |
| 4 | OS-05 | Inverse-IV-sized short strangle | 4 | NEW-EXTENDS-S-04 | Operationalize our own tail lesson: size ∝ 1/IV (corr −0.23 with future worst-case) — bigger in calm, smaller in fear |
| 5 | OS-06 | Delta-neutral rebalanced short strangle | 4 | NEW-EXTENDS-S-05 | Strip direction; earn pure VRP + gamma-rent by re-hedging to 0 delta at drift bands |
| 6 | OS-29 | Jade lizard (short put + short call spread) | 4 | NEW | VRP + put-skew harvest with NO upside tail (net credit ≥ call-spread width) — defined-risk on the dangerous side |
| 7 | OS-11 | Weekly iron condor (20Δ short / 10Δ wing), non-0DTE | 4 | NEW (K-005 is 0DTE only) | Defined-risk VRP; wings cap the tail the naked strangle leaves open |
| 8 | OS-20 | Short put after a down-day (dip-buy via short puts) | 4 | NEW | Post-selloff IV pop + mean-reversion: sell OTM put after NIFTY −X% day, collect fear premium into the bounce |
| 9 | OS-03 | Monthly (30-DTE) short strangle 12–15Δ, managed | 4 | NEW-EXTENDS-S-04 | Lower gamma, higher capacity DTE-variant of the core; the "slow" VRP benchmark |
| 10 | OS-08 | 0DTE expiry-day short straddle theta scalp | 4 | OVERLAPS-S-05 | Max theta/day on expiry; sell ATM straddle at open, defined intraday stop, flat by close |
| 11 | OS-02 | Weekly short straddle ATM, delta-hedged daily | 4 | OVERLAPS-S-05 | S-05 extended from 0DTE to a held weekly straddle with daily delta hedge |
| 12 | OS-38 | VIX-regime position-sizing OVERLAY on the short-vol book | 4 | NEW (overlay) | Not a standalone edge — a sizing multiplier (scale exposure with IV-rank) tested as an uplift on OS-01/03 |
| 13 | OS-27 | Put ratio spread (sell 2 OTM / buy 1 nearer) | 3 | NEW | Harvest steep put skew; defined-ish downside via the long put, credit financing |
| 14 | OS-45 | Intraday short strangle scalp (sell AM, cover PM) | 3 | OVERLAPS-S-05 | Capture intraday theta/vol-crush without overnight gap risk; flat every night |
| 15 | OS-13 | Weekly iron fly (short ATM straddle + wings) | 3 | NEW | ATM VRP + pin capture with capped tails; higher credit than condor |
| 16 | OS-30 | Risk reversal (sell put / buy call) when put-skew rich | 3 | NEW | Skew trade: monetize expensive puts to fund cheap calls when skew z-score extreme |
| 17 | OS-41 | INDIA VIX mean-reversion via short vol after a VIX spike | 3 | NEW | VIX is mean-reverting; sell straddle/strangle the day AFTER a VIX pop, exit on VIX normalization |
| 18 | OS-24 | Synthetic wheel (cash-settled index: short put → short call rotation) | 3 | NEW | Continuous premium engine; rotate short-put / short-call by realized assignment proxy — popular retail, cash-settled adaptation |
| 19 | OS-39 | IV/RV short straddle on the INDEX | 3 | OVERLAPS-S-01 | Extend the IV/RV≥1.4 short-straddle rule from single stocks to NIFTY |
| 20 | OS-33 | Post-event vol-reset short strangle | 3 | NEW (distinct from S-02) | Sell AFTER the event once IV stays elevated but realized collapses (not the killed pre-event crush) |
| 21 | OS-35 | Expiry-day pin ATM straddle short | 3 | OVERLAPS-expiry_seasonality | Max-pain pinning on expiry; sell ATM into the pin, post-Sept-2025 Tuesday regime only |
| 22 | OS-12 | Monthly iron condor 30-DTE, 25Δ short | 3 | NEW | Slow defined-risk condor; the low-turnover VRP variant |
| 23 | OS-10 | Mechanical roll strangle (roll tested side out-and-up) | 3 | NEW-EXTENDS-S-04 | Never take the loss at the strike: roll the challenged side at 21-DTE / breach — tests whether rolling saves or bleeds |
| 24 | OS-09 | 0DTE expiry-day short strangle (wider, defined stop) | 3 | OVERLAPS-S-05 | Wider-than-straddle 0DTE for lower gamma; defined intraday stop |
| 25 | OS-40 | VRP 9-filter composite short straddle | 3 | OVERLAPS-queued (Agarwal repl.) | Only enter when ≥k of 9 VRP-robustness filters agree; the literature-hardened selector |
| 26 | OS-14 | Broken-wing butterfly (skew-tilted) | 3 | NEW | Zero/near-zero cost fly shifted to harvest skew; convex payoff around a target zone |
| 27 | OS-21 | Short call after an up-day (rally-fade call write) | 3 | NEW | Mirror of OS-20: fade exhaustion pops by writing OTM calls after a strong up day |
| 28 | OS-28 | Call ratio spread (sell 2 OTM / buy 1) | 3 | NEW | Harvest call premium into grind-ups; credit trade with defined near-strike protection |
| 29 | OS-25 | Bull-put credit spread in an up-trend regime | 3 | K-006-ADJACENT | Directional-but-defined VRP: sell put spread when NIFTY>200DMA & up-momentum |
| 30 | OS-26 | Bear-call credit spread in a down-trend regime | 3 | K-006-ADJACENT | Mirror: sell call spread when NIFTY<200DMA & down-momentum |
| 31 | OS-31 | Put backspread into a catalyst (LOW-IV entry) | 2 | K-004-RESURRECTION | The one sanctioned long-vol variant: buy convexity only when IV is CHEAP pre-catalyst (K-004 resurrection condition) |
| 32 | OS-16 | NIFTY ATM calendar (sell weekly / buy monthly) | 2 | K-002/K-012-ADJACENT | Long term-structure carry on the LIQUID index (not the killed single-stock FF calendar) |
| 33 | OS-19 | VRP term-structure: sell weekly / buy monthly straddle, vega-neutral | 2 | OVERLAPS-FF-new-intake (Aakash) | Front-month vol richer than back; the liquidity-native term-structure trade Aakash already owns |
| 34 | OS-18 | Diagonal spread (sell near OTM / buy far further OTM) | 2 | K-002-ADJACENT | Calendar + directional tilt; theta-positive, long-vega |
| 35 | OS-34 | Turn-of-month short strangle | 2 | OVERLAPS-expiry_seasonality | Sell vol into the ±3-day month-turn window |
| 36 | OS-15 | 0DTE iron condor, REGIME-GATED (IV-crush detector) | 2 | K-005-RESURRECTION | Only fires when an intraday IV-crush regime is detected (the K-005 resurrection condition) |
| 37 | OS-36 | Results-season index vol selling (Jan/Apr/Jul/Oct) | 2 | NEW (event-cluster) | Index-level realized vol often lags implied through earnings clusters; sell the index vol, not single names |
| 38 | OS-22 | Systematic OTM covered call on NIFTYBEES | 2 | NEW | Buy-write income overlay on an index long; classic, low-alpha, capacity-huge |
| 39 | OS-42 | Short vol gated by dealer-GEX regime | 2 | OVERLAPS-Track3 | Sell only in positive-GEX (mean-reverting/pinned) regimes — but GEX data has a known cadence gap |
| 40 | OS-49 | Bull-call / bear-put debit spread, trend-following | 2 | NEW (directional buying) | Defined-risk directional; fights VRP on the buy side, needs a real trend edge to overcome debit |
| 41 | OS-23 | Zero-cost collar overlay on a NIFTY long | 2 | NEW | Long index + long put funded by short call; risk-reduction overlay, not an alpha source |
| 42 | OS-37 | Day-of-week weekly-expiry seasonal short | 2 | OVERLAPS-expiry_seasonality | Sell on the historically-best weekday into expiry; post-Sept-2025 regime only |
| 43 | OS-46 | Box-spread carry (synthetic rate arb) | 2 | NEW | Near-riskless implied-financing carry; tiny edge, entirely cost/liquidity-gated |
| 44 | OS-47 | Conversion / reversal (put-call-parity) arb | 2 | NEW | Monetize parity dislocations; market-neutral, tiny edge, execution-bound |
| 45 | OS-17 | NIFTY double calendar (CE+PE) index | 1 | OVERLAPS-K-003 | Index version of the killed double calendar; index-liquid but PE-leg was dead weight in K-003 |
| 46 | OS-44 | Gamma scalping (long straddle + delta hedge) | 2 | K-004-ADJACENT | Long-vol: profits only when realized > implied — structurally against VRP |
| 47 | OS-48 | Dispersion (short index vol / long constituent vol) | 2 | NEW but EXITABILITY-FLAG | Classic vol-arb; single-name long legs hit the A.14 exitability wall + capacity/margin |
| 48 | OS-32 | Pre-event IV-crush short straddle (RBI/Fed/Budget) | 2 | OVERLAPS-S-02 (killed pre-IC) | Sell into the event, harvest the crush — the exact family already killed pre-IC as ≈ generic short-vol |
| 49 | OS-50 | Long call/put swing on a NIFTY momentum breakout | 1 | K-001-ADJACENT (buying) | Directional option BUYING; fights VRP, theta+slippage historically ate every timing edge |
| 50 | OS-43 | ORB option BUYING (CE/PE on opening-range breakout) | 1 | DUPLICATE-K-001 | Intraday NIFTY option buying — explicitly in the killed family; listed for completeness, DO-NOT-RUN unless sniper-resurrection |

## 3. Backtest-ready specs (grouped by family; underlier = NIFTY index options unless noted)
Common Phase-1 conventions (pre-registered): entry-fill = **next-liquid-quote after signal, NOT same-day-close** (A.17 optimistic bound reported separately); no-fill on circuit-locked/zero-vol bars (drop, D-031); 1-min data filtered to ≥09:15 (auction bug); INDIA VIX from `datasets/index_daily/` (2016→); edge in ₹-points + %-spot; lot = 75 (current NIFTY). Expiry-day/day-of-week items: **post-Sept-2025 Tuesday-expiry regime cut, do NOT pool across the break.**

### Family A — Short strangle / straddle (VRP core; index-liquid, sidesteps A.14)
- **OS-01** entry: every Mon (weekly cycle) · position: SELL 1× ~16Δ (≈1SD) CE + ~16Δ PE, 5–7 DTE · exit: 50% max-profit OR expiry OR 2× credit stop.
- **OS-02** entry: Mon · position: SELL ATM straddle 5–7 DTE, hedge delta daily to 0 with NIFTY fut · exit: expiry / 50% profit.
- **OS-03** entry: monthly, ~30 DTE at start · position: SELL 12–15Δ strangle · exit: 50% profit / 21-DTE roll / 2× stop.
- **OS-04** entry: any weekly cycle WHERE INDIA-VIX percentile(1yr) > 60 · position: SELL 16Δ strangle 5–7 DTE · exit: 50%/expiry/2× stop. Cheap-test = OS-01 conditioned on the VIX gate; the kill is "gate adds nothing over unconditional OS-01."
- **OS-05** entry: weekly · position: SELL 16Δ strangle, **qty ∝ min(k/IV, cap)** (inverse-IV sizing) · exit: as OS-01. Compare to flat-size OS-01 on risk-adjusted terms.
- **OS-06** entry: weekly · position: SELL ATM/16Δ strangle, re-hedge to 0 net delta at ±0.10 delta drift bands · exit: expiry/50%.
- **OS-07** entry: staggered — open one new weekly 16Δ strangle each week so ~3 overlapping tenors are always live · exit: each leg at 50%/expiry. Tests whether staggering cuts the correlated-drawdown tail vs OS-01.
- **OS-08** entry: expiry morning 09:20 · position: SELL 0DTE ATM straddle · exit: 15:15 flat OR intraday 1.5× credit stop.
- **OS-09** entry: expiry morning · position: SELL 0DTE ~10Δ strangle (wider) · exit: flat by close / defined stop.
- **OS-10** entry: monthly 30-DTE strangle · management: roll the challenged side out-and-up at 21 DTE or on breach, keep credit ≥0 · exit: final expiry. Tests roll-vs-close.
- **OS-45** entry: 09:20 daily · position: SELL near-ATM weekly strangle · exit: 15:15 flat (no overnight). Intraday-only theta capture.

### Family B — Iron condor / fly / butterfly (defined risk)
- **OS-11** entry: Mon weekly · position: SELL 20Δ CE+PE, BUY 10Δ wings · exit: 50% profit / expiry.
- **OS-12** entry: monthly 30-DTE · position: SELL 25Δ, BUY ~10Δ wings · exit: 50%/21-DTE.
- **OS-13** entry: Mon · position: SELL ATM straddle + BUY ~10Δ wings (iron fly) · exit: 25–40% profit (fly profit-take is tighter).
- **OS-14** entry: weekly · position: broken-wing butterfly skewed to the put side (finance the fly with skew) · exit: expiry / target zone.
- **OS-15** entry: expiry day WHEN intraday IV-crush regime flag = true (needs the detector built first) · position: 0DTE IC · exit: flat by close. **K-005 resurrection — gated on building the regime detector; do not run plain 0DTE IC.**

### Family C — Calendars / diagonals (calendar graveyard — score-capped, index-only)
- **OS-16** SELL weekly ATM, BUY monthly ATM (net debit calendar) · exit: at weekly expiry, close both. Long-vega, theta-positive.
- **OS-17** double calendar CE+PE on index · **note K-003 killed the PE leg as dead weight — Phase-1 must test each leg standalone.**
- **OS-18** diagonal: SELL near ~10Δ, BUY far ~5Δ further out · exit: near expiry.
- **OS-19** vega-neutral: SELL weekly ATM straddle, BUY vega-matched monthly ATM straddle · exit: weekly expiry. **Aakash already owns the term-structure intake — coordinate, don't duplicate.**

### Family D — Conditional directional premium
- **OS-20** entry: on a day NIFTY closes ≤ −1.0% (tune threshold) · position: SELL 20–25Δ PE, 3–7 DTE · exit: 50% profit / 2-day time stop / expiry. (Return-threshold trigger — distinct from Arjun's RSI(5).)
- **OS-21** entry: day NIFTY closes ≥ +1.0% · position: SELL 20–25Δ CE · exit: as OS-20.
- **OS-22** hold NIFTYBEES; each month SELL 1-month ~5% OTM CE against it · exit: expiry, re-write.
- **OS-23** hold NIFTYBEES; BUY 5% OTM PE funded by SELL 5% OTM CE (collar), quarterly · exit: roll quarterly.
- **OS-24** SELL 20Δ PE; if breached ("assigned" proxy = spot < short strike at expiry) rotate to SELL 20Δ CE next cycle; else re-sell PE · continuous.
- **OS-25** entry: NIFTY > 200DMA & positive 20-day momentum · position: SELL 20Δ bull-put spread · exit: 50%/expiry. **K-006-adjacent: pre-register that the regime gate must beat unconditional.**
- **OS-26** entry: NIFTY < 200DMA & negative momentum · position: SELL 20Δ bear-call spread · exit: 50%/expiry. Same K-006 caveat.

### Family E — Ratio / skew / risk-reversal
- **OS-27** SELL 2× ~15Δ PE, BUY 1× ~25Δ PE (put ratio, net credit) · exit: 50%/expiry.
- **OS-28** SELL 2× ~15Δ CE, BUY 1× ~25Δ CE · exit: 50%/expiry.
- **OS-29** SELL 1× ~20Δ PE + SELL a call spread (short ~20Δ CE / long ~10Δ CE) sized so net credit ≥ call-spread width (no upside risk) · exit: 50%/expiry.
- **OS-30** entry: put-skew z-score (25Δ-PE IV minus 25Δ-CE IV) at a rich extreme · position: SELL PE / BUY CE (risk reversal) · exit: skew normalizes / time stop.
- **OS-31** entry: pre-catalyst WHEN IV-rank is LOW · position: BUY 2× far OTM / SELL 1× nearer (backspread, net ~0 cost) · exit: post-catalyst. **K-004 resurrection — only sanctioned long-vol variant; must enter cheap vol.**

### Family F — Event / seasonality (overlaps expiry_seasonality intake + killed S-02)
- **OS-32** SELL ATM straddle the session before RBI/Fed/Budget, exit T+1 after crush. **= killed S-02 family; included only to re-confirm the kill on the INDEX (single-stock version died pre-IC).**
- **OS-33** entry: 1–2 sessions AFTER the event, WHEN IV-rank still elevated but realized has collapsed · SELL strangle · exit: IV normalizes. Distinct-from-S-02 (post- not pre-).
- **OS-34** SELL 16Δ strangle over the ±3-session month-turn window · exit: end of window.
- **OS-35** SELL ATM straddle expiry morning (pin capture), Tuesday-regime only · exit: close.
- **OS-36** SELL index strangle through Jan/Apr/Jul/Oct results clusters · exit: cluster end.
- **OS-37** SELL weekly on the historically-strongest weekday into expiry (event-study first) · post-Sept-2025 only.

### Family G — VIX / regime / VRP composites
- **OS-38** OVERLAY: multiply OS-01/OS-03 position size by a function of IV-rank (e.g. 0.5×–1.5×); measured as incremental Sharpe over flat sizing, NOT standalone.
- **OS-39** SELL ATM index straddle WHEN IV/RV ≥ 1.4 (IV<100% cap), 14–21 DTE · exit: managed. **= S-01 rule ported to index.**
- **OS-40** SELL ATM straddle WHEN ≥k of the 9 Agarwal VRP filters agree · exit: managed. **Coordinate with the queued replication.**
- **OS-41** entry: session after INDIA-VIX jumps > +Xσ · SELL straddle/strangle · exit: VIX reverts to its 20-day mean / time stop.
- **OS-42** SELL strangle only in positive dealer-GEX (pinned) regimes · **Track-3 owns GEX; data has a cadence gap (402/~1300 days) — fix before running.**

### Family H — Structural / arb & long-vol (score-capped)
- **OS-43** BUY CE/PE on 15-min opening-range breakout, intraday · **DUPLICATE-K-001, DO-NOT-RUN** (listed for completeness).
- **OS-44** BUY ATM straddle, delta-hedge; profit if realized>implied · long-vol, against VRP.
- **OS-46** construct a box (bull-call + bear-put same strikes) capturing implied financing vs MMF rate · exit: expiry. Cost/liquidity-gated.
- **OS-47** conversion (long spot-synthetic + short call + long put) on parity dislocation · market-neutral, tiny edge.
- **OS-48** SELL NIFTY straddle, BUY basket of constituent straddles (dispersion) · **single-name long legs hit A.14 exitability wall + margin/capacity — flag before any build.**
- **OS-49** BUY bull-call (uptrend) / bear-put (downtrend) debit spread on breakout · defined-risk directional buying.
- **OS-50** BUY swing CE/PE on a NIFTY momentum breakout, multi-day hold · **K-001-adjacent buying; fights VRP.**

## 4. Red-flag clusters (surface for the Principal / CIO)
1. **One correlated short-vol tail (the big one).** ~34 of the 50 are net-short vol (Families A/B/D/E/F/G). Per CIO
   book rule #1 they ALL bleed together in a vol spike (April-2026 one-day cluster is the firm's scar). A high
   standalone Sharpe here is largely regime beta — the real Phase-2 test is INCREMENTAL Sharpe over the existing
   short-vol book (S-04/S-05), and portfolio-level tail sizing, not standalone metrics. Expect the "XIRR>50/Sharpe>2"
   winners to cluster in 0DTE/weekly high-theta — precisely where the left tail is fattest.
2. **Buying cluster fights the firm's strongest prior (VRP, A.1).** OS-43/OS-44/OS-49/OS-50 (and long-leg-heavy
   OS-31/OS-48) are buying/long-vol; every buying family we have tested died (K-001, K-004). Scored 1–2; OS-43 is a
   flat DUPLICATE. Kept in the list only so the sweep is honestly complete, not because they're expected to clear the bar.
3. **Calendar graveyard.** OS-16/17/18/19 are term-structure/calendar — the exact structure of K-002/K-003/K-012.
   Index liquidity removes the single-stock exitability cause of death but NOT the structural short-theta-of-term-
   structure risk; OS-19 duplicates Aakash's live intake. Score-capped ≤2; do NOT let them consume Phase-2 slots
   ahead of Family-A survivors.
4. **Overlap-with-owned (don't burn budget re-testing).** OS-32 (=killed S-02), OS-39 (=S-01), OS-40 (=queued VRP-9),
   OS-42 (=Track-3 GEX), OS-34/35/37 (=expiry_seasonality). These are legitimate to include for completeness but
   should be run as CONFIRMATIONS routed to their existing owners, not fresh families.
5. **Single-name exitability wall (A.14).** OS-48 dispersion and OS-47 conversion (if run on single names) inherit the
   dead-back-leg problem that killed K-012 — a fill-rate/existence check MUST precede any sizing work.
6. **Aggressive-bar realism.** No firm sleeve has ever shown honest post-2×-cost Sharpe>2; treat any Phase-1 setup that
   prints it as a denominator/fill/lookahead artifact until Phase-2 proves otherwise (A.2/A.8/A.14/A.16/A.17 are the
   usual culprits).

## 5. Phase-1 triage queue (execution order) & kill design
Run in ranked order (Section 2). Recommended batching for the fast pass:
- **Batch 1 (establish the VRP benchmark):** OS-01, OS-03 (baselines) → then the conditioners OS-04, OS-05, OS-07, OS-06
  measured as uplift vs baseline. A conditioner that doesn't beat its unconditional parent is killed (A.19 overlay rule).
- **Batch 2 (defined-risk & conditional):** OS-11, OS-29, OS-20, OS-13, OS-27.
- **Batch 3 (0DTE/intraday high-theta):** OS-08, OS-02, OS-45, OS-09 — flag tail behavior explicitly.
- **Batch 4 (confirmations of owned/overlap + low-score):** route OS-39/40/42/32/34/35/37 to existing owners; the ≤2
  score items get a one-line confirm-or-kill, not a full pass.

**Phase-1 pre-registered kill (per setup):** frictionless-to-1x per-trade edge ≤ 0 in ₹-points AND %-spot, OR edge
present only when pooled across the Sept-2025 expiry regime break, OR edge vanishes under next-liquid-quote fill (vs
same-day-close), OR (for conditioners) fails to beat its unconditional parent. Survivors (target top 3–5) advance to
Phase-2 Gate-4.

## 6. Trials-ledger note (DSR honesty)
This campaign adds ~40 NEW backtest line-items + ~10 overlap/confirm items to the firm's option-family trials count.
Every Phase-1 run — including kills — is counted toward the relevant family's DSR when any survivor reaches Gate-4
(A.20 turnover-matched comparator + honest trials count apply). The short-vol strangle family already carries S-04's
prior trials; OS-01/03/04/05/06/07/10 extend that ledger, they do not start a fresh one.

_Provenance: mined KILLED_IDEAS.md (K-001..K-015), STRATEGY_REGISTER (S-01..S-06), KNOWLEDGE_BASE §A (lessons 1–21),
imported_research (GOD_TIER D7/D8, STRATEGY_RESULTS), and the active ideas/ intakes (expiry_seasonality, dealer_gamma_gex).
No new external data proposed — all setups run on data already cataloged (stocks_options dual schema, index_daily VIX,
NIFTY 1-min). Any new-data need surfaces at Phase-2 via the Data Officer D-009 gate._
