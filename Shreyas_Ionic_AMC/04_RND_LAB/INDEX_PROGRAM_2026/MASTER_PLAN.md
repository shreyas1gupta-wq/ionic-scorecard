# INDEX TRADING RESEARCH PROGRAM 2026 — MASTER PLAN
**Shreyas_Ionic_AMC · drafted 2026-07-10 · owner: CIO (Rajan) / R&D (Aditya) · status: DRAFT for Principal + CEO/CIO joint approval**
**Ambition: institutional-grade research discipline (Jane Street/Graviton rigor) on retail rails (Angel One + Kotak Neo APIs, 1-min granularity, MFT–LFT horizons: minutes → months). NO real money without explicit Principal approval at the final gate (standing rule).**

---

## 0. FIRST PRINCIPLES — what retail CAN and CANNOT win

**Cannot win (do not research):** latency races, queue position, market-making spreads, cross-venue arb, anything requiring tick data or co-location. Sub-minute signals are structurally unavailable to us (Angel/Kotak REST+WS ≈ 0.5–3s round trip; our backtest invariant "fill at next 1-min close" stays MANDATORY in every design).

**Can win (the entire program lives here):**
1. **Risk premia harvesting** — VRP is proven in-house (S1-F live in paper; stock earnings short-vol live). Retail is not disadvantaged in holding risk premia; institutions' size is a handicap here, our smallness is the edge (D-031: ₹10L–10cr capacity band).
2. **Slow information** — daily flows/positioning (participant-wise OI, FII/DII), regime and macro conditioning, calendar structure. Publication lags level the field.
3. **Structural/behavioral patterns** — expiry mechanics, pinning, event premia, overnight risk transfer: effects measured in hours–days, not milliseconds.
4. **Breadth of honest experimentation** — our real edge over other retail: the falsification machine (pre-registration, frozen bars, trials ledger, era splits, adversarial verifiers). Most retail curve-fits; we kill. 33+ documented kills to date is an asset.

**Known constants (measured this week, do not re-derive):** intraday price-derived signal ceiling ≈ 2.4 pts/30–60min (16-indicator screen); option BUYING needs ≥6 pts → closed (18 designs); minute-OI exists and carries the one confirmed intraday lead (air-pocket +4.4 pts, t=3.9); 0DTE ATM spread ≈ 1.24 pts one-way median (2× first 15 min); straddle margin ≈ 15% of notional.

---

## 1. DATA PLATFORM (Kavya owns; D-009 verification per source)

### Tier 0 — on disk today
| Dataset | Span | Granularity | Status/landmines |
|---|---|---|---|
| NIFTY spot (kaggle/Zerodha) | 2015→2026-05 | 1-min | naive IST; needs tail refresh pipeline |
| NIFTY weekly options + minute OI | 2021-06→2026-06 | 1-min | tz bug fixed in chain.py; OI 3-bar lag rule |
| Stock options (210 F&O names) | HF 1-min partial + bhavcopy daily 2024-04→ | mixed | DUAL SCHEMA landmine; 0.00-price no-fill guard |
| NIFTY500 daily + PIT universe snapshots | 2005→2025 | daily | survivorship-safe via 42 snapshots |
| Earnings PIT | long | event | available_date discipline |
| Breadth daily (built this week) | 2020→2025 | daily | catalog entry pending |
| Angel live capture | rolling | 1-min | 15:45 daily task, DESK-100 owned |

