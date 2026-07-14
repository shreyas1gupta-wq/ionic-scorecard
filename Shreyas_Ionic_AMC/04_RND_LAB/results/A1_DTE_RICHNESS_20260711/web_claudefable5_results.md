MODEL: claude-fable-5 (Claude Fable 5)   TOOLS: off (each task answered by a fresh isolated context instructed to use no tools)   MODE: fresh-chat-per-task (one isolated context per task; no cross-task priming; answers pasted verbatim, unedited)
NOTE: Run orchestrated from inside a Claude Code session. Each task below was sent to a brand-new isolated subagent context running claude-fable-5 that saw ONLY that one task — not the rest of the packet, not the answer key, and not any other model's answers (a separate Sonnet-5 column from this session exists in web_run_results.md; those answers were never shown to these contexts). First reply per task is the datum; no regenerates; no edits.
PROGRESS: COMPLETE — MG01-MG08 done | T01-T10 done | T11-T20 done

===== MG01 =====
# Backtest Specification — NIFTY500 Top-20 Six-Month Momentum, Monthly Rebalance (v1.0)

Status: frozen before first run. Any edit after the first run creates v1.1 and must be logged in the trial ledger (Section 10). All dates are NSE trading dates, all amounts INR, all returns total-return unless stated.

## 0. Fixed parameters

| Parameter | Value |
|---|---|
| Evaluation window | 2015-01-01 to 2026-06-30 |
| Raw data pulled from | 2014-01-01 (signal + liquidity lookback buffer) |
| Universe | NIFTY500, point-in-time membership |
| Signal | 6-month total return (no skip-month in base; skip variant required, C4) |
| Holdings | Top 20 by signal, equal weight 5.00% at rebalance |
| Rebalance | Monthly. Signal date T = last trading day of month m; execution date E = first trading day of month m+1 |
| Execution price (base) | Close of E |
| Base AUM | ₹10 crore (capacity stress at ₹100 crore, C11) |
| Benchmark (primary) | NIFTY500 TRI |
| Cash | Idle cash accrues daily at 91-day T-bill yield (FBIL/RBI series) |

## 1. Scope and hypothesis

Hypothesis: cross-sectional price momentum in Indian large/mid/small caps survives realistic Indian delivery-trading costs (which are dominated by STT) at small AUM. The backtest's job is to measure net-of-cost excess return versus honest benchmarks and to try to destroy the result via Section 8. This is long-only, cash equities, no leverage, no derivatives, pre-tax (but turnover must be reported so STCG drag can be estimated — every holding period here is <12 months, so all realized gains would be short-term).

## 2. Data requirements and point-in-time rules

### 2.1 Security master
- Key every security on a permanent internal ID mapped to (ISIN, NSE symbol, validity date range). NSE symbols change frequently (name changes are common in India); ingest NSE's symbol-change file and never join on raw symbol across time.
- Ingest the bhavcopy `SERIES` field daily (EQ, BE, BZ, etc.). BE/BZ = trade-to-trade segment; this is an eligibility input (Section 3).

### 2.2 Prices and corporate actions
- Daily OHLCV + traded value from NSE bhavcopies (unadjusted), 2014-01-01 onward. The trading calendar is defined as "dates a bhavcopy exists" — this automatically handles Muhurat sessions and special Saturday sessions (e.g., Budget-day sessions). Do not use a synthetic calendar.
- Build two adjusted series per stock: (a) price-return series adjusted for splits, bonuses, rights, demergers; (b) total-return series = (a) plus gross cash dividends reinvested in the same stock at ex-date close. Signals and NAV use the total-return series.
- Corporate-action adjustment factors from NSE/BSE CA files or a commercial vendor (Accord/Capitaline/CMIE/Refinitiv). Do **not** use Yahoo-style free adjusted data for India; its bonus/demerger handling is unreliable.
- India-specific CA rules a junior must implement explicitly:
  - Bonus issues are ubiquitous — treat exactly like splits via ratio factor.
  - Rights issues: apply the theoretical ex-rights price factor; assume non-subscription and credit **zero** for the entitlement (conservative; note the small downward bias).
  - Demergers: the parent gaps down on ex-date and will otherwise show a fake negative 6-month return. Adjust the parent's back-history by the ex-date factor (vendor-supplied or (cum price − implied spin value)/cum price). Portfolio holding of the spun-off entity: hold, then sell at close of its 5th trading day post-listing.
  - Mergers/buyouts: convert at swap ratio on ex-date; cash consideration credited to cash on payment date.
  - Suspension/delisting-for-cause: mark at last traded price; write down 75% after 60 calendar days of suspension, 100% after 180 days unless trading resumes.
- Point-in-time rule for all of the above: a corporate action affects the backtest only from its ex-date/effective date. Adjustment factors may be applied retroactively to the price series (that is standard and not look-ahead), but eligibility, membership, and signals must use only information public on or before T.

### 2.3 Index membership (the load-bearing item)
- Reconstruct monthly point-in-time NIFTY500 membership from NSE Indices' monthly constituent/market-cap-weightage file archives, supplemented by ad-hoc replacement announcements (mergers, delistings, demergers trigger intra-review changes). Do not hardcode the review schedule — ingest actual change events with their **effective** dates (announcement precedes effective date, so using effective dates is PIT-safe).
- Membership test at signal date T = "member per the latest membership state effective on or before T."
- Validation gate: membership must exist for every month 2014-06 to 2026-06 with 500 ± 10 names. If this cannot be assembled, see kill K1. Using today's constituent list backfilled is forbidden except as the deliberate bias-measurement arm of C1.

