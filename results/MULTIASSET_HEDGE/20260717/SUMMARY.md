# Multi-asset portfolio + vol-timed NIFTY tail hedge — 2026-07-17 (DESK-20)
Spec: 40% midcap / 35% bond / 30% gold (**summed 105% → normalized to 100%**: 38.1/33.3/28.6), monthly rebalance; + NIFTY **10% OTM put, 6M expiry, rolled every 3M**, sized to **25% of portfolio notional**, **rebought only when India VIX < 30**. Real data (Nifty Midcap 150, GOLDBEES, NIFTY option bhavcopy, India VIX) + **daily mark-to-market** of the put. Window 2020-02→2026-07 (~6.4yr). Bond 7.5%/yr assumed. Corpus ₹10L.

## RESULT
| Version | CAGR | Vol | Sharpe | Sortino | MaxDD |
|---|---|---|---|---|---|
| Core (no put) | 17.4% | 9.2% | 1.13 | 1.29 | −16.9% |
| Core + put, always | 17.2% | 8.6% | 1.18 | 1.41 | −11.2% |
| **Core + put, IV<30 (spec)** | **17.3%** | **8.6%** | **1.18** | **1.42** | **−11.1%** |
20 of 21 rolls bought; 1 skipped (2020-05-04, VIX≥30 post-COVID). `put_rolls_ivgate.csv`, `metrics.json`.

## FINDINGS
1. **The 3-asset core is the star, not the options.** 17.4% CAGR at just 9.2% vol (Sharpe 1.13) is genuine diversification — midcap for return, bond for ballast, gold for crisis-hedge + its own 2020-26 bull. This is far better risk-adjusted than any single-asset + overlay tested earlier this session.
2. **The put overlay is a RARE genuinely-additive hedge** — the first this session that improved risk-adjusted return at ~zero cost. It cut MaxDD −16.9%→−11.1% (−34%), vol 9.2→8.6, and RAISED Sharpe 1.13→1.18 / Sortino 1.29→1.42, for −0.1pp CAGR. Why it works where earlier put tests bled: it's small (25% notional), cheap (10% OTM), rolled (never held into terminal decay), and sits on an already-diversified book — so the COVID payoff + 2024/25 cushioning outweighed the modest premium.
3. **The IV<30 gate barely mattered here** — always-rebuy vs IV<30 are near-identical (Sharpe 1.18 both). VIX was <30 on almost every roll date 2020-26, so the filter bound only once (May-2020). It's a sensible cost-control rule that would matter more in a sustained high-vol regime with more roll days above 30 — but in this sample it neither helped nor hurt materially. The one skip (buying protection right after the COVID spike, when puts were dearest) was marginally smart.

## HONEST CAVEATS
- **Gold's exceptional 2020-26 run (~2x) flatters the 17.4% base heavily** — 30% in gold during its best decade is a large, non-repeatable tailwind. Do not extrapolate the CAGR; the *structure* (low-vol diversification + cheap partial hedge) is the transferable lesson, not the level.
- **Executability: the 25%-notional put is a FRACTIONAL lot at this corpus** (~0.28 lots on ₹10L). You need ~₹3.5-4M+ corpus for the 25%-notional NIFTY put to round to ≥1 whole lot; below that the overlay isn't literally tradeable as specified.
- 6M 10%-OTM NIFTY puts are **thin** (far wing) — fill realism for the protection leg is weaker than the near-month tests.
- Bond 7.5% assumed (your earlier 10% would add ~0.8pp CAGR). Midcap = price index (div ~+1.3%/yr ignored, understates the equity sleeve). n=20 rolls, one crash (COVID) → put value is regime-dependent as always.

## VERDICT
Best-designed structure of the session: a well-diversified low-vol core with a cheap, partial, rolled tail hedge that genuinely lifts Sharpe/Sortino and cuts drawdown at near-zero return cost. Keep the put; the IV<30 gate is fine to keep (harmless, occasionally smart) but isn't doing much work. Real-money version needs a ≥₹3.5M corpus for whole-lot sizing, and the headline return is gold-tailwind-flattered.

## ADDENDUM — annual rebalance + 3M MOMENTUM ROTATION (60/40/0) with RSI overbought filter (`metrics_momentum.json`)
Rotation: every quarter rank mid/bond/gold by trailing-3M return → 60% top / 40% 2nd / 0% laggard; a RISKY asset (mid/gold) with 14d RSI>threshold is benched (bond exempt — monotone safe haven); same IV<30 put.
| Scheme (+ put) | CAGR | Vol | Sharpe | Sortino | MaxDD |
|---|---|---|---|---|---|
| Fixed 40/35/30 monthly (base) | 17.3% | 8.6% | 1.18 | 1.42 | **−11.1%** |
| Fixed 40/35/30 **annual** rebal | 17.2% | 8.8% | 1.15 | 1.38 | −11.5% |
| Momentum RSI>70 | 20.8% | 11.4% | 1.18 | 1.31 | −14.9% |
| **Momentum RSI>80** | **23.2%** | 11.6% | **1.34** | 1.46 | −14.9% |
Findings: (1) **Annual ≈ monthly rebalance** — negligible (−0.3 Sharpe pts). (2) **Momentum rotation lifts RETURN & Sharpe but WORSENS drawdown** — concentrating 60/40 into 2 assets (0% laggard) captured the midcap+gold trends (+6pp CAGR at RSI80) but is less diversified → vol 11.6% vs 8.6%, MDD −14.9% vs −11.1%. Classic return-for-drawdown trade. (3) **The tight RSI>70 filter HURT** (20.8% vs 23.4% RSI80) — it benched winners too early and fought the very momentum it rides; RSI>80 (only true blow-off extension) preserved the trend and was best. Lesson: an overbought filter on a momentum sleeve should be loose or absent. (4) **The put is REDUNDANT on the momentum version** (Sharpe 1.35→1.34, MDD unchanged) — the rotation already flees to bond in risk-off quarters, so it self-hedges; put and rotation are substitutes, not complements. Keep the put on the FIXED book, drop it on the momentum book.
**Objective split:** least drawdown → **Fixed 40/35/30 + put** (−11.1%, Sharpe 1.18). Max return/Sharpe → **Momentum 60/40/0 RSI>80** (23.2%, Sharpe 1.34, MDD −14.9%, put optional). Same caveats: gold 2020-26 bull flatters ALL (momentum most, since it can go 60% gold in the run); ~26 quarterly rotations, one crash; fractional-lot put needs ≥₹3.5M corpus.
