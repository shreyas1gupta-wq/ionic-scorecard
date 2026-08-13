import trend_catcher as tc
import chain
import pandas as pd

_, exps = chain.build_expiry_index()
sample = exps[::15]
print("sampling", len(sample), "expiries")
rows = []
for exp in sample:
    try:
        df = chain.load_expiry(exp)
    except Exception as e:
        print(exp, "LOAD FAIL", type(e).__name__, e)
        continue
    df = df.copy()
    df["day"] = df["t"].dt.date
    g = df.groupby("day")["volume"].sum()
    file_start = df["day"].min()
    max_file_dte = (exp - file_start).days
    max_traded_dte = -1
    for day, vol in g.items():
        dte = (exp - day).days
        rows.append({"exp": str(exp), "day": str(day), "dte": dte, "total_vol": int(vol)})
        if vol > 0 and dte > max_traded_dte:
            max_traded_dte = dte
    print(f"{exp}  file_days={df['day'].nunique():3d}  file_max_dte={max_file_dte:3d}  "
          f"max_traded_dte={max_traded_dte:3d}  total_rows={len(df)}")

r = pd.DataFrame(rows)
r.to_csv("volume_probe.csv", index=False)
print("\nDONE. rows written:", len(r))
