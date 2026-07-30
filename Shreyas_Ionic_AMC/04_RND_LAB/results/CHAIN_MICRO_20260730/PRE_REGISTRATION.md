# PRE-REGISTRATION — Chain-microstructure Stage-1 (Ishaan Gupta, ML, 2026-07-30)
Written BEFORE running `queue/151_chain_micro.py`. No results seen yet. Per D-035 / RESEARCH_SOP,
this file is not edited after results land; any change of mind is a NEW dated addendum.

## WHY THIS EXISTS
Every price-derived intraday signal tested today (23 triggers, regime x4, MA/RSI, confluence) is a
transform of the SAME NIFTY OHLC series. The option chain (`hf_index_options_1m/options/NIFTY/`,
261 valid weekly expiries, 1-min, full multi-day life per expiry) is the one source on this machine
that carries information price alone does not: who is paying up, at which strikes, in what size.
This is a genuinely orthogonal information source, tested per the BREADTH PROTOCOL's own rule
(orthogonal families > correlated variants).

## DATA / UNIVERSE
- Options: `intraday_options_strategy/datasets/raw/hf_index_options_1m/options/NIFTY/*.parquet`,
  loaded via a custom light column-projected reader (NOT `chain.load_expiry`, which crashed 3x today
  on `drop_duplicates` under ~2.6GB free RAM — see MEMORY NOTE below).
- Spot: `.../hf_index_options_1m/index/NIFTY.parquet`, filtered `time>=09:15` (pre-open auction bug).
- **[DATA] Front-week assignment**: for every actual trading day D (taken from the spot 1-min index,
  not assumed via bdate_range), the front expiry = min(E in the 261 valid expiries : E>=D). Day
  dropped from the sample if resulting DTE>7 (can happen at the very start of the series before the
  first expiry, or around a data gap) — this is a coverage limit, not a signal choice.
- **[DATA] verified today, corrects the task brief**: OI is NOT "thin from 2024" — OI is **0% null/zero
  2021-05 through 2024-12 (fully populated)**, and becomes **~65-66% zero from 2025-01 onward, even
  among volume>0 (liquid, actually-traded) rows** — i.e. a genuine 2025+ CAPTURE gap, not naturally-zero
  far strikes. Sampled 26 expiries spread across 2021-2026, columns `open_interest`+`trading_day` only.
  Signal 6 is therefore run on the CLEAN 2021-05..2024-12 sample as the primary read, with a 2025-2026
  "thinned" secondary read flagged as low-confidence.
- **[DATA] duplicate rows**: sampled expiry 2023-05-04 has **47.2% of rows as EXACT full-row duplicates**
  (every column identical, each key appearing exactly twice) on `(timestamp,strike,option_type)`. This
  is a real, systematic ingestion artifact (not a random subset), collapses correctly via
  `groupby(key).mean()` (mean of two identical values = the value) without needing the crashing
  `.duplicated()` call.
