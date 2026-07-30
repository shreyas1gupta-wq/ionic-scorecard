"""Stats for order-flow proxy cells. NO placebo run: every raw cell (both REJECT and CONTINUE,
both proxies) is negative (see orderflow.py stdout) -- a placebo cannot rescue or explain a LOSS
(there is no 'this specific trigger is special' claim to test), same logic PRICE_LEVELS_20260730
used to skip its own placebo once the scan showed nothing but losers. Reverse-the-negative check
(gross vs net) is reported explicitly instead, per the mandate's own standing convention."""
import sys
import numpy as np
import pandas as pd

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\NEWDIM_LEVELS_20260731"
sys.path.insert(0, OUT)
from common_stats import stat, era_of, null_hit_rate, concentration  # noqa: E402

RR = {"tight_atr": 1.5, "wide_atr": 1.7}


def main():
    trades = pd.read_parquet(f"{OUT}/orderflow_trades.parquet")
    trades["era"] = era_of(trades["date"])
    trades["gross_pess"] = trades["pnl_pess"]  # pre-cost pnl (net_pess = pnl_pess - cost already)

    rows = []
    for (proxy, signal, side, hyp, cfg), g in trades.groupby(
            ["proxy", "signal", "side", "hypothesis", "exit_cfg"]):
        bt = g[g["era"] != "HOLDOUT"]
        s_bt = stat(bt["net_pess"])
        s_build = stat(g[g["era"] == "BUILD"]["net_pess"])
        s_recent = stat(g[g["era"] == "RECENT"]["net_pess"])
        s_hold = stat(g[g["era"] == "HOLDOUT"]["net_pess"])
        s_gross = stat(bt["gross_pess"])
        win = float((bt["net_pess"] > 0).mean()) if len(bt) else np.nan
        months = max(1, (bt["date"].max() - bt["date"].min()).days / 30.44) if len(bt) else np.nan
        rows.append(dict(
            dimension="ORDER_FLOW_PROXY", cell=f"{proxy}|{signal}|{side}|{hyp}|{cfg}", n=s_bt["n"],
            trades_per_month=round(s_bt["n"] / months, 2) if months else np.nan,
            win_pct=round(win * 100, 1), null_hit_pct=round(null_hit_rate(RR[cfg]) * 100, 1),
            mean_pts=round(s_bt["mean"], 3), gross_mean_pts=round(s_gross["mean"], 3), avg_rr=RR[cfg],
            t=round(s_bt["t"], 3) if np.isfinite(s_bt["t"]) else np.nan,
            t_build=round(s_build["t"], 3) if np.isfinite(s_build["t"]) else np.nan,
            t_recent=round(s_recent["t"], 3) if np.isfinite(s_recent["t"]) else np.nan,
            n_holdout=s_hold["n"], mean_holdout=round(s_hold["mean"], 3) if np.isfinite(s_hold["mean"]) else np.nan,
            conc=round(concentration(bt["net_pess"]), 3) if len(bt) else np.nan,
            placebo_p=np.nan,
        ))
    out = pd.DataFrame(rows)
    out.to_csv(f"{OUT}/orderflow_cells.csv", index=False)
    print(out.to_string())


if __name__ == "__main__":
    main()
