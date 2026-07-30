import pandas as pd
import numpy as np

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\ORTHOGONAL_ALPHA_20260730"

h1 = pd.read_csv(OUT + r"\h1_crossasset_cells.csv")
rows = []
for _, r in h1.iterrows():
    verdict = "NO CONTENT (placebo-indistinguishable)" if r["placebo_p"] >= 0.05 else "CLEARS RAW PLACEBO but see post-hoc split"
    rows.append(dict(hypothesis="H1_crossasset", cell=f"{r['signal']}/{r['horizon']}", n=r["n_build"],
                      unit="pts", effect=round(r["spread_pts"], 2), t_stat=round(r["t_build"], 2),
                      placebo_p=r["placebo_p"], t_pre=round(r["t_pre"], 2) if pd.notna(r["t_pre"]) else np.nan,
                      t_post=round(r["t_post"], 2) if pd.notna(r["t_post"]) else np.nan,
                      t_oos2026=round(r["t_oos2026"], 2) if pd.notna(r["t_oos2026"]) else np.nan,
                      trades_per_month=round(r["trades_per_month"], 1), win_pct=round(r["win_rate"] * 100, 1),
                      rr=round(r["rr"], 2) if pd.notna(r["rr"]) else np.nan, verdict=verdict))

# post-hoc decomposition rows (from console output of h1_wti_short_leg.py -- hardcoded from the run, both scripts wrote CSVs too)
rows.append(dict(hypothesis="H1_posthoc_wti_short_only", cell="wti_crash_short/eod/quintile(q20)", n=229,
                  unit="pts", effect=27.60, t_stat=2.83, placebo_p=0.008, t_pre=2.41, t_post=1.51,
                  t_oos2026=1.97, trades_per_month=4.1, win_pct=59.0, rr=np.nan,
                  verdict="FORWARD-TEST CANDIDATE (post-hoc, sub-floor freq, era-consistent MAGNITUDE)"))
rows.append(dict(hypothesis="H1_posthoc_wti_short_only", cell="wti_crash_short/eod/tercile(q33)", n=382,
                  unit="pts", effect=21.06, t_stat=2.90, placebo_p=0.010, t_pre=np.nan, t_post=np.nan,
                  t_oos2026=0.40, trades_per_month=6.9, win_pct=57.9, rr=np.nan,
                  verdict="DILUTES/WASHES OUT OOS -- do not loosen threshold for frequency"))
rows.append(dict(hypothesis="H1_posthoc_wti_long_only", cell="wti_spike_long/eod/quintile(q80)", n=229,
                  unit="pts", effect=-6.76, t_stat=-0.70, placebo_p=np.nan, t_pre=-0.25, t_post=-0.89,
                  t_oos2026=np.nan, trades_per_month=4.1, win_pct=47.6, rr=np.nan,
                  verdict="DEAD (no edge on this leg, cost-eaten)"))

h2 = pd.read_csv(OUT + r"\h2_dispersion_cells.csv")
for _, r in h2.iterrows():
    verdict = "NO CONTENT vs econ magnitude (<2pt equiv, 2-leg cost-dominated); era sign unstable"
    rows.append(dict(hypothesis="H2_dispersion_niftybnf", cell=f"{r['horizon_min']}min", n=r["n_build"],
                      unit="pct-pts (spread)", effect=round(r["spread_obs_pct"], 5), t_stat=round(r["t_build"], 2),
                      placebo_p=r["placebo_p"], t_pre=round(r["t_pre"], 2) if pd.notna(r["t_pre"]) else np.nan,
                      t_post=round(r["t_post"], 2) if pd.notna(r["t_post"]) else np.nan,
                      t_oos2026=round(r["t_oos2026"], 2) if pd.notna(r["t_oos2026"]) else np.nan,
                      trades_per_month=np.nan, win_pct=np.nan, rr=np.nan, verdict=verdict))

h3 = pd.read_csv(OUT + r"\h3_breadth_cells.csv")
for _, r in h3.iterrows():
    verdict = "UNDERPOWERED-UNRESOLVED (sign-stable both eras, fails placebo at conventional 0.05)"
    rows.append(dict(hypothesis="H3_breadth_AD", cell=f"{r['horizon_days']}d_fwd", n=r["n_build"],
                      unit="%", effect=round(r["spread_pct"], 3), t_stat=round(r["t_build"], 2),
                      placebo_p=r["placebo_p"], t_pre=round(r["t_pre"], 2) if pd.notna(r["t_pre"]) else np.nan,
                      t_post=round(r["t_post"], 2) if pd.notna(r["t_post"]) else np.nan,
                      t_oos2026=np.nan, trades_per_month=round(r["trades_per_month"], 1), win_pct=np.nan, rr=np.nan,
                      verdict=verdict))

cells = pd.DataFrame(rows)
cells.to_csv(OUT + r"\cells.csv", index=False)
print(cells.to_string())
print("\nTOTAL TRIALS THIS SESSION:", len(cells))
