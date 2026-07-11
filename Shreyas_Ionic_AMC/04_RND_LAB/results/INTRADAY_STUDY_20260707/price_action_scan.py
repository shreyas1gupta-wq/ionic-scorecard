"""Broad price-action + filter scan on NIFTY spot.
Test signals for FORWARD-day directional edge (bps of next-day OC or CC return).
Signals scanned:
  S1: overnight gap-up > threshold (fade at open, short signal)
  S2: overnight gap-down < -threshold (bounce at open, long signal)
  S3: 3-consecutive close-up (fade next day, short)
  S4: 3-consecutive close-down (bounce next day, long)
  S5: yesterday close top-20% of daily range + Nifty>20DMA (continuation long)
  S6: yesterday close bottom-20% of daily range (continuation short)
  S7: NR4 - yesterday's range < 60% of 4-day avg range (breakout next day)
  S8: failed PDH break yesterday (broke PDH, closed below -> next day short)
  S9: failed PDL break yesterday (broke PDL, closed above -> next day long)
  S10: 5-day range compression (5-day range/close < 1.5%) + directional close
Then test COMBINED filter: signal + Nifty>20DMA aligning.
"""
import sys, time
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

GAME = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\09_PRODUCT\fno_game\server"
sys.path.insert(0, GAME)
import data_loader as dl

OUT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\INTRADAY_STUDY_20260707")

t0 = time.time()
s = dl._spot()
days_all = sorted(s["d"].unique())
by_day = {d: g[["hm","open","high","low","close"]].to_numpy() for d, g in s.groupby("d")}

# Build daily OHLC
daily = s.groupby("d").agg(
    open=("open","first"), high=("high","max"), low=("low","min"), close=("close","last")
).reset_index()
daily["sma20"] = daily["close"].rolling(20).mean()
daily["sma50"] = daily["close"].rolling(50).mean()
daily["above_20dma"] = daily["close"] > daily["sma20"]
# Prev-day OHLC
for c in ["open","high","low","close"]:
    daily[f"p{c}"] = daily[c].shift(1)
# Overnight gap % (current-open vs prev-close)
daily["gap_pct"] = (daily["open"] - daily["pclose"]) / daily["pclose"] * 100
# Yesterday's range
daily["p_range_pct"] = (daily["phigh"] - daily["plow"]) / daily["pclose"] * 100
# Yesterday's close position in range: 0 = at low, 1 = at high
daily["p_close_in_range"] = (daily["pclose"] - daily["plow"]) / (daily["phigh"] - daily["plow"] + 1e-9)
# 4-day avg range
daily["avg_range_4d"] = daily["p_range_pct"].rolling(4).mean()
daily["nr4"] = daily["p_range_pct"] < 0.6 * daily["avg_range_4d"]
# Consecutive up/down close (2 days closed higher = "3 up" including today)
daily["up3"] = (daily["pclose"] > daily["pclose"].shift(1)) & (daily["pclose"].shift(1) > daily["pclose"].shift(2)) & (daily["pclose"].shift(2) > daily["pclose"].shift(3))
daily["down3"] = (daily["pclose"] < daily["pclose"].shift(1)) & (daily["pclose"].shift(1) < daily["pclose"].shift(2)) & (daily["pclose"].shift(2) < daily["pclose"].shift(3))
# 5-day range compression
daily["hi5"] = daily["phigh"].rolling(5).max()
daily["lo5"] = daily["plow"].rolling(5).min()
daily["range5_pct"] = (daily["hi5"] - daily["lo5"]) / daily["pclose"] * 100
daily["compress5"] = daily["range5_pct"] < 1.5
# Failed breakout: yesterday's high > prev-PDH (2 days ago high) AND yesterday's close < that PDH
daily["pdh_2d"] = daily["high"].shift(2)
daily["pdl_2d"] = daily["low"].shift(2)
daily["fail_pdh"] = (daily["phigh"] > daily["pdh_2d"]) & (daily["pclose"] < daily["pdh_2d"])
daily["fail_pdl"] = (daily["plow"] < daily["pdl_2d"]) & (daily["pclose"] > daily["pdl_2d"])
# forward returns
daily["ret_oc"] = (daily["close"] - daily["open"]) / daily["open"] * 100  # today's open-to-close
daily["ret_cc"] = (daily["close"] - daily["pclose"]) / daily["pclose"] * 100  # yesterday close to today close
daily["ret_next_cc"] = daily["ret_cc"].shift(-1)  # NEXT day's close-to-close (forward)
daily["ret_next_oc"] = daily["ret_oc"].shift(-1)  # NEXT day's open-to-close
daily = daily.dropna(subset=["sma50","avg_range_4d","hi5","up3","down3","nr4","fail_pdh"]).reset_index(drop=True)
print(f"Daily universe after prep: {len(daily)} days")

