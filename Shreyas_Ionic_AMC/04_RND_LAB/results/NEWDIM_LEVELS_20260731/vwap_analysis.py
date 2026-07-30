"""Stats + random-entry placebo for anchored-VWAP band-touch cells."""
import sys
import numpy as np
import pandas as pd

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\NEWDIM_LEVELS_20260731"
PL = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PRICE_LEVELS_20260730"
LIB = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\lib"
sys.path.insert(0, PL)
sys.path.insert(0, LIB)
sys.path.insert(0, OUT)
from touch_engine import build_day_arrays, EXIT_CFGS  # noqa: E402
from pathsafe import simulate_exit  # noqa: E402
from common_stats import stat, era_of, null_hit_rate, concentration, random_entry_placebo  # noqa: E402

RR = {"tight_atr": 1.5, "wide_atr": 1.7}
N_DRAWS = 40  # reduced from 200 for wall-clock speed (p resolution 1/40=0.025, stated explicitly)


def main():
    trades = pd.read_parquet(f"{OUT}/vwap_trades.parquet")
    daily = pd.read_parquet(f"{OUT}/daily.parquet")
    bars = pd.read_parquet(f"{OUT}/bars_1min.parquet")
    day_arrays = build_day_arrays(bars)
    atr_by_date = daily["atr14_prior"].to_dict()
    all_dates = daily.index

    trades["era"] = era_of(trades["date"])
    rows = []
    for (anchor, sigma, side, hyp, cfg), g in trades.groupby(
            ["anchor", "sigma", "side", "hypothesis", "exit_cfg"]):
        bt = g[g["era"] != "HOLDOUT"]
        s_bt = stat(bt["net_pess"])
        s_build = stat(g[g["era"] == "BUILD"]["net_pess"])
        s_recent = stat(g[g["era"] == "RECENT"]["net_pess"])
        s_hold = stat(g[g["era"] == "HOLDOUT"]["net_pess"])
        win = float((bt["net_pess"] > 0).mean()) if len(bt) else np.nan
        months = max(1, (bt["date"].max() - bt["date"].min()).days / 30.44) if len(bt) else np.nan

        entries = bt[["date", "tmin", "direction"]].copy()
        p_val = np.nan
        if len(entries) >= 10:
            draws = random_entry_placebo(entries, day_arrays, atr_by_date, EXIT_CFGS[cfg],
                                          all_dates, simulate_exit, n_draws=N_DRAWS,
                                          seed=hash((anchor, sigma, side, hyp, cfg)) % (2**31))
            valid = draws[np.isfinite(draws)]
            if len(valid) >= N_DRAWS * 0.5:
                p_val = float((np.abs(valid) >= abs(s_bt["mean"])).mean())

        rows.append(dict(
            dimension="ANCHORED_VWAP", cell=f"{anchor}|sigma{sigma}|{side}|{hyp}|{cfg}",
            n=s_bt["n"], trades_per_month=round(s_bt["n"] / months, 2) if months else np.nan,
            win_pct=round(win * 100, 1), null_hit_pct=round(null_hit_rate(RR[cfg]) * 100, 1),
            mean_pts=round(s_bt["mean"], 3), avg_rr=RR[cfg],
            t=round(s_bt["t"], 3) if np.isfinite(s_bt["t"]) else np.nan,
            t_build=round(s_build["t"], 3) if np.isfinite(s_build["t"]) else np.nan,
            t_recent=round(s_recent["t"], 3) if np.isfinite(s_recent["t"]) else np.nan,
            n_holdout=s_hold["n"],
            mean_holdout=round(s_hold["mean"], 3) if np.isfinite(s_hold["mean"]) else np.nan,
            conc=round(concentration(bt["net_pess"]), 3) if len(bt) else np.nan,
            placebo_p=round(p_val, 3) if np.isfinite(p_val) else np.nan,
        ))
        print(f"done {anchor} sigma{sigma} {side} {hyp} {cfg}: n={s_bt['n']} mean={s_bt['mean']:.2f} "
              f"t={s_bt['t']:.2f} placebo_p={p_val}")

    out = pd.DataFrame(rows)
    out.to_csv(f"{OUT}/vwap_cells.csv", index=False)
    print(out.to_string())


if __name__ == "__main__":
    main()
