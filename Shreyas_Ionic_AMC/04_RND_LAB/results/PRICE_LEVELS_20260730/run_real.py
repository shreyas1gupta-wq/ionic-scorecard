import time
import pandas as pd
from touch_engine import build_day_arrays, simulate_all, add_costs

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PRICE_LEVELS_20260730"

daily = pd.read_parquet(f"{OUT}/daily.parquet")
bars = pd.read_parquet(f"{OUT}/bars_1min.parquet")
levels = pd.read_parquet(f"{OUT}/levels_real.parquet")
atr_by_date = daily["atr14_prior"].to_dict()

t0 = time.time()
day_arrays = build_day_arrays(bars)
print("day_arrays", time.time() - t0, flush=True)

t0 = time.time()
trades = simulate_all(levels, day_arrays, atr_by_date)
print("simulate_all", time.time() - t0, "s, trades", len(trades), flush=True)

trades = add_costs(trades)
trades.to_parquet(f"{OUT}/trades_real.parquet")
print("saved trades_real.parquet", trades.shape, flush=True)
print(trades.groupby("system").size())