# ---- Signal scan ----
def scan(cond, direction, target="ret_next_cc", label=""):
    sub = daily[cond].dropna(subset=[target])
    if len(sub) < 20: return None
    fwd = sub[target].values * direction
    return dict(signal=label, n=len(sub),
                mean_ret=round(fwd.mean(), 3),
                med_ret=round(np.median(fwd), 3),
                win_pct=round((fwd > 0).mean()*100, 1),
                std=round(fwd.std(), 3),
                sharpe_per_trade=round(fwd.mean()/max(1e-9, fwd.std()), 3),
                worst=round(fwd.min(), 2), best=round(fwd.max(), 2),
                direction=direction)

# ---- Scan a big grid ----
signals = [
    ("Gap up > 0.3pct -> fade", (daily["gap_pct"] > 0.3), -1, "ret_oc"),
    ("Gap up > 0.5pct -> fade", (daily["gap_pct"] > 0.5), -1, "ret_oc"),
    ("Gap down < -0.3pct -> bounce", (daily["gap_pct"] < -0.3), +1, "ret_oc"),
    ("Gap down < -0.5pct -> bounce", (daily["gap_pct"] < -0.5), +1, "ret_oc"),
    ("Gap up > 0.3pct -> ride (follow)", (daily["gap_pct"] > 0.3), +1, "ret_oc"),
    ("Gap down < -0.3pct -> ride (follow)", (daily["gap_pct"] < -0.3), -1, "ret_oc"),
    ("3 up-days -> fade (short next)", daily["up3"], -1, "ret_next_cc"),
    ("3 down-days -> bounce (long next)", daily["down3"], +1, "ret_next_cc"),
    ("Close top-20pct range + Nifty>20DMA -> continue (long)",
        (daily["p_close_in_range"] > 0.8) & daily["above_20dma"], +1, "ret_next_cc"),
    ("Close bottom-20pct range -> continue (short)",
        (daily["p_close_in_range"] < 0.2), -1, "ret_next_cc"),
    ("NR4 + Nifty>20DMA -> breakout long", daily["nr4"] & daily["above_20dma"], +1, "ret_next_cc"),
    ("NR4 + Nifty<20DMA -> breakout short", daily["nr4"] & ~daily["above_20dma"], -1, "ret_next_cc"),
    ("Failed PDH break -> short next day", daily["fail_pdh"], -1, "ret_next_cc"),
    ("Failed PDL break -> long next day", daily["fail_pdl"], +1, "ret_next_cc"),
    ("5-day compress + Nifty>20DMA -> long next", daily["compress5"] & daily["above_20dma"], +1, "ret_next_cc"),
    ("5-day compress + close top-20 -> long next",
        daily["compress5"] & (daily["p_close_in_range"] > 0.8), +1, "ret_next_cc"),
    ("Any Nifty>20DMA (baseline)", daily["above_20dma"], +1, "ret_next_cc"),
    ("Any Nifty<20DMA (baseline)", ~daily["above_20dma"], -1, "ret_next_cc"),
]

results = []
for name, cond, dir_, target in signals:
    r = scan(cond, dir_, target, name)
    if r: results.append(r)

df_res = pd.DataFrame(results).sort_values("sharpe_per_trade", ascending=False)
print("\n=== SIGNAL SCAN (sorted by per-trade Sharpe) ===")
print(df_res.to_string(index=False))
df_res.to_csv(OUT / "price_action_signals.csv", index=False)

# ---- For top signals: check yearly stability ----
best = df_res.head(5)
print("\n\n=== YEARLY BREAKDOWN for top 5 signals ===")
for _, row in best.iterrows():
    name = row["signal"]
    if name not in [s[0] for s in signals]: continue
    _, cond, dir_, target = next(s for s in signals if s[0] == name)
    sub = daily[cond].dropna(subset=[target]).copy()
    if len(sub) < 20: continue
    sub["fwd"] = sub[target] * dir_
    sub["year"] = pd.to_datetime(sub["d"]).dt.year
    yr = sub.groupby("year").agg(n=("fwd","size"), mean=("fwd","mean"), win=("fwd", lambda x: round((x>0).mean()*100,1))).round(2)
    print(f"\n{name}:")
    print(yr.to_string())

# ---- Simulate trading the best-of-scan via option-sell wrap ----
# For the BEST bullish signal (highest Sharpe among long-side signals): sell 3% OTM PE next day
# For the BEST bearish signal: sell 3% OTM CE next day
# Compare vs baseline (always sell PE on Mondays w/ Nifty>20DMA)

print(f"\nruntime: {time.time()-t0:.0f}s")
