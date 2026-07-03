# ALPHA RESEARCH PROGRAM — hunting the next-10-year dimension
### Master plan + hypothesis sub-plans. Built 2026-06-16. Resume-first.

> **Honest premise:** a source "never heard of / humans unaware" is a contradiction —
> if reasoning finds it, others find it. DURABLE alpha comes from 4 moats only:
> **(A) Access** (data/speed/mandate), **(B) Constrained flows** (forced participants),
> **(C) Complexity** (fuse many weak signals / harder math), **(D) Early to a new
> modality** (alt-data~2010, LLM-text~2023→). We hunt at the FRONTIER of B+C+D in
> the LESS-EFFICIENT Indian market, scoped to small capacity (an asset, not a limit).
>
> **THE LEAD NEW DIMENSION (our bet):** stop predicting *price direction* (TA, saturated)
> and *value* (crowded). Predict the **STATE & FRAGILITY of the market's own
> participants** — model the market as observable constrained agents (dealers, retail
> F&O, passive funds, leveraged shorts) and harvest their FORCED, predictable actions
> and the liquidity fragility they create. Direction-agnostic. Capacity-limited =
> perfect for ≤₹10Cr. This is under-formalized everywhere and barely touched in India.
>
> **RESUME:** read this, then run the research loop on the highest-ranked un-killed
> hypothesis. Python: `C:\...\pythoncore-3.14-64\python.exe`. We already have: 1-min
> Nifty/BankNifty/VIX (2015-26), NSE F&O EOD bhavcopy w/ OI (2021-26), Angel live API
> (chain/OI/quotes), daily equity universe. Strong starting position.

---

## THE RESEARCH LOOP (apply to every hypothesis — anti-overfit by construction)
1. **Frame** a falsifiable hypothesis + the economic WHY (which moat? who is forced?).
2. **Cheapest possible test** on data we have → effect size + sign.
3. **Adversarial verify** (try to kill it: regime split, IS/OOS, alt explanation, costs).
4. **Decision**: KILL (write why), or PROMOTE (deeper data, WFO, capacity test).
5. **Deflated-Sharpe / PBO** gate before any capital. Log every kill (negative results
   are the asset — they stop us re-testing folklore).

---

## HYPOTHESIS PORTFOLIO (ranked; each = a sub-plan). Test top-down.

### H1 — Dealer-gamma / options-positioning fields (India) ★ LEAD, data-ready
- **Moat:** B (dealer hedging is forced) + A (OI observable, under-used in India).
- **Why:** US "GEX/vanna/charm" flow trading is mature; India isn't. Dealers short
  gamma must buy-high/sell-low (amplify moves) or long gamma dampen (pin). Observable
  from option OI by strike/expiry — which we already pull (bhavcopy + Angel chain).
- **Test:** build daily/intraday net-gamma-exposure & "zero-gamma flip" level for
  Nifty from OI; test whether price (a) pins to high-OI strikes into expiry, (b)
  trends when below zero-gamma / mean-reverts above it, (c) the flip level acts as
  support/resistance. Effect size vs random.
- **Sub-tasks:** 1 reconstruct OI surface from bhavcopy; 2 estimate dealer sign
  (heuristics: calls/puts, OI change vs price); 3 compute GEX & flip; 4 event-study
  price behaviour around flip & high-OI strikes; 5 tradeable rule + cost test; 6 IS/OOS.
- **KILL if:** no statistically robust price-conditioning on gamma state after costs.

### H2 — Retail-F&O forced-action / behavior prediction (India-specific) ★ data-ready
- **Moat:** B (retail is constrained & predictable) — uniquely large/observable in India.
- **Why:** Indian retail F&O participation is enormous & behaviorally patterned: OTM
  lottery buying, expiry-day pin/unwind, margin-call cascades, herding into momentum.
  SEBI data: ~90% lose — their predictable losses are someone's edge.
- **Test:** proxy retail positioning from OI concentration in far-OTM weeklies, the
  put/call OI skew, expiry-day OI unwind patterns; test whether their crowded side
  predictably loses / gets squeezed. Fade extreme retail positioning.
- **Sub-tasks:** 1 retail-proxy from OTM OI & turnover; 2 crowding metric; 3 forward
  return of fading crowding; 4 expiry-day unwind timing; 5 rule + IS/OOS + costs.
- **KILL if:** retail-proxy has no forward predictive content OOS.

### H3 — Liquidity-fragility / "air-pocket" prediction (direction-agnostic) ★ niche, small-cap
- **Moat:** B + C, capacity-limited (ideal ≤₹10Cr).
- **Why:** Predict WHEN the book becomes fragile (thin depth, one-sided, gamma trap)
  rather than direction — then trade the resulting discontinuity (straddle the event /
  provide liquidity into the air-pocket). Most research predicts direction; fragility
  is under-modeled.
- **Test:** from 1-min data build fragility features (range expansion, volume dry-up
  then spike, gap frequency, intrabar reversals); test if high-fragility state precedes
  outsized realized moves → buy cheap convexity only then (flips our short-vol: BUY
  vol selectively when fragility predicts realized>implied).
- **Sub-tasks:** 1 fragility feature set; 2 predict next-window realized vol; 3 does it
  beat VIX-implied as a realized-vol forecaster?; 4 conditional long-gamma rule; 5
  IS/OOS, costs. (Note: this could be the LONG-side complement to our short-vol edge —
  buy vol only on predicted-fragile days, sell otherwise.)
- **KILL if:** fragility features don't beat implied as a realized-vol predictor OOS.

