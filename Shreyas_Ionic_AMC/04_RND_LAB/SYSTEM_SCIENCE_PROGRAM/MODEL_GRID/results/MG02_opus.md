# MG02 — Five Falsifiable Alpha Hypotheses (opus)

**Author:** opus (MODEL_GRID cell MG02) · **Date:** 2026-07-13 · **Scope:** Indian equity + index derivatives, small-team-testable, cheap data only.

Design rule enforced: the five differ by *mechanism axis* and *losing counterparty*, not by parameter. Axes covered — (1) intraday/overnight seasonality, (2) derivatives risk premium, (3) fundamental information diffusion, (4) behavioural risk-preference factor, (5) India-specific positioning/crowding microstructure. Every test names a **single pre-registered kill number** so a null result ends it in one pass. Tags: [INFERENCE] = reasoning, [DATA] = source, [OPINION] = prior.

---

## H1 — Overnight drift owns the index risk premium; the intraday session is flat-to-negative

**Claim.** For NIFTY / BANKNIFTY, the close→open (overnight) return series has materially positive mean and Sharpe, while the open→close (intraday) series is ~zero or negative. Holding the index only overnight beats buy-and-hold on a risk-adjusted basis.

**Mechanism [INFERENCE].** Global cues (US close, SGX/GIFT, commodities, FX) and the compensation-for-holding-overnight-gap-risk are impounded in the opening auction, so the risk premium accrues while the cash market is shut. Intraday, leveraged and margin-financed participants must flatten before close (avoid overnight margin / MIS square-off), creating persistent close-side selling pressure and mean-reverting noise.

**Who loses [INFERENCE].** Retail/prop **intraday day-traders** (MIS/leverage products) who systematically exit into the close and are absent overnight — they forfeit the drift and pay the round-trip cost to avoid gap risk they are actually being paid to bear.

