"""Download Angel One's PUBLIC instrument master (no auth) and index NIFTY NFO
options by expiry/strike/type → token. This is the discovery layer for the
SmartAPI historical/live option fetchers (data\\angel_fetch_options.py).

The master lists every tradable NFO contract with its symboltoken, which
SmartAPI getCandleData needs. Saved to datasets\\raw\\options\\angel_nfo_nifty.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import truststore
truststore.inject_into_ssl()

import pandas as pd  # noqa: E402
import requests  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402

URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
OUT = RAW_DIR / "options" / "angel_nfo_nifty.csv"


def main() -> None:
    print("fetching Angel scrip master (~50MB, public)...", flush=True)
    r = requests.get(URL, timeout=120)
    r.raise_for_status()
    df = pd.DataFrame(r.json())
    print(f"total instruments: {len(df):,}; columns: {list(df.columns)}")

    # NFO index options on NIFTY/BANKNIFTY/FINNIFTY
    opt = df[(df["exch_seg"] == "NFO")
             & (df["instrumenttype"].astype(str).str.startswith("OPTIDX"))
             & (df["name"].isin(["NIFTY", "BANKNIFTY", "FINNIFTY"]))].copy()
    opt["strike"] = pd.to_numeric(opt["strike"], errors="coerce") / 100.0  # Angel strike x100
    opt["expiry_dt"] = pd.to_datetime(opt["expiry"], format="%d%b%Y", errors="coerce")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    keep = ["token", "symbol", "name", "expiry", "expiry_dt", "strike", "lotsize", "instrumenttype"]
    opt[keep].to_csv(OUT, index=False)

    print(f"\nNIFTY/BANKNIFTY/FINNIFTY options: {len(opt):,} contracts")
    nf = opt[opt["name"] == "NIFTY"]
    print(f"NIFTY options: {len(nf):,}; expiries available: "
          f"{nf['expiry_dt'].dropna().nunique()} "
          f"({nf['expiry_dt'].min()} .. {nf['expiry_dt'].max()})")
    print("\nsample NIFTY option rows (token is what getCandleData needs):")
    print(nf.sort_values(["expiry_dt", "strike"]).head(6)[keep].to_string(index=False))
    print(f"\nsaved -> {OUT}")
    print("\nNOTE: broker masters list only CURRENTLY-TRADABLE contracts (current"
          " + next few expiries). Expired-series intraday history is NOT here —"
          " for that, RECORD live during the paper month (angel_fetch_options.py).")


if __name__ == "__main__":
    main()
