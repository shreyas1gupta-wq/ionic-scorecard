import time
import numpy as np
import pandas as pd
from touch_engine import build_day_arrays, simulate_all, add_costs

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PRICE_LEVELS_20260730"

daily = pd.read_parquet(f"{OUT}/daily.parquet")
bars = pd.read_parquet(f"{OUT}/bars_1min.parquet")
levels = pd.read_parquet(f"{OUT}/levels_real.parquet")

atr_by_date = daily["atr14_prior"].to_dict()

t0 = time.time()
day_arrays = build_day_arrays(bars)
print("day_arrays built", time.time() - t0, "s, n days", len(day_arrays))

# small subset: one system, one year
sub = levels[(levels["system"] == "SATY") & (levels["date"].dt.year == 2023)]
print("subset rows", len(sub))
t0 = time.time()
trades = simulate_all(sub, day_arrays, atr_by_date)
print("simulate time", time.time() - t0, "s, trades", len(trades))
print(trades.head(10))
trades = add_costs(trades)
print(trades.groupby(["level_name", "hypothesis", "exit_cfg"])["net_pess"].agg(["count", "mean"]))
