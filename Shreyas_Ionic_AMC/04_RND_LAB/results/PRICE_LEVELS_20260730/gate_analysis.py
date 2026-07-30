"""SATY-specific conditioning cuts the Principal explicitly asked for:
  (a) PRIORITY levels (0.382/0.618/1.0 x ATR) vs NORMAL levels (0.236/0.5/0.786 x ATR)
  (b) Saty's own "ATR consumed" gate: bucket trades by (day range used up AT the touch bar)
      / ATR14prior, <0.7 vs >=0.7 -- does high ATR-consumption (little room left) make a
      level more likely to HOLD (better REJECT, worse BREAK)?
Report ALL buckets with n (never just the favourable one), split BUILD vs RECENT per the
regime-conditioning guard: a cut only counts if it is directionally consistent in both.
"""
import numpy as np
import pandas as pd
from scipy import stats

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PRICE_LEVELS_20260730"
BUILD_END = pd.Timestamp("2024-10-01")
HOLDOUT_START = pd.Timestamp("2026-01-01")


def stat(x):
    x = x.to_numpy()
    n = len(x)
    if n == 0:
        return (0, np.nan, np.nan)
    t = stats.ttest_1samp(x, 0).statistic if n > 1 and x.std() > 0 else np.nan
    return (n, x.mean(), t)


def main():
    trades = pd.read_parquet(f"{OUT}/trades_real.parquet")
    saty = trades[trades["system"] == "SATY"].copy()
    saty["era"] = np.select([saty["date"] < BUILD_END, saty["date"] >= HOLDOUT_START],
                             ["BUILD", "HOLDOUT"], default="RECENT")
    saty_bt = saty[saty["era"] != "HOLDOUT"]

    print("=== (a) SATY PRIORITY vs NORMAL levels (build+recent, holdout excluded) ===")
    for hyp in ["REJECT", "BREAK"]:
        for cfg in ["tight_atr", "wide_atr"]:
            for pr in [True, False]:
                sub = saty_bt[(saty_bt.hypothesis == hyp) & (saty_bt.exit_cfg == cfg) &
                              (saty_bt.priority == pr)]
                n, m, t = stat(sub["net_pess"])
                # era split for consistency check
                nb, mb, tb = stat(sub[sub.era == "BUILD"]["net_pess"])
                nr, mr, tr = stat(sub[sub.era == "RECENT"]["net_pess"])
                tag = "PRIORITY" if pr else "normal"
                print(f"{hyp:6s} {cfg:9s} {tag:8s}: n={n:5d} mean={m:+7.2f} t={t:6.2f}  "
                      f"| BUILD n={nb:5d} mean={mb:+7.2f} t={tb:6.2f}  "
                      f"| RECENT n={nr:5d} mean={mr:+7.2f} t={tr:6.2f}")

    print()
    print("=== (b) SATY ATR-CONSUMED gate (day range used up AT touch / ATR14prior) ===")
    for hyp in ["REJECT", "BREAK"]:
        for cfg in ["tight_atr", "wide_atr"]:
            for lo, hi, label in [(0.0, 0.7, "consumed<0.7"), (0.7, 99, "consumed>=0.7")]:
                sub = saty_bt[(saty_bt.hypothesis == hyp) & (saty_bt.exit_cfg == cfg) &
                              (saty_bt.atr_consumed >= lo) & (saty_bt.atr_consumed < hi)]
                n, m, t = stat(sub["net_pess"])
                nb, mb, tb = stat(sub[sub.era == "BUILD"]["net_pess"])
                nr, mr, tr = stat(sub[sub.era == "RECENT"]["net_pess"])
                print(f"{hyp:6s} {cfg:9s} {label:15s}: n={n:5d} mean={m:+7.2f} t={t:6.2f}  "
                      f"| BUILD n={nb:5d} mean={mb:+7.2f} t={tb:6.2f}  "
                      f"| RECENT n={nr:5d} mean={mr:+7.2f} t={tr:6.2f}")


def cpr_width_gate():
    """CPR width conditioning (proxy for 'virgin CPR' -- see FINDINGS for the honest caveat:
    this tests NARROW-vs-WIDE CPR, not the precise multi-day zone-untouched 'virgin' definition,
    which needs one extra day of recursion this pass did not implement)."""
    daily = pd.read_parquet(f"{OUT}/daily.parquet").reset_index().rename(columns={"date": "date"})
    daily["cpr_width_daily"] = (2 * daily["prior_close"] - daily["prior_high"] - daily["prior_low"]).abs() / 3
    daily["width_ratio"] = daily["cpr_width_daily"] / daily["atr14_prior"]
    med = daily["width_ratio"].median()

    trades = pd.read_parquet(f"{OUT}/trades_real.parquet")
    cpr = trades[trades["system"] == "CPR_DAY"].merge(
        daily[["date", "width_ratio"]], on="date", how="left")
    cpr["era"] = np.select([cpr["date"] < BUILD_END, cpr["date"] >= HOLDOUT_START],
                            ["BUILD", "HOLDOUT"], default="RECENT")
    cpr_bt = cpr[cpr["era"] != "HOLDOUT"]

    print()
    print(f"=== (c) CPR_DAY width gate (proxy for virgin-CPR; median width_ratio={med:.3f}) ===")
    for hyp in ["REJECT", "BREAK"]:
        for cfg in ["tight_atr", "wide_atr"]:
            for lo, hi, label in [(0.0, med, "narrow(<med)"), (med, 99, "wide(>=med)")]:
                sub = cpr_bt[(cpr_bt.hypothesis == hyp) & (cpr_bt.exit_cfg == cfg) &
                             (cpr_bt.width_ratio >= lo) & (cpr_bt.width_ratio < hi)]
                n, m, t = stat(sub["net_pess"])
                nb, mb, tb = stat(sub[sub.era == "BUILD"]["net_pess"])
                nr, mr, tr = stat(sub[sub.era == "RECENT"]["net_pess"])
                print(f"{hyp:6s} {cfg:9s} {label:13s}: n={n:5d} mean={m:+7.2f} t={t:6.2f}  "
                      f"| BUILD n={nb:5d} mean={mb:+7.2f} t={tb:6.2f}  "
                      f"| RECENT n={nr:5d} mean={mr:+7.2f} t={tr:6.2f}")


if __name__ == "__main__":
    main()
    cpr_width_gate()
