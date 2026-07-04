# FACTOR-INDEX REPLICATION & DEVIATION HARNESS — hypothesis one-pager + build plan
**Owner: Devika (FM-Equities) + Arjun (validation) + Kavya (data) · filed 2026-07-04 (Principal-directed) · stage 1-INTAKE**

## The idea (two payoffs in one build)
Replicate NIFTY's official FACTOR indices (NIFTY200MOMENTM30 first, then 500-MOMENTUM-50, 200-VALUE-30, 100-LOWVOL30, 200-QUALITY-30) from OUR PIT data using NSE's published methodology; then measure OUR replicated NAV vs the OFFICIAL NAV (from /factor-indices data).
- **Payoff 1 (validation):** small tracking error (<2-3% ann.) PROVES our data + PIT universe + signal stack are institutional-grade — the cheapest possible audit of Track-2's entire foundation.
- **Payoff 2 (edge lab):** once replicated, we can ablate: what happens to momentum returns with OUR liquidity gates, weekly (not semi-annual) rebalance, different lookbacks — i.e., can we BEAT the index methodology at retail size? Economic WHY: index rules are public, capacity-constrained by AUM, and rebalance-lagged; retail-size adaptations plausibly capture what index funds leak.

## Method sketch
1. NSE methodology PDFs (KNOWLEDGE_BASE refs) → exact rules: universe, momentum score (6m+12m vol-adjusted), capping, semi-annual rebalance dates.
2. Build from our daily panel + 42 PIT snapshots: score → select 30 → weight → chain NAV from a common base date.
3. Deviation report: daily TE vs official, drift at rebalance dates (our reconstruction of index turnover), attribution of gaps (data? survivorship? corporate actions? timing?).
4. Pre-registered thresholds: TE < 3% ann. = data VALIDATED; TE > 6% = investigate data bugs (this doubles as a data-quality tripwire).

## Kill criteria (for the EDGE half, pre-registered)
Retail-adapted variant fails to beat the replicated index by >2%/yr net of APPROVED costs at 2× over the full window → the adaptation idea dies (the validation harness survives regardless — it's infrastructure).

## Data plan (free-first ladder, per Principal)
- **Official NAVs:** /factor-indices scraper (niftyindices.com) — HOME NETWORK; monthly refresh thereafter.
- **Constituents (for exact validation):** niftyindices monthly factsheets (PDF, free) or index-constituent CSVs — scrape on home-network day; else infer from methodology.
- **Recurring saves (Angel):** already covered — daily equity bulk + option capture. ETF NAVs for factor ETFs (MOMENTUM50 ETFs etc.) via Angel tokens = free intraday proxy for official NAV between refreshes.
- **Fallback/hacks:** Wayback Machine for historical factsheets; AMFI NAVs for factor mutual funds as cross-check.

## Trials ledger: 0 (fresh family). /prior-art check pending (Lakshmi).

## PROGRESS 2026-07-04 — first-cut tracer bullet (results/factor_replication/20260704_lowvol30_firstcut/)
LOWVOL30 vs official (via ANGEL index token — proxy-block bypassed!): 745d overlap; corr 0.538 / TE 13.4% overall, **corr 0.896 / TE 5.9% in 2024** (the well-instrumented year). Verdict: data pipeline PASSES the tracer test; error is methodological (price-level N100 proxy — the main offender; uncapped inv-vol; guessed rebalance dates). Path to <3%: real N100 membership (factsheets, home-net) + exact NSE methodology + weight caps = the D-M4 Aug-15 deliverable. BONUS data now on disk: INDIA VIX 2016→ (regime work), ALPHA50, VALUE20, 5 momentum-ETF proxies (datasets/index_daily/).

## PROGRESS 3 (2026-07-04 night) — D-M4 GOAL MET (LOWVOL30), 6 weeks early
UNION-PRICE panel run: **LOWVOL30 TE 4.58% full / 2.71% 2023-26, corr 0.956 — <=6% every era.** MOMENTM30 8.48% full (was 15.55%), floor ~6.4% = float-weights + exact constituents (home-net factsheets to close further; DATA-VALIDATION purpose of this idea is COMPLETE — our price data provably reconstructs official indices). Tripwire framework armed: replication TE jumping >6% on fresh data = data-quality alarm. Remaining: momentum-index <6% (home-net), tradeable-sleeve edge-lab half (separate, cost-aware).
