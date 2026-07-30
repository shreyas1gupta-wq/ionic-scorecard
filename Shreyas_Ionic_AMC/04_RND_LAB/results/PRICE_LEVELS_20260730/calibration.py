"""CALIBRATION CHECK (mandatory per task spec): the sweep-prior-day-level-then-reclaim
pattern is ALREADY KNOWN to work (session baseline: +6.67 pts, t=2.09, on 15-min bars).
If this level machinery cannot reproduce a comparable (same-sign, same-order-of-magnitude)
number for prior-day levels on 1-min bars, the implementation is wrong -- run this BEFORE
trusting any of the 17-system results.

Definition (symmetric, pooled into one cell):
  LOW sweep+reclaim:  day's low dips BELOW prior-day low, then a later bar CLOSES back
                      above prior-day low (reclaim) -> LONG at next bar's open.
  HIGH sweep+reclaim: day's high pokes ABOVE prior-day high, then a later bar CLOSES back
                      below prior-day high (reclaim) -> SHORT at next bar's open.
Exit: same ATR-scaled stop/target configs as the main study, via pathsafe (both bounds).
"""
import sys
import time
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\lib")
from pathsafe import simulate_exit, summarize  # noqa: E402

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PRICE_LEVELS_20260730"
EXIT_CFGS = {"tight_atr": dict(stop_f=0.30, target_f=0.45), "wide_atr": dict(stop_f=0.50, target_f=0.85)}


def main():
    daily = pd.read_parquet(f"{OUT}/daily.parquet")
    bars = pd.read_parquet(f"{OUT}/bars_1min.parquet")
    atr_by_date = daily["atr14_prior"].to_dict()
    ph_by_date = daily["prior_high"].to_dict()
    pl_by_date = daily["prior_low"].to_dict()

    day_groups = {d: g for d, g in bars.groupby("date")}
    rows = []
    for date, day in day_groups.items():
        ph, pl, atr = ph_by_date.get(date), pl_by_date.get(date), atr_by_date.get(date)
        if any(pd.isna(x) for x in (ph, pl, atr)) or atr <= 0:
            continue
        h = day["high"].to_numpy(float); l = day["low"].to_numpy(float)
        o = day["open"].to_numpy(float); c = day["close"].to_numpy(float)
        n = len(h)
        if n < 10:
            continue

        # LOW sweep + reclaim -> LONG
        sweep_lo = np.where(l < pl)[0]
        if len(sweep_lo):
            i = sweep_lo[0]
            reclaim = None
            for j in range(i, n):
                if c[j] > pl:
                    reclaim = j
                    break
            if reclaim is not None and reclaim + 1 < n:
                ei = reclaim + 1
                entry = o[ei]
                exit_bars = pd.DataFrame({"high": h[ei:], "low": l[ei:], "close": c[ei:]})
                if len(exit_bars) >= 3:
                    for cfg_name, cfg in EXIT_CFGS.items():
                        try:
                            res = simulate_exit(exit_bars, entry, 1,
                                                 stop=cfg["stop_f"] * atr, target=cfg["target_f"] * atr)
                        except Exception:
                            continue
                        rows.append(dict(date=date, side="low_reclaim_long", exit_cfg=cfg_name,
                                          pnl_pess=res.pnl_pessimistic, pnl_opt=res.pnl_optimistic))

        # HIGH sweep + reclaim -> SHORT
        sweep_hi = np.where(h > ph)[0]
        if len(sweep_hi):
            i = sweep_hi[0]
            reclaim = None
            for j in range(i, n):
                if c[j] < ph:
                    reclaim = j
                    break
            if reclaim is not None and reclaim + 1 < n:
                ei = reclaim + 1
                entry = o[ei]
                exit_bars = pd.DataFrame({"high": h[ei:], "low": l[ei:], "close": c[ei:]})
                if len(exit_bars) >= 3:
                    for cfg_name, cfg in EXIT_CFGS.items():
                        try:
                            res = simulate_exit(exit_bars, entry, -1,
                                                 stop=cfg["stop_f"] * atr, target=cfg["target_f"] * atr)
                        except Exception:
                            continue
                        rows.append(dict(date=date, side="high_reclaim_short", exit_cfg=cfg_name,
                                          pnl_pess=res.pnl_pessimistic, pnl_opt=res.pnl_optimistic))

    df = pd.DataFrame(rows)
    cost = np.where(df["date"] < pd.Timestamp("2024-10-01"), 4.47, 5.97) + 0.5
    df["net_pess"] = df["pnl_pess"] - cost
    df["net_opt"] = df["pnl_opt"] - cost
    df.to_parquet(f"{OUT}/calibration_trades.parquet")

    print("=== CALIBRATION: sweep prior-day level + reclaim (pooled long+short) ===")
    for cfg_name in EXIT_CFGS:
        sub = df[df["exit_cfg"] == cfg_name]
        n = len(sub)
        gross_mean = sub["pnl_pess"].mean()
        net_mean = sub["net_pess"].mean()
        t_gross = stats.ttest_1samp(sub["pnl_pess"], 0).statistic
        t_net = stats.ttest_1samp(sub["net_pess"], 0).statistic
        print(f"[{cfg_name}] n={n}  gross_pts={gross_mean:+.2f} t_gross={t_gross:.2f}  "
              f"net_pts={net_mean:+.2f} t_net={t_net:.2f}")
    print("BASELINE TO MATCH (sign + rough order of magnitude): +6.67 pts, t=2.09 "
          "(15-min-bar prior-session estimate)")


if __name__ == "__main__":
    main()
