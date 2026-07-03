# TRACK-2 ENGINE BUILD SPEC — Small-Cap Leadership Momentum Machine
`Author:` Devika Menon (E-016, FM-Equities) · `Date:` 2026-07-03 · `Stage:` post-TRIAGE (gate 2 PROCEED), pre-CHEAP-TEST
`Sleeve:` Momentum (FACTOR_LIBRARY) · flagship of the Equities book · `Owner build task:` DESK-100
`Reads with:` `swing_momentum/PLAN.md` (legacy, READ-ONLY), `RESEARCH_SOP.md`, `COST_STANDARDS.md` (APPROVED), `RISK_LIMITS.md` (APPROVED), `ANALYST_CHECKLISTS.md` (Minervini template)

> This is the ENGINE BUILD SPEC, not a result. It defines the universe, the v1 signal stack,
> rebalance/sizing/stop discipline, the approved cost model, the walk-forward design, the
> complete free-parameter list, pre-registered kill criteria, and the ordered build task list.
> It supersedes the legacy prototype ONLY as a firm-grade rebuild; the prototype's numbers are
> NOT carried forward (they were close-only + no-volume + survivorship-leaky — see TRIAGE §D).

---

## 0. TRIAGE VERDICT — PROCEED (gate 2, FM + Quant style)

**PROCEED to CHEAP TEST**, with one hard condition: the rebuild must re-earn its number under a
volume/liquidity gate the prototype never had. The prototype's +11.6% full / +16.1% OOS is
treated as a PRIOR, not a result.

### A. Economic WHY (plausible — behavioral + structural + capacity)
Leadership momentum in Indian small/mid-caps persists because (i) **behavioral** — under-reaction
to sustained relative strength; retail and slow institutions chase late; (ii) **structural** — the
smallest liquid leaders are below the size where large funds can build a position, so the crowd that
would arbitrage the drift is absent (capacity IS the moat, by design ≤₹10Cr); (iii) **regime-conditional**
— the edge is a momentum-regime bet, not a stationary premium, which is WHY the regime gate is the
make-or-break, not a nicety. Who loses to us: late trend-chasers who buy exhaustion and sell capitulation,
and index-constrained funds who cannot fish this small. **[INFERENCE]** — the academic 12-1 momentum
premium and Minervini/O'Neil leadership frameworks support the direction; the small-cap capacity moat is
firm doctrine (GOD_TIER D3).

