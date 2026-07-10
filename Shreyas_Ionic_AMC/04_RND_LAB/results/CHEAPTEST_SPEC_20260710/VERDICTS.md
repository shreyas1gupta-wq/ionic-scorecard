# CHEAPTEST_SPEC_20260710 — CONSOLIDATED VERDICTS
_Compiled by Head of Quant (Arjun Rao), 2026-07-10. All numbers cross-checked against on-disk result files (spot-checks: T1 RESULTS.csv, T3/T4 result JSONs, fvg results.csv, rs headline.csv, spread-calibration CSVs — all match agent claims)._

## Verdict table

| Test | Pre-registered kill bar | Measured | Verdict | Files |
|---|---|---|---|---|
| T1 regime Layer-1 (A/B/C/D 30-min drift) | day-clust \|t\|>=3 AND >=6 pts/30min, per regime | best regime A: +0.71 pts, t=2.20; 0/4 pass; max effect anywhere 1.03 pts (6-30x short) | **KILL** | `t1-regime/` (SUMMARY.md persisted by parent; RESULTS.csv, LAG1BAR.csv, PLACEBO_SHUFFLE.csv, regime_bars.csv.gz) |
| T2 PDH/PDL sweep reversal | (frozen in t2 script) | run INCOMPLETE — 200-shuffle placebo loop still executing; variant stats partial (13 rows), no verdict returned | **BLOCKED (run incomplete)** | `t2-sweep/` (t2_sweep_test.py, t2_events.csv, t2_variant_stats.csv — no SUMMARY) |
| T3 premium-confirmation filter (F8) | spread >=4 pts AND t>=2 (+80% scarcity) | spread +1.55 pts, t_clust=0.66; placebo p=1.00; 1-bar-lag spread LARGER (+3.54) = noise signature; 2023-26 spread +0.15 | **KILL** | `t3-premium-confirm/` (SUMMARY.md, t3_results.json, t3_events.csv) |
| T4 GLBS score-gate >=4/6 confluence | Spearman t>=2 AND top-bottom >=6 pts; top bucket >=10 pts | rho=0.017 t=1.67; spread 1.80 pts; top bucket 1.68 pts (6x short); placebo p=0.405; lag-fragile (134% collapse) | **KILL** | `t4-score-gate/` (SUMMARY.md, t4_result.json, 4 CSVs, README_trials.md, atm5_cache/ reusable) |
| T5 0DTE gamma/trend ride | conditional on T1 regime-C surviving | T1 regime C FAILED (effect -0.82 pts, t=-1.83) -> gate not met. Run also incomplete (t5_trades.csv 224 trades / t5_era.csv on disk, no verdict returned; era pf<1 in visible rows) | **MOOT (gate failed)** | `t5-0dte-gamma/` (t5_0dte_gamma.py, t5_era.csv, t5_trades.csv — no SUMMARY) |
| T6 OI-wall support/resistance | (frozen in t6 script; 3-bar-lag build) | run INCOMPLETE — 261-expiry computation still in background, scripts only on disk | **BLOCKED (run incomplete)** | `t6-oi-wall/` (t6_oi_wall.py, verify_oi*.py — no results yet) |
| FVG flags (a) sweep+FVG reversal (GLBS-A) | effect >=5 pts AND t>=2.5 | 1m: -4.56 pts t=-4.92 (actively loses); 5m: +0.61 t=-0.66 | **KILL** | `fvg-flags/` (SUMMARY.md, results.csv, events.csv 39,316) |
| FVG flags (b) FVG-retest continuation (GLBS-E) | effect >=5 pts AND t>=2.5 | 5m real but tiny: +1.13 pts t=3.29 (4.4 pts below floor, below ~10-pt option round-trip); 1m opposite-signed t=-32 | **KILL** | same |
| F9 RS BANKNIFTY-vs-NIFTY | >=4 pts AND day-clust t>=2 | 30-min +0.46 pts t=1.39; 60-min +0.25 t=0.31; era sign-flip; placebo p=0.555 | **KILL** | `rs-nifty-bn/` (SUMMARY.md, headline.csv, era_table.csv, events_h30/60.csv) |
| Breadth builder (F10 infrastructure) | none (BUILD task) | 1,552 days 2020-2025 built, sanity vs 5 known dates PASS; informational check: D-1 breadth does NOT condition next-day intraday (Q5-Q1 t~-0.2) | **PASS (build)** | `breadth-builder/` (breadth_daily.parquet, SUMMARY.md, conditioning_check.csv) |
| Spread calibration | none (measurement) | 0DTE ATM one-way ~1.24 pts med / 1.93 p75 (2025-26); Angel live single-stock 0.56%/0.83% one-way validates COST_STANDARDS band; COST_STANDARDS index floor ~12x too low -> flag to Tara (D-021 process) | **MEASUREMENT-COMPLETE** | `spread-calibration/` (SUMMARY.md, 6 CSVs, run logs) |

## Survivors
**None of the alpha hypotheses survived.** 6 signal tests KILLED (T1, T3, T4, FVG-a, FVG-b, F9); T5 moot (conditional gate failed at T1); T2 and T6 blocked pending background runs — they are the only two tests that could still produce a survivor.

