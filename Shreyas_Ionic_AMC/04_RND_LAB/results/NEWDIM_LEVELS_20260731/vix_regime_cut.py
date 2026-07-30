"""DIMENSION 6 -- 'any TradingView indicator you judge worth it that is NOT price-on-price'.
PICK: India VIX (level + trailing-252d percentile). REASONING: every price-on-price oscillator in
scope (RSI/Stoch/CCI/Williams/MA regime/Keltner/Donchian/Squeeze) is already dead per the mandate's
own summary. India VIX is a genuinely different data source -- an options-IMPLIED-vol index, not a
transform of the NIFTY OHLC series -- and it is the one series SHARED_CONTEXT already flagged as
worth a conditioning cut ('report trade P&L conditioned on IV percentile'). Applied here as a
REGIME CONDITIONING CUT on this study's single most promising cell (BOX4 first60m BREAK -- 4-day
balance-area compression breaking out in the opening 60 minutes, t=2.86/2.41, see
compression_cells.csv), per the SHARED_CONTEXT guard: 'report ALL buckets with their n, not just
the profitable ones' and 'a filter only counts if it holds in BOTH pre/post-Oct-2024 halves'.
NOT counted as an extra independent trial in this study's own Bonferroni tally (same convention as
PRICE_LEVELS_20260730's SATY priority/ATR-consumed gates: a re-slice of an already-logged cell,
disclosed separately).
"""
import numpy as np
import pandas as pd

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\NEWDIM_LEVELS_20260731"


def stat(x):
    from scipy import stats
    x = pd.Series(x).dropna().to_numpy()
    n = len(x)
    if n < 2 or x.std() == 0:
        return n, (x.mean() if n else np.nan), np.nan
    return n, float(x.mean()), float(stats.ttest_1samp(x, 0).statistic)


def main():
    trades = pd.read_parquet(f"{OUT}/compression_trades.parquet")
    vix = pd.read_parquet(f"{OUT}/vix_daily.parquet")
    BUILD_END = pd.Timestamp("2024-10-01")
    HOLDOUT_START = pd.Timestamp("2026-01-01")

    sub = trades[(trades["system"] == "BOX4") & (trades["window_cap"] == "first60m") &
                 (trades["hypothesis"] == "BREAK")].copy()
    sub["date"] = pd.to_datetime(sub["date"])
    sub = sub.merge(vix[["vix_pctile_252"]], left_on="date", right_index=True, how="left")
    sub["era"] = np.select([sub["date"] < BUILD_END, sub["date"] >= HOLDOUT_START],
                            ["BUILD", "RECENT"], default="RECENT")
    sub = sub[sub["date"] < pd.Timestamp("2026-01-01")]  # bt only, matches primary cell's era scope

    print(f"n with valid vix_pctile: {sub['vix_pctile_252'].notna().sum()} / {len(sub)}")
    med = sub["vix_pctile_252"].median()
    print(f"median vix_pctile_252 in this sample: {med:.3f}")

    for cfg in ("tight_atr", "wide_atr"):
        g = sub[sub["exit_cfg"] == cfg]
        print(f"\n--- exit_cfg={cfg} ---")
        for lo, hi, label in [(0.0, 0.5, "VIX_LOW_HALF(<med)"), (0.5, 1.01, "VIX_HIGH_HALF(>=med)")]:
            gg = g[(g["vix_pctile_252"] >= lo) & (g["vix_pctile_252"] < hi)]
            n, m, t = stat(gg["net_pess"])
            nb, mb, tb = stat(gg[gg["era"] == "BUILD"]["net_pess"])
            nr, mr, tr = stat(gg[gg["era"] == "RECENT"]["net_pess"])
            print(f"{label:22s}: n={n:4d} mean={m:+8.3f} t={t:6.3f} | BUILD n={nb:4d} mean={mb:+8.3f} "
                  f"t={tb:6.3f} | RECENT n={nr:4d} mean={mr:+8.3f} t={tr:6.3f}")
        # also raw thirds for a finer look
        for lo, hi, label in [(0.0, 0.33, "VIX_pctile<0.33"), (0.33, 0.67, "0.33-0.67"), (0.67, 1.01, ">=0.67")]:
            gg = g[(g["vix_pctile_252"] >= lo) & (g["vix_pctile_252"] < hi)]
            n, m, t = stat(gg["net_pess"])
            print(f"  [tercile] {label:16s}: n={n:4d} mean={m:+8.3f} t={t:6.3f}")


if __name__ == "__main__":
    main()
