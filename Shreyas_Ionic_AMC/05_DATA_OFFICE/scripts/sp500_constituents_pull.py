"""S&P500 historical constituents (PIT) from github fja05680/sp500 (D-033 class). D-009 spot-checks printed."""
import truststore; truststore.inject_into_ssl()
import io, json, requests, pandas as pd
from pathlib import Path

OUT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\05_DATA_OFFICE\data")
s = requests.Session()
s.headers["User-Agent"] = "Mozilla/5.0"
listing = s.get("https://api.github.com/repos/fja05680/sp500/contents", timeout=60).json()
cands = [f for f in listing if f["name"].lower().startswith("s&p 500 historical components")]
assert cands, [f["name"] for f in listing][:20]
best, df = None, None
for f in cands:
    raw = s.get(f["url"], headers={"Accept": "application/vnd.github.raw+json"}, timeout=120)
    raw.raise_for_status()
    d_ = pd.read_csv(io.StringIO(raw.text))
    d_.columns = [c.strip().lower() for c in d_.columns]
    d_["date"] = pd.to_datetime(d_["date"])
    print(f"  candidate {f['name']}: {len(d_)} rows to {d_.date.max().date()}")
    if df is None or d_.date.max() > df.date.max():
        best, df = f["name"], d_
print("chosen:", best)
print(f"rows {len(df)} | {df.date.min().date()} .. {df.date.max().date()}")
def members(day):
    row = df[df.date <= day].iloc[-1]
    return set(t.strip() for t in row["tickers"].split(","))
m0, m1 = members(pd.Timestamp("2020-12-18")), members(pd.Timestamp("2020-12-22"))
print("TSLA pre/post Dec-2020 add:", "TSLA" in m0, "/", "TSLA" in m1, "(expect False/True)")
m01 = members(pd.Timestamp("2001-06-01"))
print("ENE (Enron) mid-2001:", "ENE" in m01, "(expect True)  | AAPL:", "AAPL" in m01, "(expect True)")
print("count 2020-12-22:", len(m1), "(expect ~505 incl dual-class)")
df.to_parquet(OUT / "sp500_constituents_pit.parquet", index=False)
print("saved -> sp500_constituents_pit.parquet")
