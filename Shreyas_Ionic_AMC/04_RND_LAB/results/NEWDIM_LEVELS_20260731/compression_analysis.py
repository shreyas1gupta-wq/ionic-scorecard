"""Stats + random-level placebo for compression-breakout cells (NR7/NR4/BOX4 x any-time/first60m)."""
import sys
import numpy as np
import pandas as pd

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\NEWDIM_LEVELS_20260731"
sys.path.insert(0, OUT)
from compression_signals import build_day_arrays, simulate_capped, add_costs  # noqa: E402
from common_stats import stat, era_of, null_hit_rate, concentration  # noqa: E402

RR = {"tight_atr": 1.5, "wide_atr": 1.7}
N_SEEDS = 5


def cell_table(trades):
    trades = trades.copy()
    trades["era"] = era_of(trades["date"])
    rows = []
    for (sysname, hyp, cfg, cap), g in trades.groupby(["system", "hypothesis", "exit_cfg", "window_cap"]):
        bt = g[g["era"] != "HOLDOUT"]
        s_bt = stat(bt["net_pess"])
        s_build = stat(g[g["era"] == "BUILD"]["net_pess"])
        s_recent = stat(g[g["era"] == "RECENT"]["net_pess"])
        s_hold = stat(g[g["era"] == "HOLDOUT"]["net_pess"])
        win = float((bt["net_pess"] > 0).mean()) if len(bt) else np.nan
        months = max(1, (bt["date"].max() - bt["date"].min()).days / 30.44) if len(bt) else np.nan
        rows.append(dict(
            dimension="COMPRESSION", cell=f"{sysname}|{cap}|{hyp}|{cfg}", n=s_bt["n"],
            trades_per_month=round(s_bt["n"] / months, 2) if months else np.nan,
            win_pct=round(win * 100, 1), null_hit_pct=round(null_hit_rate(RR[cfg]) * 100, 1),
            mean_pts=round(s_bt["mean"], 3), avg_rr=RR[cfg],
            t=round(s_bt["t"], 3) if np.isfinite(s_bt["t"]) else np.nan,
            t_build=round(s_build["t"], 3) if np.isfinite(s_build["t"]) else np.nan,
            t_recent=round(s_recent["t"], 3) if np.isfinite(s_recent["t"]) else np.nan,
            n_holdout=s_hold["n"], mean_holdout=round(s_hold["mean"], 3) if np.isfinite(s_hold["mean"]) else np.nan,
            conc=round(concentration(bt["net_pess"]), 3) if len(bt) else np.nan,
        ))
    return pd.DataFrame(rows)


def main():
    trades = pd.read_parquet(f"{OUT}/compression_trades.parquet")
    levels = pd.read_parquet(f"{OUT}/compression_levels.parquet")
    daily = pd.read_parquet(f"{OUT}/daily.parquet")
    bars = pd.read_parquet(f"{OUT}/bars_1min.parquet")
    day_arrays = build_day_arrays(bars)
    atr_by_date = daily["atr14_prior"].to_dict()

    real = cell_table(trades)
    real.to_csv(f"{OUT}/compression_cells.csv", index=False)
    print(real.to_string())

    dist = (levels["level_price"] - levels["anchor"]).abs()
    mean_dist = dist.groupby(levels["level_name"]).transform("mean")
    rng_master = np.random.default_rng(20260731)
    seed_stats = []
    for seed in range(N_SEEDS):
        rng = np.random.default_rng(rng_master.integers(0, 2**31))
        sign = rng.choice([-1.0, 1.0], size=len(levels))
        mag = rng.uniform(0.0, 2 * mean_dist.to_numpy())
        placebo = levels.copy()
        placebo["level_price"] = placebo["anchor"].to_numpy() + sign * mag
        all_tr = []
        for cap in (None, 60):
            tr = simulate_capped(placebo, day_arrays, atr_by_date, cap)
            all_tr.append(tr)
        ptr = pd.concat(all_tr, ignore_index=True)
        ptr = add_costs(ptr)
        ptr["era"] = era_of(ptr["date"])
        bt = ptr[ptr["era"] != "HOLDOUT"]
        g = bt.groupby(["system", "hypothesis", "exit_cfg", "window_cap"])["net_pess"].mean().reset_index()
        g["seed"] = seed
        seed_stats.append(g)
        print(f"placebo seed {seed} done, n={len(ptr)}")
    placebo_all = pd.concat(seed_stats, ignore_index=True)
    placebo_all.to_parquet(f"{OUT}/compression_placebo.parquet")

    pvals = []
    for _, row in real.iterrows():
        sysname, cap, hyp, cfg = row["cell"].split("|")
        pb = placebo_all[(placebo_all.system == sysname) & (placebo_all.window_cap == cap) &
                          (placebo_all.hypothesis == hyp) & (placebo_all.exit_cfg == cfg)]["net_pess"]
        pvals.append(float((pb.abs() >= abs(row["mean_pts"])).mean()) if len(pb) else np.nan)
    real["placebo_p"] = pvals
    real.to_csv(f"{OUT}/compression_cells.csv", index=False)
    print(real[["cell", "n", "mean_pts", "t", "placebo_p"]].to_string())


if __name__ == "__main__":
    main()
