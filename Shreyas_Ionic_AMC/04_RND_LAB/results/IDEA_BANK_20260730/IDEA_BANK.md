
# IDEA BANK — NIFTY 50 futures/options, prospecting pass (2026-07-30)
**Author:** Aditya Verma (R&D). **Mandate:** find/bank genuinely new tradeable edges, RAM-light, no heavy backtests.
Every entry here is a hypothesis to be tested LATER, not a claimed result. Nothing in this file has been backtested.

## 0. What this pass does NOT re-propose (read `SHARED_CONTEXT_20260729.md` first — mandatory)
- **23 price-derived trend triggers all failed the same way today** (EMA/supertrend/breakout/S-R; confluence
  stacking collapsed n 18,697→35, t never cleared 2). **No idea below is a price transform.** Every idea draws
  on the options surface, positioning/flow data, cross-asset series, or a structural/regulatory regime break.
- **Already running RIGHT NOW, same session (Ishaan, `results/OPTION_SURFACE_SIGNALS_20260729/`):** OTM
  put-call skew, IV term structure (near/far), OI/PCR/max-pain, and a two-leg NIFTY-BANKNIFTY IV-spread
  proxy explicitly filed as "the NS-3 proxy." Panel built (1,227 days), stats not yet run. **Do not duplicate
  these four candidates.** If that run kills its Candidate 4, idea #7 below (full implied-correlation build)
  is the deeper follow-on it already flags as out-of-scope for itself.
- **Already pipelined, not re-derived:** dealer-gamma/GEX regime gate (`ideas/20260703_dealer_gamma_gex.md`,
  1-INTAKE, blocked on OI-surface cadence — only 31% trading-day coverage); FII-minus-Client **index-FUTURES**
  flow (`B-spread-flow`, Gate-3 PASS, t=2.53); FF term-structure vehicle (1-INTAKE). Ideas #2 and #12 below
  extend the flow family to **options** specifically, which is a different leg of the same data, not a repeat.
- **Already tested and dead, cited only as data/priors:** NS-1 overnight naked strangle (KILLED — tail risk,
  242-550x worst/mean; the ~5pt gross overnight decay it measured is real and reused below). Inverse-VRP
  IV-percentile buying (forward-test candidate, not a kill target here). K-004 (long far-OTM at high IV,
  KILLED) and all short-vol-on-the-same-ATM-premium constructions (OPT-SWEEP-50, 49 variants, ~1.0 Sharpe
  ceiling) — nothing here re-sells the ATM VRP a 50th way.

## 1. Ranked bank
Score = Prior(%) × Orthogonality(1=low,2=med,3=high) ÷ Effort(1=low,2=med,3=high) — a **triage heuristic**,
not a statistical estimate; read the narrative, not the third decimal. DATA-BLOCKED items are flagged and
sit lower in the *actionable* queue regardless of raw score, because effort there includes acquiring data
the firm does not have.

