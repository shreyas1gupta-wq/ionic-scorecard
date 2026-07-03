"""Probe 2: learn the NSE charting FO option-symbol format and confirm we can
pull a real intraday option candle."""
from __future__ import annotations

import sys
from pathlib import Path

import truststore
truststore.inject_into_ssl()

import pandas as pd  # noqa: E402
from openchart import NSEData  # noqa: E402

pd.set_option("display.max_rows", 60)
pd.set_option("display.width", 200)

nse = NSEData()
for q in ["NIFTY", "BANKNIFTY"]:
    fo = nse.search(q, "FO")
    print(f"\n=== search '{q}' FO: {len(fo)} rows; types={fo['type'].unique().tolist() if len(fo) else []}")
    if len(fo):
        # show any options/futures rows specifically
        opt = fo[fo["type"].astype(str).str.contains("Opt|Fut", case=False, na=False)]
        print((opt if len(opt) else fo).head(30).to_string())
