"""Check REAL volume at the exact entry/exit bars of every simulated trade so far.
Answers the coordinator's concern directly: are we reading untraded/model-priced quotes?
"""
import glob
import os

import pandas as pd
import trend_catcher as tc
import chain

files = sorted(glob.glob(str(tc.TRADES_DIR / "*.csv")))
summary = []
for fp in files:
    df = pd.read_csv(fp)
    if df.empty:
        continue
    df["exp"] = pd.to_datetime(df["exp"]).dt.date
    df["entry_t"] = pd.to_datetime(df["entry_t"])
    df["exit_t"] = pd.to_datetime(df["exit_t"])
    zero_entry = 0
    zero_exit = 0
    n = len(df)
    for exp, grp in df.groupby("exp"):
        cdf = chain.load_expiry(exp)
        for _, row in grp.iterrows():
            leg = cdf[(cdf["strike"] == row["strike"]) & (cdf["option_type"] == row["otype"])]
            leg = leg.set_index("t")
            ev = leg["volume"].reindex([row["entry_t"]]).iloc[0] if row["entry_t"] in leg.index else None
            if ev is not None and ev == 0:
                zero_entry += 1
            if row["reason"] != "expiry_intrinsic":
                xv = leg["volume"].reindex([row["exit_t"]]).iloc[0] if row["exit_t"] in leg.index else None
                if xv is not None and xv == 0:
                    zero_exit += 1
    summary.append({"file": os.path.basename(fp), "n": n, "zero_vol_entry": zero_entry,
                     "zero_vol_exit": zero_exit,
                     "pct_zero_entry": round(100 * zero_entry / n, 1),
                     "pct_zero_exit": round(100 * zero_exit / n, 1)})
    print(summary[-1])

out = pd.DataFrame(summary)
out.to_csv(tc.OUT / "volume_validation_summary.csv", index=False)
print("\nOverall:")
print(out[["n", "zero_vol_entry", "zero_vol_exit"]].sum())
