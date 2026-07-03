"""Find the best IV/RV threshold for the SHORT-vol stock-options strategy.
Loads the 660 saved trades and sweeps thresholds on IV/RV (ratio) and IV-RV (spread),
reporting mean / hit / tail (p5, worst-10% mean) / build / forward — to find a robust,
tail-controlled short-vol entry rule.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
R = pd.read_parquet(ROOT / "intraday_options_strategy/buying/rv_iv_vol.parquet")
R["ed"] = pd.to_datetime(R["entry"]).dt.date
R["spread"] = R["iv"] - R["rv"]
SPLIT = dt.date(2024, 12, 31)


def stat(x):
    x = x.dropna()
    if len(x) < 10:
        return dict(n=len(x), mean=np.nan, hit=np.nan, p5=np.nan, tail10=np.nan, sharpe=np.nan)
    return dict(n=len(x), mean=x.mean(), hit=(x > 0).mean(), p5=x.quantile(0.05),
                tail10=x[x <= x.quantile(0.10)].mean(),
                sharpe=x.mean() / x.std() if x.std() > 0 else 0)


print(f"n={len(R)}  IV/RV: min {R['iv_rv'].min():.2f} med {R['iv_rv'].median():.2f} max {R['iv_rv'].max():.2f}")

# 1) shape: short_ret by IV/RV decile
print("\n=== SHORT-vol return by IV/RV decile (find the sweet spot) ===")
R["dec"] = pd.qcut(R["iv_rv"], 10, labels=False, duplicates="drop")
g = R.groupby("dec").agg(iv_rv_lo=("iv_rv", "min"), iv_rv_hi=("iv_rv", "max"),
                         short_mean=("short_ret", "mean"), hit=("short_ret", lambda x: (x > 0).mean()),
                         worst=("short_ret", "min"), n=("short_ret", "size"))
print(g.to_string(formatters={"iv_rv_lo": "{:.2f}".format, "iv_rv_hi": "{:.2f}".format,
                              "short_mean": "{:+.1%}".format, "hit": "{:.0%}".format, "worst": "{:+.0%}".format}))

# 2) lower-threshold sweep: short only when IV/RV >= T
print("\n=== SHORT-vol: threshold IV/RV >= T (with tail + build/forward) ===")
print(f"  {'T':>5} {'n':>4} {'mean':>7} {'hit':>5} {'p5':>7} {'tail10%':>8} {'sharpe':>6} | {'BUILD':>7} {'FWD':>7}")
for T in [0.9, 1.0, 1.05, 1.1, 1.15, 1.2, 1.3, 1.4, 1.5]:
    sub = R[R["iv_rv"] >= T]
    s = stat(sub["short_ret"])
    b = stat(sub[sub["ed"] <= SPLIT]["short_ret"]); f = stat(sub[sub["ed"] > SPLIT]["short_ret"])
    if s["n"] < 10:
        continue
    print(f"  {T:>5.2f} {s['n']:>4d} {s['mean']:>+7.1%} {s['hit']:>5.0%} {s['p5']:>+7.0%} "
          f"{s['tail10']:>+8.0%} {s['sharpe']:>6.2f} | {b['mean']:>+7.1%} {f['mean']:>+7.1%}")

# 3) BAND sweep: short only when T_lo <= IV/RV <= T_hi (avoid extreme 'event priced in')
print("\n=== SHORT-vol: BAND T_lo <= IV/RV <= T_hi (avoid extremes) ===")
print(f"  {'band':>12} {'n':>4} {'mean':>7} {'hit':>5} {'p5':>7} {'sharpe':>6} | {'BUILD':>7} {'FWD':>7}")
for lo, hi in [(1.0, 1.5), (1.05, 1.5), (1.1, 1.6), (1.0, 1.3), (1.1, 1.4), (1.15, 1.5), (1.0, 99)]:
    sub = R[(R["iv_rv"] >= lo) & (R["iv_rv"] <= hi)]
    s = stat(sub["short_ret"])
    b = stat(sub[sub["ed"] <= SPLIT]["short_ret"]); f = stat(sub[sub["ed"] > SPLIT]["short_ret"])
    if s["n"] < 10:
        continue
    print(f"  {lo:.2f}-{hi:>5.2f} {s['n']:>4d} {s['mean']:>+7.1%} {s['hit']:>5.0%} {s['p5']:>+7.0%} "
          f"{s['sharpe']:>6.2f} | {b['mean']:>+7.1%} {f['mean']:>+7.1%}")

# 4) spread threshold (IV - RV in vol points)
print("\n=== SHORT-vol: threshold IV - RV >= S (vol points) ===")
print(f"  {'S':>6} {'n':>4} {'mean':>7} {'hit':>5} {'p5':>7} | {'BUILD':>7} {'FWD':>7}")
for S in [0.0, 0.02, 0.04, 0.06, 0.08, 0.10]:
    sub = R[R["spread"] >= S]
    s = stat(sub["short_ret"])
    b = stat(sub[sub["ed"] <= SPLIT]["short_ret"]); f = stat(sub[sub["ed"] > SPLIT]["short_ret"])
    if s["n"] < 10:
        continue
    print(f"  {S:>6.2f} {s['n']:>4d} {s['mean']:>+7.1%} {s['hit']:>5.0%} {s['p5']:>+7.0%} | "
          f"{b['mean']:>+7.1%} {f['mean']:>+7.1%}")
