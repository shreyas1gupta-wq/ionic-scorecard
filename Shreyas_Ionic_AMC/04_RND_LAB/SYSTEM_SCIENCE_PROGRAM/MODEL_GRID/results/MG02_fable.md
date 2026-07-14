Approach: no tools needed — I'll reason from Indian market structure and pick five hypotheses with disjoint mechanisms, each killable with free/near-free data (NSE archives, exchange filings, one cheap broker API).

# Five falsifiable alpha hypotheses for Indian markets

The five mechanisms are deliberately disjoint: (1) mispriced insurance sold to lottery buyers, (2) mandated inelastic demand on a known date, (3) a regulatory constraint forcing unwinds, (4) contractual supply released into thin float, (5) hedging-flow feedback from expiry mechanics. Different instruments, different losers, different test designs.

---

## H1. Weekly Nifty options are overpriced relative to realized moves (behavioral vol premium)

**Hypothesis.** The premium of short-dated Nifty options (weekly ATM straddles as the cleanest proxy) systematically exceeds the subsequently realized move by more than transaction costs, and still does post the 2024-25 reforms.

**Mechanism & loser.** SEBI's own studies found ~93% of individual F&O traders lose money — roughly Rs 1.8 lakh crore cumulatively over FY22-24 and about Rs 1 lakh crore in FY25 alone — with losses concentrated in bought short-dated options. Buyers are paying for lottery convexity, not hedging; the losing side is literally measured by the regulator. Prop desks and FPI algos harvest it; a small team can sit on the same side. Open question: whether the Oct/Nov 2024 reforms (one weekly per exchange, tripled lot sizes, expiry-day margins) and seller crowding have compressed it to zero.

**Cheapest kill test.** From free NSE F&O bhavcopy: each week at the prior expiry's close, record the ATM weekly straddle premium; hold to expiry; payoff = |S_T − K|. ~50 observations/year, no intraday data. Compare mean premium vs mean payoff net of costs (STT 0.1% on sold premium, spread, slippage). Split pre/post Nov 2024.

**Data.** NSE F&O bhavcopy archive (free), Nifty closes, a cost schedule.

**Kills it.** Mean (premium − payoff − costs) ≤ 0, or t < 2 — especially if positive pre-reform but ≤ 0 in the post-reform subsample. That last result means the edge existed but has been regulated/arbitraged away, which is the answer that matters going forward.

---

## H2. Nifty reconstitution front-running (mandated passive demand)

**Hypothesis.** Announced additions to Nifty 50 / Nifty Next 50 earn positive abnormal returns between announcement and effective date (deletions negative), scaled by passive-demand-to-ADV, with partial post-effective reversal.