### Tier 1 — FREE, unbiased, no-lookahead; acquire in Phase 0 (all verified-source, office-network compatible unless noted)
| Dataset | Source | Why it matters | Lookahead rule |
|---|---|---|---|
| **F&O bhavcopy full history (index options/futures 2011→2021)** | nsearchives (verified working from office) | extends VRP/weekly-selling tests to 2011-2021 DAILY incl. 2013 taper, 2015-16, **2020 COVID at real prices** — kills the "no COVID in sample" caveat at daily granularity | trade date = file date; use next-day open for signals off settle |
| **India VIX daily** (+ intraday if archived) | NSE archives | regime conditioning, VRP richness gauge, crash rule v2 | published EOD → use D+1 |
| **Participant-wise OI (FII/DII/Pro/Client, index F&O)** | NSE fao_participant archives 2018→ | positioning signals: FII net index-futures/options flow — the classic slow-information edge | published ~T evening → signals effective T+1 09:20 ONLY |
| FII/DII cash provisional | NSE (403 at office → home/VPN run or NSDL) | flow regime for LFT allocation | T evening → T+1 |
| BANKNIFTY + MIDCPNIFTY + FINNIFTY spot & options bhavcopy | NSE archives | cross-index RV, rotation, dispersion-lite | as bhavcopy |
| Sector & factor indices daily | niftyindices (home network; /factor-indices skill exists) | LFT rotation, regime | EOD → D+1 |
| Index rebalance announcements | NSE/niftyindices press releases | rebal-flow event trades | announcement date stamped |
| S&P500/VIX/DXY/crude/UST daily | Stooq/FRED | overnight gap model (US close 01:30 IST → NIFTY 09:15 = genuine ex-ante info) | US close precedes our open — clean |
| USDINR reference | RBI | macro regime | daily |
| Rollover/expiry calendar hist | derive from bhavcopy | calendar structure | derived |
**Approval note:** all Tier-1 items are free official archives → still routed through Kavya's D-009 sample verification before ingestion (standing order). New PAID sources: out of scope.

### Tier 2 — infrastructure data
Kotak Neo API onboarding (2nd broker): live quotes redundancy, real margin calculator API (fixes our 15%-notional approximation), order-book depth L1/L2 snapshots for spread measurement going forward. Angel WS live feed (up to ~1000 tokens) → tick-to-1min store to progressively replace kaggle dependency.

---

## 2. ALPHA STREAMS (each = hypothesis family → pre-registered cheap test → Gate-4 → paper)

### Stream A — VRP CORE (extend the proven edge) · owner: Arjun/Structurer
Live: S1-F (0DTE ATM straddle). Extensions, in priority order:
- **A1 Weekly VRP term structure:** which DTE (0/1/2/4) is systematically richest? Sell-at-richest-DTE portfolio vs S1-F. Data: our minutes + bhavcopy backfill. Cheap test: realized-vs-implied by DTE bucket, 2011→2026.
- **A2 VIX-conditioned everything:** entry premium %-ile vs India VIX → does conditioning sizing on VIX beat the RV3 crash rule?
- **A3 Event-window VRP:** budget/RBI/Fed/election expiries — skip, harvest at half size, or harvest post-event crush? (Macro calendar exists; cyrus owns event tags.)
- **A4 2011–2021 daily-granularity replication of S1 family** on bhavcopy backfill (incl. COVID at REAL prices; settle-to-settle with SL proxy caveats documented) — the single most important robustness test remaining.
- **A5 Skew/risk-reversal dynamics:** 25Δ-proxy RR from our minute chains — does steep skew predict next-day index return or strangle asymmetric sizing (the S1b −50 gradient suggests yes)?
- **A6 Stock-vs-index dispersion-lite** (daily bhavcopy): sell index straddle vs buy top-5 single-name straddles at earnings clusters. Ties to live earnings short-vol book.

