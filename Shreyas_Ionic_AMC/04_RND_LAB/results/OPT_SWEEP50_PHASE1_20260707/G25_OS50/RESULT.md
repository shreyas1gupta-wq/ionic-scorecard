# OPT-SWEEP-50 Phase-1 — G25 (Arjun) — OS-50 + OS-43 note

**Setup OS-50:** BUY swing CE/PE on a NIFTY momentum (Donchian) breakout, multi-day hold.
Family H, directional option BUYING, K-001-adjacent, fights VRP. Fast/cheap pass only (rank, not certify).

## Data lineage
- NIFTY spot 1-min → daily OHLC: `intraday_options_strategy/datasets/raw/hf_index_options_1m/index/NIFTY.parquet` — 477,738 bars, 2021-05-24 → 2026-06-03 (≥09:15 filtered, L2 auction guard). 1,242 trading days.
- NIFTY index weekly options 1-min: `.../hf_index_options_1m/options/NIFTY/*.parquet` — 261 valid weekly expiries 2021-05-27 → 2026-06-02 (accessor `buying/chain.py`; 1 stub file skipped, 2026-06-09). Full multi-day life per expiry (~8 trading days). Spot range 15,150 → 26,562.
- Costs: `06_TRADING_DESK/COST_STANDARDS.md` at 1× (options liquid ATM index: 0.25%/side slippage + ₹20/order×2 + 0.1% STT sell + 0.035% exch + GST + stamp) → ~1.8 pts/round-trip.
- Backtest window = full option-data span **2021→2026** (index options do not go back to 2016; INDIA VIX does but is not needed for this directional setup).

## Method (pre-registered, per campaign conventions)
- Signal: Donchian fresh-cross on daily close — close breaks prior N-day high → BUY ATM CE; breaks prior N-day low → BUY ATM PE. N=20 primary, N=10 robustness. Fresh-cross only (no flooding); one position at a time (swing).
- Entry-fill = **next-liquid-quote D+1** (first bar ≥09:20, volume>0). Same-day-close (signal-day close) reported separately as the A.17 optimistic bound.
- Strike = ATM (round spot/50). Expiry = weekly with most remaining time (DTE 3–14) that actually covers the entry day.
- Exit = min(entry + 5 trading days, last liquid day ≤ expiry), liquid quote ≤15:20. P&L booked in the EXIT period.
- No-fill on circuit-locked / zero-vol bars = DROP (predicate-pushdown liquidity check; volume>0 required). ATM index is deep — no trades were dropped for illiquidity.
- Edge reported in **rupee (premium) points** and **%-of-spot** (never %-of-premium).

## Landmine guards
L2 pre-open (bars ≥09:15) ✓ · L5 next-bar (D+1 entry strictly after signal day) ✓ · fill/liquidity gate (volume>0, drop else) ✓ · exit-period P&L booking (no spreading across hold days → no fake-low variance) ✓ · denominator-free ₹-points + %-spot (no return-on-premium/net-debit) ✓ · no future settlement (all exits ≤ 2026-06-03 data max) ✓.

## Results — negative in every cut

| Cut | N | GROSS pts/trade | NET(1×) pts/trade | %-spot NET | win% | t-stat |
|---|---|---|---|---|---|---|
| **Donchian(20) ATM, hold 5d, D+1 fill** | 74 | **−31.9** | **−33.7** | **−0.120%** | 28% | −0.93 |
| Donchian(10) robustness | 101 | −14.5 | −16.5 | −0.050% | 32% | −0.41 |
| N20 PRE Sept-2025 (regime check) | 67 | −23.3 | −25.1 | −0.085% | 30% | −0.60 |
| N20 POST Sept-2025 | 7 | −114.2 | −115.6 | −0.464% | 14% | −3.38 |
| N20 CE only | 49 | −19.8 | −21.6 | −0.050% | 33% | −0.33 |
| N20 PE only | 25 | −55.6 | −57.3 | −0.258% | 20% | −1.09 |
| N20 OPTIMISTIC same-day-close entry (GROSS) | 62 | **−38.7** | — | — | — | — |

By-year (N20 net pts): only 2022 (+642) and 2023 (+837) positive — the two clean trending-bull years for CE. 2024 (−2,545), 2025 (−668), 2026 (−714) erase it. Full-sample sum −2,491 pts. Median trade −94 pts on a ~183-pt premium (≈ −51% of premium): the classic option-buyer lottery profile — lose ~half the premium most trades, occasional trend winner not enough. N=10 shows the identical shape.

## Degenerate detectors
None triggered — there is no positive edge to scrutinize (no Sharpe>4, no smooth equity, no concentration to flag). The only "edge" is a 2022–23 bull-trend beta pocket that fully reverses 2024–26.

## Kill-criteria check (all three fire)
1. Edge ≤ 0 in **both** ₹-points (−33.7 net) **and** %-spot (−0.120% net). **FAIL.**
2. Not a pooled-regime artifact — **negative PRE Sept-2025** (−25.1 net) as well as post. **FAIL.**
3. Does not survive the fill convention — the **optimistic same-day-close entry is even worse** (−38.7 vs −31.9 gross), so there is no fill under which the edge exists. **FAIL.**
Also fails the campaign's directional-buying prior: OS-50 loses in the full sample and in the N=10/N=20 grid.

## VERDICT: **KILL** (FAKE-edge → no edge)
Weakest assumption (moot here): that a daily-breakout timing signal can overcome theta + entry-slippage on a bought weekly option. It cannot — as the firm's VRP prior (A.1) and the K-001 buying graveyard predicted. Directional index-option buying pays theta into a mean-reverting/short-vol market; the only positive years are pure trend beta that does not persist. Do not advance to Phase-2.

---

## OS-43 exclusion note
**OS-43 excluded per campaign spec, duplicate of K-001, do-not-run** (intraday CE/PE opening-range-breakout buying is explicitly inside the killed K-001 intraday-option-buying family; §1 prior-art + §3 Family H mark it DUPLICATE-K-001, listed only for completeness). Not executed.

_Artifacts: `os50_backtest.py`, `os50_trades_N20.csv` (74 trades) in this folder._
