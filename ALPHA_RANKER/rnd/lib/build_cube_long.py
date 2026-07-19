"""
Build the LONG-HISTORY close-price cube (date x symbol, 2005-04-01 -> 2025-12-05)
by reusing build_panel_long.py's own dedup + master-calendar loaders -- so this
cube is defined IDENTICALLY to the price series panel_long.parquet's forward
returns were built from (same dedup rule, same FFILL_LIMIT=5, same master
calendar = factor_navs "NIFTY 500"). Saved once to rnd/panel/cube_close_long.parquet
+ rnd/panel/cube_bench_long.parquet (NIFTY 500 level) for reuse by WAVE-2 factor
builders, avoiding a ~re-read of the 1199-column xlsx on every run.

WAVE-2 task (2026-07-17): confirm current top factors (65DMA, vol-scaled mom,
12-1 resid mom, earnings-yield, Weinstein stage-2) across REAL bear regimes
(2008/2011/2020) using the 21-year panel_long.parquet.
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent
OUT_CLOSE = RND_DIR / "panel" / "cube_close_long.parquet"
OUT_BENCH = RND_DIR / "panel" / "cube_bench_long.parquet"

sys.path.insert(0, str(_THIS.parent))
import build_panel_long as bpl  # noqa: E402


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    t0 = time.time()
    wide = bpl.load_and_dedup_master()
    tickers = [c for c in wide.columns if c != "Date"]
    master_dates, mkt_close = bpl.load_master_calendar_and_market(wide["Date"].min(), wide["Date"].max())
    log(f"master calendar: {len(master_dates)} days {master_dates.min().date()} -> {master_dates.max().date()}")

    wide_indexed = wide.set_index("Date")
    cols = {}
    for i, sym in enumerate(tickers):
        raw = wide_indexed[sym]
        px = raw.reindex(master_dates).ffill(limit=bpl.FFILL_LIMIT)
        cols[sym] = px.values
        if (i + 1) % 200 == 0:
            log(f"  ...{i+1}/{len(tickers)}")
    close = pd.DataFrame(cols, index=master_dates)
    close.to_parquet(OUT_CLOSE)
    log(f"Saved {OUT_CLOSE} shape={close.shape}")

    bench = pd.Series(mkt_close, index=master_dates, name="NIFTY500")
    bench.to_frame().to_parquet(OUT_BENCH)
    log(f"Saved {OUT_BENCH} shape={bench.shape}")
    log(f"Done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
