# ALPHA_RANKER — Killed Hypotheses Log

Per RESEARCH_PROTOCOL.md §4: every KILL verdict is logged here with reason, never retested
as-is without meeting a stated resurrection condition. Cards (full evidence) live in `rnd/cards/`.

## H001 — 65DMA vs 50DMA (2026-07-16)
**Verdict: KILL** (all 12 sub-cards: dist/slope/stack x {50,65}DMA x {1M,1Y}).
Reason: every variant fails PBO>0.5 (CSCV, range 0.85-1.00); most 1M variants additionally fail
IC_IR>=0.20 and/or lag_test_delta<=0.25.
**Not a wash on the underlying question** — the pre-registered kill criterion "65DMA not >= 50DMA
on OOS IC_IR" did NOT trigger: 65DMA's IC_IR >= 50DMA's in 5/6 construct x horizon comparisons
(loses only marginally on the 1M stack score, 0.135 vs 0.145). See `rnd/cards/H001.json`.
**Resurrection condition:** a longer/less-autocorrelated panel (current: 61 monthly dates, ~36-48
valid for 1Y) that lets PBO/DSR discriminate rather than blanket-failing every candidate in the
family (see H002 issue note) — or a redefined evaluation basis that isn't dominated by the same
PBO/DSR artifact. Do not resurrect on IC_IR alone.

## H002 — MA-period sweep {20..200} (2026-07-16)
**Verdict: KILL** (all 48 sub-cards: dist/slope x 12 periods x {1M,1Y}).
Reason: PBO>0.5 on every single variant; most 1M variants also fail IC_IR>=0.20 and/or
lag_test_delta<=0.25. DSR ~0 across the board (see issue note below).
**Pre-registered kill criterion "no stable plateau (isolated spike only)" did NOT trigger** —
found two genuine non-spike shapes: (1) distance-from-MA plateaus generically at longer windows
(100-200d, both horizons), (2) MA-slope at 1Y has a real hump centered on 55-75d (peak at 65-75),
directly supporting 65 as a structurally sound choice for the slope construct specifically.
See `rnd/cards/H002.json` for the full 12-point curve per construct/horizon.
**Disclosed issue (not a silent pass-through):** running the full 48-variant sweep in one session
under a single family id drove trials_counter to n=48 for family "H002", which the harness's
sigma_SR=1 DSR deflation punishes to ~0 regardless of true signal quality; PBO also fired at
0.85-1.00 on literally every one of the 62 cards this session (including IC_IR>0.7, clean-lag
cards), which reads as suspiciously blanket rather than differentiated. Flagged to Dr. Sameer
Bhat / the prioritizer, not diagnosed further (out of this worker's scope — harness.py untouched).
**Resurrection condition:** re-score under smaller per-length families (avoid the bulk-sweep DSR
penalty), or with harness owner sign-off on the PBO/DSR sensitivity noted above.

## H042 — MA slope vs distance robustness, 65DMA @ 1M (2026-07-16)
**Verdict: KILL** (both sub-cards).
Reason: distance-from-65DMA IC_IR=-0.077 (negative) with lag_test_delta=1.796 (fails badly);
slope-of-65DMA IC_IR=0.126 (positive but < 0.20 floor) with lag_test_delta=0.014 (clean) — both
fail PBO>0.5.
**Clean directional finding despite the KILL:** slope is unambiguously more robust than distance
at 1M — stable under the lag perturbation where distance is not (a mean-reversion/noise artifact
sign flip). See `rnd/cards/H042.json`.
**Resurrection condition:** same as H001 (panel-length / PBO-sensitivity dependent); if revisited,
build ONLY the slope construct, never bare distance-from-MA at 1M.
