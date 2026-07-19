"""
Tail-convexity analysis for ALPHA_RANKER signals — Kabir Anand (Hedging & Tail Risk).
Builds a single (date,symbol) panel of: 12 capstone legs + 4 wave-4 candidates
(clean-surplus, depreciation-laxity, beta-adj momentum, Amihud [simplified rebuild]),
merged with fwd_ret_1M_raw and market-month conditioning, then computes payoff-shape
diagnostics (NOT rank-IC): hit rate, win/loss asymmetry, skew, crash-conditional LS return.

No fabrication: wave-4 candidates rebuilt from the SAME builder functions used to
produce their cards (builders_w4t_forensic.py, builders_mom.py) — same PIT joins,
same panel. Amihud has no persisted builder (card notes "volume data is 5yr-only");
rebuilt as a standard trailing-21d Amihud illiquidity z-score from cube_close_long +
cube_volume — labelled [INFERENCE] simplified, not the exact size-residualized card
construction (which used a size-orthogonalized version we don't have the code for).
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd

RND = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER\rnd")
sys.path.insert(0, str(RND / "lib"))
sys.path.insert(0, str(RND))

OUT = Path(r"C:\Users\SHREYA~1.1GU\AppData\Local\Temp\claude\c--Users-Shreyas-1Gupta-OneDrive---Angel-Broking-Limited-Desktop-Backup-NIFTY-500\f6b730da-632d-4ec3-b4d1-d89aa1c2dbff\scratchpad")

print("Loading panel_long...")
panel = pd.read_parquet(RND / "panel" / "panel_long.parquet")
panel["date"] = pd.to_datetime(panel["date"])

# --- 12 capstone legs, wide ---
print("Loading capstone_legs...")
legs = pd.read_parquet(RND / "panel" / "capstone_legs.parquet")
legs["date"] = pd.to_datetime(legs["date"])
legs_wide = legs.pivot_table(index=["date", "symbol"], columns="leg", values="value")
print("legs_wide shape", legs_wide.shape)

# --- wave-4 candidates: clean_surplus_health, dep_health, beta_adjusted_mom ---
print("Building wave-4 forensic candidates (clean_surplus, dep_health)...")
import builders_w4t_forensic as BF
clean_surplus = BF.build_clean_surplus_health(panel)   # Series[(date,symbol)]
dep_health = BF.build_dep_health(panel)

print("Building beta_adjusted_mom (H043)...")
import builders_mom as BM
beta_adj_mom = BM.build_beta_adjusted_mom(panel)

# --- Amihud illiquidity, simplified rebuild [INFERENCE] ---
print("Building simplified Amihud illiquidity...")
close = pd.read_parquet(RND / "panel" / "cube_close_long.parquet")
vol = pd.read_parquet(RND / "panel" / "cube_volume.parquet")
close.index = pd.to_datetime(close.index)
vol.index = pd.to_datetime(vol.index)
ret = close.pct_change()
# rupee volume proxy = close * volume (shares) ; Amihud_daily = |ret| / (close*vol), skip if vol<=0
dvol = (close * vol).replace(0, np.nan)
amihud_daily = ret.abs() / dvol
amihud_21 = amihud_daily.rolling(21, min_periods=10).mean()  # trailing 21d avg
panel_dates = sorted(panel["date"].unique())
symbols_all = [c for c in close.columns]
amihud_rows = []
for d in panel_dates:
    if d not in amihud_21.index:
        continue
    row = amihud_21.loc[d]
    amihud_rows.append(row.rename(d))
amihud_panel = pd.DataFrame(amihud_rows)
amihud_panel.index.name = "date"
amihud_long = amihud_panel.stack().rename("amihud_raw").reset_index()
amihud_long.columns = ["date", "symbol", "amihud_raw"]
# cross-sectional z-score per date (winsorize 1/99)
def _z(s):
    lo, hi = s.quantile(0.01), s.quantile(0.99)
    sw = s.clip(lo, hi)
    return (sw - sw.mean()) / sw.std(ddof=0)
amihud_long["amihud_z"] = amihud_long.groupby("date")["amihud_raw"].transform(_z)
amihud_series = amihud_long.set_index(["date", "symbol"])["amihud_z"]

print("clean_surplus n=", len(clean_surplus), "dep_health n=", len(dep_health),
      "beta_adj_mom n=", len(beta_adj_mom), "amihud n=", len(amihud_series))

# --- assemble master wide panel ---
master = legs_wide.copy()
master["W4_clean_surplus_health"] = clean_surplus
master["W4_dep_health"] = dep_health
master["W4_beta_adj_mom"] = beta_adj_mom
master["W4_amihud_illiq"] = amihud_series

master = master.reset_index()
print("master shape", master.shape)
master.to_parquet(OUT / "tail_master_signals.parquet")

# --- merge fwd returns + sector + disc_event guard ---
ret_cols = ["date", "symbol", "sector", "fwd_ret_1M_raw", "fwd_ret_1Y_raw",
            "disc_event_in_window_1M", "disc_event_in_window_1Y"]
panel_ret = panel[ret_cols].copy()
merged = master.merge(panel_ret, on=["date", "symbol"], how="left")

# disc-event guard (same convention as run_long_confirm.py: NaN the fwd return
# where a discrete corporate event is flagged in the window)
mask1m = merged["disc_event_in_window_1M"].fillna(0) > 0
mask1y = merged["disc_event_in_window_1Y"].fillna(0) > 0
merged.loc[mask1m, "fwd_ret_1M_raw"] = np.nan
merged.loc[mask1y, "fwd_ret_1Y_raw"] = np.nan
print(f"disc-event masked: 1M={mask1m.sum()}, 1Y={mask1y.sum()}")

merged.to_parquet(OUT / "tail_merged.parquet")
print("merged shape", merged.shape)
print("DONE build")
