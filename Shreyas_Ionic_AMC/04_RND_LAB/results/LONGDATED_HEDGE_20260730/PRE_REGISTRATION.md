# PRE-REGISTRATION — Long-dated portfolio hedge overlay (Kabir Anand, 2026-07-30)
Written BEFORE the backtest runs (queued as `BACKTEST_QUEUE_20260730/queue/110_longdated_hedge.py`).
Nothing below is tuned after seeing results.

## Objective (Principal framing — do not violate)
This is **tail protection for the whole book**, not a standalone alpha search. Judged on what it
does to BOOK-level maxDD/CVaR for an honestly-measured cost, not on the hedge's own standalone P&L
(a "hedge" that makes money standalone is usually a naked short position wearing a costume — this
is exactly the H_putratio_1x2 lesson from 2026-07-08, restated in my charter's Lessons Learned).

## Data — upgrade over the 2026-07-08 study
The prior HEDGING_ANALYSIS_20260708 work BS-priced every option (no real chains existed then). This
run uses **REAL traded NIFTY OPTIDX prices**, 2011-2026, from
`Shreyas_Ionic_AMC/05_DATA_OFFICE/data/fo_bhavcopy_hist/fo_idx_{2011..2026}.parquet`.
- **Gate: CONTRACTS>0** on every option row used, always (41% of rows in this archive are
  listed-but-untraded model prices — CLAUDE.md landmine #9 / SHARED_CONTEXT gate).
- **Underlying reference S(t): near-month NIFTY FUTIDX close** (per day, the FUTIDX row with the
  max CONTRACTS that day — this is the liquid near-month contract), continuous 2011-2026, ONE
  consistent source for both strike selection and the 16-year crisis test. [DATA]
  **Caveat [INFERENCE]:** this is a futures proxy, not official spot, pre-2016 (no verified long-history
  spot series was at hand for that stretch outside this archive). Futures-vs-spot basis on NIFTY is
  typically small (~0.1-0.5% turning to near-zero at expiry) and immaterial to the return/drawdown-based
  conclusions here, but it is a proxy, not the settlement price options actually cash-settle against.
  For the real STACKED_BOOK 2022-2025 test I cross-check against `datasets/index_daily/nifty50.parquet`
  (official spot, 2016+) to confirm the proxy tracks spot closely in that window.
- **Never read an expiry-day option SETTLE_PR as a price** — the option universe cache is built by
  DROPPING every row where `TIMESTAMP >= EXPIRY_DT` for OPTIDX, i.e. the expiry date itself never
  enters the option-price cache at all. Any leg still open when its DTE gets small is valued by
  forward-filling its last real traded CLOSE (cap: 10 trading days of staleness), and once that
  staleness cap is breached (or the position must be valued at/after its own expiry), the fallback is
  **intrinsic value computed from S(t)** (the uncontaminated futures series) — never the option's own
  SETTLE_PR. This is the literal instruction in SHARED_CONTEXT gate #2, applied mechanically.
- Measured (see PROGRESS notes) that real traded (CONTRACTS>0) NIFTY OPTIDX contracts exist every
  single sampled year (2011,2013,2015,2018,2020,2022,2024,2026) out to 200-400+ DTE, with 5-9 distinct
  expiries per year in both the 100-200 and 200-400 DTE bands — **so 3/6/12-month tenors are
  genuinely testable at real, gated liquidity**, contrary to an earlier note in this session
  (PROGRESS_OPTION_BUYING_20260729.md "HARD DATA LIMIT") that examined a DIFFERENT dataset (the 1-min
  weekly-expiry option-chain tree, which only holds the last ~10-20 days of each contract's life by
  construction). The two data sources are not in conflict: one is a full daily archive of an
  option's ENTIRE life, the other is a 1-min tree that was truncated to near-expiry only.

## Net-hedge-positive discipline — HARD, structural, applied a priori
Only structures that are net-neutral or net-hedge-positive enter the grid at all. **Never a
net-short-tail structure, never tested "to see if it's good" — the charter rejects these on
structural grounds regardless of in-sample stats** (2026-07-08 finding: `H_putratio_1x2_95_85`
deepened the COVID-India drawdown to -50% vs -37% unhedged; its high Sortino was a small-n/near-zero-
downside-deviation artifact, not real protection). Structures tested:
1. **Protective put** (long only, net-hedge-positive): 5% / 10% / 15% OTM.
2. **Put spread 1x1** (long 10% OTM put / short 20% OTM put, same quantity): net-NEUTRAL per charter
   (1:1 debit spread explicitly allowed) — caps protection below 20% OTM in exchange for cutting cost.
3. **Collar 1x1** (long 10% OTM put / short 5% OTM call, same quantity): net-NEUTRAL — caps upside to
   fund the put.
4. **Ladder**: equal-thirds blend of 3m/6m/12m protective-10%-put, each rolled on its own native
   schedule — tests whether staggering tenors protects better per rupee than one tenor.
Explicitly NOT built, not even as a "let's see": any 1x2/2x1/3x1 ratio or backspread that sells more
premium than it buys, any naked short leg. This is a structural gate, not a result.

## Tenor x roll-cadence grid
Tenors: 3m / 6m / 12m (target ~91/182/365 calendar days to the chosen expiry; **achieved DTE is
reported**, since real-market expiry listings won't always land exactly on the target).
Roll cadence tested per tenor: 1-month forced roll, 3-month forced roll, and "native" (hold to
within ~10 days of the contract's own expiry, then replace) — native equals the 3m/6m/12m roll for
the matching tenor, so unique (tenor,roll) cells = 8: {3m:[1m,3m], 6m:[1m,3m,6m], 12m:[1m,3m,12m]}.

## Cost model (DRAFT — extends approved COST_STANDARDS D-021 to DTE bands it does not explicitly
cover; tagged [INFERENCE], not itself Principal-approved)
COST_STANDARDS gives: options liquid-ATM-index slippage floor 0.25% premium one-way; far-OTM/far-month
illiquid 1-2% premium one-way; STT 0.1% premium sell-side; exchange ~0.035%; GST 18% on
(brokerage+exchange). For legs beyond the near-dated band COST_STANDARDS was calibrated for, I
interpolate by DTE-at-transaction:
| DTE at transaction | one-way slippage (of premium) |
|---|---|
| <=20 | 0.25% (COST_STANDARDS liquid-ATM floor, verbatim) |
| 20-100 | 0.60% (interpolated) |
| >100 | 1.50% (COST_STANDARDS "far month illiquid" band, mid-point of 1-2%) |
Plus a flat ~0.15% of premium per transaction for STT/exchange/GST/brokerage (small vs slippage at
these premium levels). Round-trip cost on a leg = one-way slippage x2 (entry+exit) + 0.15% x2.
**This is a judgment extension, disclosed as such — it is the tightest defensible reading of an
approved doc, not a new standard.**

## Margin note (not deeply modeled into return metrics — this is a protection-cost lens, not a
leveraged-return lens)
Per the session's margin ruling: hedged/defined-risk structures (put spread, collar) = 5% notional;
an outright long put has no margin (premium paid in full, no leverage). This matters only for how
much of the book's collateral gets pledged, not for the hedge's own risk-adjusted return — reported
as one line, not compounded into CAGR.

## Two book contexts tested (task instruction: "state which exposure you are hedging")
1. **Full NIFTY-long proxy, 2011-2026** (i.e., a book that is simply long the index) — this is the
   vehicle for the **decisive crisis test** (needs the full 16-year span to reach 2011-12, 2013,
   2015-16, 2018, 2020, 2022, 2024-09) and for the full-sample net-hedge-positive verdict.
2. **STACKED_BOOK_20260711 (`book_daily_pnl.csv`, 4 real sleeves, Rs 1cr base, 2022-2025)** — the
   REAL current book (midsmall equity rotation + breakout equity swing + S1-F short-straddle +
   B1b futures-flow). Its NIFTY beta is MEASURED (OLS of daily book return on daily NIFTY return),
   not assumed, and the hedge notional is sized to that measured beta x book NAV — because a
   market-neutral or short-tilted sleeve (the live liquidity-sweep delta-1 candidate, 54.5%
   short-biased, is flagged in the brief as needing LESS hedging) should not be over-hedged by a
   flat "hedge the whole NAV" assumption. This window only contains 2 of the 7 crises (2022 hikes,
   2024-09 correction) — the other 5 are visible only in test #1.

## Crisis windows (search windows pre-registered here; EXACT peak/trough dates and drawdown
magnitude are computed by the script from S(t), never asserted from memory)
| Event | Search window | Rationale |
|---|---|---|
| 2011-12 Euro crisis | 2011-07-01 to 2012-01-31 | US downgrade Aug-2011, Eurozone debt crisis |
| 2013 taper tantrum | 2013-05-01 to 2013-09-15 | Bernanke taper signal May-2013, INR/EM crisis Aug-2013 |
| 2015-16 correction | 2015-03-01 to 2016-02-29 | China deval Aug-2015, oil crash, global growth scare |
| 2018 IL&FS | 2018-08-01 to 2018-10-31 | IL&FS default Sep-2018, NBFC liquidity freeze |
| 2020 COVID | 2020-01-01 to 2020-04-30 | Crash Feb20-Mar23 2020 |
| 2022 rate hikes | 2022-01-01 to 2022-06-30 | Fed hiking cycle + Ukraine war Feb-2022 |
| 2024-09 correction | 2024-09-01 to 2024-12-31 | India-specific correction from Sep-2024 ATH |
For each event, per overlay: **cost = cumulative hedge P&L over the 252 trading days preceding the
event's computed peak date** (should be negative = premium bleed); **payoff = cumulative hedge P&L
from computed peak to computed trough**; **ratio = payoff / |preceding-year cost|**. Report the
ratio per event per overlay — this is the number the CIO judges the hedge on, not a Sharpe.

## What "success" means here (no single numeric kill gate — this is a risk judgment, not an alpha
claim; the hard gate is structural, already applied above)
- Report gross cost (%/yr), book maxDD before/after, book CVaR-5% before/after, and the per-crisis
  payoff/bleed ratio for EVERY structure honestly, including cases where the answer is "not worth it."