Non-signal deliverables that stand and feed forward:
1. **breadth_daily.parquet** — usable as regime-engine input / baseline covariate only, NOT a direction signal. Next gate: none (infrastructure); register in DATA_CATALOG via Kavya.
2. **Spread calibration** — adopt interim slippage rule for all future 0DTE tests: BASE 1 index pt one-way, STRESS 2 pts, 2x multiplier 09:15-09:30, exclude/penalize 15:00+ 0DTE buys. Next gate: Tara to run D-021 amendment of COST_STANDARDS index-ATM floor (measured ~12x above current floor).
3. **atm5_cache/** (T4, 18MB ATM 5-min front-weekly build) — reusable by T2/T6 follow-ups.

## Next-gate recommendations
- **No Gate-4 backtest is warranted from this battery.** Every measured effect is 4-30x below its own pre-registered bar AND below the measured cost floor (~1-2 pts one-way index slippage vs 0.2-1.8 pt edges).
- T2, T6: single action — let the background runs complete, append their verdicts here (same frozen bars; no re-runs, no threshold changes). If either passes, THEN spec a Gate-4 via /backtest with the spread-calibration slippage rules baked in.
- File kill entries in KILLED_IDEAS: T1 regime Layer-1 (resurrection: Principal-supplied original thresholds, one re-run max), T3/F8 (resurrection: structurally different confirmation — order-flow/OI via T6 route only), T4 GLBS score-gate + GLBS-A/GLBS-E (K-001-consistent: no filter combination rescues intraday buying), F9 RS (resurrection: sub-minute BN futures order-flow lead only; no window/threshold retunes).
- Data Office: Kavya to add `intraday_options_strategy/datasets/processed/{nifty,banknifty}_1min.parquet` to DATA_CATALOG (found present but uncataloged during F9).

## Notes on verification
- All KILL verdicts backed by on-disk numbers; no UNVERIFIED findings.
- T1 SUMMARY.md was blocked at subagent level (known harness issue, journal 2026-07-07); parent persisted verbatim content to `t1-regime/SUMMARY.md`.
- Trial ledger totals across battery: T1=4, T3=1, T4=1+5 marginals, F9=2, FVG=2 sub-tests, breadth=12 informational looks (logged in respective SUMMARYs).

## T2 APPENDED VERDICT (2026-07-10, job completed post-compile — frozen bar unchanged)
**KILL.** Bar: >=5 pts AND day-clustered t>=2.5 on PDH and PDL. Measured (k=5 window): PDH +2.04 pts t=1.91, placebo p=0.24 (indistinguishable from day-composition); PDL +3.32 pts t=2.03, placebo p=0.0099. PDL is the one REAL sub-signal (survives shuffle) but is 34% under the point bar, decays across eras (6.17 -> 1.83 -> 0.92 pts), and one-bar-lag collapses 35% (WARN). ROUND and OR15 levels: noise or negative.
Resurrection condition: PDL-side sweep only, if a sub-minute/order-flow construct lifts edge >=5 pts with stable eras — otherwise closed. Evidence: t2-sweep/t2_variant_stats.csv, t2_events.csv.

## T6 APPENDED VERDICT (2026-07-10, job completed post-compile — frozen bar unchanged)
**KILL (as specified).** Bar: t>=2 AND >=5 pts for wall-cross continuation. Measured (949 walls, 261 expiries 2021-05..2026-06, 3-bar OI lag): WALL crossings show NEGATIVE day-mean excess (-0.38 to -1.96 pts, t -0.41..-1.13); era2 (2024-26) worst at -3.86 pts/60min. The trapped-writer thesis is backwards: heavy-OI walls get DEFENDED/pinned, not broken-and-squeezed.
**NEW EXPLORATORY LEAD (from the control set — NOT a pass, needs its own pre-registered test):** crossings of LOW-OI strikes ("air pockets", bottom-50% OI) show +4.40 pts day-mean at 30min (t=3.94) and +5.64 at 60min (t=3.60) — consistent with dealer-gamma pinning literature (high OI pins, low OI lets price traverse). Because this was the control, it carries full data-mining risk: intake as a fresh hypothesis, pre-register on a variant construction (PE side / stock options / different wall decile) before believing.
Evidence: t6-oi-wall/ output tables.

## SCALP-V7-0DTE APPENDED VERDICT (2026-07-10, Principal Pine script, expiry-days-only variant)
**KILL.** Frozen bars: net/trade <= 0 @BASE costs or PF < 1.15 (primary 5-min). Measured: n=747, net -1.29 pts/trade, PF 0.78, win 26%, expectancy -9.2% of premium; GROSS already negative (-0.29). Eras consistent (-1.25 / -1.33). 1-min secondary: n=4674, gross +0.12, net -0.88, PF 0.72. Zero no-fills (ATM 0DTE liquid).
Anatomy (K-001 pattern, 16th confirmation): the spot signal is real but tiny (+1.02 pts/trade on the underlying); 0DTE theta during the hold converts +1 spot pt into -0.29 gross option pts; the 1-pt one-way spread finishes it. Signal would need ~5x its size to clear the wall.
Evidence: scalpv7-0dte/ (SUMMARY.md, trades_*.csv, script with frozen registration). Trials ledger: +2.