### Stream B — FLOW & POSITIONING (MFT, the new frontier) · owner: Aditya/Ishaan
- **B1 Participant-OI signals:** FII net index-futures Δ, long-short ratio extremes, client-vs-prop divergence → T+1 direction/vol forecasts. LITERATURE-KNOWN edge in India; never tested in-house. Cheap test: quintile forward returns 2018→2026.
- **B2 Air-pocket program (our confirmed lead):** +4.4 pts/30min underlying edge. Monetization candidates (buying is dead): (i) S1-F leg-management overlay — buy back the threatened leg on air-pocket cross, (ii) futures scalp MFT with 2-pt cost hurdle, (iii) entry-timing for A-family. Pre-registered variant test each.
- **B3 GEX proxy:** dealer-gamma sign from minute-OI chain (writers' net gamma by strike) → range vs trend day classification (T1 regime engine died on price; flow-based regime may not). Predicts S1-F win-rate?
- **B4 Max-pain/pinning:** drift-to-pain in last 2h of expiry — direction filter for S1-F leg bias (relates to S1b down-shift finding).
- **B5 Basis & rollover:** futures basis extremes, rollover-week (T-3→expiry) patterns from 15 yrs bhavcopy.

### Stream C — OVERNIGHT & GAP (MFT) · owner: Dhruv/Arjun
- **C1 US-close → NIFTY-open transfer model** (S&P/VIX overnight move, clean ex-ante): gap prediction → (i) gap-fade/follow rules on futures at open, (ii) S1-F F2-veto refinement (replace blunt 1.5% with predicted-gap model).
- **C2 Overnight VRP:** sell 1-2DTE at 15:20, buy back 09:20 (theta overnight vs gap risk) — memory says overnight drift lead exists; quantify honestly with gap-tail costs; likely kills itself on 2020 dailies → cheap.
- **C3 Expiry-eve effects:** positioning unwind day (now Monday) patterns.

### Stream D — CROSS-INDEX RV & ROTATION (LFT) · owner: Devika/Sanjay interface
- **D1 NIFTY/BANKNIFTY/MIDCPNIFTY relative value:** cointegration/spread mean-reversion at daily horizon (futures legs, not options); F9 killed at 30-60min — daily untested.
- **D2 Sector/factor rotation:** momentum of factor indices → monthly tilt sleeve (feeds equity book, not derivatives).
- **D3 VIX term/RV regime → sleeve allocator:** meta-model that throttles ALL sleeves (replaces per-strategy crash rules with book-level regime budget).

### Stream E — ML OVERLAY (only on proven bases) · owner: Ishaan
- **E1 Meta-labeling S1-F:** learn P(win|features: VIX, OI-flow, gap, skew, GEX) with purged walk-forward CV; deploy only as SIZE modulator (never entry veto without pre-registered live-shadow period). The F1/F2 vetoes are the manual baseline to beat.
- **E2 Regime HMM on (RV, breadth, VIX, flow)** — allocation states for D3.
- Hard rule: ML never invents signals; it recombines pre-registered ones. DSR accounting doubles for any learned model.

### Explicitly OUT (documented kills — do not resurrect without /resurrect evidence)
Intraday option buying all forms (K-001 + 18 designs); intraday technical entries as standalone (2.4-pt ceiling); regime-engine-as-buy-filter; PCR filters; iron-fly/near-wing hedging of S1 (wings cost > edge); weekly naked strangle at t<1; scalping V7 family.

---

## 3. EXECUTION & INFRASTRUCTURE (Manoj owns; "boring excellence")
1. **Dual-broker layer:** Angel (primary, data+orders) + Kotak Neo (failover, margin API, second rate-limit budget). Unified order-manager abstraction; simulated↔paper↔live behind one interface so backtest code = production code.
2. **Order mechanics per strategy class:** 09:20 basket entries (limit-through at close±buffer); SL as SL-LIMIT with protection band (exchanges restrict SL-M on options) — model = our next-close fill assumption; TCA logs every fill vs model (HALT gate: >3 pts/day drift over 13 expiries).
3. **Live data:** Angel WS (spot + active chain tokens) → 1-min bar builder with the auction/tz guards baked in; daily bhavcopy cron (extend existing 15:45 task); VIX + participant-OI daily pulls; heartbeat + /pipeline-health weekly.
4. **Rate budget doctrine:** hist candles ≥1.2s/req (AB1021), LTP 45-token batches, order burst ≤ broker caps (verify Kotak's on onboarding); every scheduled job registered in OPERATING_CALENDAR.
5. **Kill infrastructure:** one-command flatten-all (paper + live), daily loss circuit per RISK_LIMITS, stale-data breaker (no quotes 3 min → no new entries).

## 4. PORTFOLIO & RISK (Ritika/CIO)
- Target book (12-month vision): S1-F core + 2–3 orthogonal satellites (one flow-based MFT, one overnight/gap, one LFT rotation) + existing stock earnings short-vol. Orthogonality gate (RP-17) mandatory before any satellite joins.
- Margin model: dynamic 15%-notional until Kotak margin API live; book margin cap 75% equity; regime throttle (D3) supersedes per-sleeve crash rules when live.
- Tail doctrine: no naked short-vol through identified binary events (event gate stands); far-wing catastrophe insurance revisit at book level (Kabir) once ≥2 short-vol sleeves live.
- Sizing: 0.10–0.15 Kelly per sleeve, book VaR95 1-day ≤ 2.5% (var-sanity monthly).

## 5. VALIDATION CONSTITUTION (applies to every stream; Sameer enforces)
Pre-registration with frozen kill bars BEFORE any run · trials ledger + DSR at every IC · era splits mandatory (incl. 2011-2021 dailies once backfilled) · **2026-H2+ = embargoed holdout — no in-sample touch, ever** · dual cost models (calibrated flat-point AND %-of-premium; verdict must survive both) · next-bar fills invariant · one-day-lag lookahead test per lib/lookahead_audit.py · paper forward test = final arbiter (D-030 freeze) · red-team (Nikhil) before any Gate-5.

## 6. ROADMAP & BUDGET (90 days, then quarterly review)
**Phase 0 (wk 1–2) — Foundation sprint:** Tier-1 data acquisition (bhavcopy F&O backfill 2011→2021 is THE priority; VIX; participant OI; BN/MIDCP), catalog + D-009 checks, Kotak onboarding, runner hardening, S1-F paper live (started 14-Jul).
**Phase 1 (wk 3–6) — Cheap-test wave 1:** A1, A4 (COVID-era daily replication), B1, C1 pre-registered & run (scripts, ~zero tokens); B2 monetization trio; ≤12 registered trials. Decision gate: which 2–3 advance.
**Phase 2 (wk 7–10) — Gate-4 wave:** survivors get sensitivity/red-team/DSR; portfolio orthogonality; first monthly S1-F paper reconcile vs backtest (tracking report).
**Phase 3 (wk 11–13) — IC + assembly:** IC memos on advancing strategies; book construction proposal; quarterly program review; Principal decides paper-book expansion. LIVE decisions remain Principal-only, always.
**Token budget:** heavy compute = scripts (~0); agent spend gated on credit availability — Phase-1 designs are script-first by construction. DESK-100 executes; DESK-20 reviews/ICs.

## 7. SUCCESS METRICS (12 months)
- ≥25 pre-registered experiments run; ≥80% killed (a healthy kill rate is the quality signal)
- 2–4 strategies in paper with honest Sharpe estimates; ≥1 passing 26-expiry forward gate
- Book-level paper Sharpe ≥ 1.5 at ≤10% max DD before any live request
- Zero lookahead incidents; zero unregistered trials; TCA drift within gates
- Data platform: 15-yr index derivatives history, VIX, flows — all cataloged with guards

---
# ADDENDUM v1.1 — STEP-BY-STEP EXECUTION CHECKLIST (2026-07-10; deep-research citations deferred to token refresh — resume wf_8a976163-c45)

## PHASE 0 (weeks 1-2) — numbered, owners, outputs
1. [Kavya] Verify NIFTY weekly-options launch date (weeklies began ~Feb-2019; pre-2019 bhavcopy = MONTHLY only → A4 backfill = monthly-expiry variant pre-2019, weekly 2019+). Document in DATA_CATALOG.
2. [Manoj] bhavcopy F&O backfill job 2011→2021 (nsearchives, sequential, cookie warm-up, ~2600 files): download → parse → parquet per expiry → D-009 sample checks (5 random days vs NSE site). Output: datasets/fo_bhavcopy_hist/.
3. [Manoj] India VIX daily history pull + catalog. 4. [Manoj] participant-wise OI archive 2018→ + format-break map. 5. [Kavya] BANKNIFTY/MIDCPNIFTY spot+options bhavcopy. 6. [Manoj] S&P500/VIX/USDINR daily (Stooq/FRED/RBI).
7. [Principal] Kotak Neo API onboarding (keys); [Manoj] margin-calculator API smoke test → replace 15%-notional model with broker-quoted margins in all sizing sims.
8. [Manoj] S1-F runner hardening: SL-LIMIT order template w/ protection band, freeze-qty split logic (verify current NIFTY freeze qty), TCA log columns. First paper ticket 2026-07-14.
9. [Sameer] Trials-ledger consolidation: one CSV, every 2026-07 cell (~150), DSR baseline computed.
10. [Lakshmi] Literature-priors pass for streams A-E from public papers (deferred deep-research replaces this when credits allow).

## FIRST EXPERIMENT CARDS (pre-register before running; script-first)
- **A4-CARD** COVID replication: monthly short straddle w/ 30%-SL daily proxy, 2011-2021 bhavcopy settles. KILL if 2020-Mar drawdown > 3x any 2021-26 drawdown at spec sizing, or full-period expectancy <= 0. THE priority experiment.
- **A1-CARD** DTE richness: implied-minus-realized by DTE bucket {0,1,2,4}, 2019-2026 weeklies. Decision: which DTE hosts the next sell strategy.
- **B1-CARD** FII index-futures net-flow quintiles (participant OI, T+1 signals) vs 1/3/5-day forward returns, 2018-2026. KILL if top-bottom spread < 10 bps/day or t<2.5.
- **C1-CARD** Overnight transfer: regress NIFTY 09:15 gap on S&P close move + VIX change; then gap-conditioned S1-F veto v2. KILL if R2 < 0.15 (gap model) — literature prior says ~0.3.
- **B2-CARD** Air-pocket monetization trio (leg-buyback overlay / futures MFT at 2-pt hurdle / A-family timing): one pre-registered test each, S1-F overlay first.
## Standing rule: max 12 registered trials in Phase 1; every card frozen in this file BEFORE its script runs.

---
## ADDENDUM v1.2 (2026-07-11) — Citation-pass corrections (evidence: RESEARCH_CITATIONS_20260711.md, run wf_95b6ba35-1dd, PARTIAL: 8 confirmed / 3 refuted / 4 leads)
1. **Trials registry upgraded to PREREQUISITE** (confirmed 3-0, DSR paper SSRN 2460551): DSR at graduation gates is uncomputable without N/variance/T/skew/kurt of ALL trials. Phase-0 #9 is now blocking for any Gate-4 pass.
2. **Holdout-touch counter added to embargo policy** (confirmed 3-0): ~20 holdout reuses at 95% conf makes false positives EXPECTED. New rule: every holdout window carries a touch-count; hard cap 5 touches, then the window is burnt (rolls forward).
3. **Stream A priors quantified** (confirmed, SSRN 6530119): NIFTY VRP +1.208 vol pts mean gross / +1.131 median net, 74.9% positive days, 25.1% inversion, AR(1) 0.79. Pre-register A1-CARD expectations against these; deviation > 2x in our data = data-quality investigation before celebration.
4. **Stream C gains a literature prior** (unverified leads, Wiley fut.22512): seller premium may be concentrated OVERNIGHT (intraday negative) and attenuates on jump days. NEW CHEAP CARD C2: day-night decomposition of short-straddle P&L on our own 1-min chain (script-only, no new data). If overnight dominates, S1's intraday-only design leaves premium on the table -> overnight-hold variant enters intake (subject to gap-risk sizing).
5. **Data honesty dates pinned** (confirmed via news/forum + extractor): BANKNIFTY weeklies 2016-05-27, NIFTY weeklies 2019-02-11. Phase-0 #1/#2 scope corrected: pre-2019 NIFTY backfill is monthly-expiry only by construction.
6. **Broker rails quantified** (extractor layer): Angel historical 3/s, 180/min, 5000/hr; 1-min depth 30d/request; orders ~9/s cumulative across place/modify/cancel per client code. Kotak Neo v2.0.2 SDK: zero API brokerage; accepts SL-M param but NSE blocks SL-M on index options -> ALL order templates use SL-Limit with protection band (Phase-0 #8 confirmed).
7. **Refuted-claims ledger** (do not cite): Yang-Zhang-vs-close RV magnitude claims (0-3) and "2026 VRP regime flip to -4.63" (0-3) died adversarial verification. Both become in-house measurements: VRP sign check on our recent data is a trivial Phase-0 script.
8. Remaining debt from this pass: 4 unverified Wiley/VIX claims (votes died on spend limit) + synthesis step. Re-verification is OPTIONAL - in-house tests (C2 card) supersede citation votes for decisions.

### C2-CARD (FROZEN 2026-07-11, pre-registered BEFORE script run) — Day-night decomposition of short-straddle premium
**Claim under test** (Wiley fut.22512, unverified lead): NIFTY option-seller returns are concentrated OVERNIGHT; intraday returns are negative.
**Design** (script-only, existing data, no agents): for every trading day D in the 1-min chain (2021-06..2026-06), pick the nearest weekly expiry E > D (DTE>=1 so the contract survives the night). Two non-overlapping segments, ATM re-struck at each entry (strike = round(spot/50)x50):
- INTRADAY(D): sell CE+PE at first 1-min close >=09:20, buy back at last print <=15:25 same day.
- OVERNIGHT(D->D+1): sell CE+PE at last print <=15:25 on D, buy back at first close >=09:20 on D+1.
No SL (raw premium measurement, not a strategy). Skip pair if any of the 4 prints missing; report skip count. Costs: GROSS is primary for the claim; net also shown at calibrated flat cost (1 pt/leg one-way, 2x before 09:30).
**FROZEN BARS:**
- LEAD (-> Structurer intake for overnight-hold variant): overnight mean > 0 AND t >= 2.5 AND overnight mean > intraday mean.
- REFUTE (-> C2 CLOSED, claim does not transfer): overnight mean <= 0 OR t < 1.5.
- Otherwise PARK (no follow-on trial). n < 400 pairs = INSUFFICIENT.
- SECONDARY (descriptive only, no decision power): DTE buckets {1,2,3,4+}, weekend-gap split, jump-day exclusion (|overnight gap|>1%), year-by-year + 2026-YTD sign (in-house answer to refuted claim B.3 "2026 VRP flip").
Trials-ledger: this is ONE registered trial (the primary full-sample overnight-vs-intraday comparison).
**C2-CARD OUTCOME (2026-07-11, same-day): REFUTED — CLOSED.** Overnight gross +0.59 pts t=0.48 (REFUTE bar t<1.5); premium is INTRADAY-concentrated on our data (+4.75, t=3.39) — opposite of the Wiley claim. Mechanism: ex-jump nights collect +6.17 (t=9.7) but >1% gap nights take it all back (untradeable filter); weekends negative even gross; net of costs overnight −5.41 (t=−4.4). No overnight-hold intake; S1-F flat-EOD design vindicated. BONUS: 2026-YTD premium POSITIVE on our data (overnight +1.82 / intraday +2.80 gross) — refuted claim B.3 ("2026 VRP flip") now also contradicted in-house. Evidence: results/C2_DAYNIGHT_20260711/. Trials +1.

### A1-CARD SPEC (FROZEN 2026-07-11 before run) — DTE richness: which expiry bucket pays sellers best per day
**Design** (script-only, local 1-min chain 2021-06..2026-06 — note: card originally said 2019+, our minute data starts 2021):
For each weekly expiry E and each trading-DTE k in {0,1,2,3,4,5,6}: entry day D = k trading days before E (one obs per (E,k) — non-overlapping within each k). SELL ATM straddle (strike=round(spot@09:20/50)x50, expiry E) at first 1-min close >=09:20; HOLD TO EXPIRY; payoff = intrinsic |spot_settle(E) - K| (spot last print <=15:25 on E). No SL (richness measurement, not a strategy).
Richness_gross = entry premium - intrinsic. Net = gross - 4 pts (2 legs x 2 pts pre-09:30 calibrated entry; cash settle, no exit cost). Per-day rate = richness / max(k,1).
**FROZEN DECISION BAR:** designated-DTE = the k with the highest mean per-day NET richness among those with t>=2.5 (t on per-(E,k) obs). Output -> Structurer intake for next sell-vehicle design. If NO k reaches t>=2.5 on per-day net -> card closes "no preferred DTE", no new vehicle from this card. n<150 obs in a bucket = that bucket INSUFFICIENT.
**SECONDARY (descriptive only):** era split (<2024-01-01 vs >=), win%, premium levels, worst-5 per bucket, k=0 cross-check vs S1 evidence base.
Trials-ledger: +1 (the bucket comparison is one registered trial).
**A1-CARD OUTCOME (2026-07-11, same-day): NO PREFERRED DTE — CLOSED.** No bucket reaches t>=2.5 on per-day net (best k=2 t=1.37). All-DTE gross positive but drowned by unhedged terminal variance (worst-5 to −776 pts). KEY CONTROL FINDING: k=0 (S1 day/entry, NO SL) = −1.5 net pts/day vs S1-F +10.7 with SL → the edge is MANUFACTURED by SL truncation, not raw premium; structure > signal. Design hint only: DTE 2-3 least-bad per day → any future managed mid-DTE card starts there. Evidence: results/A1_DTE_RICHNESS_20260711/. Trials +1.

### C1-CARD SPEC (FROZEN 2026-07-11 before run) — Overnight transfer: US session -> NIFTY opening gap
**Design** (script-only): NIFTY daily gap%(D) = first 1-min close >=09:15 on D vs last print <=15:25 on D-1 (kaggle minute data 2015-01..2026-06; pre-open auction bug rule applied). Regressors, both known BEFORE the NIFTY open: (1) SPX close-to-close return of the most recent US session ending before D 09:15 IST (CBOE daily, verified); (2) VIX change over that same US session (CBOE daily). OLS: gap = a + b*spxret + c*dVIX.
**FROZEN BARS (from original C1 card):** R-squared < 0.15 -> KILL the gap-model stream (literature prior ~0.3). R-squared >= 0.15 -> stage 2.
**Stage 2 (only if stage 1 passes):** gap-conditioned veto study on S1 trade days (final_three S1 daily nets): veto rule |predicted gap| > 0.75% (coefficients fit on FULL sample - flagged in-sample; this is a lead-generator, not a validated filter). Adoption lead bar: veto improves mean net AND removes >=3 of the worst-10 S1 days -> propose as S1-F v1.1 candidate (NEW version per D-030 freeze - shadow only, never touches the running paper test). Else PARK.
Trials-ledger: +1 (stage-1 regression); stage-2 conditional, +1 if run.
**C1-CARD OUTCOME (2026-07-11, same-day): STAGE-1 PASS / STAGE-2 PARK.** Gap model real: gap%=0.27*SPXret (t=16.4), R2=0.215 >= 0.15 bar, era-stable; dVIX subsumed (t=-1.0). Veto study: only 7/258 S1 days flagged, those averaged +19 pts (better than mean!), 0/10 worst days caught -> no S1-F v1.1; post-gap 09:20 entry already prices the gap, F2 covers the channel. Model banked for overnight-risk sizing + morning studies. Evidence: results/C1_OVERNIGHT_TRANSFER_20260711/. Trials +2.

### B1-CARD SPEC DETAIL (FROZEN 2026-07-11 in a pre-run commit; decision bars unchanged from v1.1: KILL if top-bottom < 10bps/day or t < 2.5)
- Signal: FII net index-futures position = (Future Index Long - Future Index Short) from participant-OI file of day D (published post-close); FLOW = 1-day change in net position, in contracts. Numeric-coerce the raw string columns; drop unparseable days (report count).
- NO full-sample quantiles (AST-gate discipline): quintile = ROLLING 252-session percentile rank of FLOW as of D (min 250 obs burn-in; 2018 mostly burns in).
- Timing (T+1, no lookahead): signal from D file -> enter NIFTY at close(D+1); forward returns close(D+1)->close(D+1+k), k in {1,3,5}. NIFTY closes from kaggle minute data (<=15:25 last print convention, consistent with other cards).
- Report: mean fwd return per quintile per k, top-minus-bottom spread in bps/day (spread_k / k), t-stat of daily spread series, era split (2018-21 vs 2022-26). Decision applies to the best k; multiple-k noted as 3 sub-trials on the ledger.
- Output: results/B1_FII_FLOW_20260711/ with RUN_CARD.json (first run-card experiment) + scanner pre-run.