- Cross-check every candidate's Sortino/Sharpe against its RAW maxDD and COVID/2020 payoff per the
  Lessons Learned entry — a high risk-adjusted ratio from a near-zero downside deviation cell is a
  red flag, not a green one.
- A structure is recommendable only if it is net-hedge-positive by construction (structural gate,
  already enforced) AND its crisis payoff/bleed ratio and book-maxDD improvement are large enough
  that a reasonable CIO would pay the measured cost — that judgment is stated explicitly in the
  memo, with numbers, not hidden inside a single score.

## Known limitations, disclosed up front
- Daily granularity: no intraday stops/precision; close-to-close marks only (per SHARED_CONTEXT gate 3).
- Futures-proxy underlying pre-2016 (basis risk vs true spot, believed small, not independently verified
  against a spot series for that stretch).
- Far-dated/far-OTM legs are real-traded but THIN (few prints across a contract's life) — staleness-capped
  forward-fill is used, and the % of valuations falling back to intrinsic is reported per config as a
  data-quality metric, not hidden.
- Executability: NIFTY index options are the correct, liquid, tradeable vehicle for this hedge (unlike
  single-stock/small-cap options, which are largely absent/illiquid in India) — no beta/basis-risk
  translation is needed here since the book's underlying equity exposure and the hedge instrument are
  both NIFTY-linked in the STACKED_BOOK test; for a broader midcap/smallcap book this would need to be
  flagged as basis risk, but that is not the book under test here.
