import pandas as pd

rows = [
# --- benchmark (unchanged, cited not re-tested) ---
dict(rank=0, structure="S1-F 0DTE ATM short straddle (CERTIFIED benchmark, unchanged)", dte=0,
     trades_per_month=17.2, margin_basis="10% dyn (naked)", n=204, mean_pts_or_rs="+10.7pts/day net",
     win_pct=74.0, avg_RR=None, t=3.92, maxDD_pct=-4.44, return_on_margin_cagr_pct=12.57,
     era_split="2021-2026, both eras positive", held_out_2026="incl. in 204", tier="CERTIFIED",
     source="STRATEGY_REGISTER / S1F_METRICS_PANEL_20260725 (not re-tested, cited)"),

dict(rank=1, structure="LD_SELL biweekly 0.10-delta naked strangle, stop-out@2x credit", dte=12,
     trades_per_month=1.43, margin_basis="10% naked", n=221, mean_pts_or_rs="build CAGR 16.53%",
     win_pct=None, avg_RR=None, t=2.235, maxDD_pct=-69.71, return_on_margin_cagr_pct=16.53,
     era_split="2011-2023 build; COVID(2020) alone = net -Rs42,545/27 trades, worst trade -50.6% margin",
     held_out_2026="2024-01..2026-06: n=64, CAGR 13.33%, maxDD -24.04%, Sharpe 0.597, PF 1.34, t=0.968",
     tier="FORWARD-TEST CANDIDATE (TOP PICK)", source="LONGDATED_SELLING_20260730/config_grid_summary.csv"),

dict(rank=2, structure="LD_SELL biweekly 0.10D naked + RV-regime-skip overlay (skip entry if own trailing RV in its own top decile)",
     dte=12, trades_per_month=1.43, margin_basis="10% naked", n=264, mean_pts_or_rs="full-period CAGR 14.85%",
     win_pct=62.7, avg_RR=None, t=2.354, maxDD_pct=-54.63, return_on_margin_cagr_pct=14.85,
     era_split="full 2011-2026 (covers COVID); DD cut -69.7%->-54.6% vs base for ~1.7pp CAGR give-up",
     held_out_2026="included in full-period 2011-2026 figure (not separately isolated)",
     tier="FORWARD-TEST CANDIDATE (fixes item-6 DD, a risk lever not a return-adder)",
     source="LONGDATED_SELLING_20260730/overlay_tests.csv row rv_regime_skip_full_period"),

dict(rank=3, structure="LD_SELL monthly 0.10D naked strangle, stop-out@2x credit", dte=30,
     trades_per_month=1.02, margin_basis="10% naked", n=156, mean_pts_or_rs="build CAGR 3.44%",
     win_pct=None, avg_RR=None, t=1.292, maxDD_pct=-72.46, return_on_margin_cagr_pct=3.44,
     era_split="build weak (CAGR 3.4%, t=1.29)", held_out_2026="n=30, CAGR 16.35%, maxDD -22.09%, Sharpe 0.666, PF 1.56, t=0.922",
     tier="FORWARD-TEST CANDIDATE (weaker build than biweekly rung)", source="LONGDATED_SELLING_20260730/config_grid_summary.csv"),

dict(rank=4, structure="LD_SELL bimonthly 0.10D naked strangle, stop-out@2x credit", dte=60,
     trades_per_month=0.48, margin_basis="10% naked", n=74, mean_pts_or_rs="build CAGR 3.68%",
     win_pct=None, avg_RR=None, t=1.110, maxDD_pct=-37.00, return_on_margin_cagr_pct=3.68,
     era_split="build n=74, t=1.11 (underpowered)", held_out_2026="n=13 (thin), CAGR 14.22%, maxDD -22.61%, Sharpe 0.754, PF 2.01, t=1.21",
     tier="UNDERPOWERED-UNRESOLVED (n too thin at this DTE)", source="LONGDATED_SELLING_20260730/config_grid_summary.csv"),

dict(rank=5, structure="LD_SELL same-expiry HEDGED (iron condor, wing ~3% OTM) -- item-4 margin test, ALL tenors/deltas avg",
     dte="12/30/60 (avg)", trades_per_month=None, margin_basis="5% hedged", n="1354 (54-cell grid)",
     mean_pts_or_rs="mean held CAGR across grid: naked +20.0% vs condor -13.6%",
     win_pct=None, avg_RR=None, t=None, maxDD_pct="naked avg -36.2% vs condor avg -64.3% (held-out)",
     return_on_margin_cagr_pct=None, era_split="condor UNDERPERFORMS naked on BOTH CAGR and maxDD despite half the margin base",
     held_out_2026="condor mean held Sharpe 0.022 vs naked 0.923",
     tier="REJECTED as a margin-efficiency trade -- wing premium give-up > margin-efficiency gain at 3%-OTM wing distance",
     source="LONGDATED_SELLING_20260730/config_grid_summary.csv, structure-axis groupby"),

dict(rank=6, structure="Ratio calendar 1x1 ATM/ATM, sell near/buy far, exit 3d-before near expiry, unconditional",
     dte="near<=3 (short leg)", trades_per_month=0.97, margin_basis="10%/5% both reported (cross-expiry, real SPAN between)",
     n=174, mean_pts_or_rs="+9.58 pts/cycle NET", win_pct=59.8, avg_RR=None, t=2.494, maxDD_pct=-45.5,
     return_on_margin_cagr_pct="mean ROM/trade 0.58%(10%marg)/1.16%(5%marg)",
     era_split="2011-2025 build; edge is POST-2019-weekly-launch concentrated per firm's Break-1 finding",
     held_out_2026="n=4 (tiny), mean -6.86pts, 3/4 wins but one bad trade (-129.5) drags mean negative",
     tier="FORWARD-TEST CANDIDATE (does NOT clear ~140-cell Bonferroni bar; held-out inconclusive on n=4)",
     source="RATIO_CALENDAR_20260730/grid_a_summary_BUILD_2011_2025.csv + HELDOUT"),

dict(rank=7, structure="Ratio calendar 1x1 ATM/ATM ROLL variant (\"income machine\": keep far leg 2 cycles, re-sell near each cycle)",
     dte="near<=3", trades_per_month=0.89, margin_basis="10%/5%", n=158, mean_pts_or_rs="+28.48 pts/cycle NET",
     win_pct=67.1, avg_RR=None, t=2.229, maxDD_pct=None, return_on_margin_cagr_pct="friction 17.8% of gross (vs 40.0% no-roll)",
     era_split="build 2011-2025; roll halves friction-as-%-gross vs no-roll baseline, confirming H4 (saved fee-event)",
     held_out_2026="n=2 (too thin to trust), mean +50.5pts (directionally consistent)",
     tier="FORWARD-TEST CANDIDATE (H4 mechanic confirmed; same Bonferroni caveat as rank 6)",
     source="RATIO_CALENDAR_20260730/grid_b_summary.csv"),

dict(rank=8, structure="Ratio calendar 2x1 and 3x2 (sell 2-3 near : buy 1-2 far) -- ALL filters, ALL exits",
     dte="near<=3", trades_per_month=None, margin_basis="10%/5% base + naked excess on the unhedged extra short leg(s)",
     n="172-221 per cell", mean_pts_or_rs="mean -26 to -310 pts/cycle NET (worst under inversion/topdecile filters, exactly when Principal's rationale wants entry)",
     win_pct="25-62%", avg_RR=None, t="-0.06 to -2.95 (negative in nearly every cell)",
     maxDD_pct=None, return_on_margin_cagr_pct=None,
     era_split="uniformly worse than 1x1 across build; worst single trades -800 to -1380pts",
     held_out_2026="not separately tested given build-side rejection",
     tier="REJECTED at this desk -- naked excess-short blows up on real vol events; do not size, do not forward-test",
     source="RATIO_CALENDAR_20260730/grid_a_summary_BUILD_2011_2025.csv ratio=2x1/3x2 rows"),

dict(rank=9, structure="Vol-ML sizing overlay on S1-F: size 2x/1x/0.5x by yesterday's H3 forward-vol-tercile prediction (naive direction: sell more when predicted LOW)",
     dte=0, trades_per_month=4.3, margin_basis="10% naked (same as S1-F base)", n=208,
     mean_pts_or_rs="Rs1805/day mean (vs Rs2097 baseline)", win_pct=67.3, avg_RR=None, t=2.36,
     maxDD_pct=-29.04, return_on_margin_cagr_pct="CAGR 60.36% (book-slice basis) vs baseline 66.31%",
     era_split="worse than baseline in both eras", held_out_2026="n/a (book window only 2022-2025)",
     tier="DEAD -- fails placebo (real beats only 9.2% of block-permuted draws; CAGR uplift -5.95pp vs placebo mean +3.98pp)",
     source="OPTSELL_EXT_20260731/vol_gate_sizing.py"),

dict(rank=10, structure="Vol-ML sizing overlay on S1-F, REVERSED: size 2x/1x/0.5x by HIGH/MID/LOW tercile (sell MORE when model predicts HIGH forward vol -- i.e. size WITH the day's rich-IV read, not against it)",
     dte=0, trades_per_month=4.3, margin_basis="10% naked", n=208,
     mean_pts_or_rs="Rs3403/day mean (vs Rs2097 baseline)", win_pct=67.3, avg_RR=None, t=3.06,
     maxDD_pct=-34.96, return_on_margin_cagr_pct="CAGR 88.29% (book-slice basis) vs baseline 66.31%",
     era_split="2022-23: CAGR 74.2->94.5% but maxDD WORSE (-32.2->-35.0%, legible trade-off); 2024-25: CAGR 126.8->198.4% AND maxDD better (-20.3->-15.2%)",
     held_out_2026="n/a (book window only 2022-2025)",
     tier="SUGGESTIVE, marginal (real beats placebo at 96.6th pctile, clears simple p95 but NOT Bonferroni at m=2 trials which needs ~97.5th; n=208 thin, do not size on this alone)",
     source="OPTSELL_EXT_20260731/vol_gate_reversed.py"),

dict(rank=11, structure="Sell spike-side option (overshoot>=3), DELTA-HEDGED, 0-1DTE, skip scheduled-event days",
     dte="0-1", trades_per_month=24, margin_basis="5% hedged (dynamic delta-hedge, own margin/gamma-scalp cost not separately isolated)",
     n=None, mean_pts_or_rs="+0.30 pts/trade (range +0.64 @0.24D to -0.25 @0.40D)", win_pct=None, avg_RR=None,
     t=None, maxDD_pct=None, return_on_margin_cagr_pct="~8-9% CAGR estimate",
     era_split="better post-Oct-2024 (+1.54)", held_out_2026="+1.72 pts/trade",
     tier="FORWARD-TEST CANDIDATE (small, within cost-model error bars, needs delta-hedge execution capability)",
     source="SPIKE_OVERSHOOT_SELL_20260730/FINAL_VERDICT.md"),
]

df = pd.DataFrame(rows)
out = "c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/Shreyas_Ionic_AMC/04_RND_LAB/results/OPTSELL_EXT_20260731/cells.csv"
df.to_csv(out, index=False)
print("wrote", out, df.shape)