**Mechanism & loser.** Indian passive AUM (ETFs + index funds, including EPFO's ETF buying) has grown past ~Rs 10 lakh crore, concentrated in Nifty-family trackers. Index funds minimize tracking error by executing at the effective-date close regardless of price — inelastic demand on a pre-announced date, several days of ADV for big promotions. Loser: index-fund investors, who buy after the run-up by mandate. The US inclusion effect decayed to ~zero as arb capital caught up; India's passive share grew late and fast, so whether it is still alive here is genuinely open.

**Cheapest kill test.** Event study: announcement-to-effective CARs vs size/sector-matched controls, plus 20-day post-effective reversal, stratified by (index weight × tracked AUM)/ADV. NSE Indices press releases give exact announcement dates; Nifty 50 + Next 50 (+ Midcap 150 for sample size) over 10 years gives 100+ events.

**Data.** NSE Indices press-release archive, EOD bhavcopy prices/volumes, per-index passive AUM from AMFI/factsheets. All free.

**Kills it.** CAR indistinguishable from zero in the most recent ~3 years regardless of the older sample; or the run-up fully reverts so the round trip nets less than costs; or the effect survives only in tiny-ADV names where impact eats it.

---

## H3. F&O ban-list forced deleveraging (constraint-driven overshoot)

**Hypothesis.** Stocks entering the F&O ban (MWPL utilization ≥ 95%) see continued negative pressure and depressed futures basis while in ban, and abnormal positive reversal after exit (< 80%), because leverage can only come off, not on.

**Mechanism & loser.** Ban names are crowded, leveraged retail-long midcaps. In ban, no fresh derivative positions are allowed; cash shorting is nearly impossible for most participants (SLB is thin), so the constraint binds asymmetrically: leveraged longs become forced sellers while bargain hunters cannot lever in — a textbook limits-to-arbitrage overshoot. Loser: constrained leveraged speculators unwinding on a schedule they didn't choose, plus hedgers paying a distorted basis.

**Cheapest kill test.** NSE publishes the ban list and MWPL utilization daily (free archive; hundreds of episodes over 8-10 years). Event study on entry and exit dates vs momentum/size-matched controls: abnormal returns, basis path, and one naive rule (buy exit day, hold 5 days) net of realistic impact costs for these names.

**Data.** NSE ban-list/MWPL archives, cash and futures bhavcopy. Free.

**Kills it.** No abnormal return or basis pattern vs controls; or a pattern smaller than the (high) round-trip cost in these illiquid names; or sign instability across sub-periods, indicating crowding noise rather than the constraint mechanism.

---

## H4. IPO anchor lock-in expiries create dated supply pressure

**Hypothesis.** Mainboard IPOs earn negative abnormal returns around the 30-day and 90-day anchor unlock dates (and the 6-month pre-IPO holder unlock), increasing in unlock-size-to-float.

**Mechanism & loser.** Anchor allocations — names, quantities, and the exact lock-in end dates — are published at listing in exchange press releases. Post-listing float is thin because retail/HNI allottees flip early, so a dated, sized supply block hits a small float. The other side is retail momentum buyers who don't read the unlock calendar. Persistence is protected by limits to arbitrage: most fresh listings have no stock futures and negligible borrow, so professionals cannot short the pre-unlock run-up. Loser: post-listing retail holders through the unlock window.

**Cheapest kill test.** For 2023-2025 mainboard IPOs (200+), scrape anchor allocation PDFs, compute unlock dates and unlock/float, run CARs in [-10, +10] around each unlock vs market and listing-cohort controls, sorted into unlock-size terciles.

**Data.** Exchange anchor-allocation and basis-of-allotment documents, listing dates, EOD prices. Free; one week of scraping.

**Kills it.** CARs around unlocks ≥ 0 or insignificant even in the top unlock/float tercile; or the effect is real but exists only pre-unlock in unshortable names *and* there is no exploitable post-unlock dip-and-reversal — real but untradeable in both directions (pure avoidance is not alpha).

---

## H5. Expiry-day hedging signature on Nifty — with a built-in natural experiment

**Hypothesis.** Nifty intraday behavior on weekly-expiry days differs exploitably from non-expiry days — the close lands nearer the maximum-OI strike than chance (pinning), or late drift amplifies when price is far from it (short-gamma chase) — and, because the cause is expiry mechanics, the signature must have migrated when NSE moved the weekly expiry from Thursday to Tuesday in 2025 (and disappeared from Bank Nifty when its weeklies were discontinued in Nov 2024).

**Mechanism & loser.** Enormous 0-1 DTE open interest concentrates mechanical delta-hedging into the final hour; high-OI strikes act as magnets or accelerants depending on the sign of aggregate hedger gamma. Loser: expiry-day directional retail, whose losses in short-dated options SEBI has documented — they pay decay at pins and get whipsawed off them.

**Cheapest kill test.** 1-minute Nifty candles from a broker API (~Rs 2,000/month) plus free per-strike OI from bhavcopy. Metric 1: ATR-normalized distance of the 15:30 close to the nearest high-OI strike, expiry vs non-expiry days. Metric 2: last-75-minute drift conditional on 14:15 distance-to-strike. Then the diff-in-diff across the Thursday→Tuesday migration: the signature must appear on Tuesdays and vanish from Thursdays.

**Data.** Broker historical API, F&O bhavcopy, exchange circulars for exact change dates. A few thousand rupees total.

**Kills it.** Expiry and non-expiry distributions statistically indistinguishable; or the signature fails to migrate with the administrative change (then it was day-of-week seasonality, not expiry mechanics); or the effect is real but below index-futures round-trip cost (~2 bps + impact).

---

**Cross-cutting discipline for all five:** split every sample at Nov 2024 (the derivatives-reform regime break) and treat pre-reform-only results as dead; net everything of realistic costs including current STT; build all event lists point-in-time from free exchange archives to avoid survivorship; and pre-register the kill criterion before looking at returns.

Sanity check: re-read the ask and verified the deliverable — exactly 5 hypotheses, each with mechanism plus identified loser, a single cheapest kill test, a data list a small team can actually obtain (free NSE/BSE archives, exchange filings, one cheap broker API), an explicit kill criterion, and five mutually distinct mechanisms (behavioral premium, mandated demand, regulatory constraint, contractual supply, hedging feedback). No tools were used, per instruction.

result: Delivered 5 distinct, cheaply testable falsifiable alpha hypotheses for Indian markets — weekly option premium vs realized, Nifty reconstitution flows, F&O ban-list forced unwinds, IPO anchor-unlock supply, and expiry-day pinning with the 2025 expiry-migration natural experiment — each with mechanism, losing counterparty, cheapest kill test, data sources, and kill criteria.