| # | Idea | Mechanism (1-line) | Info source | Orthog. | Data | Prior | Crowding | Effort | Score |
|---|---|---|---|---|---|---|---|---|---|
| 1 | NS-2 SENSEX-NIFTY vol dispersion | Two correlated indices' implied vols may not track their realized-vol gap 1:1 | Cross-index vol surface | High | **On disk**, paperwork-only block | 30% | Low-Med (illiquid 2nd leg) | Low | 90 |
| 2 | Expiry-day regime break (Nov-2024 / Sep-2025 SEBI changes) | Regulatory change is a clean natural experiment on pin risk / expiry-day range | Structural/regulatory | High | On disk | 28% | Low | Low | 84 |
| 3 | Participant-OI Client/Pro index-OPTIONS positioning | SEBI: 91-93% of individual F&O traders lose money — fade retail's aggregate option stance | Positioning/flow | Med-High | **On disk**, verified schema | 28% | High (public data) | Low | 70 |
| 4 | Cross-asset overnight gap-size conditioner (resurrect NS-1) | Predict the SIZE (not direction) of tomorrow's gap; gate NS-1's tail on quiet nights only | Cross-asset (USDINR/SPX) | High | On disk | 30% | Low | Low-Med | 60 |
| 5 | Vol-of-vol regime conditioner (India VIX 2nd moment) | Vol-of-vol spikes precede vol regime shifts, distinct from vol level the book already uses | Options surface (2nd moment) | Med-High | On disk | 25% | Med | Low | 50 |
| 6 | Day/night VRP decomposition (Bhat-Pandey-Rao 2024, NIFTY-specific) | Published finding: NIFTY IV misprices day-vs-night realized vol split, not just the total | Options surface (peer-reviewed replication) | Low-Med (same VRP family, disclosed) | On disk | 25% | Med-High (published) | Low | 38 |
| 7 | FII/Pro/Client PREMIUM-weighted option flow (variant of #3) | Rupee-conviction-weighted flow differs from raw contract-count flow | Positioning/flow | Med | On disk (needs join to premium) | 22% | High | Low-Med | 35 |
| 8 | Futures rollover-% / calendar roll-yield | NSE-published rollover % as positioning/roll-yield signal | Positioning/technical hybrid | Med | On disk | 18% | High (retail-media staple) | Low-Med | 22 |
| 9 | NS-3 full implied-correlation build (index-variance decomposition) | Rigorous version of the in-flight IV-spread proxy — true correlation, not a two-leg spread | Options surface (correlation) | High | On disk, high build effort | 20% | Low | Med-High | 20 |
| 10 | MWPL/F&O ban-list breadth as NIFTY regime signal | Aggregate stock ban-list count as a retail-speculative-froth gauge | Positioning/structural | Med-High | **MISSING** — not in DATA_CATALOG | 25% | Low | High (data) | 17 |
| 11 | Intraday U-shape realized-vol seasonality — entry-TIME optimizer for S1-F | Vol is structurally higher near open/close; refine WHEN, not WHETHER, to enter the existing straddle | Microstructure/execution | Low (refines existing sleeve) | On disk | 35%\* | Low | Low | bonus, not new alpha |
| 12 | Institutional-style dispersion trade (NIFTY vs constituent basket correlation) | Classic global desk trade; crowded globally, genuinely thinner in India's retail-dominated single-stock options | Options surface (correlation) | High | On disk, high build effort | 20% | High globally / Low in India | High | 13 |
| 13 | GIFT Nifty dynamic overnight hedge (NS-1 stretch resurrection) | GIFT Nifty trades ~21hrs/day — the one instrument that could dynamically hedge NS-1's exact kill mode (the discrete overnight gap) | Cross-venue/structural | Med | **MISSING** — not in DATA_CATALOG, likely external/paid | 15% | Low | High (data) | 7 |

\* Prior that the seasonality itself is real (near-certain, it's a universal microstructure fact); NOT a prior
on new tradeable alpha — flagged explicitly in its writeup as execution refinement, not a new return stream.

---

## 2. Detailed entries

### #1 — NS-2: NIFTY-vs-SENSEX vol premium relative value
**Mechanism / economic WHY:** SENSEX (30 stocks) is less diversified than NIFTY (50), so *some* implied-vol
premium over NIFTY is fair compensation for genuinely higher realized vol. If the market persistently prices
MORE of a gap than realized vol justifies, the excess is a liquidity/complexity premium SENSEX option buyers
overpay and sellers can harvest — plausible because SENSEX options are a fraction of NIFTY's turnover
(BSE Sensex expiry-day turnover ~₹10-15k cr vs NSE Nifty ~₹2.5-3L cr — a ~20-30x gap [DATA, WebSearch
2026-07-30]), so the premium may persist precisely because it can't be arbed away in size.
**Info source:** cross-index implied-vol surface (genuinely different axis from anything in the book —
attacks the firm's own measured ~0.35 average / 0.53 max sleeve correlation ceiling, per
`results/STACKED_BOOK_20260711/RESULTS.md`).
**Orthogonality:** HIGH — the firm's own `20260725_NEW_STRATEGY_GENESIS.md` explicitly flags this as "the one
candidate that genuinely attacks the correlation ceiling."
**Data requirement:** **AVAILABLE, verified today.** `intraday_options_strategy/datasets/raw/hf_index_options_1m/index/SENSEX.parquet`
(1-min spot, confirmed on disk) + `.../options/SENSEX/` (144 expiry files, 2023-08→2026-05, confirmed count)
+ NIFTY equivalents already in daily use. Overlap window ≈2.8 yrs. **Blocked only on paperwork** — a D-009
sample-check + DATA_CATALOG entry, not a data-acquisition problem (per `RND_ROADMAP.md`'s own sequencing:
"NS-2 after D-009 ... that check is owed anyway").
**Cheapest falsification (already spec'd, not yet run):** compute (SENSEX_IV − NIFTY_IV) minus (SENSEX_RV −
NIFTY_RV) over the overlap. If the implied gap is fully explained by the realized gap → KILL (1.22x measured
premium ratio, n=132, t=2.95 from `SX1_SENSEX_FEASIBILITY_20260711/`, is fair value, nothing to harvest).
**Honest prior:** 30% [OPINION]. Real prior evidence the premium exists (t=2.95); genuinely unknown whether
it's compensation or excess. **Crowding:** LOW-MED — few desks bother with SENSEX options at all given the
turnover gap, but that same illiquidity caps HARVESTABLE size even if the excess is real (capacity flag, not
just a crowding one). **Effort:** LOW — one regression, data and design both already exist.

### #2 — Expiry-day mechanics regime break (Nov-2024 + Sep-2025 SEBI changes)
**Mechanism / economic WHY:** SEBI's Oct-2024 circular (effective 21-Nov-2024) did six things simultaneously
[DATA, WebSearch 2026-07-30, sebi.gov.in + Zerodha/Business Standard]: (1) contract size ₹5L→₹15L, (2)
mandatory upfront premium collection from option BUYERS, (3) intraday MWPL monitoring (≥4 random snapshots/day),
(4) **removed calendar-spread margin treatment on expiry day**, (5) **limited weekly expiries to ONE
benchmark per exchange** (NSE kept only Nifty weekly; BankNifty/FinNifty/MidcapSelect/Nifty-Next-50 weeklies
discontinued), (6) +2% extreme-loss margin on short options. Then on 1-Sep-2025, NSE moved Nifty's own weekly
expiry from Thursday to Tuesday after 25 years, with BSE taking Thursday for Sensex. Each of these is a
clean, dated, exogenous structural break — not a parameter someone tuned. **Economic story:** concentrating
ALL of NSE's weekly retail options flow onto a single Nifty expiry (no more BankNifty weekly to split
attention/OI) plausibly changes pin-risk strength, expiry-day realized-range compression, and the gamma
concentration the firm's own S1-F/strangle sleeves already harvest — a genuine regime input, not a new premium.
**Info source:** structural/regulatory, completely orthogonal to price and to the options-surface tests
running today.
**Data requirement:** AVAILABLE — 16-yr F&O bhavcopy (`05_DATA_OFFICE/data/fo_bhavcopy_hist/fo_idx_{yr}.parquet`)
+ NIFTY 1-min options already used for every expiry-day analysis this session.
**Cheapest falsification:** split the existing expiry-day return/range/pin-risk statistics (already computed
for S1-F and the OPT-SWEEP-50 family) into three regimes — pre-21-Nov-2024, 21-Nov-2024→31-Aug-2025 (single-
weekly, still Thursday), post-1-Sep-2025 (Tuesday) — and test for a mean/variance shift with a simple
Welch/KS test. KILL if no regime is statistically distinguishable from its neighbors (i.e., the changes had
no measurable market-behavior effect, only a compliance effect).
**Honest prior:** 28% [OPINION] that a real, usable regime difference exists; LOWER confidence (~15%) that it
converts to genuinely NEW capital (vs. a recalibration input for S1-F's existing entry/distance rules — say
so plainly, this is partly a calibration task wearing a research-idea coat). **Crowding:** LOW — very few
retail-facing analyses split by this exact regime boundary; institutional desks likely have, though.
**Effort:** LOW — re-cutting data already computed elsewhere.

### #3 — Participant-wise OI (Client/Pro/FII/DII) on INDEX OPTIONS — fade or ride the segment
**Mechanism / economic WHY:** SEBI's own study is about as strong a "who loses and why do they keep doing
it" story as exists in Indian markets [DATA, WebSearch 2026-07-30, sebi.gov.in press release]: **93% of
~1 crore individual F&O traders lost an average ₹2L each over FY22-FY24 (aggregate ₹1.8L cr), and the FY25
update shows losses WIDENING further** even as trader count nearly doubled (51L→96L) — a textbook case of
forced/behavioral persistence (lottery-demand, overconfidence) rather than a mispricing that self-corrects.
"Client" in NSE's participant data is dominated by this population; "Pro" desks are the closer analogue to
smart money. A Pro-minus-Client (or FII-minus-Client) spread in **index OPTIONS specifically** — not futures,
which the firm already trades via `B-spread-flow` — captures a different slice: options carry convexity and
skew information futures don't (e.g., Client's aggregate call-vs-put OI tilt as a sentiment/positioning gauge).
**Info source:** positioning/flow, distinct data columns from `B-spread-flow`'s futures-only construction.
**Orthogonality:** MED-HIGH — same broad "flow" family as the already-Gate-3-PASSED B-spread-flow, so
correlation between the two spreads MUST be reported explicitly if this survives (do not double-count as two
independent sleeves without checking).
**Data requirement:** **AVAILABLE AND VERIFIED TODAY.** `05_DATA_OFFICE/data/participant_oi/participant_oi_normalized.parquet`
— 10,505 rows = 2,101 trading days (2018-01-01→today) × 5 client types (Client/DII/FII/Pro/TOTAL), confirmed
by direct read. Columns include `Option Index Call Long`, `Option Index Put Long`, `Option Index Call Short`,
`Option Index Put Short` split by `Client Type` — exactly the segment-wise index-option OI the mandate asked
about, already normalized, zero new pulling required.
**Cheapest falsification:** daily net Client index-option "greed" score (e.g., `(Call Long − Call Short) −
(Put Long − Put Short)`, z-scored on a trailing window) regressed on forward 1/3/5-day NIFTY return, Newey-West
HAC, vs a date-shuffled placebo — same method template the firm already used for B-spread-flow (B1b card).
KILL if |t|<2 on all horizons or real |t| doesn't beat the placebo's 95th percentile.
**Honest prior:** 28% [OPINION]. Mechanism is unusually strong (documented, persistent, worsening); tempered
by (a) OI level is a stock, not a flow — a Client "long calls" position after a rally may just be reactive,
not predictive, and (b) this exact NSE file is public and cheap to pull, so **crowding is HIGH** — assume
prop desks and even retail analytics platforms have looked at raw Client OI before. The genuinely uncrowded
part is doing it RIGHT (index-options-specific, HAC-correct, placebo-gated) rather than the raw idea.
**Effort:** LOW — data normalized, template exists, one regression away from a verdict.

