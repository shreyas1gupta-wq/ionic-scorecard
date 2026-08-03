"""IRONFLY_LADDER_20260802 -- step 5: reversal check.
Per firm convention (reverse strong-negative-Sharpe cells by default): for EVERY cell, compute
what the SHORT iron butterfly (sell ATM straddle, buy the OTM strangle -- exact opposite of every
leg) would have earned, using the SAME already-computed trades (no re-backtest needed).
Exact relation, verified algebraically before coding: flipping every leg's sign negates gross_pnl
exactly (gross_reversed = -gross_original), while COST is a fixed per-rung drag that applies
identically regardless of direction (same 4 legs, same round-trip). So:
    net_reversed = -gross_original - cost = -(net_original + cost) - cost = -net_original - 2*cost
This is why reversing only rescues a DIRECTIONAL loss (gross edge genuinely wrong-signed) and not
a COST-DOMINATED one (gross near zero, cost is the whole loss) -- reversing a cost-dominated loss
just pays the same cost again from the other side.
"""
import glob
import os
import time

import numpy as np
import pandas as pd

CKPT = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
        r"\Shreyas_Ionic_AMC\04_RND_LAB\results\IRONFLY_LADDER_20260802\checkpoints")
COST_TOTAL = 1.77 * 4


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


rows = []
for path in sorted(glob.glob(f"{CKPT}\\trades_d*.csv")):
    tag = os.path.basename(path).replace("trades_", "").replace(".csv", "")
    df = pd.read_csv(path)
    n = len(df)
    if n == 0:
        continue
    net = df["net_pnl"].to_numpy()
    gross_mean = net.mean() + COST_TOTAL          # = df['gross_pnl'].mean(), cross-checked below
    gross_mean_direct = df["gross_pnl"].mean()
    assert abs(gross_mean - gross_mean_direct) < 1e-6, "algebra vs direct gross mismatch"

    net_rev = -net - 2 * COST_TOTAL
    sd_rev = net_rev.std(ddof=1) if n > 1 else np.nan
    t_rev = net_rev.mean() / (sd_rev / np.sqrt(n)) if n > 1 and sd_rev > 0 else np.nan
    win_rev = (net_rev > 0).mean()

    rows.append(dict(cell=tag, n=n, gross_mean_original=gross_mean_direct,
                      net_mean_original=net.mean(), t_original=net.mean() / (net.std(ddof=1) / np.sqrt(n)) if n > 1 else np.nan,
                      net_mean_reversed=net_rev.mean(), t_reversed=t_rev, win_reversed=win_rev))

out = pd.DataFrame(rows).sort_values("net_mean_reversed", ascending=False)
out.to_csv(f"{CKPT}\\..\\reversal_check.csv", index=False)
pd.set_option("display.width", 160)
pd.set_option("display.max_rows", 40)
print(out.to_string(index=False))
log("DONE")
