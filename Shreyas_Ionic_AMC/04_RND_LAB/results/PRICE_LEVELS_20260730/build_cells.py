"""Aggregate trades_real.parquet into per-cell stats (n, pts, t, win%, RR, trades/month,
era splits), attach the system-level placebo comparator, and run the SATY-specific
priority-vs-normal and ATR-consumed-gate conditioning cuts. Writes cells.csv + prints the
top cells and the gate/priority tables (captured into gates_report.txt).
"""
import numpy as np
import pandas as pd
from scipy import stats

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PRICE_LEVELS_20260730"
BUILD_END = pd.Timestamp("2024-10-01")
HOLDOUT_START = pd.Timestamp("2026-01-01")


def era_of(dates):
    return np.select([dates < BUILD_END, dates >= HOLDOUT_START],
                      ["BUILD", "HOLDOUT_2026"], default="RECENT_24_25")


def cell_stats(sub: pd.DataFrame, n_months: float):
    n = len(sub)
    if n == 0:
        return dict(n=0, mean=np.nan, t=np.nan, win_pct=np.nan, avg_rr=np.nan, tpm=0.0)
    x = sub["net_pess"].to_numpy()
    mean = x.mean()
    t = stats.ttest_1samp(x, 0).statistic if n > 1 and x.std() > 0 else np.nan
    win = x > 0
    win_pct = win.mean() * 100
    avg_win = x[win].mean() if win.any() else np.nan
    avg_loss = -x[~win].mean() if (~win).any() else np.nan
    rr = (avg_win / avg_loss) if (avg_loss and avg_loss > 0) else np.nan
    tpm = n / n_months if n_months > 0 else np.nan
    return dict(n=n, mean=mean, t=t, win_pct=win_pct, avg_rr=rr, tpm=tpm)


def main():
    trades = pd.read_parquet(f"{OUT}/trades_real.parquet")
    trades["era"] = era_of(trades["date"])
    placebo = pd.read_parquet(f"{OUT}/placebo_seed_stats.parquet")

    # placebo comparator per (system, hypothesis, exit_cfg): mean/sd across seeds
    pb = (placebo.groupby(["system", "hypothesis", "exit_cfg"])["mean"]
          .agg(placebo_mean="mean", placebo_sd="std", placebo_seeds="count").reset_index())

    n_months_build = (BUILD_END - trades["date"].min()).days / 30.44
    n_months_recent = (HOLDOUT_START - BUILD_END).days / 30.44
    n_months_holdout = (trades["date"].max() - HOLDOUT_START).days / 30.44
    n_months_all = (HOLDOUT_START - trades["date"].min()).days / 30.44  # BUILD+RECENT only

    rows = []
    grp_cols = ["system", "level_name", "hypothesis", "exit_cfg"]
    for key, g in trades.groupby(grp_cols):
        system, level_name, hyp, cfg = key
        priority = bool(g["priority"].iloc[0])
        g_all = g[g["era"] != "HOLDOUT_2026"]
        s_all = cell_stats(g_all, n_months_all)
        s_build = cell_stats(g[g["era"] == "BUILD"], n_months_build)
        s_recent = cell_stats(g[g["era"] == "RECENT_24_25"], n_months_recent)
        s_hold = cell_stats(g[g["era"] == "HOLDOUT_2026"], n_months_holdout)
        row = dict(system=system, level_name=level_name, hypothesis=hyp, exit_cfg=cfg,
                   priority=priority)
        for pfx, s in [("all", s_all), ("build", s_build), ("recent", s_recent), ("hold26", s_hold)]:
            for k, v in s.items():
                row[f"{pfx}_{k}"] = v
        rows.append(row)

    cells = pd.DataFrame(rows)
    cells = cells.merge(pb, on=["system", "hypothesis", "exit_cfg"], how="left")
    # empirical placebo z / crude p (5 seeds -> normal approx, honestly small-sample)
    cells["placebo_z"] = (cells["all_mean"] - cells["placebo_mean"]) / cells["placebo_sd"].replace(0, np.nan)
    cells["placebo_p_approx"] = 2 * (1 - stats.norm.cdf(cells["placebo_z"].abs()))

    cells = cells.sort_values("all_t", ascending=False)
    cells.to_csv(f"{OUT}/cells.csv", index=False)
    print("cells.csv written, rows =", len(cells))
    print("TOTAL TRIALS (rows in cells.csv):", len(cells))

    # ---------------- top 10 by |t| on ALL (build+recent), min n>=20 ------------------
    disp = cells[cells["all_n"] >= 20].copy()
    disp["abs_t"] = disp["all_t"].abs()
    top10 = disp.sort_values("abs_t", ascending=False).head(10)
    cols = ["system", "level_name", "hypothesis", "exit_cfg", "all_n", "all_tpm", "all_mean",
            "all_win_pct", "all_rr", "all_t", "placebo_p_approx", "build_mean", "build_t",
            "recent_mean", "recent_t", "hold26_mean", "hold26_n"]
    pd.set_option("display.width", 220)
    print(top10[cols].to_string(index=False))
    top10[cols].to_csv(f"{OUT}/top10.csv", index=False)


if __name__ == "__main__":
    main()