### B. Data readiness — READY (verified on disk 2026-07-03, not [books])
| Input | Path | Verified | Fit for v1? |
|---|---|---|---|
| Daily OHLCV **+ volume** | `swing_momentum/data/hf_stock_minute/day/train-00000.parquet` | 6,968,616 rows · 2,535 symbols · cols incl. `volume`,`oi` · dates →**2026-01-21** | YES — **has volume**, which fixes the prototype's #1 optimism source |
| PIT universe (survivorship-safe) | `NIFTY500_TICKER_2005_2025_Final.xlsx` | **42 snapshots** Mar2005→Sep2025 (semi-annual) · 492–507 names/snap · 1,004 unique tickers | YES — membership known at 6-month resolution; forward-fill between snaps |
| Delisted price series | `Nifty500_Delisted_2005_2025.xlsx` | 1,321 daily rows · 148 delisted names (wide format) | YES — enables realizing delist losses (fixes prototype caveat #2) |
| PIT earnings (`available_date`) | `datasets/earnings_pit/unified_quarterly_pit.parquet` | 31,891 rows · 2,296 symbols · available_date 2005→2026-05 | v2 ONLY (CANSLIM/PEAD overlay); NOT needed for v1 price-only stack |

**Staleness caveat (LOUD):** the daily file's max date is **2026-01-21**. Any `asof()` after ~2026-01-22
returns a stale price (DATA_CATALOG landmine #1). Backtest window therefore ENDS 2026-01-21; the "2026 YTD"
regime slice is only ~3 weeks and must be labelled thin. Live/paper scanning uses Angel daily bulk, NOT this file.

### C. Capacity — PASS for the target account (this is the moat, not a constraint to relax)
Target = a future small retail account (D-018), well under ₹10Cr. The whole thesis REQUIRES staying small;
capacity is proven by the RESEARCH_SOP "capacity ≥3× intended size" gate applied in reverse — we cap position
at ≤10% of 20-day ADV (≤5% for micro, per COST_STANDARDS/RISK_LIMITS) and DEMAND the book still fills. A
strategy that only works at sub-₹1Cr and dies at ₹10Cr is EXPECTED and acceptable here — the capacity test
(Phase 6) maps where it decays; it does not need to scale to institutional size.

### D. Family history — the honest prior (checked RESULTS.md; do NOT cite the prototype's number as ours)
- Prototype ran end-to-end (`run_swing.py`) on a **close-only** panel. V1 (biased) +21%/OOS +34%; after the
  survivorship fix (realize −50% delist, price floor, tighter stop/regime) it **HALVED to +11.6% full /
  +16.1% OOS, Sharpe 0.43/0.60, MaxDD 23%**. The +21%→+11.6% gap was fake alpha from escaping delisting losses.
- Regime filter is ESSENTIAL: always-on MaxDD was **73%**; the gate cut it to 23%. Triple-digit years are
  EPISODIC bull payoffs (+76% 2014, +62% 2021), not a sustained rate. This matches my Lesson-Learned: defend
  this book on **diversification** (only non-short-vol driver in the firm) + episodic convexity, NOT headline CAGR.
- **The two open holes the prototype flagged and could not close:** (1) NO volume/liquidity gate (close-only
  master) — THE biggest optimism source; (2) survivorship half-fixed. This rebuild closes BOTH: the verified
  daily file HAS volume, and the delisted xlsx lets us realize delist losses. **That is the entire reason to
  rebuild rather than trust the prototype.**
- Also logged (RESULTS.md): a mean-reversion sleeve stacked onto momentum FAILED (rho +0.57, combo worse) —
  reinforces that this book's diversification value is vs the SHORT-VOL book, not vs another long-equity sleeve.

**Verdict: PROCEED.** Not a KILL — the WHY is sound, data is verified-ready, capacity fits by design, and the
one thing that could have killed it (no volume data) turns out to be present on disk. But it PROCEEDS as a
skeptic: the number must survive the volume gate + 2× approved costs before anyone believes +16% OOS.

---

## 1. UNIVERSE CONSTRUCTION (survivorship-safe — the non-negotiable)

- **Membership source: ONLY the 42 PIT snapshots** in `NIFTY500_TICKER_2005_2025_Final.xlsx`. NEVER a
  current-day constituent list (Lesson-Learned 2026-07). A name is eligible on trading date `D` iff it
  appeared in the most-recent snapshot on-or-before `D` (forward-fill semi-annual membership until the next
  snapshot supersedes it). A name dropped from a snapshot ceases to be eligible for NEW entries from that
  snapshot's date, but an open position exits on its own stop/rule (no look-ahead survivorship on exits).
- **Delisting handled as a realized loss**, not a dropped NaN: if an open name delists (present in
  `Nifty500_Delisted_2005_2025.xlsx` / price series terminates), realize the position at the last available
  price and, absent a clean last print, book a **−50% haircut** on the residual (prototype's honest convention;
  revisit with Data Officer if a better recovery estimate exists). This removes the fake alpha from escaping
  delisting losses.
- **Liquidity gate (THE validity fix the prototype lacked):** compute 20-day median rupee turnover
  (`close × volume`) per name per date from the verified daily file. Eligible for entry iff 20d ADV ≥ a floor
  AND the intended position ≤ 10% of that ADV (≤5% for micro-tier). Names failing the ADV floor are dropped
  from the tradable set on date `D` (they may sit in the snapshot but are untradeable at our size).
- **Price floor:** close ≥ ₹20 (penny-stock / print-artifact guard; prototype convention).
- **Corporate-action adjustment:** use split/bonus-adjusted series. The daily file must be checked for phantom
  gaps at action dates during DATA-11 (build step); if the file is raw-unadjusted, apply
  `corporate_action_factors` (DATA_CATALOG §3, 613 events) before any SMA/return computation.

---

## 2. SIGNAL STACK v1 (price-only; ALL-criteria Minervini + 12-1 + RS percentile)

v1 is deliberately **price-and-volume only** — no fundamentals — so it can run on the verified daily file with
zero new-data dependency. Fundamentals (CANSLIM 'C'/'A', PEAD) are **v2**, gated behind a separate one-pager.

### 2.1 Minervini Trend Template — ALL criteria must hold (no partial pass), per ANALYST_CHECKLISTS
A name is a **candidate leader** on date `D` only if EVERY one of these is true (Dhruv's template):
1. Close > 150d MA and Close > 200d MA
2. 150d MA > 200d MA
3. 200d MA rising over the last 22 sessions
4. 50d MA > 150d MA > 200d MA
5. Close > 50d MA
6. Close ≥ 30% above 52-week low
7. Close within 25% of 52-week high
8. RS percentile ≥ 70 vs the PIT-universe (see 2.3)
> (Criterion 9 "VCP volume contraction through the base" is a v2 add — see §2.4. v1 uses the 8 price/RS criteria
> + a simple breakout-volume confirmation at entry, §3.)

### 2.2 12-1 Momentum (the academic core, ranking input)
Trailing 12-month total return skipping the most recent 1 month (the classic 12-1 to avoid short-term
reversal). Computed on adjusted close. This is the PRIMARY ranking score for the leader board.

### 2.3 RS percentile (cross-sectional, PIT-universe-relative)
Cross-sectional percentile rank of 12-1 momentum (blended with 6-month for recency: `0.6·r12_1 + 0.4·r6`, the
prototype weighting — held as ONE tunable, §5) computed **only across names in the tradable PIT set on date `D`**
(never the full 2,535-symbol file — that would leak non-members). RS percentile ≥ 70 is the trend-template gate;
the continuous percentile is also the tie-break ranker for the top-N leader board.

### 2.4 v2 backlog (NOT built in v1 — logged so scope is explicit)
- **VCP detector** (Minervini criterion 9): progressively tighter contractions T1>T2>T3 on declining volume →
  pivot; entry on pivot breakout with volume expansion. This is the single most valuable v2 add.
- **CANSLIM fundamental overlay** (PIT earnings, `available_date` join): 'C' current-qtr EPS growth ≥25%, 'A'
  annual accel, 'I' institutional accumulation proxy.
- **PEAD tilt** (GOD_TIER D4): overweight names with a recent positive earnings surprise inside the drift window.

---

## 3. REBALANCE, ENTRY/EXIT, POSITION SIZING & STOP DISCIPLINE

- **Rebalance cadence: WEEKLY** (decision on last session of week, fill next-session open). Weekly matches the
  swing horizon (days→weeks), keeps turnover/cost sane for small-caps, and matches the prototype so results are
  comparable. Daily rebalance is rejected (cost + noise); monthly rejected (too slow for leadership rotation).
- **Leader board:** each rebalance, rank the tradable-and-trend-template-passing set by RS/12-1 score; target the
  **top-N** (N is a free param, §5; prototype used 20 — for a small retail account the LIVE book concentrates to
  5–12 names per PLAN, but the ENGINE ranks top-N and the sizing/heat cap does the concentrating).
- **Entry:** buy a top-N name on next-session open, with **breakout-volume confirmation** (entry-day or prior-day
  volume ≥ 1.5× its 50d average — the v1 stand-in for VCP). Entry only when the **regime gate is GREEN** (§4).
- **Position sizing — 1% risk rule (RISK_LIMITS, hard):** shares = `(0.01 × book_equity) / stop_distance_per_share`,
  where stop_distance = entry − initial_stop. Then **cap position notional at ≤ min(position_cap%, 10% of 20d ADV)**
  (≤5% ADV micro). Max risk per position = **1.0% of book equity** (RISK_LIMITS position level). This is the
  risk-per-share sizing from ANALYST_CHECKLISTS, not equal-weight — equal-weight was the prototype shortcut.
- **Initial stop:** hard stop below the pivot / last contraction low, floored so stop-distance ∈ [tightest, widest]
  band; the prototype's 15% trailing stop is the fallback trail once in profit. Stop is a HARD rule, no averaging down
  (PLAN §0 hard rules).
- **Portfolio heat cap:** sum of open risk (Σ per-name stop-distance × size) ≤ **book-heat cap** (2–3% equity per
  PLAN; held as a free param, §5). New entries blocked when the heat cap is hit — this is what actually enforces
  5–12 concentration at small equity.
- **Profit management:** trail with the 15% stop / 50DMA break; optional partials at +2R (v2 refinement, not a v1 param).
- **Exit triggers:** stop hit · trailing stop · regime turns RED (scale down / no new buys, tighten to exits) ·
  falls out of trend-template AND out of top-N for 2 consecutive rebalances (time/quality stop).

---

## 4. REGIME FILTER (the make-or-break — kept simple in v1)

- **State machine, 3 states:** GREEN (full size), YELLOW (half size / A+ only), RED (no new buys; manage exits).
- **v1 inputs (all computable from the daily file, no new data):**
  - **Direction:** Nifty-500 proxy (equal-weight of PIT-tradable set, or Nifty index if available) > its 50d AND
    200d MA → direction-up.
  - **Breadth:** % of the PIT-tradable universe passing the trend template (or above 200DMA) ≥ a threshold.
- **Mapping:** GREEN = direction-up AND breadth ≥ hi-threshold; RED = direction-down OR breadth ≤ lo-threshold;
  YELLOW = in-between. (Distribution-day count, follow-through-day, and India-VIX vol overlay are v2 regime
  refinements — logged, not in v1, to keep the free-param budget ≤5.)
- **Pre-2008 note:** if the Nifty index series is absent before 2008 the engine sits in cash (prototype behavior);
  report active-period CAGR (2009+) alongside full-period so the number isn't understated by forced-cash years.

---

## 5. FREE PARAMETERS — the COMPLETE list (≤5, per P-11 / RESEARCH_SOP)

Every tunable is listed; anything not here is FROZEN by doctrine (Minervini template thresholds, 1% risk rule,
cost model, 20d ADV window). Five parameters, each justified, each ≥30 trades/param achievable in a 2005–2026 sample.

| # | Parameter | v1 default | Grid (walk-forward, ≤3 pts) | Why tunable / justification |
|---|---|---|---|---|
| P1 | Top-N leader board size | 20 | {12, 20, 30} | Concentration vs breadth; drives trade count. |
| P2 | RS/momentum blend weight w on 12-1 (rest on 6m) | 0.6 | {0.5, 0.6, 0.7} | Recency vs stability of the momentum signal. |
| P3 | Trailing stop % | 15% | {12%, 15%, 18%} | Whipsaw vs give-back; the core give-winners-room lever. |
| P4 | Liquidity ADV floor (₹ turnover, 20d median) | TBD at build | {tight, base, loose} | The validity fix — where the small-cap moat/decay lives. |
| P5 | Regime breadth GREEN threshold | 40% | {35%, 40%, 45%} | The make-or-break gate sensitivity. |

Frozen-by-doctrine (NOT counted): all 8 trend-template thresholds (ANALYST_CHECKLISTS), 1% per-trade risk
(RISK_LIMITS), 10%/5% ADV participation caps (COST_STANDARDS), 50/150/200 MA lengths (Minervini canon),
weekly cadence, price floor ₹20, delist −50% haircut, breakout-volume 1.5× (v1 entry confirmation).

---

## 6. COST MODEL — APPROVED COST_STANDARDS, applied + 2× stress

Applied per side, per COST_STANDARDS (APPROVED D-021), on every simulated fill:
- Brokerage ₹20/order · STT equity delivery 0.1% both sides · exchange txn ~0.00297% · GST 18% on
  (brokerage+exchange+SEBI) · SEBI ₹10/cr · stamp 0.015% delivery buy.
- **Slippage: SMALL-CAP FLOOR = 35 bps one-way** (COST_STANDARDS tier), **DOUBLED to 70 bps** for exits
  into strength / panic. Micro-tier names (if any pass) use 50+ bps. Large/mid names (rare in this book) use
  their tier floor. Slippage is applied on top of the ADV-participation cap.
- **Realistic fills:** no fill on circuit-locked days; entry/exit size capped at ≤10% (≤5% micro) of that
  day's volume; model gap-through on stops (fill at open if it gaps past the stop, not at the stop).
- **PROMOTION RULE (RESEARCH_SOP gate 7 / COST_STANDARDS):** the strategy must remain **net-positive at 2× ALL
  of the above** (i.e. 70 bps small-cap floor, 140 bps on exits, doubled per-order proxies) before it advances to
  paper. Headline result reported at 1×; the go/no-go result reported at 2×. **Survive-2×-before-paper is a hard gate.**

---

## 7. WALK-FORWARD & VALIDATION DESIGN (per RESEARCH_SOP gate 4–5; Quant signs)

- **Walk-forward:** train 3y → validate 1y → roll 6m. Params (§5) frozen per window. **Grid ≤ 3×3** (the §5 grid
  respects this — tune at most the pair the plateau analysis says matters, hold the rest at default per window).
- **FINAL untouched OOS = most recent 12 months** (≈2025-01→2026-01, ending at the 2026-01-21 stale tail), opened
  **exactly ONCE** for this family. The prototype's "OOS ~2019-2025" is NOT that untouched set — it was in-sample
  to the prototype's iteration; treat it as validation, not final OOS.
- **Plateau rule:** the chosen cell must not beat its parameter-neighborhood median by >20% (spike ≠ edge).
- **Deflated Sharpe (Bailey-LdP) DSR > 0.95** with the **HONEST family trials count** (see §9 ledger) and
  **PBO (CSCV) < 25%**. Reported beside every Sharpe, no exceptions.
- **Regime slices — no catastrophic slice:** 2018 small-cap crash · 2020 COVID · 2022 rate shock · 2024 election
  vol · 2026 YTD (label THIN — only ~3 weeks to the stale tail). Also report the prototype's bull-year episodes
  (2014, 2021) separately so the episodic-convexity framing is explicit.
- **Capacity test:** re-run capping participation at ₹1Cr / ₹5Cr / ₹10Cr ADV — show where the edge decays (proves
  the moat + the ceiling; a decay at ₹10Cr is EXPECTED and fine for the target account).
- **Benchmarks:** vs buy-&-hold Nifty-500 AND vs a naive always-on RS-momentum portfolio (isolates the regime
  gate's contribution) AND vs the always-on (no-regime) variant (the 73%-MaxDD reference).
- **Minimums:** ≥30 trades per free parameter; P&L booked in the EXIT period; stable denominators (no fake-Sharpe
  from open-position marks — book on close, the filtered-portfolio lesson).
- **Guards:** imported from `04_RND_LAB/lib/guards.py` (no copy-paste); no-lookahead prefix-equality unit tests on
  every feature (the options project's `tests_smoke.py` discipline). Seeds fixed; same config reproduces to the rupee.
- **Run engineering:** every run → `results/track2_momentum/<run_id>/` (`run_id = YYYYMMDD_HHMM_<confighash8>`) with
  `config.json` (params + data snapshot: paths, row counts, max dates), `metrics.json`, `trades.csv`, `equity.png`.
  Never overwrite a run dir.

---

## 8. PRE-REGISTERED KILL CRITERIA (set BEFORE touching the engine)

The strategy is KILLED (→ KILLED_IDEAS + resurrection condition) if ANY of:
1. **Net-negative or Sharpe < 0.3 at 2× approved costs** on the walk-forward validation set (fails the promotion gate).
2. **The volume/liquidity gate destroys the edge:** with P4 at the realistic small-cap ADV floor + 10% participation
   cap, full-period CAGR falls below **buy-&-hold Nifty-500** (i.e. the prototype's +11.6% was a close-only artifact).
   → this is the single most likely killer; it is WHY we rebuild.
3. **DSR ≤ 0.95 or PBO ≥ 25%** with the honest family trials count.
4. **A catastrophic regime slice:** any of {2018, 2020, 2022} shows MaxDD worse than the always-on reference, i.e.
   the regime gate adds no drawdown protection (the gate is the whole thesis — if it doesn't cut DD, KILL).
5. **Plateau failure:** the best cell beats its neighborhood median by >20% (overfit spike).
6. **Capacity floor:** the edge only exists below the target account's intended size (decays before intended AUM) —
   then it's un-fundable even as a small sleeve.

**Resurrection conditions** (log with any kill): (a) a clean VCP/CANSLIM v2 overlay materially lifts per-trade edge;
(b) a corrected cost/ADV assumption via /post-mortem evidence; (c) fresh data extending the stale 2026-01-21 tail.

---

## 9. FAMILY TRIALS LEDGER (DSR honesty — count EVERYTHING)

This family already has PRIOR trials that MUST be counted in the DSR: the legacy prototype's V1 (biased) + V2
(survivorship-fixed) + the multi-strat mean-reversion stack + any grid cells the prototype swept. Starting honest
count for the rebuild: **≥4 prior configurations** on this family (V1, V2, multistrat-combo, always-on reference).
Every new walk-forward grid cell adds to this count. The DSR must use the cumulative honest count, not a fresh zero.

---

## 10. DESK-100 BUILD TASK LIST (ordered, ~5–8 steps)

> DESK-100 owns the build. Each step lands in `swing_momentum/` (rebuild namespace — do NOT overwrite legacy
> prototype files; new module names) and every backtest run follows §7 run-engineering. Checkpoint after each step.

1. **DATA-11 — Survivorship-safe panel + universe builder.** From the verified daily file
   (`swing_momentum/data/hf_stock_minute/day/train-00000.parquet`, 6.97M rows) + the 42 PIT snapshots + delisted
   xlsx: build (a) an adjusted daily OHLCV+volume panel with corporate-action check for phantom gaps, (b) a
   PIT membership table (forward-filled semi-annual), (c) a 20d ADV/turnover series, (d) delist-loss events.
   Output `data/eq_panel_v2.parquet` + `data/universe_pit.parquet` + `data/adv.parquet`. **No-lookahead unit tests
   here first** (prefix-equality). Data snapshot logged (paths, row counts, max date 2026-01-21).
2. **SIG-11 — Signal stack v1.** Implement 50/150/200 MAs, 52w hi/lo, 12-1 & 6m momentum, RS cross-sectional
   percentile (PIT-set-relative ONLY), and the 8-criteria Minervini trend-template ALL-pass gate + breakout-volume
   flag. Prefix-equality no-lookahead tests on every feature. Output a daily leader-board.
3. **REG-11 — Regime filter.** Direction (index/EW-proxy vs 50&200DMA) + breadth (% universe passing template) →
   GREEN/YELLOW/RED state series. Unit-test the state transitions.
4. **BT-11 — Event-driven backtest engine.** Weekly rebalance, next-open fills, 1%-risk position sizing + ADV cap +
   heat cap + hard/trailing stops + delist-loss realization + regime gating. Import guards from `lib/guards.py`.
   Portfolio accounting books P&L in EXIT period. Produce equity curve + per-trade blotter + regime-tagged P&L.
5. **COST-11 — Approved cost + fill realism layer.** Wire COST_STANDARDS per-order + STT/GST/stamp + 35bps small-cap
   slippage (2× on exits), circuit-lock skips, ADV-participation caps, gap-through on stops. Expose a `2x_stress` flag.
6. **VAL-11 — Walk-forward + validation battery.** 3y/1y/6m roll, ≤3×3 grid (§5), plateau check, DSR (honest count
   from §9) + PBO, regime slices (2018/2020/2022/2024/2026-thin), capacity test (₹1/5/10Cr), benchmarks
   (Nifty-500 B&H, naive RS always-on, always-on-no-regime). Report 1× AND 2× cost results. Open FINAL OOS ONCE.
7. **GATE-11 — Kill-criteria evaluation + IC pack.** Evaluate §8 kills mechanically; if it survives, assemble the
   IC memo (IC_MEMO_TEMPLATE) with per-trade edge, DSR/PBO, cost 2× pass/fail, capacity, correlation-to-short-vol-book,
   proposed size + WHY, kill criteria + review date → hand to Red Team (Nikhil) then CIO IC. If it fails a kill,
   → KILLED_IDEAS with resurrection condition.
8. **(conditional) V2-BACKLOG stub.** Only if v1 survives: scaffold VCP detector + CANSLIM/PEAD overlay one-pagers
   (separate RESEARCH_SOP intake each; NOT built here). Keeps scope honest — v2 needs its own gate.

---

## 11. BOARD-ROW UPDATE (return as text — I do NOT edit IDEA_PIPELINE.md)

Proposed IDEA_PIPELINE row for the Principal/R&D Head to enter:

| id | idea | sleeve | owner | stage | data | verdict | note |
|---|---|---|---|---|---|---|---|
| T2-MOM-01 | Track-2 small-cap leadership momentum (regime-gated) | Momentum | FM-Equities (Devika) / DESK-100 build | TRIAGE→CHEAP-TEST | READY (verified 2026-07-03) | **PROCEED** | Rebuild w/ volume+liquidity gate the prototype lacked; prior +11.6%/+16.1% OOS treated as PRIOR not result; kills pre-registered; family trials ≥4 carried into DSR. Spec: `04_RND_LAB/ideas/20260703_track2_engine_spec.md` |
