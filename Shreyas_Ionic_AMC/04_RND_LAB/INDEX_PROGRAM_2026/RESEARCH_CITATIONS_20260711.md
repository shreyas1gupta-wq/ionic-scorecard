# INDEX_PROGRAM_2026 — Deep-Research Citation Pass (2026-07-11)
**Status: PARTIAL** — run wf_95b6ba35-1dd completed 60/72 agents; the last 11 verification votes + the synthesis agent died on the org monthly spend limit. Everything below is banked from the completed agents. Verification = 3 independent adversarial votes per claim (2/3 refutes kill).
**Pipeline:** 5 search angles → 20 sources fetched → 93 claims extracted → top 15 verified → **8 CONFIRMED / 3 REFUTED / 4 UNVERIFIED** (votes errored, not refuted). Cost: 72 agents, ~2.58M subagent tokens.

---

## A. CONFIRMED claims (survived adversarial verification)

### Q1 — Quant-firm research process
1. **[3-0] Jane Street keeps out-of-sample holdouts deliberately SMALL** because financial data is scarce relative to other ML domains — holdout policy is a conscious scarcity trade-off, not a fixed large embargo. (Signals & Threads podcast, "Finding Signal in the Noise", In Young Cho, 2025-03-10 — https://signalsandthreads.com/) Quote: "Because you are so data limited, you would prefer to not leave that many data points out of sample."
2. **[2-1] Jane Street treats experiment reproducibility as first-class research discipline** (Ron Minsky, same episode). Quote: "Even just purely for the research process, this kind of discipline around reproducibility is really important."
3. **[3-0] Optiver closes the loop from live trading back into research** — production behaviour monitored, live feedback drives next research iteration (institutional analog of our TCA/live-vs-sim loop). (https://www.optiver.com/what-we-do/research/)

### Q1/validation statistics (Bailey & López de Prado, SSRN 2460551 — DSR paper)
4. **[3-0] DSR requires the FULL trial history** — N independent trials, variance of trial SRs, sample length T, skew/kurtosis — i.e., a complete experiment registry (all trials, not just winners) is a *computational prerequisite* for the graduation-gate statistic, not bureaucracy.
5. **[3-0] Holdout alone cannot prevent overfitting** — ~20 reuses of a holdout at 95% confidence makes false positives *expected*. An embargo policy must **count and limit touches** of the holdout window, not merely partition data.
6. **[3-0] E[max SR] across N zero-skill trials grows with N** (Euler–Mascheroni approximation, Eq. 1) — a sufficiently large unrecorded search *guarantees* a misleadingly profitable strategy.

### Q2 — Indian VRP priors (Agarwal, SSRN 6530119: NIFTY options Aug-2022→Mar-2026, 887 days, 43M 1-min bars)
7. **[3-0] NIFTY VRP positive on 74.9% of days, mean +1.208 vol pts**, AR(1)=0.786, 25.1% inversion rate, left-tail asymmetry 1.975× — direct literature prior for Stream A; NOT an always-on edge.
8. **[2-1] Post-cost the edge survives but shrinks: 72.4% survival, median net +1.131 vol pts** — a concrete pre-registerable expected magnitude for a retail short-vol stream.

## B. REFUTED claims (killed 2/3+ — do NOT cite these)
- ✗ (1-2) "Optiver runs an explicit research→backtest→production mandatory-gate sequence" — marketing-page overreach; the verified version is only the live-feedback loop (A.3).
- ✗ (0-3) "Close-to-close vs Yang-Zhang RV estimator flips VRP sign on 16.5% of days / fabricates 191.97 vol pts annual" — numbers NOT verifiable in the cited paper. (The general point "use overnight-gap-aware RV" remains sensible practice but is unproven at these magnitudes.)
- ✗ (0-3) "Early-2026 structural regime inversion flipped NIFTY VRP to −4.63 vol pts (Newey-West robust)" — not verifiable. **Do not adopt as fact**; but as a cheap in-house check, measuring our own recent VRP sign is Phase-0-trivial and settles it with our data.

## C. UNVERIFIED (votes errored on spend limit — treat as leads, re-verify or test in-house)
- ? NIFTY delta-hedged option-selling returns are **concentrated overnight; intraday negative** (mirrors S&P day-night asymmetry). (J. Futures Markets 44(8), 2024 — https://onlinelibrary.wiley.com/doi/10.1002/fut.22512) — 1 valid SUPPORT vote, 2 errored. *Directly relevant to Stream C (overnight transfer) — our S1 is intraday-only, this paper suggests the seller's premium lives overnight; testable in-house on our 1-min chain.*
- ? NIFTY VRP is primarily compensation for **overnight** risk, not intraday. (same paper)
- ? Day-night asymmetry robust across moneyness/subsamples but **attenuated on jump days** → jump/event filters materially change measured overnight premium. (same paper)
- ? India VIX subsumes historical vol as an RV forecast (sample 2007–2013). (Springer, J. Indian Business Research — https://link.springer.com/article/10.1007/s40196-013-0025-4)

## D. Source ledger (20 fetched; quality as graded by extractor)
| Source | Quality | Notes |
|---|---|---|
| signalsandthreads.com | primary | Jane Street process culture |
| optiver.com/what-we-do/research | primary | live-feedback loop |
| SSRN 2460551 (Bailey/LdP DSR) | primary | trials-registry math |
| SSRN 6530119 (Agarwal NIFTY VRP) | primary | Stream-A priors |
| Wiley fut.22512 (day-night NIFTY options) | primary | Stream-C priors (unverified) |
| Springer s40196-013-0025-4 (India VIX) | primary | old sample (2007-13) |
| smartapi.angelone.in forum 4387 (rate limits) | primary | see appendix: 3/s, 180/min, 5000/hr historical; 9/s orders |
| smartapi.angelone.in forum 4845 (history depth) | forum | 30d/req 1-min, 100d/req 5-min |
| smartapi.angelbroking.com/docs/Orders | primary | order types/params |
| github.com/Kotak-Neo/Kotak-neo-api-v2 | primary | v2.0.2 (2026-06); L/MKT/SL/SL-M params |
| kotakneo.com trade-api guide | primary | zero brokerage on API trades |
| zerodha z-connect algo-regulations | secondary | retail algo registration threshold |
| business-standard (BANKNIFTY weeklies) | secondary | weeklies from 2016-05-27 |
| tradingqna (NIFTY weeklies) | forum | NIFTY weeklies from 2019-02-11 |
| teamleaseregtech NSE circular | unreliable | 0 claims kept |
| archives.nseindia.com fao_participant_oi CSV | primary | deterministic URL, no auth, verified 2021 file |
| SEBI circular 2024/132 (Oct-2024 F&O framework) | primary | the 2025-26 regime source |
| zerodha z-connect SEBI new rules | secondary | interpretation layer |
| zerodha marketintel 440991 (freeze qty Feb-2026) | secondary | current freeze limits |
| zerodha marketintel 305785 (SL-M ban) | primary | SL-M blocked for index options |

## E. Immediate master-plan consequences (folded into MASTER_PLAN.md §ADDENDUM v1.2)
1. **Trials registry is load-bearing** (A.4–A.6): DSR at Gate-4 is uncomputable without every trial logged — our trials-ledger consolidation (Phase-0 #7) upgrades from hygiene to prerequisite.
2. **Holdout-touch counter** (A.5): add a touch-count column to the holdout embargo policy; hard cap touches per holdout window.
3. **Stream A priors now quantified** (A.7–A.8): pre-register expected VRP magnitude ≈ +1.1–1.2 vol pts median net, 72–75% positive days, 25% inversion — sized bars, not blank slate.
4. **Stream C (overnight) gets a paper prior** (C.1–C.3): day-night decomposition of our own short-vol P&L = cheap, high-value early experiment; jump-day filter interaction pre-registered.
5. **Data honesty dates**: BANKNIFTY weeklies exist only from 2016-05-27, NIFTY weeklies from 2019-02-11 → bhavcopy backfill before those dates is monthly-only by construction (fixes Phase-0 #1 scope).
6. **Broker rails quantified** (appendix): Angel historical 3/s·180/min·5000/hr, 30d-per-request at 1-min; orders ~9/s cumulative; Kotak Neo API v2.0.2 zero-brokerage, SL-M accepted by SDK but exchange-blocked for index options → design order engine around SL-Limit only.
7. **Do-not-cite list** (B): the two flashy VRP claims (YZ-estimator magnitude, 2026 regime flip) died verification — measure both in-house instead.

---

## APPENDIX — full 93-claim extract layer (per-source, UNVERIFIED except where listed above)
*(auto-salvaged from run journal; importance tags by extractor; treat as leads needing verification)*

### Source (primary, 2025-11-07) — agent 
- **[central]** Kotak Neo charges zero brokerage on trades placed through its Trade API (no extra fee for API orders).
  - quote: "The trades are allowed without any extra fee"
- **[central]** The Kotak Neo Trade API supports market, limit, and stop-loss order types, with the ability to place, modify, and cancel orders programmatically.
  - quote: "Market orders, limit orders, and stop-loss orders supported ... place, modify, and cancel orders"
- **[supporting]** Kotak Neo API authentication is a multi-step flow requiring an API access token, TOTP registration (Google/Microsoft Authenticator), UCC client code, and a 6-digit MPIN to generate trading tokens (TRADING_TOKEN, TRADING_SID) before orders can be placed.
  - quote: "Two-step authentication using TOTP and MPIN to generate trading tokens ... Place orders using endpoints with TRADING_TOKEN, TRADING_SID, and BASE_URL"
- **[supporting]** Kotak Neo claims order execution latency under 50 milliseconds and platform throughput exceeding one million trades per day.
  - quote: "Trade within a delay of less than 50 milliseconds ... The platform makes more than a million trades a day at ultra-low latency"
- **[supporting]** Instrument/market data access is provided via a master script endpoint in CSV format covering equity, ETF, and index quotes; the page does not document WebSocket streaming, rate limits, basket orders, margin APIs, or historical data depth.
  - quote: "Live market data retrieval via master script endpoint (CSV format) ... The article does not specify support for WebSocket capabilities, basket orders, margin APIs, rate limits, or detailed segment restrictions"

### Source (forum, 2024-09-27) — agent 
- **[central]** Angel One SmartAPI's historical candle API (getCandleData) supports fetching at most 100 days per request for 5-minute interval data and 30 days per request for 1-minute interval data, per a SmartAPI forum moderator.
  - quote: "we can fetch 100 days data for 5 Min interval and 30 Days data for 1 Min interval data using this API"
- **[central]** As of September 2024, a user empirically found the API returning less than the advertised depth: a 5-minute interval query for July 29 to September 20, 2024 returned data starting only from August 14, with no error raised — silent truncation of the requested window.
  - quote: "I am not able to fetch 100 days data for 5 Min interval and 30 Days data for 1 Min interval. It used to work earlier."
- **[supporting]** Angel One staff stated no changes had been made to the Historical API despite the user's report of reduced retrievable depth, meaning the observed truncation was either a transient defect or an undocumented behavior rather than an announced policy change.
  - quote: "We have not made any changes in Historical API"
- **[tangential]** The thread contains no official per-interval specification table (e.g., limits for ONE_DAY, FIFTEEN_MINUTE, ONE_HOUR), so full interval-by-interval depth limits must be sourced from the official SmartAPI docs rather than this thread.
  - quote: "The thread does not provide an official specification document listing maximum retrievable days per interval."

### Source (secondary, 2025-02-06) — agent 
- **[central]** Under SEBI's algo trading regulations, retail traders can continue automating trades through broker APIs without registering their strategies as long as they stay below an exchange-prescribed order-frequency threshold; only traders exceeding that threshold must register their algo with the exchange.
  - quote: "the regulations require exchanges to prescribe an order rate below which traders needn't register"
- **[central]** Retail traders using broker APIs for automated trading must use a static IP address that is whitelisted by their broker, and API access is restricted to that IP — a hard infrastructure constraint on any retail algo deployment (e.g., laptop on residential/corporate networks with dynamic IPs).
  - quote: "get a static IP and only use the APIs from this static IP whitelisted by the broker"
- **[supporting]** As of the article's publication (Feb 2025), exchanges had not yet defined the specific order-per-second registration threshold; the SEBI circular gave exchanges until April 1, 2025 to set up the registration framework, meaning exact retail algo compliance limits were still pending during the 2025-26 design window.
  - quote: "The exchanges are yet to set up a framework for all such registrations. The SEBI circular gives them up to April 1, 2025 to set this up"
- **[supporting]** Zerodha applies a rate limit of 10 orders per second on its APIs (Kite), and the article expects exchange-prescribed registration thresholds to sit above existing broker rate limits — a useful comparative benchmark when specifying Angel One SmartAPI / Kotak Neo throughput assumptions.
  - quote: "a rate limit of 10 orders per second on our APIs as well as Kite"
- **[tangential]** Black-box algo providers (logic not disclosed) must obtain a SEBI Research Analyst license, and all black-box algo orders are tagged with a unique exchange-issued identifier; individuals may share strategies only with family members — constraints on productizing or distributing strategies but not on trading one's own account.
  - quote: "individuals are permitted to share their strategies only with family members"

### Source (primary, ?) — agent 
- **[central]** Angel One SmartAPI's historical candle endpoint (getCandleData) is officially rate-limited to 3 requests/second, 180 requests/minute, and 5000 requests/hour — a moderator explicitly corrected the per-minute figure to 180.
  - quote: "Historical/CandleData: "3" per second, "180" per minute, "5000" per hour ... "the ratelimit per minute for getCandleData should be 180. Thank you for highlighting this. We will fix this and let you know.""
- **[central]** Order placement, modification, and cancellation on SmartAPI are limited to 20 requests/second, 500/minute, and 1000/hour, which caps multi-leg/basket execution throughput at roughly 1000 order actions per hour.
  - quote: "Place/Modify/Cancel Order: "20" per second, "500" per minute, "1000" per hour"
- **[central]** Market data polling endpoints (getLtpData and the full Quote endpoint) are each limited to 10 requests/second, 500/minute, and 5000/hour, making REST polling unsuitable for continuous real-time monitoring of a large option chain.
  - quote: "getLtpData: "10" per second, "500" per minute, "5000" per hour; Quote endpoint: "10" per second, "500" per minute, "5000" per hour"
- **[central]** SmartAPI WebSocket streaming permits 3 concurrent connections per client code with no message-rate cap, making it the intended channel for real-time market data instead of REST polling.
  - quote: "WebSocket Streaming: "3 connections per client code" with "no additional cap or limit""
- **[supporting]** Rate limits are enforced hierarchically (per-minute caps sit on top of per-second caps), and breaching them returns an 'Access denied because of exceeding access rate' error — matching the AB1021 error the firm has already hit in practice.
  - quote: "Rate limits operate hierarchically—per-minute limits are "an additional cap on top on per second ratelimit." Users reported receiving: "Access denied because of exceeding access rate" when hitting rate limits."

### Source (primary, 2026-06-08 (latest release v2.0.2)) — agent 
- **[central]** The Kotak Neo API v2 Python SDK exposes order_type values L, MKT, SL, and SL-M for order placement across segments including NSE F&O — i.e., the broker-side SDK still accepts SL-M as a parameter even though NSE banned SL-M for options at the exchange level, so any SL-M rejection for index options would occur at exchange validation, not in the SDK.
  - quote: "product=NRML, CNC, MIS, CO, BO ... order_type=L, MKT, SL, SL-M"
- **[central]** Kotak Neo v2 provides two separate WebSocket streams: a live market-data feed via subscribe() taking an instrument_tokens list with optional isIndex and isDepth flags (so index and market-depth data are stream-subscribable), and a distinct order-update feed via subscribe_to_orderfeed(), with on_message/on_error/on_close/on_open callbacks.
  - quote: "subscribe() accepts "instrument_tokens" list with optional "isIndex" and "isDepth" flags ... subscribe_to_orderfeed() - separate order feed subscription ... Callbacks: on_message, on_error, on_close, on_open"
- **[central]** The SDK includes a margin_required() endpoint for pre-trade margin calculation and a limits() endpoint for available limits by segment/exchange/product, but the README documents no basket-order or historical candle-data endpoint — snapshot quotes only, with quote_type limited to all/depth/ohlc/ltp/oi/52w/circuit_limits/scrip_details. This means Kotak Neo v2 cannot serve as the historical-data source in a dual-broker design; historical depth must come from the other broker (Angel One) or NSE archives.
  - quote: "margin_required() - calculates margin for trades ... quotes() with quote_type options: "all, depth, ohlc, ltp, oi, 52w, circuit_limits, scrip_details""
- **[central]** The official README/SDK documentation does not specify API rate limits, WebSocket connection limits, or maximum concurrent instrument subscriptions — these constraints are undocumented in the primary SDK repo and must be verified empirically or from Kotak's separate API portal before designing capture infrastructure.
  - quote: "The README does not specify: rate limits, WebSocket connection limits, number of concurrent instruments, historical data endpoints, depth data specifications"
- **[supporting]** The SDK is officially maintained and actively updated (latest release v2.0.2 on June 8, 2026), supports segments nse_cm, bse_cm, nse_fo, bse_fo, cde_fo, mcx_fo, requires Python 3.10–3.13, and uses a two-step TOTP + MPIN login flow (totp_login() then totp_validate() to generate the trade token) with registration via the Kotak Securities Trade API portal.
  - quote: "the latest release (v2.0.2) was June 8, 2026 ... The SDK supports: nse_cm, bse_cm, nse_fo, bse_fo, cde_fo, mcx_fo ... totp_validate() with mpin "generates the trade token""

### Source (primary, 2021-07-02) — agent 
- **[central]** NSE publishes a daily participant-wise open interest file for equity derivatives as a plain CSV at the deterministic URL pattern archives.nseindia.com/content/nsccl/fao_participant_oi_DDMMYYYY.csv, verified accessible without authentication for the 02-Jul-2021 date — confirming this archive is a scriptable, free, point-in-time data source for participant-flow research (Stream: FII/participant OI predictability).
  - quote: "Title row: "Participant wise Open Interest (no. of contracts) in Equity Derivatives as on Jul 02,2021""
- **[central]** The participant-wise OI file segments positions into exactly four participant categories — Client, DII, FII, and Pro — plus a TOTAL row, which defines the maximum granularity available for any participant-flow signal built from this free source (no sub-category breakdown such as retail-vs-HNI or FPI sub-types).
  - quote: "Participant Categories Present: Client, DII (Domestic Institutional Investors), FII (Foreign Institutional Investors), Pro (Proprietary traders), TOTAL"
- **[central]** The file separates index options OI into four directional legs per participant (Call Long, Put Long, Call Short, Put Short), plus index futures long/short — enough resolution to construct net-positioning and long-short-ratio signals for NIFTY/BANKNIFTY options specifically, distinct from stock derivatives.
  - quote: "Column headers include: Client Type, Future Index Long, Future Index Short, Future Stock Long, Future Stock Short, Option Index Call Long, Option Index Put Long, Option Index Call Short, Option Index Put Short, Option Stock Call Long, Option Stock Put Long, Option Stock Call Short, Option Stock Put Short, Total Long Contracts, Total Short Contracts"
- **[supporting]** OI in this file is denominated in number of contracts, not notional or delta-adjusted value, so any cross-time signal must handle contract-size (lot size) revisions by NSE to avoid spurious level shifts in FII positioning series.
  - quote: "Participant wise Open Interest (no. of contracts) in Equity Derivatives"
- **[tangential]** As a scale reference for signal construction, on 02-Jul-2021 FII index option OI was: Call Long 214,266 contracts, Put Long 302,772, Call Short 137,101, Put Short 154,294 — i.e., hundreds of thousands of contracts per leg, so daily changes are statistically meaningful rather than noise-dominated small counts.
  - quote: "FII option positions show: Index call long at 214,266 contracts, Index put long at 302,772 contracts, Index call short at 137,101 contracts, Index put short at 154,294 contracts"

### Source (forum, 2019-02-07) — agent 
- **[central]** NIFTY 50 weekly index options were only introduced on NSE in February 2019 (thread posted 2019-02-07 anticipating a Feb 11 start) — therefore NSE F&O bhavcopy contains NO NIFTY weekly option contracts before Feb 2019, and any pre-2019 NIFTY options history is monthly-expiry only.
  - quote: "Thread title: "Nifty weekly starting on Feb 11th — how does life change for me?" ... "NSE has announced the introduction of weekly options on Nifty 50. Here are the contract specifications Instrument Name OPTIDX Symbol NIFTY Expiry date Every Thursday of the week.""
- **[supporting]** At launch, NIFTY weekly options expired every Thursday, with a trading-holiday Thursday rolling the expiry to the previous trading day — the original expiry-day convention against which any expiry-day-effect study on 2019-era data must be aligned (later moved by NSE circulars).
  - quote: ""Every Thursday of the week. In case the Thursday is a trading holiday, the previous trading day shall be the expiry/last trading day.""
- **[supporting]** At introduction, NSE listed 7 weekly NIFTY expiry contracts at a time, excluding the week of the monthly expiry — so early-2019 bhavcopy rows will show up to ~7 concurrent weekly expiries plus monthlies, which matters for parsing/deduplicating the option chain in that era.
  - quote: ""7 weekly expiry contracts excluding the expiry week of monthly contracts" were available."
- **[supporting]** BANKNIFTY weekly options already existed and were actively traded before NIFTY weeklies launched in Feb 2019 (the thread compares the new NIFTY weeklies to established Bank Nifty weeklies), implying BANKNIFTY weekly option history in the bhavcopy extends further back than NIFTY's (BANKNIFTY weeklies launched mid-2016, though this page does not give that date).
  - quote: ""You might not see the kind of wild swings in Nifty weeklies which you might see in Bank Nifty weeklies.""
- **[tangential]** Practitioner prior on weekly-vs-monthly option economics circa launch: weekly ATM premiums decay faster and stack to roughly double a monthly's premium (relevant as a rough VRP-term-structure prior for stream design, but it is an uncited forum assertion).
  - quote: ""4 weekly ATMs give you two times the premium of a monthly" ... weekly options have "higher gamma and increasing delta" than monthlies."

### Source (primary, ?) — agent 
- **[central]** Optiver's research pipeline is structured as an explicit research -> backtest -> production sequence run as a tight iterative feedback loop, i.e., backtesting is a mandatory intermediate gate before production deployment.
  - quote: "Ideas move from research to backtest to production in a compressed scientific feedback loop."
- **[central]** Optiver closes the loop from live trading back into research: production behaviour of deployed models is monitored and live-trading feedback is used to drive the next research iteration (the institutional analog of a TCA/live-vs-sim feedback loop).
  - quote: "Monitor behaviour in production and use live feedback to refine what comes next"
- **[supporting]** At Optiver, research results are adversarially challenged by non-researchers (traders and engineers) at two distinct points: before deployment and again after deployment — deployment does not end scrutiny of a strategy.
  - quote: "work closely with traders and engineers, so results are challenged from multiple angles before and after deployment"
- **[supporting]** Optiver defines the model lifecycle to include 'analyzing failures' as an explicit named stage alongside problem definition, data selection, hypothesis testing, and simulation — failure analysis / post-mortem is a formal pipeline step, not ad hoc.
  - quote: "the full model lifecycle: defining the problem, selecting data, testing hypotheses, building simulations, analyzing failures"
- **[supporting]** Optiver maintains firm-wide reuse of research artifacts — code, documentation, data foundations and findings are shared across teams and regions so results in one market seed research in others (the institutional analog of a shared experiment/knowledge registry).
  - quote: "Code, documentation, data foundations and findings are shared across teams and regions, so an insight in one market can become the starting point for progress elsewhere"

### Source (primary, 2024-08 (Journal of Futures Markets, Vol. 44, Issue 8, pp. 1320-1337)) — agent 
- **[central]** In Indian NIFTY index options, short (delta-hedged option-selling) strategies earn positive and statistically significant overnight returns while intraday returns are negative — i.e., the option-seller's edge is concentrated in the non-trading (night) session, mirroring the day-night asymmetry documented for S&P 500 options.
  - quote: "We find a similar disparity in the returns for short Nifty option strategies. Positive and significant overnight option returns are accompanied by negative intraday returns."
- **[central]** The variance risk premium earned by NIFTY option sellers is primarily compensation for bearing overnight risk, not intraday risk — a literature prior directly relevant to structuring when short-vol positions should be held (overnight) vs. avoided (intraday).
  - quote: "We confirm that the variance risk premium earned by option sellers is mainly a reward for overnight risk."
- **[central]** The day-night return asymmetry in NIFTY options is robust across option categories (e.g., calls/puts, moneyness buckets) and subsamples, but is attenuated on days with significant jumps in the underlying index — implying jump/event-day filters materially change the measured overnight premium.
  - quote: "The day–night asymmetry is robust across option categories and subsamples but weaker on days with significant jumps in the underlying."
- **[supporting]** The Indian finding replicates a phenomenon first documented in developed markets: recent research on S&P 500 options found the same day-night asymmetry in option returns, so this is a cross-market anomaly rather than an India-specific artifact.
  - quote: "Recent research based on S&P 500 options has found a day–night asymmetry in option returns."
- **[supporting]** As a baseline, delta-hedged option selling in NIFTY yields positive average returns attributable to the volatility risk premium embedded in option prices — consistent with a harvestable VRP in Indian index options.
  - quote: "Delta‐hedged option selling strategies typically yield positive returns, owing to the volatility risk premium embedded in the option price."

### Source (primary, 2013-10-22) — agent 
- **[central]** India VIX is the best available forecast of future realized volatility of the NIFTY, subsuming market-wide information better than historical volatility, over the sample November 2007 to February 2013.
  - quote: "India VIX is the best estimate of future realized volatility ... implied volatility best subsumes the market-wide information."
- **[central]** India VIX is a biased (upward) forecast of realized volatility: the OLS slope of realized volatility on India VIX is 1.32 (intercept 0.20), but after correcting for measurement error via 2SLS the slope falls to 1.22 and is not statistically different from one (Wald F-test) — i.e., the apparent bias largely reflects errors-in-variables, implying only a modest volatility risk premium wedge.
  - quote: "The 2SLS estimation procedure shows that 2SLS estimates are more consistent than the simple OLS."
- **[central]** Historical volatility contains no incremental information beyond India VIX: in encompassing regressions the historical-volatility coefficient turns negative (-0.14) and statistically insignificant once implied volatility is included, while the IVIX-based model achieves adjusted R-squared of about 0.73.
  - quote: "Finally, the 2SLS procedure explains that historical volatility does not contain valuable information what already contained in the implied volatility."
- **[supporting]** The study's sample spans November 1, 2007 to February 28, 2013 and splits into a global-financial-crisis regime (2007M11-2009M06, mean India VIX ~40.4%) and a normal regime (2009M07-2013M02) identified via a Markov regime-switching model — so its priors predate weekly options and the modern (2019+) NIFTY options market structure.
  - quote: "Period 2: Global financial crisis (2007M11–2009M06) ... Period 3: Normal market (2009M07–2013M02) ... Mean IVIX during crisis (Period 2): 40.4%"
- **[supporting]** Implied volatility (India VIX) is a smoothed series relative to realized volatility: the standard deviation of realized volatility was 52% versus 35.6% for implied volatility over the sample, consistent with IVIX under-reacting to volatility spikes.
  - quote: "Standard deviation of realized volatility: 52% vs. implied volatility: 35.6%, showing implied volatility is "smoothed""

### Source (primary, Homepage undated; quoted episodes: 2025-03-10 (Finding Signal in the Noise) and 2025-05-28 (Building Tools for Traders)) — agent 
- **[central]** Jane Street ML researchers deliberately keep out-of-sample holdouts small because financial market data is scarce relative to other ML domains — i.e., the firm's holdout policy is a conscious trade-off against data scarcity, not a fixed large embargo window (episode 'Finding Signal in the Noise', guest In Young Cho, Jane Street ML/trading researcher, Mar 10 2025).
  - quote: "Because you are so data limited, you would prefer to not leave that many data points out of sample."
- **[central]** Jane Street treats reproducibility of experiments as a first-class discipline in its research process (host Ron Minsky, same episode) — supporting the idea that an experiment-registry/reproducible-run practice is core to their research-to-production pipeline.
  - quote: "Even just purely for the research process, this kind of discipline around reproducibility is really important."
- **[supporting]** Jane Street researchers independently re-verify data quality even when it comes from trusted internal pipelines — every consumer of data runs their own checks rather than assuming upstream correctness (In Young Cho).
  - quote: "You should assume that people are doing the best to give you the highest quality data possible, but you should also do your own checks."
- **[supporting]** Jane Street identifies regime non-stationarity (distribution shift in features and returns around frequent crisis events) as a primary modelling challenge, implying their validation must account for regime splits rather than pooled i.i.d. samples (In Young Cho).
  - quote: "A financial crisis seems to occur roughly every year...the distribution of features or the returns just changes."
- **[supporting]** Jane Street's trader-tooling feedback loop is same-day/next-day: tool developers sit physically adjacent to traders, observe usage directly, and ship requested features within a day (episode 'Building Tools for Traders', guest Ian Henry, May 28 2025) — a concrete benchmark for TCA/tooling feedback-loop latency.
  - quote: "We can watch them using our tools and they can directly ask for features. We can understand what they want, we can talk about it, we can write code for them and ship it and see them use it the next day."

### Source (primary, unknown (no date on page; live production docs as fetched 2026-07-11)) — agent 
- **[central]** Angel One SmartAPI enforces order-API rate limits cumulatively across placeOrder, modifyOrder, and cancelOrder at a combined maximum of 9 requests/second (each endpoint also individually capped at 9/sec, 500/min, 1000/hour), calculated per client code — this caps any retail execution engine built on SmartAPI at ~9 order actions/sec.
  - quote: "The rate limit for order APIs is enforced cumulatively across place order, modify order, and cancel order requests. The combined request count must not exceed 9 requests per second. ... NOTE: The Rate limit is calculated on the basis of client code."
- **[central]** SmartAPI documents four order types including stop-loss-market — ordertype values MARKET, LIMIT, STOPLOSS_LIMIT (SL), STOPLOSS_MARKET (SL-M) — and three varieties NORMAL, STOPLOSS, ROBO (bracket order); stop-loss orders must be sent with variety STOPLOSS, so at the API level SL-M is still an accepted parameter (any exchange-level SL-M ban for options would apply downstream, not in the API contract).
  - quote: "ordertype ... ["MARKET","LIMIT","STOPLOSS_LIMIT","STOPLOSS_MARKET"] ... ["Market Order(MKT)","Limit Order(L)","Stop Loss Limit Order(SL)","Stop Loss Market Order(SL-M)"]; variety ... ["NORMAL","STOPLOSS","ROBO"] ... How to place Stop Loss Order using SmartAPI? ... Please remember to mention the variety as STOPLOSS instead of NORMAL."
- **[central]** The historical candle endpoint getCandleData is rate-limited to 3 requests/second, 180/minute, and 5,000/hour — meaning bulk historical backfills via SmartAPI are throttled to at most ~180 instrument-window requests per minute by documentation (observed practical limits may be tighter, e.g. the firm's AB1021 experience at ≥1.2s/req).
  - quote: "api_name:"/rest/secure/angelbroking/historical/v1/getCandleData",limit_rate_second:"3",limit_rate_minute:"180",limit_rate_hour:"5000""
- **[central]** SmartAPI provides a batch margin API (/rest/secure/angelbroking/margin/v1/batch) that accepts up to 50 positions in a single request at 10 requests/second — sufficient to compute portfolio/spread margin (hedge benefit) for multi-leg option structures programmatically before order placement.
  - quote: "Access Rate Limit: 10 request per second ... Number of positions input in a request: Upto 50 positions in a single request ... api_name:"/rest/secure/angelbroking/margin/v1/batch",limit_rate_second:"10",limit_rate_minute:"500",limit_rate_hour:"5000""
- **[supporting]** For index-options trading the API supports exchange NFO ("NSE Future and Options") with producttype CARRYFORWARD mapping to NRML for overnight F&O positions, and exposes GTT rule endpoints (createRule/modifyRule/cancelRule at 9/sec, 500/min, 5000/hour) plus ancillary order-desk endpoints (optionGreek, putCallRatio, OIBuildup, estimateCharges, individual order status by uniqueorderid).
  - quote: "exchange ... ["BSE","NSE","NFO","MCX","BFO"] ... "NSE Future and Options" ... producttype ... ["DELIVERY","CARRYFORWARD","MARGIN","INTRADAY","BO"] ... "Normal for futures and options (NRML)" ... api_name:"/rest/secure/angelbroking/gtt/v1/createRule",limit_rate_second:"9",limit_rate_minute:"500",limit_rate_hour:"5000""

### Source (secondary, 2026-01-30) — agent 
- **[central]** Effective February 1, 2026, the NSE quantity freeze limit for NIFTY index futures and options contracts is 1800 (unchanged from the prior limit of 1800) — the maximum quantity per single order before the order is frozen; larger orders must be split into multiple orders of at most 1800 (24 lots at the 75-unit lot size).
  - quote: "NIFTY | 1800 | 1800 ... effective "1st February 2026" ... apply to "Index Futures and Options contracts.""
- **[central]** Effective February 1, 2026, the BANKNIFTY quantity freeze limit is 600 (unchanged), meaning any single BANKNIFTY F&O order above 600 units will hit the exchange freeze — a binding per-order size constraint for backtest fill/slicing realism.
  - quote: "BANKNIFTY | 600 | 600"
- **[supporting]** The FINNIFTY quantity freeze limit was raised from 1200 to 1800 effective February 1, 2026 — freeze limits are not static, so an execution-realism model must use period-appropriate limits rather than a single constant.
  - quote: "FINNIFTY | 1200 | 1800 ... "The quantity freeze limits for Index Futures and Options contracts are revised periodically.""
- **[supporting]** The other index freeze limits effective February 1, 2026 are MIDCPNIFTY 2800 and NIFTYNXT50 600 (both unchanged); the bulletin covers NSE indices only and says nothing about BSE's SENSEX/BANKEX.
  - quote: "MIDCPNIFTY | 2800 | 2800 ... NIFTYNXT50 | 600 | 600 ... The bulletin does not contain details about SENSEX or BANKEX."
- **[supporting]** The primary regulatory source for these limits is NSE Circular FAOP72534 (referenced by the bulletin), which is the document to cite/verify for the master plan's execution-realism assumptions rather than the broker bulletin itself.
  - quote: "Exchange Circular Reference: NSE Circular FAOP72534 (accessible via link provided in bulletin)"

### Source (primary, 2026-04 (SSRN posting; search snippets report April 6 or April 20, 2026)) — agent 
- **[central]** In NIFTY 50 index options (Aug 2022 - Mar 2026, 887 trading days, 43M+ one-minute option bars), the variance risk premium is positive on 74.9% of trading days with a mean of +1.208 vol points — a direct literature prior for a short-vol/VRP alpha stream, but far from an always-on edge (25.1% of days invert).
  - quote: "The nine analytical filters reveal that VRP is positive on 74.9% of trading days with a mean of +1.208 vol points, but exhibits an AR(1) coefficient of 0.7861, a 25.1% inversion rate, and a left-tail asymmetry of 1.975×, decisively rejecting Gaussian distributional assumptions."
- **[central]** The choice of realized-volatility estimator is a first-order methodological landmine for Indian VRP research: substituting close-to-close RV for the Yang-Zhang estimator (which captures overnight gap variance) reverses the sign of the measured premium on 16.5% of trading days and fabricates 191.97 vol points of illusory annual premium — any NIFTY VRP backtest must use an overnight-gap-aware RV estimator.
  - quote: "The choice of realized volatility estimator reverses the sign of the measured premium on 16.5% of trading days and generates 191.97 vol points of illusory annual premium when close-to-close is substituted for Yang-Zhang."
- **[central]** After transaction costs, the NIFTY VRP edge survives but shrinks: gross survival drops to 72.4% and the median net edge is +1.131 vol points — a concrete post-cost effect size to pre-register as the expected magnitude for a retail short-vol stream.
  - quote: "Transaction costs reduce gross survival to 72.4%, leaving a median net edge of +1.131 vol points."
- **[central]** A structural regime inversion in early 2026 flipped the NIFTY VRP to a mean of −4.63 vol points (statistically robust under Newey-West HAC), attributed to a macro volatility regime shift rather than a change in AR(1) persistence (Chow test p = 0.54) — i.e., naive always-short-vol strategies calibrated on 2022-2025 would currently be selling a negative premium.
  - quote: "a structural epoch inversion emerges in early 2026, producing a mean VRP of −4.63 vol points — statistically robust under Newey-West HAC correction — driven by macro volatility regime shift rather than AR(1) persistence change, confirmed by a Chow test yielding p = 0.54."
- **[supporting]** The paper's implied-vol methodology is Black-76 on ATM options with Yang-Zhang realized volatility, on a sample of 43M+ one-minute NIFTY option bars from August 2022 through March 2026 — a replicable spec (and a data-scale benchmark) for building the firm's own VRP measurement layer from 1-min option data.
  - quote: "Implied volatility is derived from ATM options via Black-76; realized volatility is computed using the Yang-Zhang (2000) estimator, which incorporates overnight gap variance structurally absent from conventional close-to-close measures."

### Source (secondary, 2024-10-03) — agent 
- **[central]** From November 20, 2024, SEBI permits each exchange to offer weekly expiry index derivatives on only ONE benchmark index; NSE discontinued weekly expiries for BANKNIFTY, FINNIFTY (Nifty Financial Services), Nifty Midcap Select, and Nifty Next 50 (keeping only NIFTY weeklies), and BSE discontinued BANKEX and Sensex 50 weeklies. Any expiry-day or weekly-VRP anomaly literature sampled pre-Nov-2024 describes a market microstructure that no longer exists for BANKNIFTY weeklies.
  - quote: "Under the new rules, stock exchanges will only be allowed to offer weekly expiry contracts on one benchmark index. ... NSE has discontinued weekly expires for Bank Nifty, Nifty Financial Services, Nifty Midcap Select, and Nifty Next 50 ... BSE has discontinued it for BANKEX and Sensex 50 indices."
- **[central]** Effective November 21, 2024, minimum index-derivatives contract value was raised to Rs. 15-20 lakh (from Rs. 5-10 lakh), with lot sizes revised: NIFTY 50 from 25 to 75, BANKNIFTY from 15 to 30 (article also lists FINNIFTY 25 to 65, SENSEX 10 to 20). This triples the minimum capital granularity for retail index-options position sizing.
  - quote: "Starting November 21, 2024, the contract value will be increased to between Rs. 15 lakhs to Rs. 20 lakhs. ... NIFTY 50: revised from 25 to 75; Nifty Bank (BANKNIFTY): revised from 15 to 30."
- **[central]** From November 20, 2024, short option positions attract an additional 2% Extreme Loss Margin (ELM) on expiry day — directly raising the margin requirement for 0DTE/expiry-day short-vol strategies (article's example: roughly Rs. 39,300 extra for one NIFTY lot at index 26,200).
  - quote: "Starting November 20, 2024, an Extreme Loss Margin (ELM) of 2% will be applied to short positions (selling options) on the expiry day to cover potential risks due to increased volatility."
- **[central]** Calendar-spread margin benefit is removed on expiry day for contracts expiring that day (article states effective February 10, 2025; cross-check vs SEBI circular which is elsewhere reported as February 1, 2025) — a hedged position previously margined at ~Rs. 50,000 requires the full ~Rs. 1 lakh on expiry day, materially changing capital efficiency of calendar/diagonal structures held into expiry.
  - quote: "To manage this risk, SEBI has decided that traders will not get any margin benefits for calendar spreads on the day of expiry for contracts expiring on that day from February 10, 2025."
- **[supporting]** From April 1, 2025, index-derivatives position limits are monitored intraday multiple times per day (not just end-of-day), so intraday peak exposure — not just EOD positions — must stay within limits; additionally, option buyers must pay the entire premium upfront (a SEBI mandate Zerodha says it already enforced).
  - quote: "Starting April 1, 2025, these will be monitored multiple times throughout the trading day. ... SEBI has mandated that an option buyer now needs to pay the entire option premium upfront."

### Source (primary, 2021-09-20) — agent 
- **[central]** Zerodha blocked Stop-loss market (SL-M) orders for index options effective 20 September 2021, meaning retail traders on that broker cannot use market-triggered stop losses on index options and must use SL-limit orders instead.
  - quote: "we have blocked the Stop-loss market (SL-M orders) for Index options from today to reduce the risk exposed towards the freak trades."
- **[central]** NSE itself discontinued the Stop-loss market order facility exchange-wide from 27 September 2021, so the SL-M ban is an exchange-level rule, not merely a broker-specific policy — any execution-realism model for Indian index options after Sep 2021 must assume stop-losses execute as SL-limit orders (with possible non-fill on gap-through).
  - quote: "In line with NSE stopping the facility of Stop-loss market orders from 27th September 2021..."
- **[supporting]** The stated rationale for blocking SL-M orders was the 'freak trades' problem in F&O (extreme prints after removal of the execution range), implying market orders on illiquid option strikes could fill at absurd prices — relevant to slippage/fill modeling for stop exits.
  - quote: "to reduce the risk exposed towards the freak trades"
- **[supporting]** The prescribed alternative to SL-M is the Stop-loss Limit (SL) order type, which introduces non-fill risk when price gaps through the limit — a constraint the master plan's backtest fill logic for stop exits on NIFTY/BANKNIFTY options must encode.
  - quote: "Users can place Stop-loss Limit (SL) orders instead."
- **[tangential]** This specific bulletin scopes the block to index options only and does not state that stock options are affected (the broader NSE change and subsequent broker policies extended market-order restrictions further, but that is not evidenced by this page).
  - quote: "Index options only. The bulletin does not mention stock options being affected."

### Source (primary, 2014-07-31) — agent 
- **[central]** The Deflated Sharpe Ratio (DSR) corrects observed Sharpe ratios for selection bias under multiple testing and for non-normal returns, and computing it requires disclosing the full trial history — number of independent trials N, variance of trial SRs, sample length T, and return skewness/kurtosis — which means a research shop must maintain a complete experiment registry (all trials, not just winners) for the statistic to be computable at graduation gates.
  - quote: "The Deflated Sharpe Ratio (DSR) corrects for two leading sources of performance inflation: Selection bias under multiple testing and non-Normally distributed returns. In doing so, DSR helps separate legitimate empirical findings from statistical flukes. ... asks the strategist to disclose: i) The number of independent trials carried out (N); ii) the variance of the backtest results; iii) the sampl"
- **[central]** Holdout / out-of-sample validation cannot by itself prevent backtest overfitting: if the holdout set is reused across trials (roughly 20 applications at a 95% confidence level), false positives become expected rather than unlikely — so an embargo policy must count and limit touches of the holdout window, not merely partition data.
  - quote: "the holdout method can not prevent backtest overfitting: Holdout assesses the generality of a model as if a single trial had taken place, again ignoring the rise in false positives as more trials occur. If we apply the holdout method enough times (say 20 times for a 95% confidence level), false positives are no longer unlikely: They are expected."
- **[central]** Under the null of zero true skill, the expected maximum Sharpe ratio across N independent trials is strictly positive and grows with N (approximated in the paper's Equation 1 using the Euler-Mascheroni constant, ~0.5772), so a sufficiently large unrecorded search guarantees discovery of a misleadingly profitable strategy.
  - quote: "After a sufficient number of trials, it is guaranteed that a researcher will always find a misleadingly profitable strategy, a false positive. ... the expected maximum of {SR_n} after N>1 independent trials can be approximated as [Equation 1] where gamma (approx. 0.5772) is the Euler-Mascheroni constant."
- **[supporting]** Worked example with concrete effect size: an annualized backtest Sharpe of 2.5 over 5 years of daily data (T=1250), selected as the best of N=100 trials with return skewness -3 and kurtosis 10, yields DSR of about 0.90 — failing a 95% confidence gate (only a 90% chance the true SR exceeds zero); the same discovery would have passed had it come from only N=46 trials.
  - quote: "many combinations yield an annualized SR of 2, with a particular one yielding a SR of 2.5 over a daily sample of 5 years. ... The analyst responds that N=100 ... T=1250 ... The investor has recognized that there is only a 90% chance that the true SR associated with this strategy is greater than zero. Should the strategist have made his discovery after running only N=46 independent trials, the inve"
- **[supporting]** The paper prescribes an optimal-stopping (1/e-law) rule to cap the number of trials in a research campaign: randomly sample roughly 37% of the theoretically justifiable strategy configurations, then continue one-by-one and stop at the first configuration that beats all previous ones — a concrete, adoptable trial-budget rule for a pipeline SOP.
  - quote: "From the set of strategy configurations that are theoretically justifiable, sample a fraction 1/e of them (roughly 37%) at random and measure their performance. After that, keep drawing and measuring the performance of additional configurations from that set, one by one, until you find one that beats all of the previous. That is the optimal number of trials, and that "best so far" strategy the one"

### Source (primary, 2024-10-01) — agent 
- **[central]** From November 20, 2024, each Indian stock exchange may offer weekly-expiry derivatives contracts on only ONE of its benchmark indices — a structural break that ended BANKNIFTY (and FINNIFTY/MIDCPNIFTY) weekly options, meaning any expiry-day-effect or weekly-VRP research sample spanning this date has a regime change in the data-generating process.
  - quote: "Henceforth, each exchange may provide derivatives contracts for only one of its benchmark index with weekly expiry. ... This measure shall be effective from November 20, 2024., i.e. from this date weekly derivatives contracts would only be available on one benchmark index for each exchange."
- **[central]** From November 20, 2024, an additional Extreme Loss Margin of 2% is levied on all short index options contracts on their expiry day (both positions open at start of day and those initiated intraday), directly raising the margin cost of 0DTE short-straddle/strangle strategies like the firm's S1-F.
  - quote: "it has been decided to increase the tail risk coverage by levying an additional ELM of 2% for short options contracts. ... This would be applicable for all open short options at the start of the day, as well on short options contracts initiated during the day that are due for expiry on that day. ... This measure shall be effective from November 20, 2024."
- **[central]** From February 01, 2025, calendar spread margin benefit is removed on expiry day for any position involving a contract expiring that day — worst-scenario loss is computed separately for expiring vs non-expiring contracts — so calendar-spread strategies face a margin spike on expiry day that backtests must model.
  - quote: "the benefit of offsetting positions across different expiries ('calendar spread') shall not be available on the day of expiry for contracts expiring on that day. ... On the day of expiry, the worst scenario loss ... shall be calculated separately for contracts expiring on the given day and for the rest of the contracts. ... shall be effective from February 01, 2025."
- **[central]** New index derivatives contracts introduced after November 20, 2024 must have a value of at least Rs. 15 lakhs at introduction, with lot sizes set to keep contract value within Rs. 15-20 lakhs at review (previous 2015-era band was Rs. 5-10 lakhs) — this roughly tripled minimum notional per lot (NIFTY lot 25→75), raising the capital floor for any per-lot strategy sizing.
  - quote: "it has been decided that a derivative contract shall have a value not less than Rs. 15 lakhs at the time of its introduction in the market. Further, the lot size shall be fixed in such a manner that the contract value of the derivative on the day of review is within Rs. 15 lakhs to Rs. 20 lakhs. ... The measure shall be effective for all new index derivatives contracts introduced after November 20"
- **[supporting]** From February 01, 2025, option premium must be collected upfront from option buyers as part of upfront margin (verified via Clearing Corporation intraday snapshots with penalties), and from April 01, 2025 index-derivatives position limits are monitored intraday via a minimum of 4 random snapshots per day with the end-of-day breach penalty structure extended to intraday breaches.
  - quote: "the upfront margin collection requirement shall also include net options premium payable at the client level. ... applicable for equity derivatives segment from February 01, 2025. ... Stock Exchanges shall consider minimum 4 position snapshots during the day. ... effective for equity index derivatives contracts from April 01, 2025."

### Source (secondary, 2016-05-05) — agent 
- **[central]** Weekly options on the Bank Nifty index began trading on NSE effective May 27, 2016 (the first weekly index options in India), so NSE F&O bhavcopy data before that date contains no weekly BANKNIFTY option contracts — pre-2016 bhavcopy holds monthly index options only.
  - quote: ""The exchange is pleased to inform members that with reference to approval received from Sebi, Weekly Options contracts on Bank Nifty index shall be made available for trading in Future & Options segment with effect from May 27, 2016," National Stock Exchange said in a circular."
- **[central]** Weekly Bank Nifty option contracts were specified to expire every Thursday, rolling to the previous trading day when Thursday is a holiday — defining the Thursday-expiry calendar regime that governs BANKNIFTY expiry-day-effect studies from May 2016 until later expiry-day changes.
  - quote: "It said that Bank Nifty contracts will expire on the every Thursday of week. In case, Thursday is a trading holiday, the contracts will expire on the previous trading day."
- **[supporting]** Weekly BANKNIFTY options expire at the normal market closing time on expiry day, meaning settlement references the end-of-day close — relevant to how expiry-pinning/max-pain tests around the closing session should be designed.
  - quote: ""All contracts shall expire at the normal market closing time on the expiry day or such other time as decided by exchange," the bourse said."
- **[supporting]** The weekly-options launch followed explicit SEBI approval, i.e., new index-derivative contract introductions in India are regulator-gated events with announced start dates (useful for event-study dating of microstructure regime changes).
  - quote: "The decision comes after receiving approval from markets regulator Securities and Exchange Board of India (Sebi)."
