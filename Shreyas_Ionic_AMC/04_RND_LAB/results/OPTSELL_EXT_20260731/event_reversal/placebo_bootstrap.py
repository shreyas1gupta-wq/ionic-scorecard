import pandas as pd
import numpy as np

OUT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTSELL_EXT_20260731\event_reversal"
COST = 3.538

real = pd.read_csv(f"{OUT}/real_cells_reversed.csv")
pb = pd.read_parquet(f"{OUT}/placebo_trades_raw.parquet")
pb["gross_pts"] = (pb["ce_exit"] + pb["pe_exit"]) - (pb["ce_entry"] + pb["pe_entry"])
pb["reversed_net_pts"] = -pb["gross_pts"] - COST
print("placebo pool sizes:", pb.groupby("cell").size().to_dict())
print(pb.groupby("cell")["reversed_net_pts"].agg(["count", "mean", "std", "min", "max"]).to_string())

mapping = {"EVENT_BUDGET": ("PLACEBO_2D", 6), "EVENT_FED": ("PLACEBO_3D", 36), "IV_TERM_CHEAP": ("PLACEBO_5D", 6)}

rng = np.random.default_rng(20260731)
N_BOOT = 5000
results = []
for cell, (pcell, n) in mapping.items():
    real_mean = real[real.cell == cell]["reversed_net_pts"].mean()
    pool = pb[pb.cell == pcell]["reversed_net_pts"].values
    boots = rng.choice(pool, size=(N_BOOT, n), replace=True).mean(axis=1)
    p_one_sided = (boots >= real_mean).mean()
    print(f"\n{cell}: real_mean={real_mean:.2f}  placebo_pool(n={len(pool)}) mean={pool.mean():.2f} "
          f"sd={pool.std():.2f} | bootstrap(n={n}) p={p_one_sided:.4f}  "
          f"placebo_boot_mean={boots.mean():.2f} placebo_boot_p95={np.quantile(boots,0.95):.2f}")
    results.append(dict(cell=cell, real_mean=real_mean, placebo_pool_n=len(pool), placebo_pool_mean=pool.mean(),
                         placebo_pool_sd=pool.std(), bootstrap_n=n, placebo_p_one_sided=p_one_sided,
                         placebo_boot_mean=boots.mean(), placebo_boot_p95=np.quantile(boots, 0.95)))

pd.DataFrame(results).to_csv(f"{OUT}/placebo_bootstrap_results.csv", index=False)
print(f"\nsaved {OUT}/placebo_bootstrap_results.csv")