### 2.4 Auxiliary data
- Daily ASM/GSM surveillance lists (NSE publishes daily; GSM exists from Mar 2017, ASM from Mar 2018 — the related filters simply don't bind before those dates).
- Daily price-band data (2/5/10/20% bands; F&O-list stocks have dynamic bands). Needed for the circuit fill rule (Section 5).
- 91-day T-bill yields (risk-free and cash accrual); NIFTY500 TRI and NIFTY200 Momentum 30 TRI levels (note: Momentum-30 history before Aug 2020 launch is backfilled by NSE — label it as such); Agarwalla–Jacob–Varma (IIM-A) India factor series for the factor regression.

### 2.5 Data validation gates (run before any strategy code)
- G1: Reconcile daily adjusted total returns for 25 randomly sampled stock-quarters against a second independent source; >25 bps disagreement on >0.5% of stock-days fails the gate.
- G2: Spot-check known events end-to-end: RIL bonuses (2017, 2024), Eicher split (2020), IRCTC split (2021), Nestlé India split (2024), Reliance→Jio Financial demerger (2023), ITC→ITC Hotels demerger (2025). The adjusted series must show no artificial jump on ex-dates.
- G3: Flag every |daily return| > 30% with no same-day CA record; every one must be manually dispositioned (real move vs data error).
- G4: No stale prices — any stock whose close is identical for 10+ consecutive sessions with zero volume gets a data-quality flag and is treated as suspended for those days.

## 3. Universe construction (apply in this exact order, evaluated at each signal date T)

1. NIFTY500 member on T (PIT, per 2.3).
2. NSE series is EQ on T (excludes BE/BZ trade-to-trade).
3. Not suspended on T; traded (volume > 0) on T and on ≥ 90% of trading days in [T−6M, T].
4. Listed on or before T−7M (guarantees full signal window; mechanically excludes recent IPOs — intended, given India's 2021/2024 IPO waves and lockup cliffs).
5. Not in GSM (any stage) and not in ASM long-term Stage II+ on T. (These carry 5% bands / 100% margin / T2T settlement; treat as untradeable-in-size.)
6. 63-day median daily traded value (MDTV) ≥ ₹5 crore.

Ties in the momentum ranking are broken by higher MDTV, then lexicographic ISIN (determinism requirement). If fewer than 20 names survive the filters, hold the shortfall in cash — never relax filters to fill the book.

## 4. Signal and portfolio construction

- Signal: `R6(i,T) = TR(i,T) / TR(i, T−6M) − 1`, where TR is the adjusted total-return level and T−6M is the last trading day of calendar month m−6. If either endpoint falls on a non-traded day for the stock, use the nearest prior traded day within 5 sessions, else the stock is ineligible.
- Rank eligible names descending on R6; select top 20; target weight 5.00% each.
- No sector constraints, no buffers, no vol scaling in the base config (variants are C10).
- Between rebalances: no trading on drift; only forced CA events per 2.2. Dividends and CA cash go to the cash bucket.

## 5. Execution convention

- Signal computed strictly from closes up to and including T. First possible trade is E = next trading day. Base fill price = close of E. (Same-day T-close execution is look-ahead by construction and appears only as a labeled diagnostic in C3.)
- Circuit rule: if a buy target closes at its upper band on E (or a sell at its lower band), assume **no fill**; retry at the next day's close, up to 3 attempts; then abandon (buy → weight stays in cash; sell → hold to next rebalance). This matters: fresh momentum names in India are frequently band-locked.
- Participation cap: a single day's trade in a stock ≤ 10% of its MDTV; split larger orders across consecutive closes (relevant only in the ₹100 crore run).
- Shares are integers, lot size 1, round down, residual to cash. Settlement (T+2 → T+1 in Jan 2023) is assumed cash-neutral via same-day buy/sell netting at the custodian; state this assumption in the report.

## 6. Cost model (per side, on traded value, delivery segment)

| Component | Buy | Sell | Notes |
|---|---|---|---|
| Brokerage | 5.0 bps | 5.0 bps | Institutional discount assumption |
| STT (delivery) | 10.0 bps | 10.0 bps | Constant across 2015–2026; the dominant line |
| Stamp duty | 1.0 bps (<Jul 2020), 1.5 bps (≥Jul 2020) | — | Buy side only post-unification |
| Exchange txn + SEBI fee + GST | 0.5 bps | 0.5 bps | Lumped |
| DP charge | — | ₹15 per ISIN per sell day | Flat, near-zero at size |
| Impact + half-spread, by MDTV | ≥₹50 cr: 10 bps; ₹10–50 cr: 20 bps; ₹5–10 cr: 35 bps | same | Applied per fill |

All-in one-way cost is therefore ~27–52 bps. The report must show measured one-way turnover (defined as 0.5·Σ|w_target − w_drifted| per rebalance, annualized — expect roughly 350–600% one-way p.a. for this design) and the implied annual cost drag in percent. If that drag is 3–5% p.a., that is the honest hurdle; do not bury it.

## 7. Accounting, benchmarks, metrics

- Daily NAV from adjusted closes; trade blotter with per-trade cost decomposition is a mandatory output (holdings file, trades file, monthly returns CSV, tearsheet).
- Benchmarks, all net where applicable: (a) NIFTY500 **TRI** — never the price index; (b) the equal-weight eligible-universe portfolio run through the *same* execution and cost engine — this is the structural benchmark, because a 20-stock EW portfolio drawn from a 500-name universe carries a large size tilt that the cap-weighted index comparison flatters; (c) NIFTY200 Momentum 30 TRI as an external anchor, and, for 2021+, live momentum index funds' actual NAVs as a reality check on achievable alpha.
- Metrics: net and gross CAGR, vol, Sharpe (91-day T-bill), max DD and DD duration, monthly hit rate, skew, worst month, beta/alpha vs NIFTY500 TRI, market-cap-bucket exposure over time, monthly Spearman rank IC of R6 vs next-month return, and a 4-factor regression (MKT/SMB/HML/WML, AJV India series) — report the alpha *after* WML loading, since "alpha" that is pure WML beta is expected, not interesting.

## 8. Control experiments (all mandatory before any conclusion)

- **C1 Survivorship A/B.** Run PIT membership vs today's-list-backfilled. Report the gap; it doubles as a data-pipeline test (gap should be material — if it's ~0, suspect the PIT join is broken).
- **C2 Cost ladder.** 0×, 0.5×, 1×, 2×, 3× the Section 6 costs. Feeds K4.
- **C3 Timing ladder.** Fill at T close (look-ahead diagnostic), E open, E close (base), E VWAP-proxy (mean of O/H/L/C), E+1 close, E+2 close. Alpha that decays steeply across E→E+2 is microstructure, not momentum. Feeds K6.
- **C4 Parameter plateau.** Grid: lookback {3,6,9,12} months × top-N {10,20,30,50} × skip-month {0,1}. Chosen config must sit on a plateau. Feeds K7.
- **C5 Rebalance-date jitter.** Shift signal/execution by +1…+10 trading days; also run four weekly-staggered quarter-size tranches. High dispersion = turn-of-month luck.
- **C6 Random-portfolio null.** 1,000 paths: each month draw 20 names uniformly from the *same* eligible universe, same execution and costs. Report the strategy's percentile on net Sharpe and net CAGR. This isolates selection skill from the EW/size effect. Feeds K5.
- **C7 Signal-sanity pair.** Bottom-20 portfolio (long losers) and the top-minus-bottom spread, gross. If longs-of-losers ≈ longs-of-winners, the ranking carries no information regardless of what the headline shows.
- **C8 Subperiods and concentration.** Fixed windows: 2015–17, 2018–19 (mid/small-cap bear), Feb–Apr 2020 (crash and momentum whipsaw), 2020–21, 2022, 2023–24 (small-cap mania), 2025–H1 2026. Also: cumulative excess PnL contribution of the top 10 stock-months, and best-rolling-12-month share of total excess. Feeds K8.
- **C9 Fragility of edge cases.** Rerun with (a) worst-case −100% on all suspended/delisted-for-cause positions at suspension date, (b) ASM/GSM filter off. Conclusions must not flip.
- **C10 Construction variants.** Rank-weighted, inverse-63-day-vol weighted, sector cap of 6 names, and a hold buffer (incumbents kept while ranked ≤ 40, refill from top). The buffer variant's turnover/cost/alpha trade-off must be tabulated — it is the likely production design.
- **C11 Capacity.** Rerun at ₹100 crore with the 10% MDTV participation cap and multi-day fills. Report % of target rebalance value unfilled within 3 days, and net alpha. (Arithmetic to keep in mind: ₹5 crore per name needs ₹50 crore MDTV for a one-day 10%-participation fill — the NIFTY500 tail fails this.)
- **C12 Holdout.** Development sample: Jan 2015–Jun 2023. The Jul 2023–Jun 2026 window is untouched until the config is frozen, then run **once**. Every configuration ever executed (including all of C2–C10) goes into a trial ledger; report a deflated Sharpe ratio using that trial count.

## 9. Kill criteria (any single trigger kills or voids; no renegotiation after the fact)

- **K1 (void)** PIT membership cannot be assembled per 2.3's validation gate. Do not run; a current-list backtest is not a result.
- **K2 (void)** Data gates G1–G4 fail. Fix data; all prior runs void.
- **K3** Full-sample net (1×-cost) excess CAGR vs NIFTY500 TRI < +3.0% p.a., or net Sharpe < benchmark Sharpe + 0.15.
- **K4** Net excess CAGR ≤ 0 at 2× costs.
- **K5** Net Sharpe below the 95th percentile of the C6 random-portfolio null, or below the EW-eligible-universe benchmark net Sharpe + 0.10 — either way it's the size/EW effect wearing a momentum costume.
- **K6** Moving fills from E close to E+2 close removes > 40% of gross excess return.
- **K7** Median excess CAGR over the neighbor grid {5,6,7 months} × {top 15, 20, 30} × {skip 0, 1} < 60% of the chosen config's excess.
- **K8** Top 10 stock-months > 35% of cumulative excess PnL, or any single rolling 12-month window > 70% of full-period excess.
- **K9** Holdout (C12): net excess return ≤ 0, or net Sharpe < 50% of the development-sample net Sharpe.
- **K10 (per-AUM kill)** At ₹100 crore, >15% of rebalance value unfilled within 3 days in more than 25% of months — the strategy may still pass at ₹10 crore, but the ₹100 crore claim dies.

Additionally, an investability flag (not a kill): if net max drawdown exceeds the benchmark's by more than 20 points while K3's margin is under +5% p.a., the risk isn't being paid for; say so in the report.

## 10. Process discipline

- This document is hashed and committed before the first run; the engine reads one YAML config that mirrors Section 0; a single command reproduces every table from a versioned data snapshot.
- Trial ledger: every executed configuration (parameters, git commit, data snapshot ID, headline stats) is appended automatically. The deflated-Sharpe calculation in C12 uses this ledger's count — no forgetting inconvenient runs.
- The holdout is opened once. If v1.0 dies, v1.1 requires a new hypothesis note stating what changed and why *before* rerunning, and the holdout result of v1.0 is reported alongside.
- Unit tests required before first run: CA adjustment on the G2 event list, PIT membership join (a stock that left the index must vanish from eligibility the correct month), circuit no-fill logic, and turnover/cost reconciliation (sum of blotter costs = NAV cost drag to the rupee).

Sanity check performed: re-read the ask — all six requested elements are covered concretely (data + PIT rules in §2, universe in §3, signal timing and execution convention in §4–5, cost model with India-specific statutory lines in §6, twelve control experiments in §8, ten numeric kill criteria in §9), with every parameter given an explicit value so a junior quant can implement without follow-up questions.

result: Delivered a frozen, implementable backtest spec for a NIFTY500 top-20 six-month momentum strategy (2015–2026): point-in-time data rules, ordered universe filters, T-signal/E-close execution with circuit-lock handling, an STT-dominated Indian cost model (~27–52 bps one-way), 12 mandatory control experiments, and 10 numeric kill criteria.

===== MG02 =====
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

===== MG03 =====
Design doc below. Since no tools are allowed, my sanity check is a requirements re-read at the end mapping each of the four guarantees to the specific mechanism that enforces it.

# Resume-safe EOD ingestion pipeline

Example flavor: NSE-style bhavcopy zips posted ~18:00 IST; everything generalizes.

## 1. Disk layout (one filesystem, so renames are atomic)

```
data/
  incoming/                      # *.part downloads + *.meta.json (etag, expected size, url)
  raw/YYYY/MM/DD/file.zip        # immutable, verified originals (chmod 444 after landing)
  raw/YYYY/MM/DD/file.zip.sha256 # sidecar written at verification time
  quarantine/YYYY-MM-DD/         # failed verification + .reason.json, kept 30 days
  dataset/trade_date=YYYY-MM-DD/ # parquet partition + _SUCCESS marker containing the source sha256
  ledger/ingest.db               # SQLite (WAL) — rebuildable index, NOT the source of truth
  logs/YYYY-MM-DD.jsonl
```

Hard rule: `incoming/` and `raw/` are on the same mount so `rename()` is atomic. Nothing ever writes directly into `raw/` or `dataset/`; both are reached only by rename-after-verify.

## 2. Ledger

```sql
CREATE TABLE files (
  source TEXT, file_kind TEXT, trade_date TEXT,
  state TEXT CHECK(state IN ('PENDING','VERIFIED','INGESTED','HOLIDAY',
                             'QUARANTINED','WAITING_RETRY','NEEDS_HUMAN')),
  url TEXT, size INTEGER, etag TEXT, sha256 TEXT,
  attempts INT DEFAULT 0, last_error TEXT, next_retry_at TEXT,
  verified_at TEXT, ingested_at TEXT, operator_note TEXT,
  PRIMARY KEY (source, file_kind, trade_date));
CREATE TABLE alerts (key TEXT PRIMARY KEY, first_at TEXT, last_at TEXT,
                     count INT, resolved_at TEXT);
CREATE TABLE lease  (name TEXT PRIMARY KEY, owner TEXT, expires_at TEXT);
```

Two invariants that make this crash-safe:

- **The ledger records only durable facts, never in-flight status.** There is no `DOWNLOADING` state; a crash mid-download simply leaves a `.part` file, which the next run resumes. Attempt counts and `next_retry_at` are durable facts, so backoff survives restarts.
- **Filesystem first, ledger second.** File lands in `raw/` before the row says `VERIFIED`; the `_SUCCESS` marker lands before the row says `INGESTED`. Every crash window between the two is closed by `rebuild-ledger` (below), which re-derives state from disk — never by trusting a flag.

## 3. Work planning — absence is a first-class state

A versioned trading-calendar file (holidays, timezone `Asia/Kolkata`) expands into the expected set of `(source, file_kind, trade_date)` rows. Each expected file gets a `PENDING` row; holidays get `HOLIDAY`. This is what makes "nothing is ever lost" enforceable: a missing day is a visible non-`INGESTED` row, not silence. `pipeline gaps --since 2020-01-01` lists every unfilled trading day in seconds. An ad-hoc exchange holiday is resolved by a human with `pipeline mark-holiday 2026-07-14 --reason "..."` (recorded with operator note).

## 4. Download step (the unreliable-proxy defenses)

Per file, worker does:

1. `HEAD` (or `GET Range: bytes=0-0`) → capture `Content-Length`, `ETag`/`Last-Modified` into `incoming/name.meta.json`.
2. If `name.part` exists and stored ETag matches, resume with `Range: bytes=<part_size>-`. ETag mismatch or no `Accept-Ranges` → delete `.part`, restart from zero.
3. Stream in 1 MiB chunks. Timeouts: connect 15 s, read 60 s. **Stall watchdog:** if throughput < 20 KB/s averaged over 60 s, abort the attempt (equivalent to curl `--speed-limit 20480 --speed-time 60`) and retry immediately with a Range resume — a stall costs 60 s, not a hang.
4. **Retry schedule** on failure: 1 m, 5 m, 15 m, 60 m, then hourly, ±20% jitter, persisted in `next_retry_at` so restarts don't reset backoff. Honor `Retry-After` on 429/503.
5. **Block detection:** HTTP 403/429, connect-reset, or a 200 whose Content-Type/magic bytes are HTML instead of the expected zip (corporate proxies inject 200 block pages — never trust a 200). On block signature: back off 90 ± 30 min, force concurrency to 1, and keep a 3–8 s jittered politeness gap between requests on one keep-alive session. Default concurrency is 1 anyway — at 0.7 MB/s the link, not the loop, is the bottleneck, and parallelism only raises block risk.

## 5. Verification gate (corrupt bytes can't pass)

Runs on the completed `.part`, still in `incoming/`:

1. Byte size == Content-Length and == sidecar expectation.
2. Publisher checksum if the archive provides one.
3. Structural: zip CRC test of every member (`zipfile.testzip`), full gzip decode, strict-schema CSV parse.
4. Semantic hard-fails: zero rows; embedded trade date != requested date (catches "server served yesterday's file / an error page"). Soft warning (log only): row count outside 50–200% of the trailing 20-day median.
5. Compute SHA-256 → write sidecar → `fsync` file → atomic rename into `raw/YYYY/MM/DD/` → fsync directory → `chmod 444` → ledger row `VERIFIED`.

Failure → move to `quarantine/` with `.reason.json`, re-download from scratch (proxy mangling is the usual cause). Three failures with *identical* bad bytes → `NEEDS_HUMAN` (source-side problem). If a re-download of an already-`VERIFIED` date returns different bytes, never overwrite: store as `name.<sha8>.v2` and raise a RESTATEMENT alert for a human decision.

## 6. Ingestion — exactly-once by construction

Idempotency key: `(trade_date, file_sha256)`. Reads only from `raw/`.

- Parquet target: write to `dataset/_tmp/<uuid>/`, atomic-rename to `dataset/trade_date=YYYY-MM-DD/` containing `part-<sha8>.parquet`, write `_SUCCESS` (embedding the source sha256) last, then ledger `INSERT OR IGNORE` → `INGESTED`. The partition path is a pure function of the key, so re-running after any crash overwrites the same partition with the same bytes — replay converges, never duplicates. No appends anywhere (appends are how double-ingest happens).
- SQL target: `DELETE FROM eod WHERE trade_date=?; INSERT ...; INSERT INTO ingested(sha256, trade_date)...` in **one transaction**, with the idempotency table in the target DB itself.

Orphan `_tmp/` dirs and `.part` files older than 7 days are removed by a janitor step.

## 7. Scheduling and single-writer safety

systemd timer (or cron) runs the same idempotent command `pipeline run` at 18:30 IST, hourly until 23:00, and once at 07:00 next day for stragglers. Every run: acquire lease → plan → download → verify → ingest → alert-evaluate → heartbeat. The **lease** is a ledger row (`owner`, `expires_at`, heartbeat-refreshed every 60 s, stealable after 5 min stale) so an overlapping cron fire or a second machine can never double-run — critical during migration.

## 8. Alerting — silent unless a human must act

- **Never alerts:** retries, stalls, resumed downloads, a verification failure fixed by re-download, holiday skips. These go to JSONL logs and an optional daily digest line.
- **Alerts (Slack webhook + email fallback):** (a) any trading day not `INGESTED` by the SLA of T+1 09:00 IST — the only "data missing" signal a human ever needs; (b) 3× identical-bytes verification failure; (c) block signature persisting > 4 h despite backoff (means: call IT about the proxy); (d) RESTATEMENT detected; (e) disk < 10 GB, unwritable ledger, or lease conflict.
- **Dedup:** the `alerts` table keys each condition; re-fire only every 24 h while unresolved, and send an auto-resolve note when the condition clears. No repeats, no pager fatigue.
- **Dead-man switch:** the box that is down cannot alert about itself, so each successful cycle pings an external healthchecks.io-style URL with a 26 h grace period. Silence → external alert. This closes the "whole machine died quietly" hole.

## 9. New-machine takeover

`raw/` (plus its sidecars) is the only irreplaceable artifact — the ledger and dataset are both derivable from it — and it is rsync/rclone'd nightly to a second location along with a WAL-safe `sqlite3 .backup` snapshot.

Takeover: (1) install pinned code + config on the new box; (2) copy or mount the data dir (worst case: just `raw/`); (3) `pipeline rebuild-ledger` — every `raw/` file whose bytes match its sidecar hash → `VERIFIED`, every dataset partition with a `_SUCCESS` marker matching that hash → `INGESTED`, everything expected-but-absent → `PENDING`; add `--verify-all` to re-hash the whole copy after an untrusted transfer; (4) enable the timer. The first `pipeline run` resumes any `.part`, backfills the gap since the last file, and the lease guarantees safety even if the old machine wasn't stopped yet.

## Sanity check — requirement → enforcing mechanism

| Requirement | Mechanism |
|---|---|
| Nothing lost | Calendar-derived expected set makes absence visible; SLA alert + `gaps`; immutable append-only `raw/`; nightly offsite copy |
| Nothing double-ingested | `(trade_date, sha256)` idempotency key; rename-into-place partitions or single-transaction SQL; `INSERT OR IGNORE` ledger; no appends; lease against concurrent runners |
| Corrupt data never enters | Verify-then-rename gate (size, CRC, strict parse, embedded-date match, sha256) before anything touches `raw/`; quarantine; 200-with-HTML proxy-page detection |
| Alert only when actionable | Retries/stalls are silent; alerts only on SLA breach, persistent block, repeated identical corruption, restatement, ops faults; deduped with auto-resolve; dead-man switch for total silence |
| New machine mid-history | Self-describing `raw/` + sidecars + `_SUCCESS` markers; `rebuild-ledger`; lease steal; resumable `.part` files |

Crash-safety spine, restated in one line: durable facts only in the ledger, filesystem-before-ledger ordering, atomic renames on one mount, and idempotent re-checks to close every crash window.

result: Delivered a concrete resume-safe EOD ingestion design — staged-download/verify/rename flow with Range-resume and stall watchdog, sha256-keyed idempotent ingest, rebuildable SQLite ledger with lease, SLA-and-deadman-only alerting, and a rebuild-ledger takeover path for new machines.

===== MG04 =====
**PRE-MORTEM RISK MEMO — Short Index-Options Book (Paper)**
From: Risk | Date: 14 July 2026 | Written as if: July 2027, the morning after our worst week ever

**Premise.** Last week contained the Union Budget and the RBI MPC decision. The book — short NIFTY premium: defined-risk credit spreads plus naked strangles — lost **~14% of NAV in five sessions**, erasing roughly six months of expected theta. This is what killed it.

**Working assumptions (scale linearly):** NAV ₹1 cr; NIFTY ≈ 26,000; lot 75. Six naked strangles at ±4% strikes (~200 pts credit each, ₹90k total); spreads with aggregate max loss ₹6L; opening margin ~18–20% NAV; book vega ≈ –₹10k per India-VIX point; expected P&L +0.4–0.7% NAV/week.

**The kill chain, in order**
1. **We were short the event, not the market.** Event-week IV looked rich (weekly straddle ~2.5%), so we sold the "post-event crush." Two events in one week meant no crush after event #1 — IV stayed bid for event #2, and theta's promise was repaid as vega.
2. **The gap did the damage before any rule could fire.** Budget tax shock: –3.4% opening gap. Strangle puts went 8-delta to 45-delta overnight. No intraday trigger protects against an open.
3. **We rolled instead of closing** ("vol mean-reverts"), then the MPC surprised two days later: another –4.2%. India VIX 14 → 27. Strangle gamma/intrinsic ≈ –6% NAV; spreads pinned near full max loss on the put side ≈ –5%; vega mark ≈ –1.5%. Note: defined-risk caps the loss, not the probability of realizing it.
4. **Liquidity and margin finished it.** Short options ballooning ITM plus an ad-hoc exchange margin hike pushed utilization past 85%; forced covering into spreads 8–15× normal width added ~1.5–2% NAV of pure slippage, with weekly-expiry gamma compounding it.

**Quantified tail** (paper fills; add 30–50% for live):

| Weekly scenario | Rough odds | Book P&L |
|---|---|---|
| Normal event week, IV crush | base | +0.4 to +0.7% NAV |
| ±1× implied move | ~1 in 3 | +1% / –1.5% |
| –6%, VIX ~25 (budget shock) | ~1 in 15 event-weeks | **–5 to –7%** |
| –9% over 2 sessions, VIX ~30 (Jun-2024 class: NIFTY –5.9% in a day) | ~1 in 30–50 | **–10 to –13%** |
| –13% day, VIX 60–80 (Mar-2020 class) | ~once a decade | **–15 to –22%, realized at forced-exit prices** |

Asymmetry: the plausible worst week is **20–40× the expected weekly gain**. The strangles are ~15% of deployed margin but drive over half the tail loss.

**Pre-committed de-risk triggers** (mechanical; pre-staged as basket orders; not debatable in the moment)
1. **T-2 rule:** by the close two sessions before the first event, zero naked short options — buy wings or close. Budget up to 30% of open credit for wings; pay it.
2. **Size caps:** event-week margin ≤ 35% NAV; aggregate defined-risk max loss ≤ 8% NAV; net vega no shorter than –₹10k/VIX pt.
3. **Strike rule:** no short strike inside 1.25× the straddle-implied move; if IV expansion pulls one inside, exit same session.
4. **VIX triggers:** India VIX > 18 close or +20% intraday → cut short vega 50%; VIX > 24 → flat all short premium.
5. **Spot triggers:** index touches any short strike → close that structure within 15 minutes, not at max loss; intraday move > 1× implied → halve the book.
6. **P&L circuit:** –2% NAV day → halve; –3.5% day or –5% week → flat, 10-session trading halt, written post-mortem before restart.
7. **Per-position stop:** any short structure marking ≥ 2.5× credit received → close.
8. **Margin rule:** utilization > 50% for any reason (including exchange hikes) → cut below 40% same session; never add capital to defend short options in an event week.
9. **Two-event rule:** if event #1 moves > 1× implied, no short gamma into event #2. Period.
10. **Halt protocol:** if index circuit breakers trip, exit 50% of remaining short gamma within 30 minutes of reopen via staged limits, the rest by close — decided now.

**What cannot be hedged at acceptable cost**
- **The overnight gap itself.** Wings sized for a 2020-class move cost 25–40% of gross theta; full protection ≈ no strategy. Sizing (trigger 2) is the only real control.
- **Post-shock liquidity.** First-30-minute spreads widen 5–20×; stops guarantee exit, not price. Tail slippage of 1.5–2.5× theoretical is budgeted, not hedged.
- **Trading halts.** Nothing lets us act during a halt; reopen risk is naked.
- **Vol-of-vol and put skew.** No liquid India-VIX derivative; a put ladder that truly caps skew blowout bleeds ~2–4% NAV/year — more than half the strategy's expected return. Above VIX 24 we exit rather than hedge.
- **Exchange/broker action.** Ad-hoc margin hikes and RMS auto square-off are external and uninsurable; only low utilization mitigates.
- **The paper-to-live gap.** Every figure above assumes mid fills that will not exist in the tail; assume live losses ≥ 1.3–1.5× paper.
- **Us.** The largest residual risk is overriding this memo mid-week. Hence pre-staged orders and a signature on this page before the week begins.

**Bottom line.** The events don't kill this book; naked gamma held through clustered events on the false premise of a single IV crush does. Triggers 1, 2, and 9 are the difference between a bad week and the worst week.

---

Sanity check: re-read the ask — pre-mortem voice (loss already happened, 12 months out), numeric tail, exact pre-commit triggers, and honest unhedgeables are all covered in one page; the scenario arithmetic (strangle point losses × lot 75 × 6 lots + spread max loss + slippage) reconciles with the table's NAV percentages.

result: One-page pre-mortem memo delivered — a Budget+RBI-week gap through naked NIFTY strangles drives a –5% to –22% NAV tail (20–40× weekly expected gain), with 10 pre-committed de-risk triggers and an explicit list of unhedgeable risks (overnight gaps, post-shock liquidity, halts, skew, paper-to-live slippage).

===== MG05 =====
## Derivation

For each value $i \in \{1, \dots, n\}$, define the indicator $X_i = 1$ if value $i$ appears at least once in the $n$ draws, and $X_i = 0$ otherwise. Then $D = \sum_{i=1}^n X_i$.

A single draw misses value $i$ with probability $\frac{n-1}{n}$. The draws are independent, so value $i$ is missed by all $n$ draws with probability $\left(1 - \frac{1}{n}\right)^n$. Hence

$$E[X_i] = P(X_i = 1) = 1 - \left(1 - \frac{1}{n}\right)^n.$$

By linearity of expectation (which needs no independence between the $X_i$):

$$E[D] = \sum_{i=1}^n E[X_i] = n\left[1 - \left(1 - \frac{1}{n}\right)^n\right] = n - \frac{(n-1)^n}{n^{n-1}}.$$

For the limit, divide by $n$:

$$\frac{E[D]}{n} = 1 - \left(1 - \frac{1}{n}\right)^n \xrightarrow{\,n \to \infty\,} 1 - e^{-1},$$

using the standard limit $\left(1 - \frac{1}{n}\right)^n \to e^{-1}$.

**Sanity check.** For $n = 1$: $E[D] = 1(1 - 0) = 1$, correct. For $n = 2$: the four equally likely outcomes $(1,1), (1,2), (2,1), (2,2)$ give distinct counts $1, 2, 2, 1$, so $E[D] = \frac{3}{2}$, matching $2\left(1 - \frac{1}{4}\right) = \frac{3}{2}$.

## Final answers

- **Exact closed form:** $\displaystyle E[D] = n\left[1 - \left(1 - \frac{1}{n}\right)^n\right] = n - \frac{(n-1)^n}{n^{n-1}}$
- **Exact limit:** $\displaystyle \lim_{n \to \infty} \frac{E[D]}{n} = 1 - \frac{1}{e} = \frac{e-1}{e} \approx 0.63212$

result: E[D] = n[1 - (1 - 1/n)^n] exactly, and E[D]/n converges to 1 - 1/e as n approaches infinity.

===== MG06 =====
This is the coupon collector problem with n = 4, answerable directly by decomposing T into geometric waiting times.

## Derivation

Write T = T₁ + T₂ + T₃ + T₄, where Tᵢ is the number of draws needed to see a *new* suit after i − 1 distinct suits have appeared.

While you hold i − 1 distinct suits, each draw is new with probability p = (4 − (i−1))/4, so Tᵢ is geometric with mean 4/(4 − i + 1):

- T₁: p = 4/4 → E[T₁] = 1
- T₂: p = 3/4 → E[T₂] = 4/3
- T₃: p = 2/4 → E[T₃] = 2
- T₄: p = 1/4 → E[T₄] = 4

By linearity of expectation:

E[T] = 1 + 4/3 + 2 + 4 = 4·(1 + 1/2 + 1/3 + 1/4) = 4·H₄ = **25/3 ≈ 8.3333…**

Sanity check: 4·H₄ = 4·(25/12) = 25/3, and the term-by-term sum 12/12 + 16/12 + 24/12 + 48/12 = 100/12 = 25/3 agrees; the decimal 8.3̅ matches the known coupon-collector value for n = 4.

result: Expected draws to see all 4 suits is E[T] = 25/3 ≈ 8.3333 (coupon collector, 4·H₄).

===== MG07 =====
Here is the verification protocol I would run, written as an executable checklist. Design assumption throughout: the vendor is presumed guilty of (a) backfilling history from a current-view database, (b) stamping synthetic announcement dates, and (c) covering a survivorship-biased universe, until each is disproven. Everything below is code in the repo, re-run on every delivery — not a one-time exercise.

## Phase 0 — Quarantine and structural interrogation (before any statistics)

1. **Isolate.** Data lands in a `vendor_raw` schema, read-only, with no import path into research code. Nothing touches a backtest until promoted by the pipeline in Phase 6.
2. **Key census.** Test primary-key uniqueness on (entity_id, period_end, statement_basis [standalone/consolidated], audit_status, vintage). If there is **no vintage/first-reported dimension** — one mutable row per company-quarter with an announcement-date column stapled on — record that up front: the dates alone can never prove point-in-time-ness, and the burden shifts entirely to the Phase 3 tests.
3. **Vendor questionnaire with falsifiable answers:** (a) the exact date live capture began — everything before that is backfill *by construction*; (b) the source of pre-live announcement dates; (c) restatement policy (overwrite vs. append); (d) whether they can re-deliver historical snapshots ("the file as it existed on 2019-06-30"). Order two snapshots (e.g., as-of 2019 and as-of 2023) now — needed for test 3.5. Inability or refusal to produce snapshots is itself evidence about their live practice.
4. **Unit and convention probes.** Compare 10 mega-cap revenue figures against known magnitudes to catch lakh/crore/million scaling instantly (a 10x or 100x error is the classic Indian-data failure; banks historically filed in lakh, others in crore). Pin down: does "FY2016" mean year ending March 2016; are quarter labels fiscal or calendar; how are non-March fiscal years handled — pull **Siemens India (September FYE)** and a Dec-FYE MNC subsidiary, and specifically **Bosch's 15-month transition year to a March FYE (~2014-15)**.

## Phase 1 — Full-universe internal forensics (automated, all ~2000 companies × ~84 quarters)

1. **Accounting identities with tolerances:** PBT − tax ≈ PAT; EPS × share count ≈ PAT (flag >2%); assets = liabilities + equity where balance sheets exist; sum of four quarters vs. FY. Flag — but do not fail — exact Q4 = FY − 9M matches: Indian Q4 figures are explicitly "balancing figures," and the check is whether the vendor *knows* this (a derived-Q4 flag) rather than presenting Q4 as independently reported.
2. **Regulatory-impossibility scan (India-specific, high yield):** quarterly filings under Clause 41/LODR historically contained P&L only — balance sheets were **half-yearly**, cash flows **annual** (half-yearly only from roughly 2019), and consolidated quarterly reporting was optional until it was mandated around FY2019-20 (Kotak committee). So: non-null *quarterly* balance-sheet items in 2008, quarterly cash flows in 2012, or near-complete consolidated quarterly coverage in 2012 are synthesized (interpolated, forward-filled, or annual data restamped). Identify which fields these are; they get blocked in Phase 6. (Pin exact effective dates from SEBI circulars during implementation; the scan itself works empirically — look for field-coverage discontinuities and demand they map to a known regulatory change.)
3. **Staleness and duplication:** zero-variance runs of ≥4 quarters (forward fill); identical value-vectors across different companies (copy errors); mid-series jumps of exactly 10x/100x (unit regime change).
4. **Announcement-lag forensics.** Plot the full distribution of (ann_date − period_end) by quarter, by era:
   - **Floors/ceilings:** lag < 7 days is essentially impossible in India (TCS, the fastest large cap, reports ~10-12 days after quarter end); lag > 120 days gets individually explained.
   - **Regime shape:** mass inside 45 days (60 for Q4/audited annual), clustering in the final two weeks, and four seasonal waves (Jul, Oct-Nov, Jan-Feb, Apr-May).
   - **Fabrication signatures:** point-masses exactly at day 45/60; identical dates across large swaths of the universe; **zero weekend dates** — Saturday board meetings are routine in India (HDFC Bank habitually reports on Saturdays), so an all-weekday distribution means someone "cleaned" or generated the dates; zero late filers ever (real exchanges fine late filers every year — a tail must exist).
   - **The COVID litmus test:** SEBI extended the March-2020 (and June-2020) quarter deadlines well into mid/late 2020. The Mar-2020 quarter must show that fat tail of June-July 2020 announcements. A tidy 45/60-day distribution for that one quarter is near-proof the dates were synthesized from statutory deadlines.
5. **Coverage curves:** companies-with-data per quarter, split by exchange, size decile, and alive-today vs. dead. Look for the backfill cliff — a coverage jump in the year the vendor actually started operating.

## Phase 2 — External value verification

Ground-truth hierarchy: (a) **exchange XBRL Reg-33 filings** (bulk-downloadable from BSE/NSE, roughly FY2016 onward) — use as a *census*, not a sample; (b) original results PDFs from the BSE corporate-announcements archive (goes back to the mid-2000s) — for sampling the pre-XBRL era; (c) an incumbent database (Prowess/Capitaline/Ace/Bloomberg) as tie-breaker only — many Indian vendors share upstream provenance, so vendor-DB agreement is not independence.

1. **Post-2016 census:** machine-compare revenue, PBT, PAT, EPS — plus NII and gross/net NPA for banks — for *every* company-quarter against exchange XBRL. Metrics: exact-match rate, material discrepancy rate (|relative error| > 1%), sign flips. Proposed gate: material errors < 0.5%, sign flips ~zero unless explained by regrouping.
2. **Pre-2016 stratified hand-sample:** 60 company-quarters checked line-by-line against filing PDFs. Strata are mandatory, not proportional: era (2005-09 / 2010-15), size including micro-caps, sector cells that *must* be filled (bank, NBFC, IT, PSU, commodity), status (alive / delisted / merged mid-history), and ≥5 non-March-FYE names. Plus 400-800 semi-automated spot checks of revenue/PAT/EPS against a second database.
3. **Adversarial named set — inspected exhaustively, never sampled:**
   - **Satyam FY08-FY09:** the fraudulent as-originally-reported numbers should be present (that is *correct* for PIT); forensically restated figures under those quarters is a current-view tell.
   - **Yes Bank Q3 FY20:** results were delayed to mid-March 2020, far past the 45-day deadline — the vendor's date must reflect that.
   - **Vodafone Idea Q2 FY20:** the ~₹50,000 crore AGR loss must be present in full, not winsorized by an outlier filter.
   - **PNB Q4 FY18; CG Power's FY18 restatement (disclosed Aug 2019).**
   - **Tata Motors:** standalone vs. consolidated diverge wildly (JLR) — perfect test that statement_basis labels are trustworthy.
   - **A GST-boundary FMCG/manufacturer:** the gross-of-excise → net-of-GST revenue break at Q1 FY18 must be visible if data is genuinely as-reported.
   - **An Ind AS Phase-1 company's FY16 quarters:** must be the original Indian-GAAP figures, not the Ind AS restated comparatives republished in FY17 filings.

## Phase 3 — Point-in-time tests (the heart of the protocol)

1. **Date ground truth:** for 300-500 stratified company-quarters plus the entire adversarial set, pull exact board-meeting-outcome filing timestamps from the BSE archive. Compute exact-match rate and the (vendor − true) distribution. Interpret the *shape*: a systematic +1/+2 day bias suggests newspaper-publication dates (Reg 47 requires publication within 48h) — recalibratable; a heavy, irregular right tail suggests database-entry dates masquerading as announcement dates — disqualifying.
2. **Comparative-fingerprint test (the decisive, scalable one).** Every Indian quarterly filing republishes the year-ago quarter as a comparative, and regroupings/restatements/demergers routinely make that comparative differ from the original filing. From XBRL, assemble all cases where original(Q) ≠ comparative-of-Q-in-filing(Q+4). For each divergent pair, which value does the vendor store against Q? A true first-reported database matches the originals; a current-view database matches the later comparatives *while still stamping the original announcement date* — i.e., manufactured point-in-time. Run on every divergent case post-2016. Gate: ≥95% original-matching, or hard fail.
3. **IPO backfill probe:** for the 2021-22 cohort (Zomato, Paytm, Nykaa, LIC), pre-listing quarters only became public via the prospectus. If those quarters exist with announcement dates in 2019-20 (period_end + 45 days), the dates are fabricated. Also check Hexaware (delisted 2020, re-listed 2025) as a joint PIT and entity-continuity probe.
4. **Market-reaction event study — measures exactly what a backtest will consume.** For ~2,000 random company-quarters with clean price data, compute abnormal volume and |abnormal return| in event time around ann_date. Genuine dates produce a sharp t0/t+1 spike (t+1 because many Indian releases are post-close or on Saturdays); entry dates produce a smeared or lagged spike. Quantify: fraction of events whose max |abnormal return| within [-5,+5] falls on t0/t+1 (chance ≈ 18%), and the correlation of earnings surprise sign with t0/t+1 return. **Negative control:** rerun with all dates shifted +15 trading days and confirm the spike vanishes (proves the test has power). Run **separately by era** — backfilled years often fail while recent years pass, which feeds the tiering below.
5. **Snapshot diff:** using the two historical deliveries from Phase 0, diff a known restatement (CG Power) plus 50 random rows. The older snapshot must contain the older values.
6. **Forward shadow capture:** for the next one or two earnings seasons, scrape BSE announcements live and log our receipt time; when the vendor's update arrives, measure **vendor delivery latency** per record. Correct historical stamps do not make the feed tradable at those stamps — the simulator must use max(ann_datetime, ann_date + observed p95 vendor latency).
7. **Intraday convention:** if the vendor supplies date-only (no timestamp), fix the conservative rule now — signal usable at t+1 open at the earliest — and use the timestamp sample to measure how much that convention costs.

## Phase 4 — Coverage and survivorship

1. **Independent universe reconstruction** from exchange delisted/suspended lists and index-vendor archives (historical Nifty 500 / BSE 500 constituent snapshots).
2. **Index-snapshot recall:** for constituents as of 2007, 2010, 2014, 2018, 2022, the vendor must cover ≥99% of that quarter's Nifty 500, every gap individually explained. Repeat at the bottom of the cap spectrum with BSE SmallCap snapshots, where the real damage hides.
3. **Death-rate comparison:** "~2000 companies" is suspiciously close to NSE's *current* active count; distinct listed entities since 2005 across NSE+BSE number several thousand more. Compute distinct entities ever in the dataset, and the fraction of the vendor's FY2008 universe whose data terminates before 2016; compare against exchange delisting base rates. If nearly everything in the 2008 universe survives to today, history was backfilled onto a current universe — structural survivorship bias.
4. **Named dead-company checklist** (each must exist with sensible terminal quarters): Satyam/Mahindra Satyam through the 2013 merger, Kingfisher Airlines, Deccan Chronicle, Bhushan Steel through IBC, Amtek Auto, Gitanjali Gems, Manpasand Beverages, DHFL through 2021, Videocon, Jet Airways, RCom, Cairn India through the 2017 merger, **HDFC Ltd through July 2023**, and a sample of 20 from the ~331 suspected shell companies suspended in August 2017.
5. **Entity-mapping audit:** 50 corporate events sampled from exchange circulars — name/symbol/ISIN changes, mergers, demergers (RIL→Jio Financial 2023, Crompton 2016, Arvind 2019). Verify ID persistence, no duplicate entities, and no history grafted across demerger boundaries (restated pre-demerger financials stamped with pre-demerger dates is a PIT violation, not just a mapping bug).

## Phase 5 — Acceptance gates, tiering, quarantine mechanics

| Check | Proposed gate | Consequence if failed |
|---|---|---|
| Comparative-fingerprint (3.2) | ≥95% match to originals | **Hard reject as PIT source.** Values may be salvageable as current-view reference only |
| Date fabrication signatures (1.4), incl. COVID tail | No deadline point-masses; COVID tail present | Dates rejected; salvage path below |
| Date accuracy vs. exchange timestamps | ≥90% within ±1 trading day post-2010 | Dates quarantined for that era |
| Post-2016 XBRL value census | Material errors <0.5%, sign flips ~0 | Reject or field-level block |
| Index snapshot recall | ≥99% Nifty 500, gaps explained | Reject for cross-sectional backtests |
| Death-rate vs. exchange base rate | Within ~20% of base rate | Pre-live-capture era demoted to Tier B/C |
| Event study (3.4), per era | Clear t0/t+1 concentration; negative control clean | Era-level demotion |

**Tiering of what a backtest may touch:**
- **Tier A (backtest-approved):** eras and fields passing everything including the event study. Dates used with the conservative intraday rule plus measured vendor latency.
- **Tier B (research-only):** eras with verified values but unproven dates (typically the pre-live-capture backfill). Vendor dates are **discarded and replaced** with a synthetic conservative availability rule (period_end + era-specific statutory deadline + 5 trading days), and any strategy must survive a +15-trading-day lag sensitivity test before promotion.
- **Tier C (blocked):** fields failing the impossibility scan (e.g., pre-2015 quarterly balance sheets) — physically excluded from the promoted schema so nobody can "forget."
- **Salvage rule:** if values pass the fingerprint test but dates fail, rebuild announcement dates ourselves from the BSE archive (it is scrapeable for the full history). If values fail the fingerprint test, no date repair can save the dataset for PIT use.

**Quarantine mechanics:** promotion ETL writes `fundamentals_pit` with lineage columns (delivery batch, validation run id, tier). Every new delivery is diffed against the prior one; **any mutation of previously delivered historical rows halts promotion** until explained — legitimate restatements must arrive as new vintage rows, silent edits are an incident. Two full earnings seasons of shadow-capture probation before Tier A data feeds anything sized in production. Final artifact is a signed acceptance memo listing every check, its result, and the disposition of every failure — the memo, not a feeling of comfort, is what admits the data to backtests.

Rough effort: Phases 0-1 are a few days of engineering; the XBRL census and fingerprint test are the bulk of the build (1-2 weeks) and become permanent monitoring infrastructure; the hand-sample is 2-3 person-days; shadow capture runs in the background across a quarter.

result: Delivered a phased verification protocol for the Indian quarterly fundamentals vendor — quarantine and structural checks, full-universe forensics (regulatory-impossibility and COVID-deadline tests), XBRL census plus adversarial named-case sampling, four independent point-in-time tests (comparative-fingerprint, IPO backfill, event study, snapshot diff), survivorship audits against index snapshots and named dead companies, and concrete acceptance gates with tiered promotion rules.

===== MG08 =====
Answering from reasoning alone, as asked — no tools. One framing fact first, because it sets the prior: a 2.1 Sharpe over 14 years is a t-stat of ~2.1 × √14 ≈ 7.9, in the *hardest* modern regime for cross-sectional equity ML (post-2010, post-anomaly-decay), published for free. Honest first-shot academic ML long-short results in this era cluster around 0.5–1.2 gross. So the question isn't whether something inflates the number, but which mechanisms and in what order of likelihood.

## 1. The "out-of-sample" period isn't — test-set reuse / multiple testing (near-certain)
**How it inflates:** 940 features plus architecture, horizon, rebalance frequency, and portfolio-construction choices give thousands of researcher degrees of freedom. If any were selected because they looked good on 2010–2023 — across months of team iteration, this is almost unavoidable — the reported Sharpe is the *max of many correlated noisy trials*, not an estimate. With a Sharpe standard error of ~0.3–0.5 over 14 years, picking the best of a few hundred configurations manufactures 1–1.5 Sharpe units from a true zero.
**The check:** freeze the released code/config and run it once, untouched, on data the authors could not have consulted — 2024 through mid-2026. A real 2.1 process stays strongly positive; a mined one reverts toward zero. (Proxy if you can't wait: demand the trial count and compute the Deflated Sharpe Ratio.)

## 2. Look-ahead leakage in the features — point-in-time failures (very likely; one leak among 940 suffices)
**How it inflates:** fundamentals aligned to fiscal-period-end instead of filing date let the model trade earnings 45–90 days before the market saw them; restated rather than originally-reported values leak corrections. News sentiment is worse: vendor histories are backfilled and re-scored with models built *after the fact*, and any sentiment classifier fine-tuned on 2010–2023 labels encodes which words predicted returns over the test period itself. Full-sample feature standardization in the ML pipeline is the same bug in miniature. A flexible model finds the one leaking column and rides it — producing exactly the claimed signature: implausibly high *and* implausibly stable.
**The check:** lag every feature by a conservative availability buffer (fundamentals +90 days unless filing-dated, news +1 trading day) and rerun the frozen pipeline. A real signal decays mildly; a leak collapses discontinuously.

## 3. Gross-of-cost returns on a high-turnover book (near-certain to be present; often disclosed, still fatal to replication in dollars)
**How it inflates:** models mixing daily prices and news load on short-horizon signals with turnover of 50–200% of the book per rebalance. The reported numerator is gross alpha, much of which is compensation for crossing spreads and providing liquidity — costs a real trader pays, not earns. Add short-leg borrow fees and impact, and the published pattern is gross ~2 falling to ~0–0.5 net.
**The check:** compute annualized one-way turnover from their positions and apply a size-dependent cost curve (effective half-spread by cap decile + borrow fees on shorts); report the net Sharpe. If the paper can't even produce turnover, that is itself the finding.

## 4. The alpha lives in micro-caps and an unshortable short leg (likely, especially if equal-weighted)
**How it inflates:** cross-sectional ML predictability concentrates in the smallest deciles; equal-weighted decile spreads put half the book in names with tiny ADV, wide spreads, and hard-to-borrow or no-borrow shorts. Stale closes and bid-ask bounce in these names mechanically manufacture short-horizon "reversal alpha" that exists in the database, not the market. Capacity is a few million dollars.
**The check:** rerun value-weighted on a liquid universe (top ~1,000 by market cap, price > $5, borrowable shorts). The genre-typical result is a 50–80% Sharpe loss — the surviving number is the honest headline.

## 5. Same-bar execution — trading at prices that predate signal availability (moderately likely; a quiet engine bug)
**How it inflates:** signal built from day-t closes (or news published through 4:00 pm, or after-hours filings), fills assumed at the day-t close. The backtest captures the market's reaction to information at a price set *before* the information was actionable; with news sentiment this silently harvests the announcement-day jump itself. Vendor "story creation" timestamps, often backdated relative to true dissemination, compound it.
**The check:** delay all fills to the t+1 open (and require exchange-timestamped information strictly before each fill) and rerun. A drop much beyond ~20–30% flags the timing bug rather than genuine fast alpha.

## 6. Survivorship and merge-induced coverage bias — missing delistings (plausible, and specifically invited by this design)
**How it inflates:** inner-joining prices, fundamentals, *and* news coverage silently drops firms that died, delisted, or were too small for news coverage — the panel is conditioned on survival. Longs in distressed names show "recoveries" because the corpses are absent; positions in stocks that delist exit at the last stale price instead of the ~−30% average performance-delisting return. The ML model then learns and amplifies this biased conditional mean.
**The check:** count security deaths per year in their final panel against CRSP baseline delisting rates (~4–8% of listings/year) and verify delisting returns are applied in the P&L. A near-zero death count confirms the bias.

**Overall read:** items 1–3 are each individually close to certain in this genre and jointly sufficient to explain 2.1 → ~0.5 investable; 4–6 are the standard residual suspects a referee should clear in that order. The single highest-value replication act is the combination of checks 1+2: frozen pipeline, lagged features, post-2023 data — one run answers most of the list.

Sanity check against the ask: 6 items, ranked by probability, each with an explicit inflation mechanism and exactly one decisive check — covered, no tools used.

result: Ranked the 6 likeliest reasons the claimed 2.1 OOS Sharpe won't survive — test-set reuse, feature look-ahead, gross-of-cost reporting, micro-cap concentration, same-bar execution, survivorship — each with its inflation mechanism and one decisive verification check.

===== T01 =====
## Review — T01 cross-sectional reversal engine

### Defect 1 (material): UTC date extraction mislabels the trading day → the "next session" entry is actually the same close the signal was computed from (lookahead / non-implementable fill)

**Where:** `hf["date"] = hf["ts"].dt.date`, together with `entry_d = dates[i + 1]`.

**Mechanism:** The vendor stamps are tz-aware UTC and the sample stamp is `2025-03-04 18:30:00+00:00`. 18:30 UTC is exactly **00:00 IST of 2025-03-05** — the standard midnight-IST daily-bar convention, i.e. this bar belongs to IST trading day **March 5**, not March 4. Taking `.dt.date` in UTC labels it March 4 — one day early. The bhav panel is indexed by *naive IST calendar date*, so the two panels are misaligned by one session.

Consequence: `rev1.loc[d]` is really the 1-day return ending at the close of IST day **d+1**. The code then "conservatively" enters at `dates[i+1]` — the close of IST day d+1 — i.e. it enters **at the very same close whose move generated the signal**, with zero lag. Same-close execution of a reversal signal is the classic fake backtest: you capture bid-ask bounce and end-of-day noise you could never trade against, and the deliberate one-day skip in the code is silently undone. This alone plausibly manufactures a Sharpe of 2.4.

**Fix:** `hf["ts"].dt.tz_convert("Asia/Kolkata").dt.date` (then confirm the bar-stamp convention: midnight-start vs midnight-end), and verify alignment empirically by checking that vendor `close` equals bhav on the *same* date label for a sample of symbol-days before running any PnL.

### Defect 2 (material): PnL computed from an unadjusted official close panel while the signal panel is split-adjusted

**Where:** `ret = bhav.pct_change()` used as the executed return; data note says vendor `close` is split/bonus adjusted but `bhav_close.parquet` is raw exchange prints.

**Mechanism:** `pct_change()` on unadjusted closes produces fake ±50%/±90% "returns" across every split, bonus, and face-value change (and omits dividends). Any held name crossing an ex-date during the entry→exit window books an enormous fictitious PnL day. On a 30-name daily-churn F&O book over 2021–2025 there are many such events; the reported per-trade-day mean and Sharpe are contaminated in both directions and cannot be trusted.

Related red flag in the same field: **"94.8% exact match"** against exchange prints. An official close panel should match ~100%. A 5.2% error rate in the *execution* price panel injects large spurious one-day returns; because a bad print reverses the next day by construction, price errors masquerade as reversal PnL whenever the error correlates with the vendor panel (shared upstream source), and add fat-tailed noise even when it doesn't.

**Fix:** apply a corporate-actions adjustment factor to bhav before `pct_change()` (or compute returns from the audited adjusted series and use bhav only for execution levels), and reconcile the 5.2% mismatches before believing any number.

### Defect 3 (material): NaN exits silently dropped — survivorship in exactly the names the strategy buys

**Where:** `gross = ret.loc[exit_d, held].mean()` — pandas `mean()` skips NaN.

**Mechanism:** A name that is suspended, delisted, hits a ban/circuit, or leaves the panel between entry and exit shows NaN in `ret` and is silently excluded from the basket average. A deep-oversold reversal screen preferentially selects names about to be suspended or delisted (fraud, default news), so the omitted observations are strongly biased toward large losses. This truncates the left tail and inflates both mean and Sharpe.

**Fix:** require a valid exit price; for missing exits, impute the realized outcome (last traded price, delisting recovery, or a conservative loss), and weight the basket by actual investable names at entry.

### Non-material comments (not defects in the arithmetic shown)

- Cost of 0.0010 correctly equals 5bp/side round trip; but 10bp all-in (incl. STT, impact) is optimistic for daily churn of 30 single-stock names — sensitivity to 20–30bp should be reported.
- Long-only, unhedged basket: the Sharpe includes market beta over a bull period; report vs. a beta/sector-neutral version.
- Universe should be verified as point-in-time F&O membership, not today's list (potential survivorship upstream of this code).
- `d in ret.index` mixes `datetime.date` keys with the bhav index type; if bhav's index were ever `DatetimeIndex` this comprehension silently yields zero positions — assert non-empty overlap.

### Numbered list of claimed material defects

1. UTC `.dt.date` on midnight-IST-stamped bars shifts the vendor panel one session early; the "enter next close" step therefore executes at the same close the signal is computed from — zero-lag lookahead. Fix: tz-convert to Asia/Kolkata and verify labels against bhav.
2. Executed returns computed from the unadjusted bhav panel (vs. adjusted signal panel): splits/bonuses create fake return spikes, and the 5.2% print-mismatch rate injects spurious "reversal" PnL. Fix: adjust bhav for corporate actions and reconcile mismatches.
3. `mean()` silently drops NaN exit returns, excluding suspended/delisted names that the oversold screen preferentially buys — left-tail truncation inflating mean and Sharpe. Fix: enforce valid exits or impute realized outcomes.

===== T02 =====
## Review — T02 NIFTY dip-buy overlay

The per-trade backtest loop itself is mostly clean — several classic traps are absent. `i + 3 >= len(df)` correctly drops incomplete trades; NaNs from `pct_change()` / `rolling(20)` evaluate to `False` in the signal, so no spurious early trades; and the cost deduction is internally consistent (3 bp per side = 6 bp round trip = 0.0006, subtracted once per trade). The signal uses only same-day and past data, no `shift(-1)` style leakage. But there are material problems.

### Defect 1 (material): the 19.4% CAGR is not produced by this code and is arithmetically impossible from the reported trade stats

The script prints trade count, mean per trade, and win rate — nothing else. The register entry's headline CAGR comes from nowhere. Sanity check: 74 trades × +0.41% ≈ +30% cumulative (≈ +35% compounded) over 8 years, with the book in the trade only ~3 sessions at a time. That is roughly a 3.5–4% CAGR contribution at full notional, not 19.4%. Either the CAGR silently includes the underlying index book's own return (in which case it is not the overlay's number), or it was computed some other, unshown way. **Mechanism:** the register would record a performance figure ~5x what the shown evidence supports. **Fix:** compute CAGR in the code from the overlay's daily P&L stream (mark positions daily, flat otherwise) and report that; state the index-book baseline separately.

### Defect 2 (material): overlapping trades — "full notional" is violated and trade stats are not what they claim

Signals can fire on day *t* and again on *t+1* or *t+2* while the first trade is still open (dip clusters are exactly when this strategy fires — 2020 will produce back-to-back signals). The loop books each as an independent full-notional trade. **Mechanism:** (a) any full-notional CAGR translation is wrong because realized exposure exceeds 1x during clusters (or, if capped at 1x in practice, many of the 74 trades could not have been taken at reported size); (b) overlapping trades share the same underlying days, so the 74 trades / 62% winners are not independent observations — a few clustered episodes drive multiple "wins." **Fix:** either suppress signals while a position is open (non-overlapping trades), or run a proper daily portfolio simulation with an explicit exposure cap, and re-report.

### Defect 3 (material, execution): entry at the very close that defines the signal

`entry = close.iloc[i]` — the signal requires knowing the day's official close (ret < −1.2% and close > 20-DMA), yet the fill is assumed at exactly that close. On NSE the close is the last-30-minute VWAP for the index / closing price for futures; you cannot condition on the final print and trade at it. In practice you'd trade ~15:25 on a provisional signal, accepting slippage and occasional signal flips near the −1.2% boundary. For a mean-reversion entry into a falling market, late-day momentum means the tradeable price is systematically biased against you relative to the close. On a +41 bp edge, a few bp of systematic slippage plus boundary misclassification is material. **Fix:** enter at next-day open (re-run and report that number), or model a 15:25 execution with realistic slippage; symmetrically for the exit.

### Non-material comments (labelled as such)

- Spot index closes are used as proxies for tradeable futures prices; basis and roll are ignored. Small for a 3-day hold, but note it in the register.
- 6 bp total cost with no market-impact allowance is thin for "full notional" on an index book, though defensible for NIFTY futures.
- The reported "+0.41% per trade after costs, 62%, 74 trades" are at least *consistent with what this script would print*; only the CAGR is unsupported by the shown code.

### Claimed material defects

1. Reported 19.4% CAGR is not computed anywhere in the code and is ~5x larger than what 74 × 0.41% over 8 years can support — the headline register number is unsubstantiated.
2. Overlapping trades: clustered signals create simultaneous positions, invalidating the "full notional" sizing/CAGR claim and making the 74 trades non-independent.
3. Look-ahead in execution: entry (and exit) assumed at the same closing print used to generate the signal, which is not implementable and biases the edge upward; re-test with next-open or modelled near-close fills.

===== T03 =====
## Review — T03 post-earnings drift memo

The memo is unusually clean on the classic failure modes: point-in-time universe, publication-date timestamps, next-open entry, turnover-matched placebo, denominator sanity (Rs 3.1 / Rs 740 = 0.419% matches the +0.42% claim), and the headline t-stat is internally consistent (0.42/2.5 × √412 ≈ 3.41). But there is one material defect, and it is in the statistical inference itself.

### Material defect: the significance claim is contradicted by the memo's own placebo test

**The claim:** "t-stat 3.4 … Entry edge appears real against matched nulls" (Result section + Verdict), citing the strategy at the **92nd percentile** of the 200-basket placebo distribution.

**The mechanism:**

1. **92nd percentile is a one-sided p-value of ~0.08.** Eight percent of *random-entry* baskets with the same trade count, same universe-dates, and the same 10-session exit engine produced an edge as large as the strategy's. That is a *fail* at any conventional gate threshold, not evidence the edge is "real against matched nulls." The sentence asserts the opposite of what the number shows.

2. **The gap between t = 3.4 and the 92nd percentile is itself diagnostic, and it indicts the t-stat, not the placebo.** If the 412 trades were independent, the standard error of a basket's mean would be 2.5%/√412 ≈ 0.123%. The strategy sits (0.42 − 0.06)/0.123 ≈ 2.9σ above the placebo mean — that would be roughly the 99.8th percentile, not the 92nd. Landing at only the 92nd percentile means the empirical dispersion of placebo basket means is roughly double the iid value (~0.25–0.26%). That is exactly what overlapping 10-session holds, earnings-season clustering of entries, and a shared market factor do: they cut the effective sample size to roughly a quarter of 412, which deflates the honest t-stat to ~1.6–1.8. The per-trade t = 3.4 assumes independence that the memo's own placebo empirically refutes.

**Why it corrupts the result:** the memo advances a marginal, p≈0.08 result under the banner of a 3.4-sigma finding. Anyone downstream who reads "t 3.4, real against matched nulls" will weight the sensitivity-battery results accordingly. In a bullish 2021–25 window a long-only 10-day hold picks up drift for free (visible in the +0.06% placebo mean — the placebo correctly nets this out, the t-stat does not).

**Fix:** treat the placebo/percentile (or a block bootstrap over calendar-time clusters, or a calendar-time portfolio regression with Newey–West/cluster-robust errors) as the significance measure, and delete or caveat the per-trade t-stat. Report the verdict honestly: edge is positive but only ~92nd percentile against the matched null — insufficient on its own; the sensitivity battery must be framed as testing a *marginal* candidate, not confirming an established one.

### Non-material comments (clearly labelled as such)

- *Non-material:* The Rs 50L / max-8-positions / CAGR 9.8% arithmetic is under-specified. At ~82 trades/yr × 0.42% net, hitting 9.8% on Rs 50L requires ~Rs 14L average per position; whether that is consistent with "max 8 concurrent" depends on sizing rules not stated. Ask for the sizing spec; as written it is ambiguous rather than demonstrably wrong.
- *Non-material:* Skipping entries when "first-15-minute volume was zero" is technically a decision made with post-open information for an at-open fill. It is an executability filter (a zero-volume open has no real fill anyway) and only 9 trades, so no material bias; note it and move on.
- *Non-material:* Mar/Sep semiannual snapshots approximate membership between snapshot dates (intra-period index changes are missed). Standard limitation; worth a footnote.
- *Non-material:* Skipping upper-circuit-locked opens is correct and, if anything, conservative (it removes the most explosive positive-surprise names you couldn't actually buy).

The memo's stated recommendation (sensitivity battery, not register entry) is directionally sensible — but it must be re-motivated on the corrected significance basis.

### Claimed material defects

1. Significance is overstated and self-contradictory: "92nd percentile of the placebo distribution" is p≈0.08 (a fail against the matched null), and the discrepancy versus t = 3.4 shows the per-trade t-stat is inflated ~2x by non-independent (overlapping, season-clustered) trades; honest t is roughly 1.6–1.8. The claim "entry edge appears real against matched nulls" is wrong as written. Fix: use the placebo/block-bootstrap distribution (or cluster-robust calendar-time regression) as the inference, and restate the verdict accordingly.

result: One material defect — the memo's significance claim is false by its own placebo: 92nd percentile ≈ p 0.08 (not significant), and the gap to the reported t=3.4 shows the t-stat is ~2x inflated by overlapping/clustered trades; everything else checks out internally.

===== T04 =====
Review of T04 — quarterly revenue-growth rotation

**Defect 1 (material): Look-ahead on fundamentals — trading on `quarter_end`, not the reporting date.**
The rebalance line is `rebal_day = close.index[close.index.searchsorted(qe, side="right")]`, i.e. the first trading day *after the fiscal quarter ends*. But `rev_yoy` for that quarter is not knowable then — Indian listed companies report quarterly results up to ~45 days after quarter end (60 for Q4/annual). The strategy is therefore buying the top revenue growers using numbers that will only be published weeks later. Because earnings announcements move prices in the direction of the surprise, this leaks the announcement drift into the backtest and is exactly the kind of defect that produces a fake 21.7% vs 12.9% spread. Fix: use the actual announcement/filing date per (symbol, quarter) from a PIT fundamentals feed, and rebalance on the first trading day after all selected names have reported (or lag every signal by the filing deadline, e.g. qe + 45/60 days). Relatedly, if `quarterly_revenue.parquet` holds current (restated) figures rather than as-first-reported values, that is a second leak in the same field — must be as-reported PIT data.

**Defect 2 (material): `pct_change(4)` is row-based, not calendar-based YoY.**
`rev.groupby("symbol")["revenue"].pct_change(4)` divides by the value 4 *rows* earlier. If any quarter is missing for a symbol (common in fundamentals files — late filings, gaps, new listings), the "YoY" compares quarters that are not one year apart, e.g. Q1FY26 vs Q2FY25, producing seasonal garbage that can rank a name into the top 30 on spurious growth. Fix: merge each row against the record where `quarter_end == quarter_end - 12 months` (or pivot to a symbol × quarter-end grid and shift on the calendar axis), so a missing base quarter yields NaN rather than a wrong denominator. Also filter/handle non-positive base revenue, which makes `pct_change` sign-flip meaningless.

**Defect 3 (material): delisted/suspended holdings contribute zero return — survivorship reintroduced through the price panel.**
Membership is PIT, but returns are computed as `(weights.shift(1) * ret).sum(axis=1)`. On a union close panel, a stock that delists, is suspended, or goes to zero simply stops having prices; its `ret` becomes NaN, and pandas' `sum` skips NaN — so a held position that blows up silently exits at its last price with no loss (and its weight is never redistributed, quietly also deleveraging the book). In a small-cap-tilted high-growth basket over 2016–2025 (IL&FS-era defaults, SEBI suspensions), this materially inflates the basket CAGR. Fix: on disappearance, force a terminal return (delisting proceeds or −100% for defaults, last traded price for M&A cash-outs) and re-normalize remaining weights; at minimum, treat NaN returns on held names as a flagged event, not an implicit 0.

**Defect 4 (non-material robustness note, clearly labelled as such):** `close.index.searchsorted(qe, side="right")` returns `len(index)` when the last fiscal quarter end falls on/after the final price date, so `close.index[...]` raises IndexError — the loop must guard `if pos >= len(close.index): continue`. Also non-material: between rebalances the weights are held constant (implicit free daily rebalancing back to equal weight, uncosted) and the "open fill" is actually approximated as the rebalance-day close via `shift(1)`; both are conventional approximations, worth stating honestly but unlikely to flip the conclusion. Fiscal-year-end heterogeneity (Dec vs Mar enders landing in different `qe` buckets, so some quarters have thin cross-sections and get skipped by the `< 60` filter) is worth checking but is a data-coverage question, not an outright leak.

Claimed material defects:

1. Fundamentals look-ahead: rebalancing the day after fiscal `quarter_end` uses revenue figures not published until up to 45–60 days later (and possibly restated values); fix by trading only after per-name announcement dates from PIT as-reported data.
2. Row-based YoY: `pct_change(4)` compares 4 rows back, not 4 quarters back, so any missing quarter corrupts the growth signal; fix with a calendar-aligned 12-month self-join (plus non-positive-base handling).
3. Delisting/suspension returns silently dropped: NaN returns on held names are summed as zero, so blow-ups exit costlessly at the last print — survivorship in returns despite PIT membership; fix by applying terminal delisting returns and re-normalizing weights.

result: T04 has three material defects — a reporting-lag look-ahead (trading on quarter-end before results are published), a row-based `pct_change(4)` that mis-computes YoY when quarters are missing, and NaN-summed delisting returns that erase losses — so the 21.7% CAGR is not credible as reported.

===== T05 =====
## Review — T05 "fastest growers" screen

The timing architecture is fine: `asof_date` is publication-lagged, the rebalance snapshot uses `asof_date <= asof` with `tail(1)`, entry is next open, membership is PIT. No lookahead there. The defect is in the growth metric itself, and the author's own sample table proves the ranking is corrupted.

### Defect 1 — sign-flipped growth for negative prior EPS (confirmed in the sample)

`f["growth"] = (ttm_eps - ttm_eps_prev) / ttm_eps_prev` is mathematically meaningless when `ttm_eps_prev <= 0`, and the sample shows it actively inverting the ranking:

- **SUNWINDPWR**: EPS went from **-1.20 to -2.55** — losses more than doubled, a *deteriorating* company. Growth = (-2.55 − (-1.20)) / (-1.20) = **+1.13**, ranked **8th** and bought.
- **JPINFRAVENT**: same mechanism, -0.35 → -0.68, worsening loss scored as +0.94, ranked 9th and bought.
- **TURNCORP**: **-5.00 → +1.00**, a genuine loss-to-profit turnaround — arguably a real "fast grower" — gets growth = 6.00 / (-5.00) = **-1.20** and is ranked 496th, near bottom, excluded.

Mechanism: dividing by a negative base flips the sign of the change. The screen systematically buys companies whose losses are accelerating and excludes turnarounds. Whatever the +34% CAGR is, it is not the return of an earnings-growth strategy; the metric does not measure what the write-up claims.

Fix: restrict to `ttm_eps_prev > 0`, or use a sign-robust formulation such as `(ttm_eps - ttm_eps_prev) / abs(ttm_eps_prev)` (still weak, see Defect 2), or better, a price-scaled earnings change: `(ttm_eps - ttm_eps_prev) / price`.

### Defect 2 — no denominator floor: tiny-base EPS dominates the ranking

**ZENVITECH** (0.04 → 1.62, "growth" 39.5x) and **ORBIPHARM** (0.11 → 2.05, 17.6x) top the list purely because the base is a few paise, while **BLUECHIPCO** with a large, real 24% EPS increase on a Rs 98 base ranks 61st and is never selected. With no floor on `ttm_eps_prev`, the ratio is unbounded as the base → 0, so the top-20 basket is populated almost entirely by near-zero-base noise (rounding artifacts, one-off items, micro-caps). The reported +34% is then the return of a "near-zero prior EPS" portfolio, not an earnings-growth portfolio, and is unlikely to survive out of sample or the stated 40bp costs at realistic capacity.

Fix: require a minimum absolute prior EPS (or minimum earnings yield `ttm_eps_prev / price`), or use the price-scaled change above, which fixes Defects 1 and 2 simultaneously.

### Defect 3 — `shift(4)` is row-based, not period-based

"TTM EPS four quarterly refreshes ago" assumes every symbol has exactly one row per fiscal quarter. In a publication-lagged table this routinely fails: a missed/delayed filing, a restatement row, or a re-publication inserts or drops rows, so `shift(4)` compares against 3 or 5 quarters ago (or a restated duplicate of the same quarter) for those symbols. That injects spurious extreme "growth" values into exactly the tail of the distribution the screen selects from.

Fix: join on fiscal period end (`period_end` shifted 12 months) rather than row position; deduplicate to one row per symbol per fiscal period first.

### Non-material comments

- `tail(1)` at rebalance imposes no staleness cutoff — a symbol that stopped filing years ago stays rankable on old data. Add e.g. a 12-month max age. (Robustness, not the source of the headline number.)
- The loop body is omitted and vouched for by the value-sleeve audit; that audit does not cover this sleeve's ranking logic, which is where the problem is.

### Numbered list of claimed material defects

1. Growth formula divides by `ttm_eps_prev` with no sign handling: negative-base names get sign-flipped scores, so the screen buys deteriorating loss-makers (SUNWINDPWR, JPINFRAVENT) and rejects genuine turnarounds (TURNCORP).
2. No minimum-base filter: near-zero prior EPS produces unbounded ratios, so the top-20 basket is dominated by tiny-denominator noise (ZENVITECH, ORBIPHARM) while large real growers (BLUECHIPCO) are excluded — the +34% CAGR does not reflect an earnings-growth signal.
3. `shift(4)` row-shift instead of a fiscal-period join: irregular publication rows (delays, restatements) misalign the year-over-year comparison and feed spurious extremes into the selected tail.

===== T06 =====
## Review — T06: monthly NIFTY short strangle

**1. The 2026-07 cycle is fabricated by a silent `asof` fallback (material).**
The expiry calendar runs through **2026-07**, but the spot/chain dataset ends **2026-06-30** — and today is 2026-07-14, so the July 2026 monthly expiry (~last week of July) has not even occurred. For that cycle, `settle_spot = spot.asof(exp)` does not fail; `asof` silently returns the *last available* observation, i.e. the 2026-06-30 close. The code therefore books a fully "settled" July 2026 cycle using a stale June spot as the settlement print — a result for a position that is still open. Given both strikes are 3% OTM at entry, this phantom cycle will almost always land as a full-premium win, padding the hit rate and average.
**Fix:** restrict the loop to expiries with `exp <= spot.index.max()` (and, more defensively, raise instead of `asof`-falling-back when the exact settlement date is missing). Report 2019-01 through 2026-06 only.

**2. The reported worst cycle (−412 pts) is inconsistent with this code on real data (material — indicates a dropped/corrupted crisis cycle or numbers not produced by this code).**
Mechanism check against known history: for the March 2020 expiry, entry at ~45 DTE lands around 10–12 Feb 2020, ref spot ≈ 12,100–12,200, so `pe_k` ≈ 11,750–11,850. NIFTY settled the March 2020 monthly expiry (26 Mar 2020) around 9,300–9,400. Payoff on the put alone is ≈ 2,300–2,500 pts against perhaps 250–350 pts of collected premium: a loss well in excess of −1,500 pts, held-to-expiry with no stop anywhere in the code. A worst cycle of only **−412** is therefore impossible if the March 2020 (and likely April 2020) cycle actually ran through this loop. The most likely mechanisms: (a) the "volume>0 verified" chain filter or a data gap caused `chain.price` to drop/NaN the COVID entry and the cycle silently vanished, or (b) the reported numbers were not generated by this code/dataset. Either way the headline risk statistic is fake.
**Fix:** assert every calendar expiry produces a row (fail loudly on missing chain prints rather than skipping), and manually reconcile the Feb–Apr 2020 cycles against exchange data before accepting any summary stats.

**3. Cycle-count mismatch corroborates #2 (material).**
2019-01 through 2026-07 inclusive is **91** monthly expiries; the report shows **90 cycles**. One expiry disappeared without explanation. Combined with defect #1 (July 2026 shouldn't be there at all), a correct run should show 90 cycles ending 2026-06 — but then the presence of "2026-07" in the header and the impossible worst-loss both say at least one *historical* cycle (plausibly a 2020 one) was silently dropped. Every dropped cycle in a short-vol backtest is survivorship bias in the direction of overstating performance.
**Fix:** log every expiry with its entry date, strikes, and data status; require `len(r)` to equal the calendar length after the end-date filter.

**Non-material comments (not defects):**
- Premium is taken at entry-day **close prints**, i.e. last trade, not the bid; a seller realistically fills at/near bid on 45-DTE far-month strikes, so premium is modestly overstated. Recommend bid-side or mid-minus-slippage; 4.5 pts all-in costs is on the light side for two legs round-trip but defensible.
- NSE final settlement is based on the closing value derived from the last ~30 minutes of trading, not necessarily the plain series close; using `spot.asof(exp)` is a standard, small approximation.
- With 45-DTE entries on a monthly cycle, two positions are open simultaneously at all times; per-cycle point stats are fine, but any capital/margin-based translation must account for the overlap.
- Strike selection off the *prior* day's close is fine (no lookahead) — noted only because it slightly misaligns strikes vs. entry-day spot.

**Claimed material defects:**
1. `spot.asof(exp)` silently substitutes the 2026-06-30 close as "settlement" for the unexpired July 2026 cycle, fabricating a completed winning cycle; filter expiries to the data range and hard-fail on missing settlement dates.
2. Reported worst cycle of −412 pts is impossible given the code's hold-to-expiry logic through March 2020 (true loss > ~1,500 pts); a crisis cycle was silently dropped or the numbers were not produced by this code — reconcile Feb–Apr 2020 explicitly.
3. Cycle count (90) does not match the 91-expiry calendar claimed (2019-01 to 2026-07), evidencing silent cycle loss; make missing data a loud failure, not a skip.

===== T07 =====
## Review

I walked the code path chronologically (decision → execution → exit) checking each data access against what would have been knowable at that moment, then checked the settlement mechanics and the reported numbers for internal consistency.

**Decision timing.** The reference level `idx_close.asof(tuesday)` and the liquidity screen in `pick_expiry` (CONTRACTS > 0 on Tuesday) both use only Tuesday-EOD data, and the decision is explicitly made after Tuesday's close. Execution happens the *next* business day. No look-ahead here.

**The classic bhavcopy traps are correctly avoided.** NSE F&O bhavcopy carries a row for every listed contract even when untraded, with stale OHLC and a *theoretical* SETTLE_PR. This submission (a) guards fills with `CONTRACTS == 0` / `OPEN <= 0` checks, (b) does not use SETTLE_PR as a tradeable price anywhere, and (c) does not exit at the option's own expiry-day bhavcopy CLOSE (which is a stale last-trade print for OTM legs) — it settles at intrinsic value off the official index close, which is the correct final-settlement convention for NIFTY index options.

**No-fill skip is legitimately conservative.** Skipping when a leg didn't trade on entry day uses full-day volume (not knowable at 09:15), but since the resolution is "no trade booked," no phantom P&L enters the results; this is the standard conservative treatment, not a bias.

**P&L arithmetic.** Credit = shorts minus longs at entry; payoff = short-call spread intrinsic + short-put spread intrinsic; pnl = credit − payoff. Signs are correct. Slippage and charges are deducted.

**Reported numbers are internally consistent.** Wing width is 1.5% of the index (~270–360 pts over 2021–2025), so a fully-capped worst week of −312 pts net of credit is plausible; 224 + 31 = 255 weeks against ~260 calendar weeks over 5 years is consistent with a few holiday/anchor gaps; +6.1 pts/week at 71% hit rate is arithmetically feasible for this structure.

**Event skips** (budget, RBI, election results) are all scheduled dates knowable ex-ante, so the filter is implementable in real time.

**Verdict: No material defect.**

Non-material comments (clearly labelled as such):

- *Fill realism:* the four legs' bhavcopy OPENs are first-trade prints occurring at different times in a volatile opening auction; treating all four as simultaneously fillable is optimistic. Slippage/costs are already charged, but with only +6.1 pts/week of edge I'd want a sensitivity run with a spread-based haircut per leg.
- *`asof` silently substitutes:* if the expiry date is missing from `idx_close` (data gap), `asof(expiry)` returns a prior day's close instead of failing loudly. Use an exact-date lookup with an assertion for the settlement leg.
- *Monthly fallback changes tenor:* weeks routed to the current monthly have a very different holding period and risk profile; results should be reported split weekly vs. fallback.
- *Filter provenance:* confirm the event-skip list was fixed before the backtest was run, not tuned after seeing which weeks lost.
- *Regime note:* NIFTY weekly expiry day changed during 2025 (Thursday → Monday/Tuesday transitions); worth verifying the Tuesday anchor doesn't systematically collide with expiry and inflate the skip count late in the sample.

**Claimed material defects:**

1. None.

===== T08 =====
## Review — T08 NIFTY opening gap fade

**Defect 1 (material): `day_open = g.iloc[0]["open"]` uses the first print the vendor ships, which is a pre-open session print, not the tradable 09:15 open.**

- The scenario explicitly says the file "includes every print the vendor ships for the session." NSE has a pre-open call-auction session from 09:00 (order entry to ~09:08, indicative equilibrium prints until 09:15). Regular trading starts at 09:15. So `g.sort_values("ts").iloc[0]` on a full vendor file is a ~09:00–09:08 bar, and its `open` is an **indicative auction price** — nobody can transact at it.
- Mechanism of corruption: pre-open indicative prices systematically overshoot relative to where the regular session actually opens (thin, indicative, and they converge toward fair value by 09:15). Measuring the "gap" off that print and simultaneously "entering" at it means the strategy is booking the mechanical convergence of an untradable auction print to the real market. That manufactures both extra qualifying trades (gaps look bigger than the tradable gap, inflating the 388 count) and fake mean-reversion PnL — exactly the shape of the reported +9bp/58% result.
- Fix: filter to the continuous session before taking the open, e.g. `g = g[g["t"] >= time(9, 15)]`, and compute the gap from the first regular-session bar.

**Defect 2 (material): entry is executed at the exact price that defines the signal.**

- `entry_px = day_open` is the same number used to compute `gap`. You only know the opening print after it has occurred; you cannot then trade at that print. This is a one-bar look-ahead, and for a fade strategy it is the worst possible kind: the opening print of a 1-min series is the noisiest tick of the day, and "selling the print you just observed was high" harvests pure bid-ask/print noise. With a claimed edge of only 9bp per trade, next-bar entry (or entry at the 09:16 open) can plausibly erase or flip the result.
- Fix: enter at the open of the bar *after* the signal bar (e.g. first bar with `t >= time(9, 16)` when using the 09:15 open as the signal), or model an opening-auction fill only if the signal itself uses pre-auction information — which it doesn't here.

**Non-material comments (robustness/consistency, not claimed as defects):**

- If the file is a NIFTY **index** series rather than futures, the 09:15 index open is itself computed partly from stale constituent quotes and is not tradable at the quoted level even in principle, while costs are modeled as futures costs. Worth confirming the instrument; if it is index data, this becomes a third material defect (basis and stale-open artifact).
- `g[g["t"] >= time(10,15)].iloc[0]` raises `IndexError` on any truncated session; and on the Muhurat evening session (~18:15–19:15) both the "open" and the "exit" bars are evening prints, so that day is silently treated as a normal day. Guard for short/special sessions.
- `prev_close` relies on the parquet being globally sorted by `ts`: `groupby("d")["close"].last()` takes the last row *in file order*, not the latest timestamp. `m = m.sort_values("ts")` should be done once up front (the per-day sort inside the loop doesn't fix `prev_close`).
- Cost arithmetic itself is fine: 1bp/side = 0.0002 round trip, subtracted once per trade.

**Numbered list of claimed material defects:**

1. `day_open` is taken from the file's first print, which includes NSE pre-open auction bars (09:00–09:15) — the gap is measured against, and the entry filled at, an untradable indicative price, mechanically fabricating mean-reversion profit and inflating trade count.
2. Entry at `entry_px = day_open`, the same price that generates the signal — a look-ahead fill; entry must be at the next available bar after the signal is observable.

===== T09 =====
**Verdict: one material defect — a look-ahead in the breadth feature. Everything else checks out.**

## Material defect

**`df["adv_dec"] = (df["advances"] / df["declines"]).shift(-1)` — the `.shift(-1)` is look-ahead bias.**

- Mechanism: `shift(-1)` pulls the *next* row's value backward. So the value of `adv_dec` sitting on day t's row is the advance/decline ratio of day **t+1**. The signal is described (and executed) as "evaluated at day t's close, from data known by that close," and the trade enters at day t+1's open. But day t+1's breadth count is only known after day t+1's session ends — hours *after* the entry at t+1's open. The model is therefore conditioning entry on the breadth of the very session it trades into: it goes long precisely on days when tomorrow turns out to be a broad up-day (advances > 1.5× declines is a strong up-session marker). This is a classic peeking filter and will manufacture exactly the kind of result reported — low time-in-market (38%), inflated CAGR (17.1%), and an implausibly shallow max DD (-11%) — because bad sessions are filtered out using knowledge of those sessions' own breadth.
- The scenario statement even rules out the usual excuse: the data are stated to be correctly IST-dated daily breadth counts per session, so no timestamp-convention shift is needed.
- Fix: use the breadth known at day t's close, i.e. `df["adv_dec"] = df["advances"] / df["declines"]` (no shift; or `.shift(1)` if one wants an extra day of conservatism / if breadth is published with a lag). Then re-run; expect the edge to shrink dramatically or vanish.

## Checks that pass (no defect)

- **Execution alignment**: `o2o_next = open.shift(-2)/open.shift(-1) - 1` on the signal row is exactly the t+1-open to t+2-open return — consistent with "signal at t's close, trade next session open-to-open." No look-ahead here.
- **Other features**: `mom10`, `vol20`, `above_dma`, `vol_regime_ok` all use data through day t's close. `fillna(False)` on warm-up rows correctly forces flat rather than leaking.
- **Costs**: `pos.diff().abs() * 0.0003` charges 3 bp per side on each position change; sign/structure is correct.
- **CAGR annualization**: `n = strat.notna().sum()` counts trading days (last two rows are NaN via the open shifts and are excluded consistently from both `prod` and `n`), so `(1+strat).prod()**(252/n)-1` is a legitimate geometric annualization.

## Non-material comments

- The first `pos.diff()` is NaN→0, so any position held on day 1 pays no entry cost — negligible.
- 3 bp per side is optimistic for an index sleeve once impact/slippage at the open is included; worth stressing at 5–10 bp, but this is a robustness note, not a correctness bug.
- Buy-and-hold is presumably measured close-to-close while the strategy is open-to-open; a same-basis comparison would be cleaner. Non-material.
- `mom10 > 0` and `above_dma` overlap heavily as trend filters; redundancy, not error.

## Numbered list of claimed material defects

1. Look-ahead bias in the breadth filter: `df["adv_dec"] = (df["advances"] / df["declines"]).shift(-1)` conditions day t's signal (executed at t+1's open) on day t+1's not-yet-known advance/decline ratio, fabricating the reported outperformance. Fix: remove the `.shift(-1)` (use same-day or lagged breadth) and re-run.

===== T10 =====
## Review — T10, EVT-1 diversifier memo

This memo's central claim ("uncorrelated return stream") is an artifact of how the correlation was computed, and its own monthly table contradicts it. The stacking arithmetic is also wrong. Details:

### Defect 1 — Zero-dilution of the daily correlations (the "uncorrelated" claim is fake)

The memo states the sleeve holds positions on ~19% of trading days and "flat days book 0," then computes daily Pearson correlations over all 1,731 observations. Mechanically, ~81% of the EVT-1 series is exact zeros. Padding a return series with zeros on inactive days shrinks the measured correlation toward zero regardless of what happens on active days: the covariance only accumulates on the ~330 active days, while the correlation is normalized as if there were 1,731 informative observations. A sleeve that is strongly correlated with the book *whenever it is in a position* can easily print pairwise correlations of +0.01 to +0.03 on this construction.

**Fix:** compute correlations conditional on days the sleeve is active (~330 obs), and/or at monthly horizon, and separately in stress regimes. The "indistinguishable from zero" line is meaningless as computed.

### Defect 2 — The memo's own tail evidence contradicts independence

In the worst-5-book-months table, EVT-1 loses money in **all five** of the book's worst months, and its standalone worst month (-6.2%) is exactly Mar-2020 — the book's worst month. That is the signature of positive tail dependence: the sleeve sells event/announcement premium and gets hit in the same systemic drawdowns as the book (classic short-vol-like profile, consistent with its SV-IDX kinship). Diversification value is determined precisely by co-movement in the left tail, which here is strongly positive even while the full-sample daily correlation prints ~0.

**Fix:** the diversification case must be argued on conditional/stress correlation and joint drawdown behavior, not full-sample daily corr. On the evidence shown, the sleeve *adds* tail risk.

### Defect 3 — The Sharpe stacking math is wrong even granting independence

With risk weights 80/20 and zero correlation, the combined Sharpe is
(0.8·1.05 + 0.2·0.94) / √(0.8² + 0.2²) = 1.028 / 0.825 ≈ **1.25**, not ~1.38.
1.38 is approximately √(1.05² + 0.94²) ≈ 1.41 — the *optimally weighted* full root-sum-of-squares combination, which is not achievable at a fixed 20% risk weight. The memo applies "root-N combination of independent streams" (which assumes equal-Sharpe, equal-weight streams) to an unequal, fixed-weight case. So the projected uplift is overstated even before Defects 1–2 kill the independence assumption.

**Fix:** use the correct portfolio Sharpe formula with the fixed weights and a realistic (stress-conditional) correlation; the true uplift is far smaller than 0.33 and may be negative.

### Defect 4 — "Benefit does not depend on the sleeve's standalone return staying at backtest levels" is false

Diversification benefit from an added sleeve requires a positive expected return (positive marginal Sharpe relative to correlation). If EVT-1's forward return degrades to zero, adding it at 20% risk weight adds volatility with no return and *lowers* book Sharpe (0.8·1.05/0.825 ≈ 1.02 < 1.05 even at zero correlation). The claim inverts the actual condition and is being used to justify immediate full-size funding.

**Fix:** delete the claim; condition sizing on a haircut forward Sharpe estimate.

### Non-material comments (not defects per se)

- ~14 trades/yr over 7 years is ~98 trades; the standalone Sharpe of 0.94 carries a wide confidence interval, arguing for a phased-in weight rather than "fund at 20% immediately."
- Even the standard error argument for the daily correlations (±~0.024 on 1,731 obs) is moot given Defect 1 — the effective sample is the active days.

### Verdict on the ask

Do not approve at 20% risk on diversification grounds. The correlation evidence is an artifact, the tail evidence shows co-crash behavior, and the projected Sharpe is miscalculated.

---

**Claimed material defects:**

1. Daily correlations computed over all days including ~81% structural zeros — zero-dilution artifact fakes the "uncorrelated" result; must condition on active days / use monthly and stress correlations.
2. Positive tail dependence shown in the memo's own worst-months table (EVT-1 down in all five worst book months, worst month = Mar-2020) contradicts the independence claim and negates the diversification case.
3. Sharpe stacking arithmetic wrong: correct zero-correlation, 80/20 combination gives ~1.25, not ~1.38; the ~1.38 figure corresponds to optimal equal-risk combination not available at the proposed weight.
4. False claim that the diversification benefit is independent of the sleeve's forward return — at zero forward return the sleeve strictly lowers book Sharpe.

===== T11 =====
**Material defect found: the smoother is centered, so the entry signal uses future data (lookahead).**

**Defect — `iv_ma = iv.rolling(11, center=True).mean()`**

- **The exact line:** `iv_ma = iv.rolling(11, center=True).mean()`, feeding `rich = iv > 1.15 * iv_ma`.
- **Mechanism:** With `center=True` and window 11, the moving average at day *d* is the mean of IV over days *d−5 … d+5*. The richness test on day *d* therefore compares today's IV against an average that includes the **next five sessions' IV values**, which are unknowable at the close of day *d*. This is not a neutral smoothing artifact — it biases the signal in exactly the direction that manufactures profit for a short-vol strategy:
  - `iv > 1.15 × centered-MA` fires precisely when today's IV is high relative to *both* the recent past *and the coming week*. In other words, the rule selects **local IV peaks** — days after which IV is, by construction of the filter, about to fall.
  - Selling a straddle immediately after an IV local maximum harvests the subsequent vol crush that the signal literally peeked at. The reported +2.1% per trade and 76% hit rate are therefore substantially (possibly entirely) an artifact of lookahead, not a tradeable edge.
  - Note that executing at the *next session's open* does not cure this: the execution timing is honest, but the signal itself was computed with future data.
- **Fix:** Use a trailing window: `iv_ma = iv.rolling(11).mean()` (optionally `min_periods=11`), so the day-*d* average uses only days *d−10 … d*. If a symmetric smoother is preferred for other analysis, it must be lagged for signal use, e.g. `iv.rolling(11, center=True).mean().shift(5)` — then re-run the backtest. Expect the entry count, mean P&L, and hit rate to change materially; the current headline numbers should be discarded.

Everything else checks out or is honest:

- Entry at the next session's open (given end-of-day signal data) is the correct anti-lookahead execution convention — no defect there.
- `entry_days = rich & ~rich.shift(1).fillna(False)` correctly picks the first day of each episode; the `fillna(False)` handles the first row properly.
- The leading/trailing NaNs from the rolling window make `rich` False there (NaN comparisons are False), which is safe, not a bug.

**Non-material comments (clearly labelled as such):**

- *Non-material:* Dropping trades where a leg is untraded at entry (`if t is not None`) is realistic (you cannot fill an untraded leg), but it's worth reporting how many of the 96 signal days were skipped, since illiquid days often coincide with the highest-IV episodes and the skip could quietly cherry-pick.
- *Non-material:* The 15% richness threshold and 11-day window should be shown across a small grid to demonstrate the result isn't a parameter-tuning artifact.
- *Non-material:* Overlapping trades are possible (a new rich episode can start while a prior straddle is still open, up to 15 sessions); worth confirming capital/margin treatment, though it doesn't fake the per-trade statistic.

**Numbered list of claimed material defects:**

1. Centered rolling mean (`rolling(11, center=True)`) injects 5 days of future IV into the richness signal — the entry rule selects IV peaks by peeking ahead, fabricating the vol-crush profit. Fix: trailing `rolling(11).mean()` (or shift the centered MA by 5) and re-run.

result: Review complete — one material defect: the centered 11-day IV moving average gives the entry signal 5 days of lookahead, selecting IV peaks and faking the short-vol edge; fix is a trailing (or lagged) MA and a re-run.

===== T12 =====
## Review — T12 weekly short straddle on F&O bhavcopy

**The headline losses are a data artifact, not pin risk.** Look at the fingerprint in the worst-5 list: the "loss" each week is approximately equal to the *level of the NIFTY index itself* on that date — 2021-04-08: 14,466 (NIFTY was ~14,800), 2024-02-29: 21,880 (NIFTY ~22,000), 2023-08-31: 23,912 (NIFTY ~19,300 plus whatever the other leg contributes). A straddle's expiry debit is |S − K|; on a week where the index moved <0.4% against a strike set one day earlier, the true debit is at most a few hundred points. A debit of ~20,000 points is arithmetically impossible for the strategy — it can only arise if a price field is carrying the *underlying's* value instead of an option premium.

### Material defect

**Lines:**
```python
ce_x = fo.row(week.expiry, week.expiry, k, "CE").SETTLE_PR
pe_x = fo.row(week.expiry, week.expiry, k, "PE").SETTLE_PR
```

**Mechanism:** On the expiry-day row of an *expiring* contract, the NSE F&O bhavcopy `SETTLE_PR` field does not reliably hold the option's final premium. For expired/exercise-settled series (and for strikes with no trade on expiry day), the field is populated with the settlement reference — effectively the underlying's final settlement level, or another placeholder — rather than the intrinsic value of the option. The engine then books `debit = ce_x + pe_x` ≈ index level, manufacturing five-figure "losses" on quiet weeks. The comment in the code ("SETTLE_PR is the official settlement and avoids stale CLOSE prints") is exactly backwards *for the expiry-day row*: that heuristic is fine for daily MTM rows, not for the terminal row of an expiring option.

This corrupts every summary number: the −118.3 avg, the 64% hit rate (any week where the field is polluted on either leg flips to a catastrophic loss), and the entire "worst weeks" table. The author's proposed fix (add a stop) would be optimizing around a phantom.

**Correct fix:** Do not read the option price off the expiry-day bhavcopy row at all. Compute the terminal payoff analytically:

```python
S = final_settlement_price(week.expiry)   # NSE official final settlement
debit = max(S - k, 0) + max(k - S, 0)     # = abs(S - k)
```

using the exchange's official **final settlement price** of the index (the last-30-minutes weighted average NSE publishes), not the plain index close — hold-to-expiry positions are cash-settled against that number. Alternatively, sanity-guard the field: assert `ce_x < strike_interval * some_bound` and `ce_x + pe_x << index_level`; any violation flags the data quirk.

After this fix, re-verify: the "four-digit losses on flat weeks" should vanish entirely, and hit rate / average P&L must be re-reported.

### Non-material comments (labelled as such)

- *Non-material:* Entry at `ce.CLOSE + pe.CLOSE` uses last-trade prints, which can be stale intraday marks even when `CONTRACTS > 0`; using entry-day `SETTLE_PR` (where it *is* a valid daily settlement, i.e. non-expiry rows) or applying a spread haircut would be more honest. Direction of bias is unclear, likely small.
- *Non-material:* `continue` on untraded strikes silently drops weeks (261 vs ~300+ calendar weeks). This is a legitimate tradability filter, but the write-up should disclose the skip count; if skipped weeks correlate with stressed regimes it mildly flatters results.
- *Non-material:* Strike is set ATM off the *prior* day's close but the trade executes at entry-day close, so the position can start noticeably off-ATM after a gap day. Defensible design choice, worth stating explicitly.
- *Non-material:* NIFTY weekly expiry day migrated during 2020–2025 (Thursday, later moved); confirm `week.expiry` tracks the actual contract expiry calendar rather than a hardcoded weekday.

### Claimed material defects

1. Expiry-leg valuation reads `SETTLE_PR` from the expiry-day bhavcopy row of the expiring option, which for expired series carries the underlying settlement level (the worst-week "losses" ≈ NIFTY index level prove it), not the option's terminal premium — corrupting P&L, hit rate, and the "pin risk" narrative. Fix: value expiring legs as `abs(official_final_settlement − K)` per leg payoff, never from the option row's SETTLE_PR.

result: One material defect — expiry exit uses bhavcopy SETTLE_PR on expiring option rows, which holds the underlying settlement level (worst losses ≈ NIFTY level), fabricating huge losses; compute payoff as |final settlement − strike| instead.

===== T13 =====
Review of T13 — 12-1 momentum on NIFTY-500.

The headline claim (24.8% CAGR vs 12.1%) is not credible as produced, because of one dominant defect that fakes the result, plus a secondary consistency problem in the cost/fill accounting.

**Defect 1 (material) — universe is the *current* constituent snapshot, not point-in-time.**

- Exact lines:
  ```python
  universe = pd.read_csv("nifty500_constituents.csv")["Symbol"].tolist()
  # downloaded from the index provider's website, 2026-07 refresh, 500 symbols
  close = close[[c for c in close.columns if c in universe]]
  ```
- Mechanism: the price panel is survivorship-complete, but this filter immediately throws that away. The 2026-07 membership list contains only companies that survived and grew enough to be in the NIFTY-500 *today*. Restricting the 2013-2025 backtest to those names is (a) survivorship bias — delisted, bankrupt, and shrunken names are excluded, so the losers momentum would have bought and ridden down never appear; and (b) look-ahead index-inclusion bias — many 2026 constituents were small/micro caps in 2013-2018, and selecting them then implicitly conditions on their future success. Momentum strategies are especially sensitive to this: past winners that later blew up are exactly the names removed. This alone routinely inflates long-only momentum CAGRs by several hundred bps to double digits; it is the most plausible source of most of the 24.8%−12.1% spread.
- Fix: use point-in-time index membership — at each month-end `me`, rank only stocks that were NIFTY-500 constituents *as of me* (historical constituent files / index-change announcements), keeping delisted names in the panel so their post-selection returns (including delisting outcomes) are captured.

**Defect 2 (material) — cost/fill accounting is internally inconsistent with the stated no-fill logic.**

- Exact lines:
  ```python
  port = apply_fill_rules(weights.shift(1) * ret)
  port -= turnover_costs(weights, bps_per_side=45)
  ```
- Mechanism: `apply_fill_rules` is applied to the *return contribution* series, after the weights are already fixed. If an entry is blocked (circuit-locked / zero-volume open), the correct treatment is that the position is not established — the capital stays in the previous holding or cash, and no transaction cost is paid — and the fill is retried or skipped. Here the weights matrix is unchanged, so (a) `turnover_costs(weights, …)` charges 45bp turnover on trades that per the fill rules never executed, and (b) whatever `apply_fill_rules` does to the return stream (e.g. zeroing the contribution) leaves the portfolio implicitly under-invested with no cash accounting. Depending on how the helper behaves this can bias the result either way, but the reported number cannot be trusted: the fills and the costs are computed from two different portfolios. On the NSE this matters — small-cap momentum winners hitting upper circuits at the open is common, and "you can't buy the circuit-locked winner" is a first-order drag on realized momentum returns.
- Fix: apply no-fill logic to the *weights* (carry forward the previous position when a trade can't fill), then compute both returns and turnover costs from those realized weights.

**Non-material comments (not counted as defects):**

- `close.pct_change()` and `pct_change(231)` with pandas' default forward-fill of missing prices will manufacture 0% returns across suspension gaps and stale momentum for illiquid names. With a proper point-in-time delisted-inclusive panel this becomes more important; use `fill_method=None` and explicit staleness filters.
- `nxt = close.index[close.index.searchsorted(me, side="right")]` raises IndexError when `me` is the final date in the panel; guard the last month-end.
- The "next-open entry" is actually approximated as next-session close-to-close via `weights.shift(1)` (weight set on `nxt` first earns the `nxt+1` return). That's a mildly conservative one-day implementation lag, not look-ahead — fine, but the write-up should say so rather than claiming next-open execution.
- The 12-1 window (`shift(21).pct_change(231)`, i.e. t−252 to t−21) is constructed correctly; no issue there.

Numbered list of claimed material defects:

1. Universe filtered to the 2026-07 constituent snapshot — survivorship + index-inclusion look-ahead bias that inflates the momentum CAGR; must use point-in-time membership with delisted names retained.
2. No-fill rules applied to return contributions while turnover costs are charged on the original (unexecuted) weight path — fills and costs computed from inconsistent portfolios; no-fill handling must modify the realized weights, from which both P&L and costs are then derived.

result: Review complete — two material defects found: (1) current-snapshot universe filter reintroduces survivorship/look-ahead bias despite the survivorship-complete panel, and (2) fill rules and 45bp turnover costs are computed from inconsistent weight paths; the 24.8% CAGR is not trustworthy as reported.

===== T14 =====
## Review — T14 overnight selected-nights memo

**Verdict: not passable as written.** The headline economics may or may not survive, but at least two of the reported statistics are internally impossible, and the control section contains an arithmetic inconsistency. Details:

---

### Defect 1 — The Sharpe/t-stat are inconsistent with the memo's own tail numbers (the significance claim is fake or miscomputed)

- **Claim:** net +1.9bp/night, Sharpe 1.21, t = 3.8 over 962 selected nights; worst night −1.9%.
- **Mechanism:** t = 3.8 on a mean of ~1.9–3.1bp over 962 nights implies a nightly P&L standard deviation of roughly `mean × √962 / t ≈ 15–25bp`. Equivalently, Sharpe 1.21 on ~2.6%/yr implies annual vol ≈ 2.15%, i.e. nightly vol ≈ 13–15bp. But the memo itself reports a **worst night of −1.9% = 190bp** — a 12–14σ event under that vol — and NIFTY overnight gap vol is empirically on the order of 40–80bp/night, not 15bp. With a realistic σ ≈ 50–60bp, t ≈ 1.0–1.6 and Sharpe ≈ 0.5–0.7: **not statistically significant**. The reported stats cannot have been computed from the actual nightly return series (common causes: Sharpe/t computed on a smoothed or cumulative series, a stray scaling factor, or vol taken from a different unit than the mean).
- **Fix:** recompute mean, σ, Sharpe, and t directly from the raw per-night return vector; the numbers must reconcile with the −1.9% worst night. Report the corrected t. If it's ~1.2, the sleeve is not validated.

### Defect 2 — The exposure-matched baseline arithmetic is impossible; the "+2.2bp selection edge" mixes gross and net

- **Claim:** all nights average +0.9bp/night gross; a random 55%-of-nights baseline earns "+0.9bp/night **net of the same costs**"; selection adds +2.2bp.
- **Mechanism:** a random subset of nights has the same expected gross as all nights, +0.9bp. Net of the stated 1.2bp costs, the baseline must be **−0.3bp/night**, not +0.9bp. The +0.9bp "net" figure is the gross figure relabelled. The quoted +2.2bp gap is therefore either gross-vs-gross (3.1 − 0.9) or net-vs-net (1.9 − (−0.3)) — coincidentally both 2.2 — but the memo's stated basis for it is wrong, and the control as written asserts an impossible number. This matters for the memo's own framing: after costs, indiscriminate overnight holding *loses* money, which should be stated.
- **Fix:** report both legs on a consistent basis: baseline gross +0.9bp / net −0.3bp; strategy gross +3.1bp / net +1.9bp; selection edge +2.2bp on either basis.

### Defect 3 — Cost assumption of 1.2bp round trip is implausibly low for Indian index futures

- **Claim:** "costs 1.2bp/night round trip (exchange + impact, futures)."
- **Mechanism:** on NSE, STT on the futures **sell leg alone** is 1.25bp (0.0125%, and 2bp after the Oct-2024 change, which falls inside the 2019-2025 window), before exchange transaction charges, SEBI fee, stamp duty, GST, spread, and impact. A realistic all-in round trip is ~2–3bp. Since the gross edge is only 3.1bp, the net edge is acutely cost-sensitive: at 2.5bp the sleeve earns ~+0.6bp/night and the "+2.6%/yr" claim collapses to under 1%. Citing "the approved cost standard" does not discharge this — the number as stated is below statutory charges alone for part of the window.
- **Fix:** itemize the cost stack per leg per regime (pre/post STT change), and re-run net figures. If the standard genuinely says 1.2bp for this instrument, the standard needs auditing.

### Defect 4 — In-sample rule selection; the placebo tests the wrong null

- **Claim:** "favourable weekday bucket" and vol-percentile-below-60 thresholds, validated by 500 random same-size night subsets (97th percentile).
- **Mechanism:** the weekday bucket and the 60th-percentile threshold were (nothing in the memo says otherwise) chosen on the same 2019-2025 window they are evaluated on. The random-subset placebo answers "is this better than a random subset?" — but the correct null is "is this better than the best rule found by searching weekday × vol-threshold combinations?" With ~30+ implicit candidate rules, a 97th-percentile result against random subsets is roughly what the *best* of the searched family would show under the null. Era splits don't cure this: they are splits of the fitting window, not out-of-sample.
- **Fix:** state when the rule was frozen; validate on a true hold-out or walk-forward, or run the placebo over the searched rule family (all weekday buckets × threshold grid) rather than random subsets.

---

**Non-material comments (not defects):**
- Booking no fill on the 3 limit-locked nights is the right treatment, but confirm those nights' hypothetical P&L is excluded from both strategy and baseline symmetrically.
- Worst month (−1.7%) being milder than worst night (−1.9%) is possible (intra-month recovery) but worth a one-line reconciliation.
- Roll treatment for front-month futures around expiry should be stated (presumably in the cost standard).

---

### Claimed material defects

1. Sharpe 1.21 / t = 3.8 are inconsistent with the memo's own worst night (−1.9%) and any plausible NIFTY overnight vol — the significance statistics are wrong; realistic vol gives t ≈ 1–1.6.
2. The exposure-matched baseline "+0.9bp net of the same costs" is arithmetically impossible (gross 0.9 − costs 1.2 = −0.3bp net); gross and net are conflated in the key control.
3. Round-trip cost of 1.2bp is below statutory Indian futures charges alone for part of the window; net edge and +2.6%/yr are overstated.
4. Signal parameters (weekday bucket, 60th-percentile vol threshold) appear fitted in-sample with no hold-out, and the random-subset placebo does not account for the rule search.

===== T15 =====
## Review — T15 IV-percentile strangle seller

**Defect 1 (material): full-sample z-score — look-ahead in the entry signal.**

```python
mu = hist["iv"].mean()
sd = hist["iv"].std()
hist["iv_z"] = (hist["iv"] - mu) / sd
```

`mu` and `sd` are computed over the entire 2015–2025 file, then applied to every day, including days years before most of that data existed. Every signal from 2015–2019 is standardized using the 2020 crash and the 2021–2025 regime — information unavailable at trade time. Mechanism of corruption: the crash inflates the full-sample `sd`, which compresses everything else's z-scores, so "IV rich but not crash" is calibrated with perfect hindsight about where the distribution's tail sits. Ironically this also defeats the stated purpose ("generalizes across vol regimes") — a single global mean/sd is the *least* regime-adaptive standardization possible. **Fix:** compute z with an expanding or rolling (e.g. trailing 1–2y) window using only data up to the signal day, and re-run.

**Defect 2 (material): the crash filter's headline claim is a direct artifact of Defect 1.**
The write-up boasts "worst trade −21% of premium (Mar-2020 skipped by the crash filter)". The `iv_z < 2.5` cutoff only "skipped" March 2020 because the z-score was built from a distribution that already contained March 2020. A real-time expanding-window z in early 2020 (fit on the placid 2015–2019 vol regime) would have crossed 1.0 with much smaller absolute IV and could easily have triggered entries in late Feb 2020 (z between 1.0 and 2.5 on the way up) — exactly the trades that destroy short-strangle strategies. The −21% worst-trade and 79% hit rate are therefore not credible as reported. **Fix:** same as Defect 1; if a crash filter is wanted, define it on point-in-time information (e.g. IV level vs trailing percentile, or realized-vol spike), then report the worst trade honestly.

**Defect 3 (material, conditional on implementation): `liquidity=("both_legs_traded",)` is ex-post sample selection unless it is strictly an entry-time check.**
`sell_weekly_strangle` returns `None` and the trade is silently dropped. If "either leg had no trades" is evaluated over the holding period (or at exit), the filter uses information not available at entry, and — worse — no-trade prints in index options cluster in stressed/gappy sessions, so the dropped trades are disproportionately the losers. That mechanically inflates the mean and the hit rate. Even if it is entry-time-only (which would be executable), the printed `entries: len(tr)` counts post-filter *fills*, not signal entries, so "214 entries" understates how often the rule fired and hides the drop rate. **Fix:** enforce the liquidity check strictly at the entry open (consistent with "entry-day option prices are verified"), and report both signal count and filled count with the skip reasons.

**Non-material comments (clearly labelled as such):**
- Overlapping positions: signals evaluate daily and each trade is held to weekly expiry, so consecutive-day entries hold near-identical positions. The 214 trades are not independent; the 79% hit rate has far fewer effective observations than it appears. Doesn't fake the mean, but any significance claim should use non-overlapping entries or cluster-robust errors.
- No transaction-cost/slippage statement beyond "open prints" — for weekly index strangles, spread crossing on two legs is a large fraction of 1.7% of premium; worth confirming "net" includes realistic costs.
- Bare `except`-style silent skip (`if t is not None`) with no logging of why trades were excluded makes the sample unauditable.

## Claimed material defects

1. Entry z-score standardized with full-sample (2015–2025) mean/std — look-ahead bias contaminating every signal; must be expanding/rolling point-in-time.
2. The "Mar-2020 skipped by the crash filter" claim (and hence the −21% worst trade / 79% hit rate) is an artifact of that in-sample standardization; a point-in-time filter likely admits pre-crash entries.
3. The `both_legs_traded` liquidity skip is outcome-correlated sample selection unless provably evaluated only at the entry open; as coded, dropped trades also make the reported "214 entries" a post-filter count, misstating the sample.

===== T16 =====
## Review — T16 quality-tilt certification memo

**Verdict: do not certify. The +3.1pp "selection edge" is almost entirely a manufactured cost artifact, not alpha.**

### Material defect: turnover-mismatched hurdle makes the cost model non-comparable

The memo's central comparison is rigged by construction, even though the *rate* charged (45bp/side) is identical for both arms:

- **Strategy arm:** semiannual rebalance, 38%/yr one-way turnover → cost drag ≈ 2 × 0.38 × 45bp ≈ **0.34pp/yr**. Check against the table: 15.0% gross → 14.6% net, a 0.4pp gap. Consistent.
- **Hurdle arm:** random baskets **refreshed monthly**, ~330%/yr one-way turnover → cost drag ≈ 2 × 3.30 × 45bp ≈ **2.97pp/yr**. Check: 14.7% gross → 11.5% net, a 3.2pp gap. Consistent.

So of the claimed +3.1pp net edge over the median, roughly **2.6–2.8pp is nothing but the differential cost drag** created by forcing the hurdle to churn ~9x faster than the strategy. "Both arms charged the same honest cost model" is true of the rate and false of the comparison: identical bp/side applied to structurally different trading volumes is not an identical cost assumption.

**The gross numbers give the game away:**
- Gross edge over median: 15.0% vs 14.7% = **+0.3pp** — negligible.
- Gross vs p95: 15.0% vs **16.9%** — the strategy is *well inside* the random distribution before costs. The headline claim "clears even the 95th percentile" (14.6 vs 13.7 net) exists only because the p95 basket was charged ~3pp of costs it wouldn't incur if it were run at the strategy's cadence.

**Mechanism of corruption:** monthly-refreshed random baskets replace nearly the whole 40-name book each month (a fresh random draw of 40 from a large segment overlaps very little with the prior draw), so their turnover is an artifact of the hurdle's refresh schedule, not of any investable comparison. A "hurdle" that is guaranteed to bleed ~3pp/yr in costs is a hurdle any low-turnover strategy — including a random buy-and-hold — will "beat."

**Correct fix:**
1. For the *selection edge* question, compare **gross vs gross** (or equivalently, charge zero costs to both). Result: +0.3pp over median, below p95 → no certifiable selection edge on these numbers.
2. For the *implementable* question, match the hurdle's trading structure to the strategy's: random baskets rebalanced semiannually with matched holding behavior (or at minimum report the hurdle at the strategy's turnover profile), each arm charged its own actual costs.
3. If the +3.1pp figure is to be registered at all, it must be decomposed and re-labelled as "cost drag avoided vs a monthly-churn straw man," which is not an expected-outperformance claim.

### Secondary point (material to the verdict, derivative of the above)

The claim "register at +3.1pp/yr expected outperformance over segment random" is wrong as stated even taking the table at face value: the number measures the strategy against a *specific, artificially high-turnover implementation* of segment random, not against segment random exposure. The statistical gates cited (DSR 0.98, PBO 22%, plateau, lookahead 0-FAIL) do not address this — they validate against overfitting and lookahead, and are silent on hurdle mis-specification, so they cannot rescue the comparison.

### Non-material comments (clearly labelled as such)

- 38%/yr one-way turnover for a semiannual quality screen is plausible; no issue.
- The 45bp/side all-in figure for mid/small is a reasonable order of magnitude; not challenged.
- Reporting only p50/p95 of the hurdle net distribution is thin — showing the strategy's percentile rank in both gross and net distributions would make the artifact visible immediately.

---

**Numbered list of claimed material defects:**

1. **Turnover-mismatched hurdle:** identical 45bp/side cost rate applied to a 38%/yr-turnover strategy vs a ~330%/yr-turnover monthly-refreshed random hurdle injects ~2.6–2.8pp/yr of differential cost drag into the "+3.1pp edge"; gross-vs-gross the edge is +0.3pp and the strategy sits below the random p95 (15.0% vs 16.9%), so the certified selection edge and the "clears p95" claim are artifacts. Fix: assess selection on gross returns and/or use a turnover-matched (semiannually rebalanced) random hurdle; do not register +3.1pp.

result: Reject certification — the +3.1pp "edge" is a cost artifact from comparing a 38%-turnover strategy to a 330%-turnover monthly-refreshed random hurdle under the same per-side cost; gross edge is only +0.3pp and below the random p95.

===== T17 =====
## Review — T17 calendar-spread timing engine

**Material defect: look-ahead selection of the entry day (`win["ff"].idxmax()`).**

- **Exact line:**
  ```python
  best = win.loc[win["ff"].idxmax()]
  entry_day = next_session(best["date"])
  ```
- **Mechanism:** The engine's stated question is "which day inside T-30..T-10 should we enter?" — a decision that must be made *inside* the window, in real time. This code instead scans the **entire** T-30..T-10 window after the fact and picks the day with the maximum `ff`. On any given day during the window, you cannot know whether today's `ff` is the window maximum — that is only knowable once the window has closed (at T-10), by which point the "optimal" entry day is usually already in the past. The `next_session(...)` fill does **not** repair this: shifting the fill one day forward avoids trading on the same day's settlement print, but the *selection* of that day still conditions on every future `ff` value in the window. Suppose the max falls on T-25; a live trader standing at T-24 has no way to know that T-26..T-10 won't print higher. The result is a hindsight-optimal stopping rule.
- **Why it fakes the result:** Selecting the per-cycle max of a noisy daily series and then measuring PnL from that point systematically harvests noise — it's per-cycle in-sample optimization repeated 86 times. The +7.2 pts / 69% hit rate is an upper envelope, not an achievable strategy. Expect a large drop under any causal rule.
- **Fix:** Replace with an ex-ante stopping rule that uses only information available at decision time, e.g.: enter on the first day `ff` exceeds a threshold calibrated on *prior* cycles (or a trailing rolling quantile), or a secretary-style rule ("observe T-30..T-24, then enter on first day beating the observed max"). Benchmark against the naive fixed-day entry (e.g., always T-20) to measure the timing signal's true incremental value.

**Non-material comments (clearly labelled as such):**

- *Cost accounting (possible, cannot confirm from snippet):* `costs_pts(2)` may be charging 2 leg-trades, but a calendar spread opened and closed involves 4 leg executions (2 legs in, 2 legs out). If `costs_pts` takes leg count per side, costs could be understated ~2x. Verify the function's convention.
- *Reported cycle count:* cycles are dropped for `len(win) < 8` and for liquidity (`spread is None`). Skipping untradeable spreads is legitimate ex-ante, but the write-up should disclose how many of the ~90 possible cycles were dropped and confirm drops aren't correlated with stress periods (which would flatter the hit rate). Not a defect per se, a disclosure issue.
- *One decision, one signal:* using next-session open fills against a settlement-derived signal is correctly non-anticipative on the *fill* side — that part is fine.

**Claimed material defects:**

1. Look-ahead bias in entry-day selection: `win["ff"].idxmax()` picks the window's best day using the full future window, which is unknowable in real time; the `next_session` fill does not remove the hindsight in the day *selection*. Fix: causal/ex-ante stopping rule calibrated on prior data, benchmarked against fixed-day entry.

===== T18 =====
## Review — T18 paper-book fill audit

The tell here is the failure pattern itself: 501/501 UNFILLABLE, *including ATM NIFTY weeklies that trade lakhs of contracts a day*. A uniform 100% failure rate across wildly different liquidity regimes almost never means "the book was untradeable" — it means the query or the matching logic is structurally excluding the data. And it is.

### Material defect: `fromdate` excludes the entry-day daily bar

```python
"fromdate": leg.entry_date.strftime("%Y-%m-%d") + " 09:15",
```

The scenario states explicitly that the broker's ONE_DAY candles are **stamped at 00:00 IST**. The entry day's daily candle therefore carries timestamp `entry_date 00:00`, which is *before* the requested `fromdate` of `entry_date 09:15`. The broker API filters candles by timestamp, so the entry day's bar is never returned — the earliest bar in the response is the *next* trading day.

The matching loop then looks for a bar whose date prefix equals the entry date:

```python
if c[0][:10] == leg.entry_date.strftime("%Y-%m-%d"):
```

No such bar exists in the response, so `entry_bar` stays `None`, and every leg — regardless of actual liquidity — falls into the `entry_bar is None → "UNFILLABLE"` branch. This mechanically produces exactly the observed output: 501/501 UNFILLABLE with "no entry-day bar," and it does so identically for illiquid far-OTM legs and deep-liquid ATM weeklies. The conclusion ("void the week's paper results") is built entirely on this artifact.

**Fix:** request `fromdate = entry_date + " 00:00"` (or `entry_date - 1 day`) so the 00:00-stamped daily bar is inside the window. After the fix, re-run and confirm ATM NIFTY legs come back with non-zero volume as a sanity check before drawing any conclusion.

### Secondary / non-material comments

- **Missing imports / undefined names (consistency check on the "observed output"):** the snippet imports only `time`, but uses `pd.Timedelta`, `pd.Series`, and an undefined `lot_value`. As shown, this script would raise `NameError` before printing anything. Presumably these exist in the surrounding module; if not, the claimed output could not have come from this code. Worth confirming, but I'm treating it as snippet truncation, not a material defect.
- **No liquidity-tier sanity check in the process:** an audit that flags an ATM NIFTY weekly as zero-volume should trip an internal plausibility alarm before recommending voiding results. Recommend adding an assertion like "known-liquid control symbols must return OK" to the audit itself.
- **Units in the THIN test:** `entry_bar[5] * lot_value(leg)` assumes the volume field is in the same unit (contracts vs. lots vs. shares-equivalent) that `lot_value` expects; NSE F&O volume conventions vary by API. Verify the unit once against a known contract. Non-material to the current (all-UNFILLABLE) result.
- **Day-level volume ≠ fillability at the entry timestamp:** even once fixed, daily volume is a weak proxy — a leg entered at 15:25 in a contract that traded only in the morning would pass. Consider minute candles around the entry time for a stricter audit. Robustness note only.

### Claimed material defects

1. `fromdate` is set to `entry_date 09:15`, but ONE_DAY candles are stamped at 00:00 IST, so the entry day's bar is excluded from the API response; the date-match loop then finds no entry bar and every leg is mislabelled UNFILLABLE. Fix: use `00:00` on the entry date (or start a day earlier), then re-run — the "void the week" recommendation is currently unsupported.

===== T19 =====
## Review — T19 mid-cap momentum, union panel

I checked each of the classic failure points for this kind of study.

**Survivorship:** union panel including delisted names, with delistings held at last traded price and the loss realized on the delisting date rather than silently dropped. No survivorship defect.

**Membership look-ahead:** `members.asof(me)` takes the latest point-in-time snapshot *on or before* the rebalance date. That is the correct direction (backward-looking asof), so no future-membership leak. 42 Mar/Sep snapshots also implies history extending well before 2014, so early rebalances aren't starved.

**Signal look-ahead / window arithmetic:** `mom = close.shift(21).pct_change(231)` evaluated at month-end `me` gives `close[me-21] / close[me-252] - 1` — a proper 12-1 momentum (252-day lookback, 21-day skip), using only data through `me-21`. Correct, and if anything conservative.

**Execution look-ahead:** signal is formed from the close on `me`; targets are set for `first_session_after(me)` and filled at the open, with a no-fill check on locked/zero-volume opens and 45bp/side costs. No same-bar fill, no fill-at-signal-price. Clean.

**Null construction:** same panel, same PIT universe, same dates, same cost model, percentile of 10,000 nulls. Methodologically sound as described.

**Conclusion: No material defect.**

Non-material comments (clearly labelled as such — not defects that make the result wrong or fake):

- **`pct_change` fill behavior vs the stale mask.** On older pandas, `pct_change`'s default `fill_method='pad'` forward-fills NaNs before differencing, which partially undoes `close.mask(stale)` — names with frozen runs can re-enter the ranking with a padded momentum value instead of being dropped by `dropna()`. On pandas ≥2.1 the default is deprecated/removed, so behavior is version-dependent. Recommend `pct_change(..., fill_method=None)` explicitly in both `ret` and `mom`. Worth verifying, but it weakens a hygiene filter rather than injecting look-ahead, and stale names would mostly show near-zero momentum and fail to reach the top-40 anyway.
- **`ret = close.pct_change()` is defined but never visibly used** in the snippet; presumably consumed by `run_engine`. Cosmetic here.
- **Delisting mark at last traded price** slightly overstates recovery for hard bankruptcies (true recovery is often near zero), i.e., a mildly optimistic but disclosed assumption. Suggest a sensitivity run marking distress delistings to zero.
- **`mom.loc[me]` will KeyError if a `month_end` is not a trading day** in the index; use `.asof`/reindex for robustness.
- **"Turnover-matched by construction"** for random baskets is asserted, not shown — independently redrawn 40-name baskets would have much higher turnover (and costs) than a 12-1 momentum book, which would flatter the strategy's percentile. If the null code genuinely constrains turnover to match, fine; I'd ask to see that construction.
- **Interpretation, not a defect:** 93rd percentile of the null is p ≈ 0.07 — honestly reported, but it does not clear a conventional 95% bar, so the write-up should not be read as strong evidence of alpha.

Numbered list of claimed material defects:

1. None.

===== T20 =====
## Review — T20: RSI-dip entry validation memo

### Defect 1 (material): the placebo arm uses a different exit engine than the strategy arm

The strategy exits via **+2.0% target / -4.0% stop / 20-day timeout, first touch**. The placebo exits at the **close of day 5, fixed-time**. This breaks the experiment: the test no longer isolates the *entry* signal, because the two arms differ in *two* things (entry rule AND exit rule), and the exit rule alone manufactures most of what the memo attributes to the entry.

Mechanism, concretely:

- An asymmetric first-touch bracket with a **tight target (+2%) and a wide stop (-4%)** mechanically produces a high win rate on *any* entry, including random ones. For a typical large-cap with ~1.5–2% daily vol, the probability of touching +2% before -4% within 20 sessions is well above 50% even for a zero-drift process — 60%+ win rates are exactly what this bracket produces on noise. So "61% vs placebo 52%" is comparing a bracket exit's win rate to a fixed-horizon exit's win rate. It's meaningless; the 9-point gap is largely an exit artifact, not entry information.
- The mean/trade comparison is similarly contaminated: a first-touch bracket harvests intraday volatility and truncates the return distribution differently than a day-5 close, so the two means are draws from different payoff functionals. In an upward-drifting 2018–2025 large-cap universe, the bracket's early profit-taking plus long stop distance shifts the mean in ways that have nothing to do with RSI.
- The memo even acknowledges the mismatch ("chosen to approximate the typical holding period") — matching the *average* hold does not match the *payoff shape*, which is what determines mean and win rate.

**Fix:** run the 500 random-entry baskets through the **identical exit engine** (+2%/-4%/20d first-touch, same fill and cost assumptions). Only then does "strategy > placebo p99" speak to entry selection information. Until this is done, the conclusion "the entry signal carries real selection information … p < 1%" is unsupported and the certification must be withdrawn.

### Defect 2 (material): the placebo null ignores the temporal clustering of signal entries, so the p-value is overstated

RSI(3) < 20 entries are not spread uniformly in time — they cluster heavily in market-wide selloff episodes (many names trigger on the same few dates). The 1,904 strategy trades are therefore highly cross-correlated, and the effective sample size is far below 1,904. The placebo baskets ("random entries, same names, same period, same number of trades per name") spread entries roughly uniformly across 2018–2025, giving each basket's mean a much **smaller variance** than the strategy's mean has under the null. A too-narrow null distribution makes the p99 threshold (+0.24%) artificially tight, so clearing it does **not** imply <1% probability under a correct null.

**Fix:** make the placebo match the strategy's entry-date structure — e.g., sample placebo entry dates from the strategy's actual signal-date distribution (permute names across signal dates), or use a block bootstrap that preserves the clustering. Combined with Defect 1's fix, this is the minimum for the significance claim.

### Defect 3 (material pending verification): "intraday touch, next-tick fill" with no stated resolution of same-bar target/stop ambiguity

If the backtest runs on daily OHLC bars (nothing in the memo says intraday data was used), then on a bar whose range touches **both** +2% and -4%, the touch order is unknowable. The standard optimistic bug — assume the target hit first — systematically inflates mean/trade and win rate on exactly the high-volatility bars where the signal fires. "Next-tick fill" on an intraday touch also assumes zero slippage through the level, which is optimistic for stop fills (gaps through -4% fill worse than -4%).

**Fix:** state the data granularity; if daily bars, resolve same-bar ambiguity conservatively (stop first), and fill gap-throughs at the open, not at the stop level. If results survive, this becomes a non-issue; as written, it cannot be verified and biases upward.

### Non-material comments (clearly labelled as such)

- Costs at 30bp/side "identical in both arms" is fine per-trade, but note per-day cost drag differs slightly given different holds; immaterial here.
- p99 from 500 baskets rests on ~5 tail observations — noisy but usable; 2,000+ baskets would be cheap and better.
- The placebo does not condition on the >100-DMA filter; that's acceptable only if the memo claims the *combined* entry (filter + RSI) carries information, but it means the RSI dip specifically is not what's being certified. Worth clarifying, not a validity defect on its own.

### Numbered list of claimed material defects

1. **Exit-engine mismatch between arms** — strategy uses an asymmetric +2%/-4%/20d first-touch bracket, placebo uses a fixed day-5 close; the bracket alone mechanically generates ~60% win rates and a different mean, so the "beats placebo p99" result does not test the entry signal. Fix: identical exit engine in the placebo.
2. **Null distribution ignores entry-date clustering** — RSI-dip trades cluster in selloffs (correlated, low effective N), while placebo entries are time-uniform, shrinking the null's variance and inflating significance. Fix: placebo entries must preserve the signal's temporal clustering (permute names across actual signal dates or block bootstrap).
3. **Unverified same-bar touch resolution and fill assumptions** — "intraday touch, next-tick fill" on (apparently) daily bars, with no rule for bars touching both target and stop and no gap-through slippage; the default optimistic resolution inflates both mean and win rate. Fix: conservative same-bar resolution and gap-aware stop fills, or demonstrate intraday data was used.

result: T20 memo's validation is invalid as written — the placebo uses a different exit engine than the strategy, its null ignores signal-date clustering, and same-bar target/stop resolution is unverified, so the "<1% under the null" certification is unsupported.

======================================================================
# END OF FILE — all 8 MG tasks and all 20 T tasks completed (claude-fable-5, fresh context per task, no tools, answers verbatim).
