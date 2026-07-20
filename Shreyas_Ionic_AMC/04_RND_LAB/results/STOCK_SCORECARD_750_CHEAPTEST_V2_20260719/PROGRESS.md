# STOCK_SCORECARD_750 CHEAP-TEST V2 — PROGRESS
Owner: Arjun Rao (quant-head). Started 2026-07-19.

## GOAL
Deeper validation of the CURRENT (v6.3) frozen methodology: decile forward-return power of the
composite score, PIT-safe, on the 332-name reference universe. 3Y-weighted vs 1Y-weighted composites
tested SEPARATELY (distinctness claim). Hard gates = placebo + regime decomposition. Plus sector-exemption
artifact check and a SEPARATE face-validity check of analyst expected_next_3y_growth on the 84 researched names.

## METHOD DECISIONS (locked)
- Universe = 332 from reference_full_with_portfolio.csv (survivor-biased current membership; << full 750; noted).
- Pillars computed PIT: Quality, Growth, Value(4-comp), Stage-mechanical, SectorMacro-mechanical, Accumulation.
  Ownership Flow DROPPED (no FII/DII history in local data) -> weights renormalized over 6 pillars/horizon.
  Regime weight-tilt & sector-macro regime_fit_adj SKIPPED historically (can't PIT-reconstruct current-regime call).
- Formulas reverse-validated vs reference CSV: quality=mean(roe_pct,roce_pct) exact; value 4-comp exact;
  stage_3y=mean(ret12,ret24,rs12)x(1 if>200dma else 0.5); stage_1y=mean(ret3,ret6,rs3)x(50dma gate)+tiny RSI;
  sector_macro=pctile(sector_mean_ret); accumulation=pctile(OBV slope). Composite base-wt blend recon corr:
  all-7=0.987, 6-pillar-no-ownership-renorm=0.963 vs CSV composite_3y.
- shares_i = market_cap_approx*1e7/latest_close (BHEL check = 348cr shares, exact). mcap_fd=shares*close_fd.
- PE=close/EPS; PB=mcap/bookequity (rank-invariant units); fcf_yield=avg_fcf/mcap.
- Winsorize 2/98 each raw input within panel before ranking. Gates: BS(fin-sector D/E exempt)+liquidity. Penalty/boost.
- Primary horizon 12M fwd (Adj Close), monthly rolling 2021-08-31..2025-06-30 (matches original). 36M = context.
- Placebo: shuffle composite within month, 200 draws, seed 20260719, decile spread D10-D1 kill bar.

## STATUS
- [DONE] read prior cheap-test, FROZEN_METHODOLOGY v6.3, probed data coverage, reverse-eng formulas
- [IN PROGRESS] writing engine v2_scorecard_pit.py
- [ ] run engine, validate vs CSV at current date
- [ ] aggregate metrics, sector-exemption check, face-validity, write config/metrics/summary

## OUTPUT DIR
Shreyas_Ionic_AMC/04_RND_LAB/results/STOCK_SCORECARD_750_CHEAPTEST_V2_20260719/

## RUN-1 RESULTS (2026-07-20) — 36 monthly formations 2022-07..2025-06
- final_3y_adj: decile spread -13.3pp, mono_rho -0.58 (INVERTED), IC -0.062 NW-t -2.53, placebo pctile 0.0 (p=1.0 -> SIGNIFICANT NEGATIVE)
  decile D1..D10 fwd12m: +54.4 +45.5 +46.7 +39.0 +32.0 +28.6 +33.1 +28.3 +33.2 +41.1  (D1 lowest-score = HIGHEST return)
- final_1y_adj: spread -3.2pp, mono -0.07 (FLAT), IC +0.015 NW-t 1.38 (n.s.), placebo pctile 12 (fails to beat null)
- combined 60/40: spread -10.7pp, IC -0.034, placebo p=1.0
- distinctness: rankcorr(3y,1y)=0.53 (DISTINCT, not copies); combo does NOT beat 1Y-alone
- 36M context: spread -73pp, IC -0.067 (also negative at 3y horizon)
- sector-exemption: BENIGN — financials 8.4% of top decile vs 15% of universe (UNDER-rep, no artifact)
- CONFIRMED not a bug: panel spot-check 2023-03 D1 fwd +143% vs D10 +94% (junk melt-up); score orientation correct (Hold 53 vs Sell 41)
- KEY DRIVER: fundamental tilt (Q+V+G=58% of 3Y) fought the 2023-24 small/mid junk melt-up and lost over the ONLY testable window
- run-2 (enhanced, decomposition ic_qv/ic_qual/ic_val/ic_mom3 + pillar-save) IN PROGRESS to separate window vs composition

## COMPLETE (2026-07-20) — run-2 (with decomposition) DONE
- FACTOR DECOMPOSITION (headline): Value IC +0.095 (NW-t +2.46, 89% mo pos) ROBUST POSITIVE;
  Quality IC -0.106 (NW-t -1.93, worst in melt-up -0.235) NEGATIVE; Momentum +0.060; Q+V equal -0.016 (null);
  full 3Y composite -0.034. => composite equal-weights a good Value signal vs a regime-negative Quality signal.
- Deliverables in run dir: config.json, metrics.json (incl. DECOMP), v2_scorecard_pit.py, SUMMARY.md,
  face_validity.json, panels/ (36 parquets), run.log/run2.log.
- VERDICT: WEAKER than original as a composite (inverts/nulls, fails placebo+monotonicity on the only
  testable window 2022-07..2025-06), RICHER in diagnosis. Weakest assumption: the original's positive
  early window (2021-08..2022-05) is NOT PIT-testable here; everything testable is quality-hostile.
- TASK DONE. Findings returned to coordinator.

## ADDENDUM (Principal follow-up 2026-07-20) — DROP Quality entirely
- Recompute (needed: sector_macro_1y/accum_1y weren't cached). Quality dropped, 5 pillars renorm, overlays identical.
- noQ_3y: IC +0.005 (nwT +0.22), placebo pctile 52 (p=0.48) -> significantly-NEGATIVE base becomes NULL (inversion fixed, no edge).
- noQ_1y: IC +0.066 (nwT +2.18), mono +0.52, placebo pctile 83 (p=0.17) -> weak & FRAGILE (fails >95 kill-bar, melt-up-only +0.160, recent INVERTS -0.067).
- VERDICT: moderates negative into noise; does NOT create a placebo-clearing positive. Isolated Value (+0.095, t+2.46) beats every blend.
- metrics.json key "no_quality_composite" added (base keys byte-identical). SUMMARY.md ADDENDUM appended. Script updated. DONE.
