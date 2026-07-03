"""One-time precompute for WFO: filters + signal events for all 27 signal
variants (EMA fast × EMA slow × ORB minutes) over the FULL dataset.

SL/target/max-trades don't affect signal generation, so the WFO grid only
needs these 27 cached event tables. Outputs:
  processed/filters.parquet      (regime filters, variant-independent)
  processed/vix_on_bars.parquet  (same-minute VIX ffilled to nifty bars)
  processed/events/ev_f{F}s{S}o{O}.parquet
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import (  # noqa: E402
    EMA_FAST_GRID, EMA_SLOW_GRID, ORB_MINUTES_GRID, PROCESSED_DIR, StrategyParams,
)
from features.regime_filter import build_filters  # noqa: E402
from features.signals import signal_events  # noqa: E402

EVENTS_DIR = PROCESSED_DIR / "events"


def main() -> None:
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    nifty = pd.read_parquet(PROCESSED_DIR / "nifty_1min.parquet")
    vix = pd.read_parquet(PROCESSED_DIR / "vix_1min.parquet")

    t0 = time.time()
    filt = build_filters(nifty, vix)
    filt.to_parquet(PROCESSED_DIR / "filters.parquet")
    vob = vix["vix"].reindex(nifty.index).ffill().to_frame("vix")
    vob.to_parquet(PROCESSED_DIR / "vix_on_bars.parquet")
    print(f"filters + vix_on_bars done in {time.time() - t0:.0f}s", flush=True)

    n = 0
    for f in EMA_FAST_GRID:
        for s in EMA_SLOW_GRID:
            for orb in ORB_MINUTES_GRID:
                n += 1
                out = EVENTS_DIR / f"ev_f{f}s{s}o{orb}.parquet"
                if out.exists():
                    print(f"[{n}/27] {out.name} cached, skip", flush=True)
                    continue
                t1 = time.time()
                p = StrategyParams(ema_fast=f, ema_slow=s, orb_minutes=orb)
                ev = signal_events(nifty, filt, p)
                ev.to_parquet(out)
                print(f"[{n}/27] {out.name}: {len(ev)} events "
                      f"({time.time() - t1:.0f}s)", flush=True)
    print(f"ALL DONE in {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
