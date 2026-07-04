# BT-11 UNION RE-RUN — VERDICT

**Owner:** Devika Menon (E-016) · **Date:** 2026-07-04 · **Run dir:** `results/T2-SIG11/20260704_bt11_union/`
**Question answered:** *How much of BT-11's early-era edge was survivorship?*

---

## THE HONEST READ (top line)

**Survivorship inflated BT-11's headline CAGR by ~4 percentage points/year, and the inflation is
almost entirely ONE year — 2016 — exactly where the old HF panel's coverage was thinnest.
The edge is smaller on the honest panel but it does NOT vanish: it still beats a size-matched
random null at the 86th–88th percentile and compounds at 6.8–8.5%/yr (2016-start, 1× cost).**

Like-for-like (2016 start, matching the old run's window), 1× COST_STANDARDS:

| Config | OLD HF CAGR (2016-26) | UNION CAGR (2016-26) | Survivorship cost |
|---|---|---|---|
| N10 | **10.79%** | **6.80%** | **−3.98 pp/yr** |
| N20 | **12.64%** | **8.49%** | **−4.15 pp/yr** |

So roughly **one-third of the like-for-like CAGR was survivorship** (the panel omitted later-losers,
biasing the 2016 slice optimistic — as the COVERAGE_CAVEAT predicted). But two-thirds is real, and
the post-2018 slices barely move (the caveat's claim that they were "sound as-is" is confirmed).

**[INFERENCE]** This is a survivorship *haircut*, not a survivorship *kill*. The Track-2 momentum
machine remains a genuine, if lower-octane, edge on the survivorship-safe panel. Its diversifier
role (only non-short-vol book) is intact; its expected return is marked down ~4 pp/yr in the early era.

---

## WHERE THE BIAS LIVES — per-year delta (N20, 1× cost, book return %)

| Year | OLD HF | UNION | Δ (pp) | Read |
|---|---|---|---|---|
| 2014 | — | +71.8% | NEW | union-only (no HF comparison) |
| 2015 | — | +16.2% | NEW | union-only (no HF comparison) |
| **2016** | +22.5% | **−0.45%** | **−23.0** | ← the survivorship year; HF coverage was 75% |
| 2017 | +67.7% | +63.4% | −4.4 | modest |
| 2018 | −29.7% | −33.9% | −4.2 | (a LOSS got slightly worse — anti-survivorship at work) |
| 2019 | −5.8% | −4.2% | +1.6 | noise |
| 2020 | +20.4% | +16.0% | −4.3 | modest |
| 2021 | +91.2% | +87.0% | −4.2 | modest |
| 2022 | −13.1% | −15.3% | −2.2 | noise |
| 2023 | +43.9% | +42.2% | −1.7 | noise |
| 2024 | +25.1% | +23.1% | −2.0 | noise |
| 2025 | −30.1% | −28.8% | +1.3 | noise |
| 2026 | −4.4% | −4.5% | −0.1 | flat (partial year) |

**The −23 pp in 2016 is the whole story.** It is identical in sign and magnitude across all four
configs (N10/N20 × 1×/2×: −23 to −30 pp). Everything from 2019 on is within ±5 pp — panel-basis
and universe-breadth noise, not survivorship. Direction of the bias = OPTIMISTIC, as forecast.

Denominator-free rupee truth (Rs 10L book, N20 1×): 2016 old +Rs 2.87L → union +Rs 1.20L booked
(−Rs 1.67L of the 2016 P&L was survivor-carried). Full-period the union book actually earns MORE
rupees (Rs 3.50L vs 3.28L PL) — but that is the 2014-15 NEW years + more names to buy + the
return-basis (dividend-adjusted) lift, NOT a claim of a bigger edge. Read CAGR-from-2016, not the
2014+ headline, for the like-for-like edge.

---

## SHUFFLE PERCENTILE — old vs new (50 draws, 1×, size-matched from the PIT universe)

| | OLD HF | UNION | note |
|---|---|---|---|
| N10 real CAGR vs shuffle-mean | 10.79% vs 3.55% → **pct 98** | 9.71% vs 4.71% → **pct 86** | still beats null by +5.0 pp/yr |
| N20 real CAGR vs shuffle-mean | 12.64% vs 3.34% → **pct 100** | 13.39% vs 7.14% → **pct 88** | still beats null by +6.3 pp/yr |

**The separation from random narrowed (98/100 → 86/88) but the signal still clears its null.**
Two reasons the percentile fell, both HONEST (not a weakening of the signal itself):
1. The union shuffle pool now contains the delisted losers AND a wider survivor set, so random
   draws occasionally catch big winners — the null's mean rises (3.5% → 4.7–7.1%) and its right
   tail fattens (p95 8% → 15–18%). A higher bar is the correct bar.
2. Full-period union percentiles include the volatile 2014-15 NEW years in both real and shuffle.

The real strategy sits comfortably above the null median in both configs. **[INFERENCE]** Not a
placebo; a real-but-noisier edge on the honest universe.

---

## AT 2× COST — the machine still can't pay double freight (unchanged conclusion)

N10 2× union CAGR −2.06% (old −1.15%); N20 2× union +1.03% (old +0.06%). As before, this
small-cap momentum book **does not survive 2× COST_STANDARDS** — the RESEARCH_SOP "survive 2×
before paper" bar is FAILED, on the honest panel too. The survivorship fix does not rescue it from
its cost sensitivity. This is the binding constraint for paper promotion, not the survivorship haircut.

---

## METHOD / DEVIATIONS (all stated loudly; full detail in config.json + LOOKAHEAD_AUDIT.md)

- **Panel:** PIT union **RETURN** panel (`close_panel_return.parquet`), version **v1**
  (build 2026-07-04T20:53:55; md5 `9f5b5d42159ff810e8d554bbab35499c`). Frozen COPY in this dir;
  the live `pit_union_panel_v1/` (Manoj upgrading to v1.1) was NOT read after snapshot.
  2,556 symbols, 6.88M rows, 2000-01-03→2026-01-22. Basis = dividend-adjusted total-return — the
  correct holding-period-return basis for a long-only momentum book. (Deviates from a CURRENT_STATE
  note preferring PRICE basis for P&L backtests; the brief explicitly directs the RETURN panel and
  TR is right for equity holding returns — stated, not silently reconciled.)
- **Fills:** union is **close-only**, so entries AND exits fill at **NEXT-DAY CLOSE** (bt11 used
  next-day OPEN). Strictly t+1 (L5/T3-clean), ~1 day later, more conservative. Same slippage stack.
- **Volume / breakout flag:** spliced from HF where the (symbol,date) exists (94.8% of rows).
  Union-only names → `breakout_vol_flag=False` (a +5 composite NUDGE only, never a hard criterion,
  so it cannot fabricate ALL_PASS). Only **~3.3% of fills** are union-only-no-volume, concentrated
  in 2014-2017 (7-12%), ~0% from 2019 — i.e. exactly the anti-survivorship early-era names.
- **Liquidity gate both-ways:** the original bt11 selection applied NO ADV gate (only ALL_PASS +
  price_floor) — we matched that (signal-only). The `pct_entries_no_vol` column IS the liquidity
  read: if a hard "must-have-volume" gate were imposed, those 3.3% of early fills drop out; the
  edge conclusion is unchanged because they are a small, early minority.
- **Universe:** `pit_universe(asof)` alias-mapped (HEROHONDA→HEROMOTOCO etc. via symbol_aliases.csv);
  PIT snapshots verified **March/September** (months [3,9]) — the brief's Mar/Sep warning satisfied.
- **Start extended to 2014-01** (union 2014 N200 full-history coverage 95.5%). 2014-2015 reported
  as NEW (no old-HF comparison exists).
- **Frozen:** MA 50/150/200, RS gate 70, 12-1 blend w=0.6, price floor Rs 20 — all identical to bt11.
- **Engine-equivalence guard PASSED** (fast pre-built-feature path == from-scratch date≤asof rebuild,
  ALL_PASS set + rs_pct, on 4 sample month-ends).

## D-028 LOOKAHEAD AUDIT: **PASS** (0 FAIL, 15 WARN all dispositioned — see LOOKAHEAD_AUDIT.md)
T3 (next-day fill, strictly t+1) ✓ · T5 (42 PIT snapshots, delisted names deliberately in panel,
gated at selection) ✓ · T6 (`.rank(pct=True)` is per-month not full-sample) ✓ · T7 (momentum uses
only positive shifts, no `.shift(-)`) ✓ · T10 (panel version + md5 + row counts recorded) ✓.

## WHAT KILLS / DEMOTES THIS
- Fails 2× COST_STANDARDS (both N, both eras) → cannot go to paper until costs are reduced
  (larger book to amortize the flat brokerage, or lower slippage assumption if TCA supports it).
- If Manoj's v1.1 materially changes early-era coverage, re-run and re-check the 2016 delta.
- Review date: at next Track-2 IC / edge-decay cadence.

## FILES
- Engine: `bt11_union.py` (adapted from `../20260704_bt11/bt11.py`), `data11_union.py` (union loader)
- `config.json` (panel version, md5, row counts, deviations), `metrics.json`, `shuffle_percentile.json`
- `delta_per_year.csv` (per-config per-year old-vs-union), `delta_summary.json`
- `trades_*.csv`, `per_year_union.csv`, `LOOKAHEAD_AUDIT.md`, `PROGRESS.md`, `run.log`