- Costs/margin/lot/event-exclusion: firm standards as of today (Rs25/lot/side, lot=65, SCH = the
  session's standard scheduled-event-day set `{2024-06-04,2024-06-03,2024-02-01,2023-02-01,2022-02-01,
  2025-02-01,2026-02-01,2024-07-23}`).

## MEMORY NOTE (binding on implementation)
Two jobs today segfaulted (0xC0000005) and one hit `numpy._core._exceptions._ArrayMemoryError`
specifically inside `chain.load_expiry`'s `df.drop_duplicates(["t","strike","option_type"])` at
expiry 175/257 — a 3.91MB allocation failed, i.e. severe heap fragmentation after many repeated
read/free cycles in one long-lived process, not a true OOM. Mitigations used here:
1. Column-projected `pq.read_table(path, columns=[...])` — 9 columns only (no `open`/`symbol`/`expiry`).
2. Deduplication via `groupby(key, sort=False).agg('mean')`, never `.duplicated()`/`drop_duplicates()`.
3. Each expiry file processed to a small aggregate, then `del` + `gc.collect()` immediately.
4. **Orchestrator/worker split**: the queued script spawns short-lived child `python` processes (one
   per batch of ~15 expiries) via `subprocess.run`; each child exits (returning ALL its memory to the
   OS) before the next starts, so fragmentation cannot accumulate across the full 261-expiry sweep.

## SIGNALS (all computed PER-DAY / causally; no cross-day state leak; no full-sample percentiles)
For signals 1-5, every raw series is converted to a **causal rolling z-score**: trailing 20-trading-day
mean/std of the raw signal, **shifted by 1 day** (today's bucket never uses today's own distribution),
recomputed daily. "Top decile" = z>=1.2816, "bottom decile" = z<=-1.2816. This is the SAME mechanism
that satisfies both "normalise so it's scale-free 2021-2026" (signal 1's own ask) and the binding
method's "trailing/expanding windows only — no full-sample percentiles."

1. **CE-vs-PE volume imbalance**: `(CE_vol - PE_vol)` per minute, all strikes, front-week chain only.
2. **Strike-migration**: share of chain volume in strikes ABOVE spot vs BELOW spot per minute,
   `vol_above/(vol_above+vol_below)`.
3. **Rolling PCR (real volume, not OI)**: `PE_vol/CE_vol` on a trailing 30-min window (resets daily);
   and **PCR_ROC** = PCR(t) - PCR(t-15min). Two sub-signals.
4. **Aggressor proxy** [INFERENCE, not DATA — no tick/quote data on this machine]: volume-weighted
   `(close-low)/(high-low)` for CE minus same for PE, restricted to strikes within 3 steps (150 pts)
   of spot. Persistent closes near the bar high on rising volume is read as buyers lifting offers;
   this is a proxy, explicitly not verified against a real order book.
5. **Cross-strike IV dislocation**: BS IV (functions replicate `measure_overshoot.py`'s `bs()`/`iv()`
   — same formula, not re-derived; that script is NOT imported directly because it is a top-level
   script with no `__main__` guard and would re-run its own full pipeline on import) for OTM call and
   OTM put at 1-step and 3-step (50/150 pts) from spot, on a 15-min snapshot grid. Signal =
   **jump in the 3-step wing skew** `(IV_call3 - IV_put3)` from one 15-min snapshot to the next.
6. **OI build-up vs unwind** (daily, 2021-05..2024-12 clean / 2025-2026 thinned secondary):
   `ΔOI_CE - ΔOI_PE` day-over-day (within the same front-expiry's continuous run only, never across
   an expiry rollover) vs next full trading day's close-to-close signed return.

## PRE-REGISTERED CELLS (exact count, entering the trials ledger)
| id | signal | horizons | n cells |
|---|---|---|---|
| CM-01..03 | CE-PE vol imbalance | 15/30/60 | 3 |
| CM-04..06 | strike migration | 15/30/60 | 3 |
| CM-07..09 | PCR level | 15/30/60 | 3 |
| CM-10..12 | PCR ROC | 15/30/60 | 3 |
| CM-13..15 | aggressor proxy | 15/30/60 | 3 |
| CM-16..18 | IV wing-skew jump | 15/30/60 | 3 |
| CM-19 | OI build/unwind, clean 2021-2024 | next-day C2C | 1 |
| CM-20 | OI build/unwind, thinned 2025-2026 | next-day C2C | 1 |
**TOTAL new cells: 20.** Firm cumulative before this run (stated by the task): 466. New cumulative:
**486 → Bonferroni bar p < 0.05/486 ≈ 0.000103** (soft gate, sets tier only — never a kill switch,
per the corrected 2026-07-30 evaluation framework).

## STAGE-1 TEST (run BEFORE any P&L)
For each cell: pool all (day, minute) observations in build period **2021-05..2025-12** (2026 held
out, reported separately, selected on nothing). Effect size = `mean(fwd_pts | top decile z) -
mean(fwd_pts | bottom decile z)`, in signed NIFTY index points. Placebo = **day-block permutation**
(500 draws: shuffle which trading day's signal-series is paired with which trading day's forward-return
series, holding minute-of-day alignment fixed so intraday seasonality cannot manufacture a fake edge)
recomputing the same effect-size statistic; p = share of |null effect| >= |observed effect|.

## KILL CRITERIA (pre-registered, HARD — per SHARED_CONTEXT's corrected framework)
- **Placebo p >= 0.05 → DEAD.** This is the only Stage-1 hard kill (no lookahead / same-bar fill by
  construction: forward return always computed strictly after the signal timestamp; no P&L yet so
  concentration/maxDD/thin-fill kills do not apply until Stage 2).
- Placebo p < 0.05 is necessary, NOT sufficient, to proceed to Stage 2.

## STAGE-2 GATE (only for Stage-1 survivors)
A cell proceeds to Stage 2 (naked long option P&L, 0.40-0.80 delta, honest fills, real costs) only if
BOTH: (a) placebo p<0.05, AND (b) |effect_pts| >= 10 (this session's own calibration bar — the best
price-derived trigger all day was 10.03 pts / t=3.10 and even that did not clear the futures cost bar,
so anything smaller is not worth building a P&L harness for). Cells beating placebo but under 10 pts
are tiered UNDERPOWERED-UNRESOLVED (if economically non-trivial, >=2pts) or DEAD (if <2pts — an
effect that large-n can render "significant" at negligible magnitude is not a live lead, per the
Principal's own "look at pnl... not too large mdd" instruction: a ~0-pt effect has no pnl regardless
of its p-value).

## SIGN CONVENTION
No direction is assumed for any signal (2026-07-04 lesson: US market-structure sign conventions may
invert in India). Effect size is signed as computed (top-decile minus bottom-decile); a negative value
means the "high" bucket of the signal precedes DOWN moves relative to the "low" bucket — this is
reported as-is, not flipped to force a "long" story.
