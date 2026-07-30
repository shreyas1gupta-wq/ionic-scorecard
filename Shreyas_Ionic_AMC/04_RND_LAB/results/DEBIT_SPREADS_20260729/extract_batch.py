"""Child process for preload_legs (run_debit_spreads.py). Reads a small JSON spec of
{expiry_iso: [[strike, option_type], ...]}, extracts each expiry's needed
(strike,option_type) slices from the HF 1-min options parquet (column-pruned: skips
trading_day/symbol/expiry/open_interest, the memory-heavy unused columns), and writes
one pickle per expiry to the scratch dir. Runs as an isolated OS process so a native
crash (observed: pyarrow segfault under real system memory contention -- this machine
runs multiple concurrent firm agents, psutil showed ~3.3-3.7GB free of 16.8GB) only
costs this batch, never the long-lived parent/orchestrator.
"""
from __future__ import annotations

import datetime as dt
import json
import pickle
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

REPO = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
BUYING = REPO / "intraday_options_strategy" / "buying"
sys.path.insert(0, str(BUYING))
import chain  # noqa: E402

LEAN_COLS = ["timestamp", "open", "close", "volume", "strike", "option_type"]


def main():
    spec_path, outdir = sys.argv[1], sys.argv[2]
    spec = json.loads(Path(spec_path).read_text())
    mapping, _ = chain.build_expiry_index()
    outdir = Path(outdir)
    for exp_str, pairs in spec.items():
        exp = dt.datetime.strptime(exp_str, "%Y-%m-%d").date()
        pairs_set = {(int(s), o) for s, o in pairs}
        strikes = {p[0] for p in pairs_set}
        path = mapping.get(exp)
        if path is None:
            continue
        tbl = pq.read_table(path, columns=LEAN_COLS)
        df = tbl.to_pandas()
        del tbl
        df["t"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
        sub = df.loc[df["strike"].isin(strikes), ["t", "strike", "option_type", "open", "close", "volume"]]
        del df
        result = {}
        for (strike, otype), g in sub.groupby(["strike", "option_type"], observed=True):
            if (strike, otype) not in pairs_set:
                continue
            s = g.set_index("t")[["open", "close", "volume"]].sort_index()
            s = s[~s.index.duplicated(keep="first")]
            result[(strike, otype)] = s
        del sub
        with open(outdir / f"{exp_str}.pkl", "wb") as f:
            pickle.dump(result, f)
        del result
    print("BATCH_DONE", flush=True)


if __name__ == "__main__":
    main()
