"""D-033 pull: CBOE vol-index suite (daily) + Ken French factors (daily).
CBOE: VIX, VIX9D, VIX3M, VIX6M, VVIX, SKEW from cdn.cboe.com (proven domain).
French: 5-factors 2x3 daily + momentum daily from Dartmouth (probed 200).
Output: 05_DATA_OFFICE/data/. Spot-check verification before accept.
"""
import io, zipfile
from pathlib import Path
import truststore
truststore.inject_into_ssl()
import pandas as pd, requests

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data"
UA = {"User-Agent": "Mozilla/5.0 Chrome/126"}

# ---- CBOE vol suite ----
CBOE = {"VIX": ("2020-03-16", 82.69, 1.0),   # COVID peak close
        "VIX9D": None, "VIX3M": None, "VIX6M": None, "VVIX": None, "SKEW": None}
for idx, chk in CBOE.items():
    url = f"https://cdn.cboe.com/api/global/us_indices/daily_prices/{idx}_History.csv"
    try:
        r = requests.get(url, headers=UA, timeout=90)
        if r.status_code != 200:
            print(f"[{idx}] HTTP {r.status_code} - skipped"); continue
        df = pd.read_csv(io.StringIO(r.text))
        df.columns = [c.strip().upper() for c in df.columns]
        dcol = "DATE"
        df[dcol] = pd.to_datetime(df[dcol])
        ok = True
        if chk:
            dstr, exp, tol = chk
            row = df[df[dcol] == dstr]
            got = row["CLOSE"].iloc[0] if len(row) and "CLOSE" in df.columns else None
            ok = got is not None and abs(got - exp) <= tol
            print(f"[{idx}] {dstr} close={got} expect~{exp} -> {'OK' if ok else 'FAIL'}")
        if ok:
            df.to_parquet(OUT / f"cboe_{idx.lower()}_daily.parquet", index=False)
            print(f"[{idx}] SAVED {df[dcol].min().date()}..{df[dcol].max().date()} n={len(df)}")
    except Exception as e:
        print(f"[{idx}] ERR {type(e).__name__}: {str(e)[:80]}")

# ---- Ken French factors ----
FR = [("F-F_Research_Data_5_Factors_2x3_daily_CSV.zip", "ff5_daily.parquet", 3),
      ("F-F_Momentum_Factor_daily_CSV.zip", "ff_mom_daily.parquet", 13)]
for zname, oname, skiprows in FR:
    url = f"https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/{zname}"
    try:
        r = requests.get(url, headers=UA, timeout=120)
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            raw = z.open(z.namelist()[0]).read().decode("utf-8", errors="ignore")
        lines = raw.splitlines()
        start = next(i for i, ln in enumerate(lines) if ln.strip()[:8].isdigit())
        hdr = lines[start - 1]
        cols = ["Date"] + [c.strip() for c in hdr.split(",") if c.strip()]
        data = []
        for ln in lines[start:]:
            p = ln.split(",")
            if p[0].strip().isdigit() and len(p[0].strip()) == 8:
                data.append(p[:len(cols)])
        df = pd.DataFrame(data, columns=cols)
        df["Date"] = pd.to_datetime(df["Date"].str.strip(), format="%Y%m%d")
        for c in cols[1:]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna()
        df.to_parquet(OUT / oname, index=False)
        print(f"[{oname}] SAVED {df.Date.min().date()}..{df.Date.max().date()} n={len(df)} cols={cols[1:]}")
    except Exception as e:
        print(f"[{oname}] ERR {type(e).__name__}: {str(e)[:80]}")
