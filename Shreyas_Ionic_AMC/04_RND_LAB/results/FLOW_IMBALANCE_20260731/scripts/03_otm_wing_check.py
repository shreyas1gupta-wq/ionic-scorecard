"""Side-check (not a new backtest): does restricting to the near-ATM band (spot +/- 8
strikes) discard meaningful value-weighted OI-flow, or is OTM noise as expected?
Samples ~16 expiries spread across the eras, computes total |dOI|*premium*lot value for
near-ATM strikes vs strikes beyond the band, on the SAME cleaned OI series. Reports the
near-ATM value SHARE of total chain flow. Cheap: sampled, not the full 261-expiry set.
"""
import sys, gc
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "lib"))
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
from chainlock import chain_slot  # noqa: E402
import chain  # noqa: E402

RES_DIR = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/FLOW_IMBALANCE_20260731"
LOT_SIZE = 65
BAND_STRIKES = 8


def value_share_for_expiry(exp, spot_idx):
    with chain_slot("flow-otm-check", min_free_gb=1.0):
        df = chain.load_expiry(exp)
        df = df[["t", "trading_day", "close", "open_interest", "strike", "option_type"]]
        rows = []
        for tday_str, day_df in df.groupby("trading_day"):
            tday = dt.date.fromisoformat(tday_str)
            day_spot = spot_idx[(spot_idx.index.date == tday) & (spot_idx.index.time >= dt.time(9, 15))]
            if day_spot.empty:
                continue
            spot_ref = float(day_spot.iloc[0]["close"])
            strikes = np.sort(day_df["strike"].unique())
            if len(strikes) < 2:
                continue
            step = float(np.median(np.diff(strikes))) or 50.0
            lo, hi = spot_ref - BAND_STRIKES * step, spot_ref + BAND_STRIKES * step
            d = day_df.sort_values(["strike", "option_type", "t"]).copy()
            d["oi_clean"] = d["open_interest"].where(d["open_interest"] != 0, np.nan)
            d["oi_clean"] = d.groupby(["strike", "option_type"])["oi_clean"].ffill()
            g = d.groupby(["strike", "option_type"]).agg(
                d_oi=("oi_clean", lambda s: s.diff().abs().sum()),
                px=("close", "mean"))
            g["value_cr"] = g["d_oi"] * g["px"] * LOT_SIZE / 1e7
            g = g.reset_index()
            near = g[(g["strike"] >= lo) & (g["strike"] <= hi)]
            rows.append(dict(expiry=str(exp), trading_day=tday_str,
                              near_atm_cr=near["value_cr"].sum(),
                              total_cr=g["value_cr"].sum()))
        del df
    chain.load_expiry.cache_clear()
    gc.collect()
    return rows


def main():
    mapping, exps = chain.build_expiry_index()
    spot_idx = chain.load_index()
    # spread sample across the eras: every 16th expiry
    sample = exps[::16]
    print(f"sampling {len(sample)} expiries")
    all_rows = []
    for exp in sample:
        rows = value_share_for_expiry(exp, spot_idx)
        all_rows.extend(rows)
        print(f"  {exp}: {len(rows)} days")
    out = pd.DataFrame(all_rows)
    out["near_atm_share"] = out["near_atm_cr"] / out["total_cr"].replace(0, np.nan)
    out.to_csv(RES_DIR / "otm_wing_check.csv", index=False)
    print(out["near_atm_share"].describe())
    print(f"median near-ATM share of total chain value-weighted flow: "
          f"{out['near_atm_share'].median():.1%}")


if __name__ == "__main__":
    main()
