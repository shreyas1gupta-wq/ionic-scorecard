"""Probe openchart for real intraday NFO option candles.

Goal: measure the REAL 09:20 ATM straddle premium on recent NIFTY expiry days
to confirm/replace the extrapolated 0DTE IV multiplier (m~0.96) — the project's
#1 open risk. No auth; routed through NSE servers (truststore for proxy CA).
"""
from __future__ import annotations

import sys
from pathlib import Path

import truststore
truststore.inject_into_ssl()

import pandas as pd  # noqa: E402

try:
    from openchart import NSEData
except Exception as exc:  # noqa: BLE001
    print(f"import failed: {exc}")
    sys.exit(1)


def main() -> None:
    nse = NSEData()
    try:
        nse.download()  # builds the symbol master (NSE + NFO)
    except Exception as exc:  # noqa: BLE001
        print(f"download() master failed: {type(exc).__name__}: {str(exc)[:200]}")
    # 1) can we even search NFO?
    try:
        fo = nse.search("NIFTY", "FO")
        print(f"search NIFTY FO: {type(fo)}, rows={len(fo) if fo is not None else 0}")
        if fo is not None and len(fo):
            print(fo.head(10).to_string())
    except Exception as exc:  # noqa: BLE001
        print(f"search FO failed: {type(exc).__name__}: {str(exc)[:200]}")
        return
    # 2) try an index intraday pull first (sanity), then an option symbol
    end = pd.Timestamp.now()
    start = end - pd.Timedelta(days=8)
    try:
        idx = nse.historical("NIFTY 50", "NSE", start.to_pydatetime(),
                             end.to_pydatetime(), "1m")
        print(f"\nNIFTY 50 1m: rows={0 if idx is None else len(idx)}")
        if idx is not None and len(idx):
            print(idx.tail(3).to_string())
    except Exception as exc:  # noqa: BLE001
        print(f"index historical failed: {type(exc).__name__}: {str(exc)[:200]}")


if __name__ == "__main__":
    main()