### H4 — Information-propagation geometry (lead-lag network)  small-cap niche
- **Moat:** C. **Why:** shocks diffuse through related instruments (supply-chain,
  sector, ownership, co-movement) with a LAG; trade the laggard. Under-researched in India.
- **Test:** learn a lead-lag graph (Granger / transfer-entropy / lagged correlation)
  across the equity universe; when a "leader" moves, forward-test the "follower."
- **Sub-tasks:** 1 build co-movement/lead-lag graph; 2 stability of edges OOS; 3 event-
  study follower response; 4 tradeable lagged-momentum rule; 5 capacity (small-caps) + costs.
- **KILL if:** lead-lag edges are unstable OOS (likely fragile — test honestly).

### H5 — LLM "narrative-state" extraction (not sentiment — inflection)  modality D
- **Moat:** D + A. **Why:** beyond bag-of-words sentiment — use an LLM to track the
  EVOLVING consensus narrative around a name/sector and detect INFLECTIONS (the story
  changing) before price. Under-covered Indian mid/small-caps + regional disclosures.
- **Test:** LLM-summarise rolling news/filings/calls into a "narrative state"; detect
  state-change; forward return after inflection. Start with a small labeled set.
- **Sub-tasks:** 1 corpus (news/filings for N names); 2 LLM narrative-state pipeline;
  3 inflection detector; 4 forward-return event study; 5 cost/latency feasibility.
- **KILL if:** narrative-inflection has no forward edge beyond price momentum.

### H6 — Meta-regime / edge-aliveness allocator (the "dimension of dimensions")
- **Moat:** C. **Why:** every micro-edge decays/regime-switches. The alpha of KNOWING
  WHEN each edge is live (and allocating across H1–H5 + our 0DTE short-vol + swing
  momentum) may exceed any single edge. Non-stationarity AS the signal.
- **Test:** build a meta-model that predicts each sleeve's near-term Sharpe from a
  market-state vector (VIX, breadth, gamma-state, dispersion, trend); allocate dynamically.
- **Sub-tasks:** 1 sleeve return panel; 2 state vector; 3 predict-then-allocate; 4 does
  dynamic allocation beat static equal-risk OOS?; 5 overfit guard (few states, simple model).
- **KILL if:** dynamic allocation doesn't beat static OOS (overfit risk high — be strict).

### H7 — Reflexivity / squeeze game-theory (Soros, formalized)  speculative
- **Moat:** B+C. **Why:** model belief↔fundamental feedback & cross-participant
  positioning (dealers+retail+shorts) to detect self-reinforcing moves (gamma/short
  squeeze, expiry pin) early and their exhaustion. Combine H1+H2.
- **Test:** define squeeze-precursor state (high short OI + gamma + crowding); forward
  study of squeeze magnitude. **KILL if** precursors don't predict squeezes OOS.

### H8 — FII/DII & participant-wise flow (India institutional flow) ★ HIGH VALUE, observable
- **Moat:** B (large constrained institutional flows) + A (NSE/SEBI publish them daily —
  uniquely transparent in India). The dominant directional driver of Indian equities.
- **Why:** FIIs/DIIs move the index; their daily cash + F&O flows, and NSE participant-
  wise OI (client/FII/DII/pro long-short), are PUBLISHED. Persistent flow → trend; flow
  exhaustion/divergence → reversal. Index-rebalance & passive flows are forced & dated.
- **Test:** ingest daily FII/DII cash & index-fut/options flow + participant-wise OI;
  test (a) flow persistence predicts next-day/week index direction, (b) FII-vs-DII
  divergence as a signal, (c) extreme FII F&O net-position as a contrarian/continuation
  signal, (d) index-reconstitution front-running of forced passive buying.
- **Sub-tasks:** 1 scrape/store FII-DII daily + participant-wise OI (NSE) + index-rebal
  calendar; 2 flow features (net, momentum, divergence, extremes); 3 forward-return study;
  4 regime use (risk-on/off) feeding the meta-allocator H6; 5 rule + IS/OOS + costs.
- **KILL if:** flows have no forward predictive content beyond price momentum OOS.
- NOTE: this is also a top input to SYSTEM 5 (data-edge) in `..\OPERATING_STANDARD_2026.md`.

---

## PHASES (program-level)
- [ ] P1 Frontier scan: deep-research the 2024-26 literature on flow/microstructure,
      gamma/positioning, LLM-signal, fragility — confirm what's known vs open (use the
      deep-research harness). Update rankings.
- [ ] P2 Data layer: OI-surface reconstruction (bhavcopy + Angel), equity panel, news/
      filings corpus for H5. Reuse the options project's pipeline.
- [ ] P3 Run the research loop on H1 → H2 → H3 (data-ready first), logging kills.
- [ ] P4 Promote survivors to WFO + capacity test (≤₹10Cr) + deflated-Sharpe gate.
- [ ] P5 H6 meta-allocator over all survivors + the existing 0DTE & swing sleeves.
- [ ] P6 Paper → live (small), monthly edge-decay review.

## ANTI-OVERFIT DISCIPLINE (binding)
Small grids; one-shot OOS; deflated Sharpe + PBO; demand an economic WHY (which moat?
who is forced?) BEFORE believing any backtest; log every kill; capacity-test everything
(if it only works at <₹10Cr, that's fine — it's the moat — but KNOW it).

## NEXT-SESSION ENTRY POINT
→ P1 frontier scan (optional, fast) THEN H1 sub-task 1: reconstruct the Nifty OI/gamma
surface from `intraday_options_strategy\datasets\raw\options\fo_*.csv` (we have OI by
strike/expiry 2021-26) → compute GEX & zero-gamma flip → event-study price behaviour.
H1 is data-ready TODAY and is the highest-conviction new dimension.
