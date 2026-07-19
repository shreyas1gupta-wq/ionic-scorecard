# 04 — Framework: 1-MONTH lens (systematic / quant-heavy)

**Character:** near-term, market-microstructure + catalyst + positioning driven. Fundamentals are ~static over a month, so they act as a **gate/penalty**, not a driver. This is the most systematic, most quant, fastest-changing lens. Updated **month-end**.

**Question it answers (per brief Q7):** *"If I buy at this month-end and sell next month-end, what is the probability and distribution of my return, and how confident am I?"* — e.g. buy 30-May, sell 30-Jun → `p_up`, `e_return`, `return_dist`, `win_rate`.

**Universe:** NIFTY 750. Gated by liquidity (min ADV / max impact cost) — illiquid names get widened uncertainty and capped size, not a fake fill (firm landmine 7b/D-031: no-fill = drop).

## Factor library (theme → factors)
### Momentum (high weight)
- Multi-lookback price momentum: 1M, 3M, 6M returns with the **most-recent-month skip** (avoid short-term reversal contamination).
- Relative strength vs sector index and vs Nifty (12-1 and 3-1).
- Distance from 20/50 DMA; MA alignment/slope.
- 52-week-high proximity (anchoring/breakout tendency).

### Sentiment / Flow / Positioning (high weight)
- Volume & **delivery %** trend (NSE), OBV, volume-price divergence.
- **F&O positioning** (where listed): OI build-up (long/short), futures basis/premium, **PCR**, rollover %, change in OI vs price (long buildup / short covering classification).
- Bulk/block deal flow, FII/DII proxy at stock level where available.
- India-VIX / stock IV rank (options-implied fear).

### Catalyst (high weight)
- **Earnings-date proximity** (pre-results drift + post-earnings-announcement drift window).
- Estimate-revision momentum (analyst upgrades/downgrades last 4–8 weeks) — the fastest fundamental signal that works at 1M.
- Index rebalancing (inclusion/exclusion flows), F&O ban/inclusion, ex-dividend/bonus/split, corporate actions.
- Results-season seasonality; sector rotation phase.

### Mean-reversion / exhaustion (high weight, opposite sign to momentum in extremes)
- RSI(14) extremes, Bollinger %B, distance from anchored VWAP, gap statistics.
- Overbought/oversold vs own history; short-term reversal (last-week return, sign-flipped).
- Volatility state (ATR percentile) — high vol → widen return_dist, reduce conviction magnitude.

### Value / Quality / Growth / Forensic (low weight — GATE only at 1M)
- Not drivers over a month, but a **hard forensic red flag or an extreme-overvaluation + downtrend combination caps the score** (you don't want to be long a fraud into a catalyst).

## Scoring specifics (1M)
- Weight prior (see `02`): Momentum 0.30, Sentiment/Flow 0.25, Catalyst 0.25, Mean-rev 0.10 (folded into Momentum theme with sign logic), Value/Quality/Growth 0.05, Forensic gate.
- **Regime switch that matters most here:** trend vs chop. In a strong uptrend, momentum weight ↑ and mean-reversion weight ↓; in chop/high-vol, mean-reversion weight ↑ and momentum ↓. The regime classifier flips these.
- Calibrate score→P on **monthly forward returns**, regime-conditioned. Win-rate = historical hit-rate of the score bucket over 1M.
- Output the explicit buy-date/sell-date framing with the distribution.

## Thesis paragraph style (1M)
Systematic and terse: *setup* (e.g. "3M RS top-decile, long OI buildup, cleared 52w base on above-avg delivery"), *catalyst* (e.g. "results 12-Jun, 3 upward revisions"), *invalidation* (e.g. "close below ₹X / 50DMA voids"), and the probabilistic read. No narrative.

## Exit / review discipline (1M)
- Re-scored every month-end; a flip below a threshold → exit signal.
- Intra-month: hard technical invalidation level set at entry (stop/review), event-risk flag if an unscheduled catalyst hits.
- Trailing logic optional (ATR-based) for the tactical variant.

## Known 1M landmines (from firm docs — enforce)
- Pre-open auction bug (use bars ≥09:15), HF timezone bug (convert to IST date), circuit/volume no-fill, Angel ONE_DAY 00:00 stamp. Import `04_RND_LAB/lib/guards.py`.
- Don't confuse expiry-day option settle with option price; gate F&O signals on CONTRACTS>0 and liquid expiry.
