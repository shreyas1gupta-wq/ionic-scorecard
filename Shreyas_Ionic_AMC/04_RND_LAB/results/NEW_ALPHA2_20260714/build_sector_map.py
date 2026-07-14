import pandas as pd, pickle, os
os.environ["PYTHONIOENCODING"] = "utf-8"
ROOT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
OUT = os.path.join(ROOT, r"Shreyas_Ionic_AMC\04_RND_LAB\results\NEW_ALPHA2_20260714")

sector_map = {}
for f in ["Backtest D_2026_3 (2).csv", "Backtest D_2026_4.csv", "Backtest w_2026_2.csv"]:
    p = os.path.join(ROOT, "..", "..", "Downloads", f) if False else fr"C:\Users\Shreyas.1Gupta\Downloads\{f}"
    if not os.path.exists(p):
        continue
    d = pd.read_csv(p)
    for _, r in d.iterrows():
        if pd.notna(r.get("Sector")) and r["Sector"] != "":
            sector_map[r["Symbol"]] = r["Sector"]
print(f"From Chartlink CSVs: {len(sector_map)} symbols")

pkl_path = os.path.join(ROOT, "stocks_data_cache.pkl")
if os.path.exists(pkl_path):
    with open(pkl_path, "rb") as fh:
        cache = pickle.load(fh)
    sec2 = cache.get("sectors", {})
    added = 0
    for sym, sec in sec2.items():
        clean = sym.replace(".NS", "")
        if clean not in sector_map and isinstance(sec, str):
            sector_map[clean] = sec
            added += 1
    print(f"Added from stocks_data_cache.pkl: {added}")

print(f"Total sector map: {len(sector_map)} symbols")
sm = pd.DataFrame(list(sector_map.items()), columns=["symbol", "sector"])
sm.to_csv(os.path.join(OUT, "sector_map.csv"), index=False)
print(sm["sector"].value_counts().head(20).to_string())