### #4 — Cross-asset overnight gap-size predictor, as a CONDITIONING FILTER to resurrect NS-1
**Mechanism / economic WHY:** NS-1 (overnight strangle harvest) was killed purely on TAIL SHAPE — worst
night 242-550× the mean nightly gain, at every strike distance tested — not on the mean edge being absent
(t=0.30-0.72, edge real but small, ~5pt gross at ATM). Its own resurrection condition (implicit in
`KILLED_IDEAS.md` K-017's sibling entries) is explicitly "a construction that changes WHICH nights are
entered... not a re-run of the unconditional population." The economic logic: overnight index gaps are driven
by overnight global-market and currency moves; if the SIZE (not direction) of tonight's likely gap is
partially predictable from USDINR's own overnight move and the US market's overnight session, skip/de-size
the strangle on the nights flagged as high-gap-risk and keep it on the quiet majority.
**Info source:** cross-asset (USDINR, S&P 500) — a completely different information channel from NS-1's own
design, satisfying the "genuinely different mechanism" bar.
**Data requirement:** AVAILABLE, verified in DATA_CATALOG: `05_DATA_OFFICE/data/usdinr_fred_daily.parquet`
(FRED DEXINUS, 1973-2026, 13,409 rows, D-033-verified) and `05_DATA_OFFICE/data/us_sp500_daily.parquet`
(1975-2026, n=12,988). NS-1's own gap dataset — `results/DTE_1DTE_BACKTEST_20260725/gaps_1dte.csv` (259
nights, columns `day, strike, prem_dm1_1525, prem_d0_open, gap_ratio, spot_dm1, spot_d0_open`) — is the target
series to condition.
**Cheapest falsification:** on the SAME 258-259 nights NS-1 already measured, regress |NIFTY overnight log
return| (or the realized `gap_ratio`) on (a) |USDINR overnight change| and (b) |S&P 500 overnight-session
return| as of that evening. KILL if neither predictor clears |t|≥2 for the ABSOLUTE gap size, or if the
resulting quiet-night subset still shows a worst/mean ratio >50× (i.e., filtering by macro-quietness doesn't
actually shrink the specific tail that killed NS-1 — check this explicitly, don't just check the mean).
**Honest prior:** 30% [OPINION] that the size-predictor itself is statistically real (overnight FX/US-market
moves plausibly correlate with next-day Indian gap size — a well-worn cross-asset intuition); materially
LOWER (~15%) that filtering shrinks NS-1's specific 242-550× tail enough to make the strangle survivable,
because the worst nights recorded were index-specific/event-specific (the fat right tail NS-1's sibling
niche found lands on dates like the Russia-Ukraine invasion, which a same-evening USDINR/SPX read may or may
not have flagged in time). Report both numbers honestly, don't let the first prior imply the second.
**Crowding:** LOW (few retail/prop desks condition overnight Indian vol-selling on next-day US session data
this explicitly). **Effort:** LOW-MED — three series already in hand, one regression, one filtered re-run of
an already-written backtest.

### #5 — Vol-of-vol regime conditioner (India VIX second moment)
**Mechanism / economic WHY:** vol-of-vol (the volatility OF implied volatility itself) is a distinct
statistical moment from the vol LEVEL the book already trades (IV/RV in S-01, entry-IV filters elsewhere).
Spikes in vol-of-vol are a standard precursor signal for vol-regime transitions in the international
literature (VVIX-style construction) — a genuinely different axis, not a relabeled IV filter.
**Info source:** options surface, 2nd-moment statistic.
**Data requirement:** AVAILABLE — India VIX daily OHLC is in `05_DATA_OFFICE`'s NSE all-indices archive
(verified 2026-07-11, 2011-2026, India VIX 2020-03-24 close 83.61 exact per DATA_CATALOG); CBOE VVIX also on
disk (2006-2026) as a global cross-check/comparator.
**Cheapest falsification:** rolling std-dev of India VIX (10-20d window) as the vol-of-vol proxy; bucket
by quintile; test whether next-5-day realized-range or the S1-F sleeve's own per-trade P&L (already logged)
differs meaningfully across quintiles, same placebo-vs-shuffle discipline as every other candidate here. KILL
if no monotonic pattern or the top-vs-bottom quintile spread doesn't beat a bootstrap placebo.
**Honest prior:** 25% [OPINION]. Directionally plausible mechanism, unverified for India specifically, and
the FIRM's own dealer-gamma one-pager already flags that India's retail-short-options-writing base may not
transfer US market-structure assumptions cleanly — the same caution applies here.
**Crowding:** MED (VVIX-style ideas are well-known globally, less commonly built for India VIX specifically).
**Effort:** LOW — both series already in hand.

### #6 — Day/night VRP decomposition — direct NIFTY replication of Bhat, Pandey & Nageswara Rao (2024)
**Mechanism / economic WHY:** a peer-reviewed paper specifically on NIFTY options — Bhat, A., Pandey, P., &
Nageswara Rao, S.V.D., "The asymmetry in day and night option returns: Evidence from an emerging market,"
*Journal of Futures Markets* 44(8), 1320-1337 (2024) [DATA, WebSearch 2026-07-30] — finds the delta-hedged
variance risk premium in Nifty options is earned almost ENTIRELY overnight, with intraday delta-hedged
returns going the OTHER way, mirroring Muravyev & Ni (2020, JFE) on SPX: option prices are set as if day and
night instantaneous volatility are equal, when realized intraday vol is structurally 2-3× overnight vol — so
sellers are compensated for overnight risk, but partially give it back intraday. **This is directly relevant
to, and different from, NS-1**: NS-1 tested an UNHEDGED naked strangle overnight and died on gap-tail risk;
this paper's construction is DELTA-HEDGED, which changes what kind of risk is actually being harvested (basis/
gamma-scalping vs raw directional gap exposure).
**Info source:** options surface, published/peer-reviewed replication target — different from a self-
generated hypothesis, so it carries an academic prior the firm's other candidates don't.
**Orthogonality:** LOW-MED, disclosed honestly — this is a decomposition WITHIN the VRP family the book
already harvests (per `NEW_STRATEGY_GENESIS.md`'s own "standing honesty note"), not a new factor. Its value
is locating WHERE the mispricing sits (day vs night), which could refine construction, not diversify the book.
**Data requirement:** AVAILABLE — same NIFTY 1-min option chains already used for NS-1 and S1-F; needs one
extra same-day snapshot (15:25 close) alongside the ones already pulled, to split total daily decay into
"trading-hours" vs "overnight" legs.
**Cheapest falsification:** on the existing ~1,200+ expiry days already indexed, compute ATM straddle value at
09:16, 15:25 (same day), and 09:16 next day; decompose total 1-day decay into the two legs; compare relative
magnitudes to the paper's finding (overnight >> intraday, opposite signs). KILL as a NEW-ALPHA candidate if
the split doesn't suggest a construction NS-1 didn't already test (e.g., if the intraday leg alone, isolated
from overnight, still doesn't clear costs — likely, since NS-1's own 1DTE forebear already found intraday-
exposed variants worse).
**Honest prior:** 25% [OPINION] of yielding something ACTIONABLE beyond NS-1/S1-F; near-certain (~80%) the
decomposition itself replicates directionally, since it's now been shown twice (US, India) with the same sign.
**Crowding:** MED-HIGH — it's published, in a finance journal, specifically on Nifty; assume some Indian
prop desks have read it. **Effort:** LOW — measurement only, no new construction to build yet.

### #7 — FII/Pro/Client PREMIUM-weighted option flow (construction variant of #3)
**Mechanism:** contract-COUNT-weighted OI (idea #3) treats a far-OTM weekly and a near-ATM monthly identically
per contract; a RUPEE-PREMIUM-weighted flow (OI change × that day's option price) captures conviction/capital
commitment instead, which could be a materially different — and possibly cleaner — signal.
**Info source / data:** same `participant_oi_normalized.parquet`, joined to daily ATM/near-ATM premium levels
already computed for other candidates. **Orthogonality:** MED — same family as #3, must be tested as one
family with #3 for DSR/trials-ledger honesty (do not present both as independent discoveries if they
correlate, which is likely).
**Cheapest falsification:** same regression template as #3, premium-weighted instead of contract-weighted;
report the correlation between the two constructions' daily signals up front.
**Honest prior:** 22%. **Crowding:** HIGH (same public-data caveat as #3). **Effort:** LOW-MED (one extra join).

### #8 — Futures rollover-% / calendar roll-yield signal
**Mechanism:** NSE's published near-to-next-month rollover percentage is a widely-watched retail/media
sentiment number; high rollover with rising OI is read as trend-continuation conviction, and roll YIELD
(futures basis vs fair cost-of-carry around expiry) is a small, real cash-and-carry-adjacent number.
**Info source:** positioning/technical hybrid — computable from the existing 16-yr F&O bhavcopy without new
data. **Orthogonality:** MED. **Data:** AVAILABLE (`fo_bhavcopy_hist`).
**Cheapest falsification:** same regression template; expect this one to be the weakest because it's a
retail-media staple already priced into flow.
**Honest prior:** 18% [OPINION] — flagged low specifically because of crowding, not mechanism doubt.
**Crowding:** HIGH. **Effort:** LOW-MED.

### #9 — NS-3, done properly: full implied-correlation index (not the in-flight two-leg proxy)
**Mechanism:** today's `OPTION_SURFACE_SIGNALS_20260729` Candidate 4 explicitly labels itself a **simplified
two-leg IV-spread proxy**, honestly disclosed in its own pre-registration as NOT a real implied-correlation
index and flagged as "out of scope for this cheap test... a Gate-2/3 follow-on if this proxy shows anything."
The real construction needs the constituent-weight variance decomposition: index variance = Σw_i²σ_i² +
Σ_{i≠j} w_i w_j ρ σ_i σ_j, requiring per-stock IVs for BankNifty's ~12 constituents and current index
weights, to back out an implied correlation that can be compared to trailing realized correlation and traded
on mean reversion at percentile extremes.
**Info source:** options surface, correlation factor — genuinely orthogonal (per NS-3's own framing).
**Data requirement:** stock-level option chains for BankNifty's constituents exist in `stocks_options/`
(dual-schema per CLAUDE.md landmine #4; large-cap bank names are liquid, should have good coverage) plus
BankNifty's published constituent weights (need a current + historical weight file — check PIT availability
before building, since a current-weight-only build would be a lookahead risk per the T1-T10 taxonomy).
**Cheapest falsification:** WAIT for today's simpler proxy to report first — if Candidate 4 already clears
its placebo, this build becomes the natural Gate-2/3 escalation, not a parallel effort. If Candidate 4 dies,
this is the one candidate that could still resurrect NS-3 on rigor grounds (weak proxy killed, true construct
untested) — but note NS-3 was itself sequenced LAST and flagged "least certain to be tradable" by its own author.
**Honest prior:** 20% [OPINION]. **Crowding:** LOW (the correct build is genuinely more work than most shops
bother with for India). **Effort:** MED-HIGH — multi-name IV surface + weight history, a real build, not a
cheap test; do not start this until the in-flight proxy's verdict is in.

### #10 — MWPL / F&O ban-list breadth as a NIFTY regime signal — DATA-BLOCKED
**Mechanism / economic WHY:** when a stock's aggregate F&O open interest crosses 95% of its Market-Wide
Position Limit, NSE places it under a ban (no fresh positions) until OI falls back below 80% [DATA, WebSearch
2026-07-30]. The BREADTH of the ban list (how many stocks are banned at once) is a live, mechanical proxy for
aggregate retail/speculative over-positioning — directly on-theme with the mandate's "retail-flow dominance"
angle and SEBI's own loss statistics (idea #3). A wide ban list plausibly marks froth that later mean-reverts
or de-levers, which could gate NIFTY index-option sizing (same spirit as the dealer-gamma regime gate already
in the pipeline, but a genuinely different, much denser and simpler data source).
**Info source:** positioning/structural, index-level regime input built from single-stock mechanics.
**Data requirement: MISSING.** Not found in `05_DATA_OFFICE/DATA_CATALOG.md` under any search for ban-list,
MWPL, or position-limit history. NSE publishes a daily ban list (and the position-limit circulars), so this
is very likely a D-033-eligible reliable-official-source auto-fetch (exchange archive, not a sketchy scrape)
— **flagged to Data Officer as a new-source proposal, not fetched here** per the R&D charter (propose, never
auto-fetch). Could plausibly also be reconstructed from OI vs published MWPL values already partially on
disk, which the Data Officer should evaluate as a cheaper alternative to a fresh daily-file pull.
**Cheapest falsification (once unblocked):** daily ban-list count vs forward NIFTY realized range / vs the
book's own realized short-vol P&L, same placebo template.
**Honest prior:** 25% [OPINION]. **Crowding:** LOW (the breadth-as-signal framing, as opposed to the ban list
itself, is not a retail-media staple). **Effort:** HIGH until the data question is resolved — this is a
data-acquisition task wearing a research idea's coat, exactly the case the mandate asked to flag explicitly.

### #11 — Intraday U-shape realized-vol seasonality — entry-TIME optimizer, not a new signal
**Mechanism:** the U-shaped intraday volatility pattern (high near open/close, low midday) is one of the most
robust stylized facts in market microstructure internationally [DATA, WebSearch 2026-07-30, ScienceDirect].
**Framed honestly:** this is NOT a new return stream — it's a candidate refinement to WHEN the firm's existing
0DTE straddle (S1-F) enters/exits within the day, not whether to trade. Included as a bonus, cheap,
near-zero-risk-of-harm item, not counted as a headline "new edge."
**Info source:** microstructure/execution. **Orthogonality:** LOW (same book, same premium, different clock
time). **Data:** AVAILABLE (existing 1-min NIFTY bars).
**Cheapest falsification:** bucket realized 1-min vol by 15-min time-of-day bucket across the full history;
check whether shifting S1-F's entry time later in the morning (past the open U-shape) changes decay captured
per unit of realized-range risk taken.
**Honest prior:** the seasonality existing is ~near-certain (universal fact); the EXECUTION IMPROVEMENT being
worth the engineering effort is a separate, much lower-confidence question (~15%) — say both numbers, don't
conflate them. **Crowding:** irrelevant (it's a timing refinement, not a standalone strategy to crowd out).
**Effort:** LOW.

### #12 — Institutional-style dispersion trade (NIFTY index vs constituent-basket correlation)
**Mechanism / economic WHY:** the classic global vol desk trade — sell index implied correlation (sell index
vol, buy single-name vol on the largest constituents, or the reverse) — profits when realized correlation
diverges from what the index/single-name vol spread implies. Genuinely orthogonal (a correlation factor, not
direction or level). **Crowding is the whole story here:** this trade is heavily crowded at the INSTITUTIONAL
level globally (major vol desks run systematic dispersion books), but India's single-stock options market is
overwhelmingly retail-dominated with far fewer professional dispersion desks — a plausible genuine niche
specifically because of India's market structure, not despite it.
**Info source:** options surface, correlation. **Data requirement:** available in principle —
`stocks_options/` covers 210 F&O names (dual schema per CLAUDE.md #4) for the single-stock legs; NIFTY chains
for the index leg. Building even a 10-15-name basket IV surface with correct weights and liquidity screens is
a REAL build, not a cheap test.
**Cheapest falsification:** before any structure — compute realized correlation vs an at-the-money implied-
correlation proxy (using index ATM IV and cap-weighted single-name ATM IVs for the top 10 NIFTY weights only,
to keep it cheap) over a rolling window; check whether the spread shows persistent sign and predictive value
for a forward realized-correlation move.
**Honest prior:** 20% [OPINION]. **Effort:** HIGH — flag as a longer-runway idea, not a quick win; sequence
AFTER the cheaper items above clear or kill.

### #13 — GIFT Nifty dynamic overnight hedge — the structural fix to NS-1's exact kill mode — DATA-BLOCKED
**Mechanism / economic WHY:** NS-1 died because an unhedged overnight strangle cannot survive a discrete gap
— there is no market to dynamically hedge against between 15:25 and 09:15. GIFT Nifty (NSE IX, GIFT City),
successor to SGX Nifty, trades ~21 hours a day [DATA, WebSearch 2026-07-30] — uniquely among major index
futures proxies, it is LIVE through almost the entire Indian overnight gap. In principle this converts NS-1's
unhedgeable discrete jump into a hedgeable (if imperfectly, on basis/liquidity grounds) continuous process —
a distinctly INDIAN structural feature (most world indices don't have a comparable near-24h domestic-linked
proxy), not a transplant from elsewhere.
**Info source:** cross-venue/structural — a genuinely different mechanism (the hedge instrument itself, not
a new signal).
**Data requirement: MISSING.** GIFT Nifty / NSE-IX historical tick or even 1-min data was not found anywhere
in `DATA_CATALOG.md`; Angel SmartAPI is NSE/BSE-domestic only. This would need an external vendor or scrape,
almost certainly requiring Data Officer verification + Principal approval (D-009/D-033 sketchy-source gate,
not an auto-fetch case) before a single number is trusted.
**Cheapest falsification once data exists:** re-run NS-1's exact 5-arm strangle test, adding one static hedge
at 15:25 (using GIFT Nifty futures at whatever timestamp NS-1 exits, adjusted for the GIFT Nifty-NIFTY basis)
and check whether the worst-night/mean ratio (242-550× unhedged) falls meaningfully — pre-register a bar (e.g.
must fall below ~20× to be worth pursuing further, since NS-1's own bar was 3×).
**Honest prior:** 15% [OPINION], lower than the other candidates for two reasons stated plainly: (a) NS-1's
tail was so extreme that even a real hedge may not shrink it enough, and (b) the hedge itself introduces a new
basis/liquidity risk that hasn't been sized. **Effort:** HIGH — this is explicitly a data-acquisition task
first, a research task second, exactly the case the mandate asked to be honest about rather than oversell.

---

## 3. Not ranked — explicitly flagged as monitoring, not a new-alpha idea
**VRP regime-shift check around the Nov-2024 SEBI tightening.** Upfront premium collection + the 2% extreme-
loss margin on short options both raise the cost of leveraged retail option BUYING — if that measurably thins
retail buying volume, the book's OWN certified edge (S1-F, 12.57% CAGR) could see its VRP magnitude change
(richer OR cheaper, direction unclear a priori). This is a defensive/risk-monitoring re-cut of existing data
(split the S1-F ledger pre/post 21-Nov-2024), not a new tradeable idea, and is flagged here so it doesn't get
silently lost — but it does not compete for a ranked slot under a "new edges" mandate. **Effort:** LOW,
**owner:** should route to Sameer (sensitivity) or Arjun (signal), not treated as an R&D intake item.

---

## 4. Honesty notes (self-red-team, before this goes anywhere)
1. **Ideas #3 and #7 are one family, not two** — report their correlation together or the trials ledger is
   dishonest about how many independent bets were actually placed.
2. **Every "on disk" data claim above was verified by direct file read or grep today** (SENSEX/BANKNIFTY file
   counts, participant_oi schema and row count, USDINR/SPX/India-VIX catalog entries) — not assumed from memory.
3. **Web-sourced facts are tagged [DATA] with the search date** where they came from WebSearch rather than the
   firm's own verified files (SEBI circular contents, the Bhat/Muravyev papers, GIFT Nifty trading hours,
   BSE/NSE turnover comparison) — these are reported as found, not independently re-verified against a primary
   source PDF (the SEBI PDF and JFM paper were not fully fetched; treat citations as pointer-verified, not
   content-verified, until someone actually reads the primary document before citing it in a memo that leaves R&D).
4. **Two items are honestly not "ideas" in the pipeline's normal sense** — #10 and #13 are data-acquisition
   proposals dressed as research ideas; say so to whoever reads this next rather than let them rank as if
   testable today.
5. **No idea here has been cheap-tested.** This is a prospecting/harvest pass only, per the mandate; every
   prior above is this author's [OPINION], stated as such, not a measured result.