**Cheapest killing test.** Take NIFTY daily OHLC, build two return series: overnight `r_on = open_t/close_{t-1} − 1`, intraday `r_id = close_t/open_t − 1`. Compare cumulative product, mean, and annualised Sharpe of each. One script, minutes to run. (Note DATA LANDMINE #2: use the 09:15 real open, not the 09:00 pre-open auction print, if working from 1-min bars; from daily bhavcopy the official open is fine.)

**Data needed [DATA].** NIFTY / BANKNIFTY daily OHLC, 2010→now. Free (NSE index history / Stooq / Angel getCandleData ONE_DAY — mind LANDMINE #8, use `fromdate = date−1 00:00`). No option or intraday data required for the kill test.

**What kills it (pre-registered).** Overnight annualised Sharpe **< 1.25× intraday Sharpe**, OR overnight mean return **≤ 0 after a 3–5 bp per-side gap-execution haircut** (you cannot trade the auction print costlessly). Either → dead, because the effect must survive the fact that you must actually transact at/near the open.

**Prior-art caveat [OPINION].** Well documented in US/global indices; India-specific magnitude and post-2020-retail-boom persistence are the real questions. If real but shrinking, that is a decay finding, not a kill.

---

## H2 — Positive variance risk premium in NIFTY weekly index options (IV persistently exceeds subsequent RV)

**Claim.** ATM NIFTY implied volatility systematically prices above the realized volatility that follows over the option's life; a defined-risk short-vol structure (e.g. short strangle / iron condor) has positive expected P&L before the tail.

**Mechanism [INFERENCE].** Options are insurance. Structural, price-insensitive **buyers of protection** (portfolio hedgers) and **lottery-ticket buyers** (retail weekly-option punters, now a huge share of NSE volume) bid IV above the actuarially fair level. The premium is compensation for bearing crash/gamma risk that most participants pay to shed.

**Who loses [INFERENCE].** The **net option buyer** — retail weekly OTM buyers chasing convex payoffs and institutional hedgers paying for downside insurance. Their expected loss is the seller's premium.

**Cheapest killing test.** For each week, take ATM IV (invert Black-Scholes on the ATM NIFTY option settle, or use India VIX as the proxy) at entry, and compute the realized vol of NIFTY over the same forward window. VRP = mean(IV − RV_forward), annualised. No live trading, no greeks engine — just a paired IV-vs-realized comparison. **Critically weight by P&L, not by count**, so the few large-loss weeks are included honestly.

**Data needed [DATA].** India VIX daily history (free, NSE) OR NIFTY option bhavcopy for ATM IV (free NSE archives; respect LANDMINE #9 — never read expiry-day option SETTLE_PR as the option price, and gate on CONTRACTS>0), plus NIFTY spot for realized vol. All free.

**What kills it (pre-registered).** Mean(IV − RV_forward) **≤ 0**, OR the premium goes **negative once the worst-decile realized-vol weeks are P&L-weighted** (i.e. the tail eats the whole edge). Either → dead; a short-vol edge that only exists when you exclude the crash weeks is not an edge.

**Prior-art caveat [OPINION].** VRP is one of the most-published anomalies on earth and is crowded on NIFTY. The kill test's job is not "does VRP exist" (it likely does) but "does it survive tail-weighting after retail crowding compressed it post-2023." Treat a thin surviving margin as a fail for a *small, undercapitalised-for-tails* team.

---

## H3 — Post-earnings announcement drift (PEAD) in Indian mid/small-caps

**Claim.** Stocks with a large positive price reaction on the earnings-announcement day continue to drift in the same direction for 20–60 trading days; the effect is stronger in under-covered mid/small-caps than in large-caps.

**Mechanism [INFERENCE].** Slow information diffusion + limited analyst coverage of smaller names → investors underreact to the earnings signal and revise expectations gradually rather than instantly. Large-caps are efficiently priced; the edge lives where attention is scarce.

**Who loses [INFERENCE].** **Slow-updating and inattentive holders** of under-covered stocks who do not re-price on the print, and the market-makers who anchor to stale expectations.

**Cheapest killing test.** Using the PIT earnings dataset (`available_date`, avoids LANDMINE #3/#7 lookahead), proxy the surprise by the announcement-day (or announcement-window) abnormal return — no consensus-estimate data required. Sort event-stocks into quintiles by this reaction; measure the average 20/40/60-day forward return of Q5 (biggest positive reaction) minus Q1. One event-study script.

**Data needed [DATA].** PIT quarterly earnings with announcement dates (`datasets/earnings_pit/unified_quarterly_pit.parquet`, already held) + daily closes for the NIFTY 500 universe (survivorship-safe via `NIFTY500_TICKER_2005_2025_Final.xlsx`, LANDMINE #6). All in-house.

**What kills it (pre-registered).** Q5−Q1 40-day forward spread **not positive at t-stat ≥ 2**, OR the spread **fully absorbed by a 6-1 momentum control** (regress the spread on the stock's prior-6m return; if alpha → 0, it is just momentum in disguise). Either → dead.

**Prior-art caveat [OPINION].** Classic and durable globally; the India-specific, cheaply-testable twist is the large-cap-vs-small-cap coverage split. Must also clear the cost gate — small-cap PEAD is notoriously expensive to trade (impact/slippage), so pair any survivor with a `fill-audit` before excitement.

---

## H4 — Betting-against-beta / low-volatility anomaly in NIFTY 500

**Claim.** Low-realized-volatility (low-beta) stocks deliver equal-or-higher raw returns and materially higher risk-adjusted returns than high-vol stocks; a long-low-vol / short-(or-underweight)-high-vol tilt has positive alpha.

**Mechanism [INFERENCE].** Leverage-constrained investors (most retail, many mandates) who want more return cannot borrow, so they overpay for high-beta and lottery-like high-vol names to reach for return. This bids high-vol stocks to low expected returns and leaves low-vol stocks cheap on a risk-adjusted basis (Frazzini-Pedersen BAB).

**Who loses [INFERENCE].** **Leverage-constrained, return-reaching retail** crowding into high-beta / high-vol lottery stocks — a documented and growing Indian retail behaviour.

**Cheapest killing test.** Rank the survivorship-safe NIFTY 500 each month by trailing 12-month realized vol; form the bottom-decile (low-vol) and top-decile (high-vol) equal-weight baskets; compare next-12-month return and Sharpe. Cross-check against the official **NIFTY 100 Low Volatility 30 / Alpha Low-Vol** index vs plain NIFTY as a free external validation.

**Data needed [DATA].** Daily closes, NIFTY 500 PIT universe (in-house, LANDMINE #6). Optional validation: official niftyindices.com factor-index closes (free; the `factor-indices` skill fetches them — home-network only). No fundamentals needed.

**What kills it (pre-registered).** Low-vol decile forward Sharpe **≤ high-vol decile Sharpe**, OR the official NIFTY Low-Vol 30 index **fails to beat NIFTY on Sharpe** over 2010→now. Either → dead. (Raw-return underperformance alone does NOT kill it — the claim is risk-adjusted; only a Sharpe failure kills.)

**Prior-art caveat [OPINION].** Very well known; there is a tradable index, so a naive version is not proprietary alpha. Worth testing only as (a) a cheap sanity anchor that our data plumbing reproduces a known effect, and (b) a base to add a genuinely differentiated overlay later. Flag as low-novelty.

---

## H5 — F&O security-in-ban list flags crowded leverage; forward reversal after ban entry (India-specific)

**Claim.** When a single-stock derivative enters the NSE **F&O ban period** (market-wide open interest > 95% of the position limit), it marks extreme crowded speculative positioning; the underlying tends to **mean-revert / underperform** over the following days versus its pre-ban trend, and unwinding into ban-exit is exploitable.

**Mechanism [INFERENCE].** A ban-list entry is a hard, observable signal that leveraged directional positioning has maxed out — no *new* positions can be opened, so the marginal speculative buyer is removed and forced unwinds dominate. Crowded, over-leveraged momentum in that name is at its most fragile precisely when everyone is already in.

**Who loses [INFERENCE].** **Crowded, over-leveraged directional speculators** who piled into the F&O name late (chasing the move that drove OI to the limit) and must unwind as the ban forces position reduction.

**Cheapest killing test.** Scrape the daily NSE F&O ban list (published every trading day, free). For each name-entry event, measure the underlying's forward 1/3/5/10-day return, and compare to (a) its own prior 10-day trend and (b) a same-day sector/beta-matched control. One scraping script + one event-study. India-specific and essentially free.

**Data needed [DATA].** NSE daily "Securities in ban period" list history (free NSE archive / daily bhavcopy companion file) + daily closes for the banned names. Both cheap and obtainable; no OI-depth or paid feed required — the ban list *is* the pre-computed crowding flag.

**What kills it (pre-registered).** Post-ban-entry forward return (vs the beta-matched control) **not negative — i.e. no reversal — at t-stat ≥ 2 over the 1–5 day window**, OR any apparent reversal **vanishes after a realistic small/mid-cap round-trip cost + no-fill-on-circuit adjustment** (LANDMINE #7b — banned names are often circuit-locked, so many fills are fictional). Either → dead.

**Prior-art caveat [OPINION].** Under-published relative to H2/H4 and genuinely India-microstructure-specific, so the most likely to be *uncrowded* of the five. Biggest execution risk: banned stocks hit circuits and gap, so the fill-realism gate is where this most plausibly dies — build that into the very first test, not later.

---

## Summary matrix

| # | Edge | Mechanism axis | Losing side | Cheapest kill test | Kills it if |
|---|------|----------------|-------------|--------------------|-------------|
| H1 | Overnight index drift | Intraday/overnight seasonality | Intraday day-traders (flatten into close) | Split NIFTY daily OHLC into overnight vs intraday return series | Overnight Sharpe < 1.25× intraday, or overnight mean ≤ 0 after 3–5 bp gap cost |
| H2 | NIFTY VRP (short vol) | Derivatives risk premium | Net option buyers (hedgers + retail lottery) | Mean(ATM IV − forward RV), P&L-weighted | ≤ 0, or negative once worst-decile RV weeks weighted |
| H3 | Mid/small-cap PEAD | Fundamental information diffusion | Slow-updating holders of under-covered names | Event-study: Q5−Q1 fwd return by announcement-day reaction | 40-day spread t < 2, or fully absorbed by 6-1 momentum |
| H4 | Low-vol / BAB | Behavioural risk-preference factor | Leverage-constrained retail reaching for beta | Low-vol vs high-vol decile forward Sharpe; NIFTY Low-Vol 30 vs NIFTY | Low-vol Sharpe ≤ high-vol Sharpe (index cross-check fails) |
| H5 | F&O ban-list reversal | India positioning/crowding microstructure | Crowded over-leveraged speculators | Event-study on daily NSE ban-list entries vs beta-matched control | No negative fwd return t ≥ 2, or gone after circuit/cost realism |

**Ranking on novelty × cheapness × uncrowdedness [OPINION]:** H5 (most India-specific, likely least crowded) and H1 (cheapest to test, one data series) are the highest-priority first passes; H3 next (in-house PIT data, real coverage angle); H2 and H4 are near-certain to "exist" but are crowded/published, so treat them as data-plumbing sanity anchors and only pursue with a differentiated overlay. All five are killable with data already on the laptop or free from NSE — no vendor spend required.
