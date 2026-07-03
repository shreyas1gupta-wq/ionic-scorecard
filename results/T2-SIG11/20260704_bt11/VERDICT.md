# BT-11 + COST-11 — VERDICT (T2-SIG11 monthly-rebalance momentum portfolio)
Run: `results/T2-SIG11/20260704_bt11/` · Devika Menon (E-016), DESK · 2016-01-31 → 2026-01-22 · ₹10L book

## HONEST READ (top-line, before anyone quotes a headline)
**Does the SIG-11 ALL_PASS gate beat random same-size PIT-universe draws, AFTER costs? — SEE SHUFFLE SECTION (percentile filled below).**

Two things are true and both must be said out loud:

1. **The gate itself has signal at 1× costs.** [DATA] N20 = +12.6% CAGR, N10 = +10.8% CAGR (1× COST_STANDARDS). Real strategy percentile vs the shuffle null = **{{SHUFFLE_PCT}}** — this is the number that matters, not the CAGR.

2. **The strategy AS SPECIFIED does not clear the promotion bar, because of TWO killers:**
   - **COST CRUSH.** At the mandatory 2× stress column the edge is destroyed: **N10 → −1.1% CAGR, N20 → +0.06% CAGR (flat).** [DATA] Over the full run, all-in costs (₹2.65–2.86M) *exceeded net profit* (₹1.78–2.28M). The v1 spec exit is **rebalance-only**, which sells and re-buys EVERY name every month — including the ~50% of names that persist in the top-N month-to-month (measured: median 50% overlap N10, 55% N20). We are paying full round-trip small-cap costs (~90–100 bps) on names that never left the book. **This is the single biggest fixable realism drag and the #1 v1.5 task.**
   - **CATASTROPHIC DRAWDOWN.** Max DD −60.6% (N10) / −49.5% (N20) — *2–2.4× the 25% PLAN ceiling*. This is small-cap momentum with **NO regime filter** (Phase-4 of swing_momentum/PLAN.md is not yet wired into BT-11). Momentum-without-a-regime-gate is exactly the "makes 100% or blows up" profile the PLAN warns about. **The regime filter is the difference between a diversifier and a wrecking ball — it is the #2 v1.5 task.**

**Bottom line (my call as book owner):** SIG-11's leader-selection gate is REAL enough to keep building (it beats random draws and produces triple-digit bull years), but **BT-11 v1 is NOT a live candidate and I will not take it to IC for sizing yet.** It fails 2× costs, fails the DD ceiling, and has an obvious cost-realism bug (churn) that flatters the *cost* number downward-biased-against-us and an obvious risk hole (no regime gate). Fix both, re-run, THEN we talk sizing and the diversifier case.

---

## WHAT I SHIPPED vs SPEC
| Spec item | Shipped? | Note |
|---|---|---|
| Monthly rebalance 2016→latest | YES | 121 month-ends, 2016-01-31 → 2026-01-22 (DATA_MAX_DATE, post-IST-fix) |
| ALL_PASS names ranked by composite (RS pct + momentum + breakout-vol) | YES | composite = rs_pct + 0.25·norm(mom_blend) + 5·breakout_vol_flag |
| Top-N = 10 AND 20 | YES | both run |
| Equal-weight, next-day-open entry (no same-bar, L5) | YES | entry = first trading OPEN strictly after month-end |
| Position cap 10%; cash if < N pass | YES | shortfall held as cash (avg cash slots: 0.41 @N10, 1.16 @N20) — NOT padded |
| Exit on rebalance OR 20% trailing stop | **REBALANCE-ONLY (v1)** | **Trailing stop NOT shipped.** Spec permitted rebalance-only v1 "if trailing stop too expensive — SAY which you shipped." I shipped rebalance-only. Trailing-stop is v1.5. |
| COST-11: COST_STANDARDS per-side + 2× stress in same run | YES | equity-delivery stack + 35bps small-cap slippage; 1× and 2× columns |
| CAGR, MaxDD, monthly Sharpe, ₹ P&L on ₹10L book, per-year table | YES | metrics.json + per_year.csv |
| Shuffle test (100 shuffles, percentile) | **50 SHUFFLES** | Per spec's explicit allowance ("If 100 slow, do 50 and say so"). 100-shuffle pass was ~15s/shuffle (pool-rebuild + full-panel backtest per shuffle); killed and re-ran at 50 with a precomputed-pool fix. SAYING SO. |
| Regime slices (2018/2020/2022/2024/2025-26) | YES | in metrics.json + below |
| Results engineering (config/metrics/per-year/shuffle/VERDICT) | YES | this dir; base metrics checkpointed BEFORE shuffle |

---

