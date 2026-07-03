"""Refresh NSE forthcoming-results calendar and merge into the project earnings CSV."""
import truststore; truststore.inject_into_ssl()
import requests, datetime as dt
from pathlib import Path
import pandas as pd

PROJ = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
CSV = PROJ / "datasets/nse_earnings_dates/earnings_dates.csv"
SOPT = PROJ / "intraday_options_strategy/datasets/raw/hf_index_options_1m/stocks_options"
stocks = {p.name for p in SOPT.iterdir() if p.is_dir()}

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
     "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9",
     "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-board-meetings"}
s = requests.Session(); s.headers.update(H)
new = []
try:
    s.get("https://www.nseindia.com/", timeout=25)
    s.get("https://www.nseindia.com/companies-listing/corporate-filings-board-meetings", timeout=25)
    for url in ["https://www.nseindia.com/api/corporate-board-meetings?index=equities",
                "https://www.nseindia.com/api/event-calendar"]:
        try:
            r = s.get(url, timeout=30)
            data = r.json()
            print(f"OK {url.split('/api/')[1]}: {len(data)} rows")
            for row in data:
                sym = row.get("symbol") or row.get("bm_symbol")
                purp = (row.get("purpose") or row.get("bm_purpose") or "")
                date = (row.get("date") or row.get("bm_date") or "")
                if sym in stocks and "result" in purp.lower():
                    new.append({"symbol": sym, "date": date, "purpose": purp})
        except Exception as e:
            print(f"  endpoint fail {url[-30:]}: {type(e).__name__} {str(e)[:60]}")
except Exception as e:
    print(f"NSE unreachable: {type(e).__name__} {str(e)[:80]}")

print(f"\nfetched {len(new)} forthcoming F&O-stock results rows")
if new:
    nd = pd.DataFrame(new).drop_duplicates()
    # normalize date to %d-%b-%Y to match existing CSV
    def norm(x):
        for fmt in ("%d-%b-%Y", "%d-%b-%Y %H:%M", "%Y-%m-%d", "%d %b %Y"):
            try: return dt.datetime.strptime(str(x).strip()[:20], fmt).strftime("%d-%b-%Y")
            except: pass
        return None
    nd["date"] = nd["date"].map(norm); nd = nd.dropna(subset=["date"])
    nd.to_csv(PROJ / "datasets/nse_earnings_dates/forthcoming_results.csv", index=False)
    print("saved -> forthcoming_results.csv")
    up = nd.copy(); up["d"] = pd.to_datetime(up["date"], format="%d-%b-%Y")
    up = up[up["d"] >= dt.datetime(2026, 7, 1)].sort_values("d")
    print("\nUPCOMING F&O-stock results (Jul-2026+):")
    for _, r in up.iterrows():
        print(f"  {r['d'].date()}  {r['symbol']:14s} {r['purpose'][:40]}")
