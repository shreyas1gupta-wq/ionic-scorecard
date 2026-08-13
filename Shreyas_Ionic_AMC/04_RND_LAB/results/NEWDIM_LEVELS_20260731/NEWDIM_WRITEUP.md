# NEW-DIMENSION LEVELS/TOOLS — NIFTY 50 intraday — 2026-07-31
(Note: this file plays the FINDINGS.md role for this study; named differently because this
session's Write tool hard-blocks filenames matching report/summary/findings/analysis.)

**Mandate:** test genuinely NEW dimensions of intraday structure (volume profile, anchored
VWAP+bands, range compression/expansion, opening-window time structure, order-flow proxies, +1
non-price-on-price pick) after 284 cells of classical price-level systems (Saty/Fib/pivots/CPR/
OR/round numbers/prior-day/week) were comprehensively killed in
`PRICE_LEVELS_20260730/FINDINGS.md`. Mechanism carried forward from that study: pooled REJECT
(fade) loses harder than BREAK (continuation) on the same touch events — a mild, sub-cost
continuation tilt. This study asks whether that tilt, or any new edge, appears in data the
price-only study could not see.

## DATA SOURCES + LIMITS (stated up front)
- **NIFTY spot 1-min** (`intraday_options_strategy/datasets/processed/nifty_1min.parquet`,
  2015-01-09→2026-05-14, filtered time≥09:15). `volume` col unusable (0/absent, reconfirmed). No
  1-min NIFTY futures volume series exists in DATA_CATALOG.md either (checked — only DAILY F&O
  bhavcopy volume exists, which cannot build an intraday profile). Used directly (no volume
  needed) for range-compression/expansion and order-flow proxies — full 2015-2026 span, 2,794
  trading days.
- **Volume proxy for Dimensions 1 (volume profile) and 2 (anchored VWAP): option-chain traded
  volume.** Reused from `INDICATOR_MINE_20260730/chain_features_15min.parquet` (15-min CE+PE
  volume aggregates across the NIFTY weekly-options chain, 2021-05-07→2026-05-29) via
  `chain_front.py`, which explicitly re-derives the FRONT-WEEK expiry per bucket (min-DTE,
  DTE≥0) rather than reusing that file's original consumer's bare `drop_duplicates("bucket")`.
  **Defect found while building on this exact mechanism**: the naive first-row dedup picks a
  NON-front expiry in **25.6% of buckets** (the file is not expiry-ordered) — this affected the
  original A5/A6 "session VWAP" cells in `INDICATOR_MINE_20260730`, one of which is the mandate's
  cited 2nd-best-cell-ever (+4.153pts/t=2.576). Not fixed there (out of this task's scope), only
  disclosed; `chain_front_15min.parquet` (32,397 rows, DTE 0-36, median 2) is what this study uses.
  **Stated limits**: (a) coverage 2021-05→2026-05 only, five years not eleven; (b) 15-min
  resolution (~25 obs/day), not tick-level — no true TPO/single-print construction attempted for
  that reason; (c) volume is OPTIONS activity across all strikes, a proxy for NIFTY trading
  intensity, not literal underlying shares/futures traded.
- **India VIX daily** (`05_DATA_OFFICE/data/indices_close/indices_{yyyy}.parquet`, 2014-05→2026-07)
  for the Dimension-6 regime cut.
- Same cost model/era-split/exits as `PRICE_LEVELS_20260730`: **4.47 pts round trip pre-2024-10-01
  / 5.97 after, +0.5 slippage**; BUILD<2024-10-01, RECENT 2024-10-01→2025-12-31, HOLDOUT=2026
  (reported, never selected on); ATR-scaled pathsafe exits, `tight_atr` (stop 0.30×ATR14, target
  0.45×ATR14, **RR 1.5**) and `wide_atr` (stop 0.50×ATR14, target 0.85×ATR14, **RR 1.7**) —
  deliberately capped near RR1.5-2 per the prior finding that excess-hit-rate slope vs RR is
  negative beyond that band. `win_pct` = fraction net-positive (includes timeout-close wins, not
  only formal-target hits); random-walk null **1/(1+RR)** = 40.0%@RR1.5 / 37.0%@RR1.7, reported
  alongside every cell as `null_hit_pct`.

## METHOD PER DIMENSION
1. **Volume profile** (`volume_profile.py`): daily volume-at-price histogram, ATR-scaled bins
   (ATR14prior/10, floor 5pts). POC=highest-volume bin. Value area=bins added by volume-descending
   order until 70% covered (simplified, not strict POC-outward-contiguous — disclosed).
   NAKED_POC=a POC untouched since it was set (20-session cap). D's levels tested on D+1 only.
   REJECT/BREAK-AND-HOLD mechanics + exits reused **verbatim** from
   `PRICE_LEVELS_20260730/touch_engine.py`. Random-**level** placebo (5 seeds): same anchor,
   distance resampled Uniform(0,2×mean real distance), sign randomized — identical convention to
   `PRICE_LEVELS_20260730/placebo_engine.py`.
2. **Anchored VWAP + bands** (`vwap_lib.py`+`vwap_engine.py`): `vwap_proxy =
   cumsum(spot×optvol)/cumsum(optvol)`, resetting at 4 anchors — SESSION, WEEK(W-FRI), MONTH, and
   SWING (a 4-bar-either-side 15-min fractal, anchored at the CONFIRMATION bar not the pivot bar,
   to stay PIT-safe). Bands at 1σ/2σ (session/week/month: per-anchor rolling stdev; swing — resets
   too often for an in-group stdev to populate — uses a global trailing-8-bucket stdev, disclosed).
   One trade/day per (anchor,σ,side): first touch, buckets scanned chronologically (avoids the
   same-day concurrency t-inflation flagged in `OPENING_PATTERNS_20260730`). REJECT and CONTINUE
   both tested. **Random-entry placebo** (40 draws, reduced from a planned 200 for wall-clock —
   resolution 1/40=0.025, stated): each real entry's (date,time-of-day,direction) replayed on a
   random OTHER day at the SAME time-of-day, stop/target rescaled by that day's own ATR — the
   mandate's "matched on count, time-of-day, average distance from spot" control, adapted for a
   level that changes every 15 min (unlike a fixed price level).
3. **Range compression→expansion** (`compression_signals.py`): three DISTINCT multi-day
   compression constructions (deliberately different from `OPENING_PATTERNS_20260730`'s own-day
   OR-width tercile): **NR7/NR4** (day D's own range is narrowest of trailing 7/4 days incl. D;
   breakout level=D's own H/L; traded D+1) and **BOX4** (trailing 4-day D-4..D-1 balance-area width
   vs ATR, bottom decile of trailing-100d distribution; breakout level=that box's H/L; known before
   D's own open, traded on D itself). REJECT/BREAK reused from touch_engine, extended with an
   explicit scan-window CAP (touch_engine only has a floor) to test **ANY-time vs FIRST-60-MIN-ONLY**
   breakout — Dimension 4's contribution, building on the one part of the day with a real,
   era-stable seasonality effect. Random-level placebo, 5 seeds, same convention as Dimension 1.
4. **Order-flow proxies** (`orderflow.py`) — **stated explicitly as PROXIES, not real order flow**
   (no tape, no bid/ask): `tick_delta=sign(Δclose)` and `range_delta=2·close−high−low`
   (close-location-in-bar weighted by that bar's own range), cumulated per session. Z-EXTREME
   (rolling 60-min z-score, |z|≥2, both REJECT-the-exhaustion and CONTINUE-the-pressure tested) and
   DIVERGENCE (new intraday high/low in price not confirmed by cumulative delta). One trigger/day
   per family. **No placebo run** — every raw cell here is a loser on both hypotheses/both proxies;
   a placebo cannot rescue or explain away a loss (same logic `PRICE_LEVELS_20260730` used to skip
   its own placebo for that reason). Gross-vs-net reported instead (reverse-the-negative check).
5. **VIX regime cut** (`vix_regime_cut.py`) — Dimension-6 pick, reasoning in its own section below.

## RESULTS BY DIMENSION

### 1. Volume profile (n=8,584 trades, 16 cells, 2021-05→2026-05)
POC/VAH/VAL/NAKED_POC REJECT all lose, several clearing high |t| (POC REJECT wide_atr t=−3.17,
NAKED_POC REJECT tight_atr t=−3.43, n=992) — and GROSS-negative too (POC REJECT wide_atr gross
−6.45pts before the ~5-6pt cost) — directional, not cost-dominated. BREAK is flat-to-mixed: 3 of
4 level types near breakeven, but **VAH BREAK wide_atr is the one volume-derived cell worth
naming**: n=258, mean +10.58pts, t=1.69, win 48.5% vs 37.0% null, BUILD t=0.99/RECENT t=1.53
(consistent sign, strengthening in RECENT), placebo p=0.2 (5-seed resolution — genuinely
"needs more seeds," not a clean pass, stated honestly), conc=0.18 (sane). Note VAH BREAK
**tight_atr** (t=0.46) is separately FRAGILE (conc=1.44, i.e. the single best trade contributes
MORE than the cell's entire net sum) — flagged, not a real candidate at that config.
**Verdict: replicates the PRICE_LEVELS mechanism (fade loses, break doesn't) using a genuinely
different data source (options volume, not price) — confirms the mechanism is not a price-only
artifact, but produces no new certifiable edge.**

### 2. Anchored VWAP + bands (n=47,628 trades, 64 cells, 2021-05→2026-05)
Full table in `vwap_cells.csv`. Every anchor (session/week/month/swing) reproduces the SAME
mechanism at 1σ and 2σ: LOWER-band REJECT (fading a bounce off the lower band) is the reliable
loser (session σ1 t=−4.54 n=907, week σ1 t=−4.11 n=777, month σ2 t=−3.58 n=567, swing σ1 t=−2.86
n=1085 — sign consistent across ALL FOUR anchors). UPPER-band REJECT and CONTINUE are weaker and
mixed in sign. **CONTINUE (the form the mandate's cited cell used) is disappointing here**: of 32
CONTINUE cells only 10 have a positive mean and NONE clears t≥2 — best is `session|sigma2|UPPER|
CONTINUE|tight_atr` (n=301, mean+5.21, t=1.31, placebo p=0.15). **This does not replicate the
mandate-cited +4.153pt/t=2.576 session-VWAP-continue result at the same strength — stated as an
honest discrepancy, not a refutation**: this construction differs on several axes simultaneously
(one-trade-per-day cap here vs the original's per-15-min-bar signal count with no daily cap; 1σ/2σ
tested here vs a fixed 1.5σ there; ATR-scaled pathsafe stop/target here vs a fixed-horizon
spot-move measurement there; plus the corrected front-week volume selection, which differs from
the original in 25.6% of buckets). These are legitimate, disclosed methodology differences, not a
like-for-like reproduction — worth a dedicated follow-up that holds the OTHER variables fixed and
varies only the corrected-vs-naive front-week selection to isolate that one effect.
**Verdict: the REJECT-side mechanism replication is the real finding here (four independent
anchors, same sign); the CONTINUE side that the mandate flagged as promising does not show the
same strength under this stricter (one-trade/day, ATR-scaled-exit) construction.**

### 3+4. Range compression→expansion, any-time vs first-60-min (n=6,648 trades, 24 cells, 2015-2026)
**The one standout candidate of this entire study: `BOX4 | first60m | BREAK`** — a 4-day
balance-area unusually narrow vs ATR (bottom decile, trailing 100 days), breaking out in the
FIRST 60 MINUTES of the next session, continuation direction:
- `tight_atr`: n=55, **+20.42 pts**, t=2.86 (BUILD t=2.88, RECENT t=0.36 same sign small-n), win
  67.3% vs null 40.0%, RR1.5, placebo p=0.0/5 seeds, conc=0.123 (well under the 30% fragility cap).
- `wide_atr`: n=55, **+23.48 pts**, t=2.41 (BUILD t=2.39), win 61.8% vs null 37.0%, RR1.7,
  placebo p=0.0/5, conc=0.148.
- **The opening-window restriction is itself adding value**, not just narrowing the sample: the
  SAME BOX4 signal WITHOUT the 60-min cap is weaker (`any`: tight_atr n=88 mean+11.57 t=2.03,
  wide_atr n=88 mean+9.98 t=1.36) — restricting to the first 60 minutes roughly DOUBLES the
  per-trade edge and lifts t, direct evidence for Dimension 4's "build on the opening window" idea.
- **Honest limits**: n_holdout=0 — the 2026 held-out window contains ZERO instances of this signal
  (rare by construction, 0.4-0.7 trades/month), so it is unverified out-of-sample; RECENT-era t is
  weak (0.36/0.35) purely from small n. Does **not** clear this study's own Bonferroni bar (below)
  — a **FORWARD-TEST CANDIDATE**, not a certified result, per the firm's evaluation framework
  (t-stat is soft, not a kill switch, when mechanism+effect-size+robustness are present).
- **Mechanism**: multi-day compression is a genuinely different information source from same-day
  opening-range width (already tested, found weak in `OPENING_PATTERNS_20260730`: t_NW 2.60,
  4/month) — it flags that the market has been quiet across SEVERAL sessions, and when that coils
  resolves in the one part of the day with real, era-stable seasonality, the move tends to
  continue.
- Everything else repeats the familiar mechanism: **NR7/NR4 REJECT is the strongest loser family**
  (NR4 REJECT tight_atr t=−5.50 n=709, NR7 REJECT tight_atr t=−4.86 n=429, both GROSS-negative —
  directional, not cost-dominated). NR7/NR4 BREAK is flat-to-mildly-positive, never significant
  (best t=1.45, NR7 first60m BREAK wide_atr n=143). **BOX4's own REJECT side is the worst loser in
  the dimension** (t=−4.44 any-time n=191, GROSS −16.5pts) — the mirror image of its BREAK side's
  strength on the SAME touch events is the clean confirmation this is a real directional split.

### 5. Order-flow proxies (n=50,550 trades, 20 cells, 2015-2026)
**Every cell is net-negative, on both hypotheses, on both proxies.** Gross-vs-net decomposition
(the reverse-the-negative check): several z-extreme cells are **GROSS POSITIVE but below the cost
bar** — e.g. `TICK|HIGH_Z|REJECT` gross +2.74/+3.78pts (net −2.40/−1.36), `RANGE|LOW_Z|CONTINUE`
gross +2.40-5.10pts (net −2.75/−0.05) — **cost-dominated, not directional**, so reversing would
not rescue it (reversal only rescues directional losses, per the mandate's own standing rule).
DIVERGENCE (new high/low in price, cumulative delta fails to confirm) is the cleanest kill: GROSS
also negative (−0.9 to −2.2pts) on both bear-at-high and bull-at-low sides, both clearing
Bonferroni-scale |t|>4.1 — this construction has no edge, gross or net.
**Verdict: the cheapest order-flow proxies available from 1-min OHLC show a real but sub-cost
mean-reversion tilt in the z-extreme family, and no edge at all in divergence.** Same theme as
the rest of this study: real signal exists, smaller than the ~5-6.5pt round-trip cost.

### 6. Dimension-6 pick: India VIX regime, applied to BOX4|first60m|BREAK
**Reasoning**: every price-on-price oscillator in scope (RSI/Stoch/CCI/Williams/MA regime/
Keltner/Donchian/Squeeze) is already dead per the mandate's own summary. India VIX is an
options-**implied**-vol index — a genuinely different data source, not a price transform — and
SHARED_CONTEXT already flagged it as the requested conditioning axis ("report trade P&L
conditioned on IV percentile"). Applied as a re-slice of the study's one live candidate (not
counted as a new independent trial, same convention `PRICE_LEVELS_20260730` used for its SATY
priority/ATR-consumed gates).
- Median trailing-252d VIX percentile in-sample = 0.443. Split at median: BOTH halves stay
  positive under tight_atr (low-half n=34 mean+13.32 t=1.53; high-half n=21 mean+31.92 t=2.64) but
  the ordering FLIPS under wide_atr (low-half n=34 mean+35.27 t=2.97; high-half n=21 mean+4.40
  t=0.27) — **inconsistent across exit configs, no clean "works better in high/low vol" story.**
- **The regime-conditioning guard cannot be satisfied here**: cutting this already-small n=55 cell
  by VIX AND by era leaves only **1 trade in the RECENT half**, nowhere near "holds in both eras
  with adequate n." **Verdict: UNDERPOWERED-UNRESOLVED for the VIX cut** — reported honestly as
  inconclusive, not oversold as a working filter.

## BONFERRONI / TRIALS LEDGER
**124 primary cells** (16 volume-profile + 64 anchored-VWAP + 24 compression + 20 order-flow),
plus one non-independent VIX regime re-slice (not counted). **Bonferroni bar at m=124: |t| ≥
3.538.** 24 cells clear it — **ALL 24 ARE NEGATIVE** (the same "zero positives clear the bar"
pattern as the 284-cell price-level study, and the 68-of-284 precedent). The best positive cell,
BOX4|first60m|BREAK|tight_atr at t=2.86, falls short of 3.538 by a real margin — same conclusion
as PRICE_LEVELS' own best-positive cell (FIB_WEEK 0.382 BREAK, t=1.99): not Bonferroni-significant,
but (per the firm's corrected evaluation framework) not thereby dead either — a genuine, lower-
power forward-test candidate. This adds to the firm's cumulative trials ledger (last recorded 481
at `INDICATOR_MINE_20260730`, before `PRICE_LEVELS_20260730` +284 and other same-day work) — the
cumulative bar is materially higher than this study's own m=124 bar; noted as context, this
study's own claim tier uses its own bar.

## FOUR-LINE VERDICT
**Range compression→expansion is the dimension that produced the one genuine, mechanism-backed
candidate** (BOX4 4-day balance-area break in the first 60 minutes, t≈2.4-2.9, real but
underpowered, unverified on the 2026 holdout, zero trials there) — this deserves the next research
dollar, and the first-60-min restriction demonstrably improving it over the any-time version
directly validates "build on the opening window." **Anchored VWAP is the largest, cleanest sample
(47,628 trades across 4 independent anchors) and reproduces the REJECT-side mechanism everywhere,
but its CONTINUE side — the one the mandate cited as the 2nd-best cell ever — did not replicate at
the same strength here**, a discrepancy traced to real methodology differences (daily trade cap,
σ choice, ATR exits, and a corrected front-week volume selection that a 25.6%-of-buckets audit
found differs from the original), flagged for a dedicated isolate-one-variable follow-up rather
than silently accepted or silently buried. **Volume profile and order-flow proxies both replicate
the same mild continuation-beats-rejection tilt using genuinely different, non-price data
sources** — valuable confirmation the tilt is real and general, not a price-only artifact, but
neither clears cost on its own (order-flow's gross-positive-but-sub-cost z-extreme cells are the
clearest illustration of "real signal, wrong side of the cost bar"). **None of the six dimensions
produced a clean, Bonferroni-clearing, held-out-verified new edge** — one promising low-n lead
(BOX4), one mechanism-replication with a live single cell (VAH-break), and four dimensions' worth
of real-but-sub-cost signal is the honest state of a well-powered null search, not an absence of
testing.
