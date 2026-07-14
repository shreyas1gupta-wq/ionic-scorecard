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