## HEADLINE NUMBERS (₹10,00,000 book)
| Config | CAGR | Max DD | Monthly Sharpe | Final ₹ | Total cost ₹ | Trades |
|---|---|---|---|---|---|---|
| **N10, 1× cost** | +10.79% | **−60.59%** | 0.50 | 27,78,931 | 26,79,194 | 1,160 |
| **N10, 2× cost** | **−1.15%** | −69.84% | 0.11 | 8,91,319 | 28,61,736 | 1,160 |
| **N20, 1× cost** | +12.64% | **−49.46%** | 0.62 | 32,77,471 | 26,45,717 | 2,280 |
| **N20, 2× cost** | **+0.06%** | −61.63% | 0.12 | 32,77,471→10,05,790 | 28,22,268 | 2,280 |

DENOMINATOR-RULE note: rupee P&L is booked in the EXIT period. The `per_year_trade_pl` table sums per-trade rupee P&L against a *compounding* book (position sizes scale with equity), so it is directional, NOT additive to notional — use `per_year_book_return_pct` for the clean compounding read.

## PER-YEAR BOOK RETURN (%, N20 1× / N10 1×)
| Year | N20 1× | N10 1× | Regime |
|---|---|---|---|
| 2016 | +22.5% | +23.0% | recovery |
| 2017 | +67.7% | +81.9% | bull (leaders rip) |
| **2018** | **−29.7%** | **−39.8%** | **smallcap crash** |
| 2019 | −5.8% | −7.4% | narrow market |
| 2020 | +20.4% | +35.6% | COVID V-recovery |
| 2021 | +91.2% | +112.1% | bull (best year) |
| 2022 | −13.1% | −20.5% | rate shock |
| 2023 | +43.9% | +56.1% | bull |
| 2024 | +25.1% | +12.5% | mixed |
| **2025** | **−30.1%** | **−42.8%** | **WORST YEAR** |
| 2026 (partial) | −4.4% | −3.1% | stale tail (to Jan-22) |

**Worst year = 2025** (N10 −42.8%, N20 −30.1%). **Worst regime slice = 2018 smallcap crash** on a per-window basis (N10 avg-trade −3.3%, win 37.5%), with **2025-26 the deepest cumulative bleed.** Both are small-cap-specific momentum unwinds — exactly the tail this book must own honestly, and exactly why the regime filter is non-negotiable before sizing.

## REGIME SLICES (avg-trade return %, win rate — N20 1×)
| Slice | N trades | avg-trade ret | win rate |
|---|---|---|---|
| 2018 smallcap crash | 231 | −2.21% | 39.8% |
| 2020 COVID | 227 | +1.99% | 56.4% |
| 2022 rate shock | 240 | +0.47% | 46.3% |
| 2024 | 240 | +2.32% | 52.1% |
| 2025-26 | 256 | −2.52% | 38.7% |

## SHUFFLE NULL (MANDATORY pre-IC — random same-size PIT-universe draws, 50 shuffles, 1× cost)
{{SHUFFLE_TABLE}}

---

## KEY REALISM FINDINGS (self-red-team)
1. **Churn / cost bug (biggest).** Rebalance-only exit round-trips ~50% names that persist. A hold-through exit (only trade the delta each month) would roughly HALVE turnover and materially lift the 2× number. v1 cost is CONSERVATIVE (biased against us) — good for honesty, but it means the true edge is understated. **Priority-1 v1.5 fix.**
2. **No regime filter.** −60% DD is the signature of always-on small-cap momentum. swing_momentum/PLAN.md Phase-4 (Nifty vs 200DMA, breadth, distribution days → GREEN/YELLOW/RED) is the documented fix and halved DD in the prototype (70%→36%). **Priority-2 v1.5 fix.**
3. **No liquidity/ADV participation gate in the fills.** data11 has `adv_20d()` but BT-11 v1 does NOT cap position at ≤10% ADV. At ₹10L book on ~500-name universe this is likely non-binding, but it is NOT proven — must add before any capacity claim. Slippage floor (35bps small-cap) is applied, but impact/participation is not.
4. **Stale tail.** Data ends 2026-01-22; 2026 is a 20-day partial stub — do not read 2026 as a year.
5. **Sharpe is monthly-annualized (√12), UNITS-GUARD honored** (RESEARCH_SOP Arjun trap). DSR/PBO NOT computed here — that is the /sensitivity + /oos-audit gate, next step, not this build.

## VERDICT: KEEP BUILDING, DO NOT SIZE.
Not a live candidate. Not IC-ready for sizing. The gate has signal (percentile above the null), but v1 fails 2× costs and blows the DD ceiling. Next: (1) hold-through exit, (2) regime filter, (3) ADV gate, (4) THEN /sensitivity + /red-team + /oos-audit, (5) THEN diversifier-correlation case vs the short-vol books for IC.

## FILES
- `bt11.py` — engine (feature build once + monthly rebalance + COST-11 + shuffle)
- `config.json` — params + data snapshot · `metrics.json` — all 4 configs · `per_year.csv`
- `shuffle_percentile.json` — the null · `trades_N{10,20}_cost{1,2}x.csv` — blotters
