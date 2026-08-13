"""Random-level placebo: same anchor as the real system, same count, distance resampled
from Uniform(0, 2*mean_real_distance) so the EXPECTED distance from spot matches the real
system exactly, sign randomized. This tests whether the SPECIFIC level (a particular Saty
ratio, a particular pivot, prior-day-close, ...) matters, or whether ANY similarly-distant
price attracts the same touch/reject/break statistics (price touches *some* level constantly).
Compared at the (system, hypothesis, exit_cfg) granularity -- pooled across level_name, since
an individual placebo draw has no stable per-level_name identity across days.
"""
import sys
import time
import numpy as np
import pandas as pd
from touch_engine import build_day_arrays, simulate_all, add_costs

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PRICE_LEVELS_20260730"
N_SEEDS = 5


def main():
    daily = pd.read_parquet(f"{OUT}/daily.parquet")
    bars = pd.read_parquet(f"{OUT}/bars_1min.parquet")
    levels = pd.read_parquet(f"{OUT}/levels_real.parquet")
    atr_by_date = daily["atr14_prior"].to_dict()
    day_arrays = build_day_arrays(bars)

    dist = (levels["level_price"] - levels["anchor"]).abs()
    mean_dist = dist.groupby(levels["system"]).transform("mean")

    seed_results = []
    rng_master = np.random.default_rng(12345)
    for seed in range(N_SEEDS):
        rng = np.random.default_rng(rng_master.integers(0, 2**31))
        t0 = time.time()
        sign = rng.choice([-1.0, 1.0], size=len(levels))
        mag = rng.uniform(0.0, 2 * mean_dist.to_numpy())
        placebo = levels.copy()
        placebo["level_price"] = placebo["anchor"].to_numpy() + sign * mag
        trades = simulate_all(placebo, day_arrays, atr_by_date)
        trades = add_costs(trades)
        g = (trades.groupby(["system", "hypothesis", "exit_cfg"])["net_pess"]
             .agg(["count", "mean"]).reset_index())
        g["seed"] = seed
        seed_results.append(g)
        print(f"seed {seed} done in {time.time()-t0:.1f}s, trades={len(trades)}", flush=True)

    allg = pd.concat(seed_results, ignore_index=True)
    allg.to_parquet(f"{OUT}/placebo_seed_stats.parquet")
    print("saved placebo_seed_stats.parquet", allg.shape)


if __name__ == "__main__":
    main()
