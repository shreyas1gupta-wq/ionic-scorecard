# W5PC — PEAD + Technical Confirmation ("Minervini earnings-breakout") clubbed test

**Owner:** Dhruv Kapoor (Technical) · **Date:** 2026-07-17 · **Script:** `rnd/wave4/run_w5_pead_clubbed.py`
**Card:** `rnd/cards/W5PC_pead_clubbed.json` · **Event-level parquet:** `rnd/wave4/w5pc_event_level.parquet`

## Question
Plain event-time PEAD is dead (`W3_pead_eventtime`: IC -0.0032, n=2642, KILLED). Does clubbing the
earnings-surprise signal with a Minervini-style technical confirmation — **top-decile surprise AND
volume-surge AND gap-up AND uptrend** — revive it as an entry-timing overlay?

## [DATA] Method / no-lookahead
- Reuses the exact `W3_pead_eventtime` event-window construction: market-adjusted abnormal return
  (stock minus NIFTY500) over `[+2 trading days, +45 calendar days]` anchored to `available_date`
  (real board-meeting date, PIT, `date_source=='actual'` only).
- **np_surprise**: known at `available_date` — no lookahead (own-trailing-4Q-trend expectation).
- **volume-surge**: max volume in `[event_pos, event_pos+2]` / trailing median volume in
  `[event_pos-63, event_pos-3)` (63-session lookback, 3-session gap to exclude pre-print run-up).
  Known at/after print.
- **uptrend**: close(event_pos) vs trailing 150DMA ending at event_pos (trailing only, no forward peek).
- **gap-up PROXY**: `close(event_pos-1) -> close(event_pos)` return > +2%. **Caveat:** no
  `cube_open_long.parquet` exists in this repo — true 09:15 opening-gap data is not available, so this
  is a close-to-close reaction-day proxy, not a real gap. Flagged, not hidden.
- Top-decile surprise computed **within** the recent-era matched subsample (not the full-history
  distribution), to keep the population internally comparable.

## [DATA] RECENT-ERA-ONLY — flagged prominently
`cube_volume.parquet` starts **2021-07-16**. The underlying quarterly-PIT candidate pool itself is
already ~2020+ (W3's own date range: 2020-01-30 → 2025-11-14), so restricting to
`available_date >= 2021-07-16` only trims ~10 of 4396 candidate events — this is **not** a large cut
relative to the existing PEAD test, but it means **neither** the plain-PEAD comparator **nor** this
clubbed test has any pre-2020/pre-2021-07 coverage. One market regime, thin sample at the sharp end.
Date range actually tested: **2021-07-21 → 2025-11-14**.

## Results

| Group | n | mean abn_ret | median | hit-rate | skew | up/down ratio | low-t? |
|---|---:|---:|---:|---:|---:|---:|---|
| Plain PEAD (matched universe, all surprises) | 2632 | -0.31% | -1.25% | 44.0% | 0.70 | 1.16 | no |
| Surprise top-decile ONLY | 264 | -1.04% | -1.65% | 41.3% | 0.67 | 1.09 | no |
| + volume-surge >2x ONLY | 206 | -1.05% | — | 40.3% | 0.52 | — | no |
| + volume-surge >3x ONLY | 162 | -0.79% | — | 42.0% | 0.50 | — | no |
| + uptrend (>150DMA) ONLY | 140 | -0.52% | -1.43% | 42.1% | 0.46 | 1.20 | no |
| + gap-up-proxy ONLY | 57 | -0.56% | — | 45.6% | 0.59 | — | no |
| **FULL CLUB (vol>2x + gap + uptrend)** | **29** | **+1.01%** | +0.84% | **55.2%** | 0.60 | 1.05 | **YES** |
| **FULL CLUB (vol>3x + gap + uptrend)** | **24** | **+2.99%** | +2.87% | **66.7%** | 0.70 | 1.11 | **YES** |

## [INFERENCE] Reading
1. **No single confirmation revives it alone.** Volume-surge alone, uptrend alone, and gap-up alone
   each still show a NEGATIVE mean abnormal return (-0.5% to -1.1%) — none flips the sign of dead PEAD
   by itself. Uptrend-only comes closest (smallest loss, -0.52% vs -1.04% for surprise-decile alone).
2. **Only the FULL stack (all three technical filters together) flips positive** — mean +1.0% to +3.0%,
   hit-rate 55-67% vs the 44% baseline (plain PEAD) and 41% for surprise-alone. This is a genuine,
   sizeable directional flip, not a marginal wobble.
3. **n=24-29 for the full club is thin — low-t rule invoked.** This is judged on effect size and
   mechanism, NOT statistical significance (no p-value/DSR claim is being made). At this n, a handful
   of large winners can dominate the mean; the median (+0.84% / +2.87%) confirms the flip isn't purely
   mean-driven by one outlier, which is reassuring, but 24-29 events over one ~4.3-year window is not
   enough to certify anything.
4. **The edge, where it appears, is a HIT-RATE effect, not a convexity/skew effect.** Upside/downside
   ratio for the full club (1.05-1.11) is essentially the SAME as plain dead PEAD (1.16) — the whole
   sample carries a modest ~+0.7 skew regardless of grouping (ordinary equity-return skew, not
   something the technical filter is adding). The story is "more of the clubbed trades win" (55-67%
   vs 44%), not "the winners are much bigger relative to the losers." **Payoff is NOT meaningfully more
   convex** — this is a hit-rate/entry-timing story, consistent with Dhruv's overlay mandate (timing,
   not a standalone tail-convexity source).
5. Mechanism plausibility: this is exactly the Minervini "earnings breakout" pattern — a strong
   surprise that the market confirms with volume + a same-day pop + an already-established uptrend is
   a genuinely different animal from a strong surprise in isolation (which can be a value-trap beat, a
   one-off, or fought by institutions distributing into the print). The mechanism is sound; the sample
   is too thin here to confirm it's tradeable at scale.

## [OPINION] Verdict
**MAYBE — plausible revival as an entry-TIMING overlay, not certified.** The technical confirmation
stack (volume + gap + uptrend, ALL required) does flip the dead-PEAD sign and roughly doubles hit-rate
in this recent-era sample, matching the Minervini mechanism (don't buy the surprise, buy the surprise
the TAPE confirms). But n=24-29 is a cheap-test-grade sample, one-regime, and the "gap-up" is a proxy
(no true opening-gap data). This is NOT a certified factor and should NOT be sized as a standalone
cross-sectional signal — it is, at most, a confirmation filter layered onto an existing fundamental
signal at entry time, and it needs a larger/longer sample (more history, or a broader universe) before
any capital allocation. Individual confirmations (volume-only, trend-only, gap-only) do NOT work alone
— clubbing genuinely appears necessary, not just additive noise, but "appears" is doing real work in
that sentence at n=24.

## Invalidation / what would kill this
- A larger sample (e.g. extending volume history, or widening the universe) that flattens the hit-rate
  back toward ~44-50%.
- A true open-price gap definition (vs the close-to-close proxy used here) failing to reproduce the flip.
- A regime check showing the +full-club effect concentrated in one narrow sub-period (2021-07 to
  2025-11 spans very different vol/liquidity regimes — no era-split was run here; flagged as NEXT STEP,
  not done).
