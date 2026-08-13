"""AMENDMENT A1 control: is "net-positive on held-out 2026 H1" informative at all?

Every volatility-breakout cell came out net-positive on the 2026 H1 forward set while its
build set was deeply negative. A uniform forward sign across mechanically unrelated
triggers is the signature of a REGIME, not of edge. So: run RANDOM signals through the
same config in the same window. If random also pays, the forward sign carries no
information and no cell may claim credit for it.

Outputs: random_2026h1_trades.csv, random_2026h1.json
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent
RESULTS = OUT.parent.parent
sys.path.insert(0, str(RESULTS / "OPTION_PL_HARNESS_20260729"))
import opt_pl as H                                    # noqa: E402

N = 1500
SEED = 20260730
FWD_START = dt.date(2026, 1, 1)
CAPITAL = 3_00_000.0

CFG = H.OptCfg(min_dte=1, max_dte=7, strike_offset=0,
               max_hold_days=0, squareoff_hhmm="15:25",
               lots=1, allow_opposite_signal_exit=False)     # == C1


def main():
    spot = H.load_spot()
    days = sorted({d for d in spot.index.date if d >= FWD_START})
    print(f"[window] {len(days)} sessions {days[0]} .. {days[-1]}", flush=True)
    rng = np.random.default_rng(SEED)
    sigs = []
    for _ in range(N):
        d = days[int(rng.integers(0, len(days)))]
        # same entry window the real cells use: 09:20-14:30
        mins = int(rng.integers(0, 311))
        sigs.append({"t": pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=20 + mins),
                     "direction": int(rng.choice([1, -1]))})
    s = pd.DataFrame(sigs).sort_values("t").reset_index(drop=True)

    tr = H.run_signals(s, CFG, progress=250)
    tr.to_csv(OUT / "random_2026h1_trades.csv", index=False)
    m = H.summarize(tr, "RANDOM control, 2026 H1, config C1", capital=CAPITAL)
    H.fill_report(tr, quiet=False)

    f = tr[tr.status == "filled"]
    out = {k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
           for k, v in m.items() if k not in ("reasons",)}
    out["exit_reasons"] = m.get("reasons")
    out["n_random"] = N
    out["seed"] = SEED
    out["interpretation_rule"] = ("if net_total > 0 here, then 'forward net-positive' is "
                                 "uninformative in 2026 H1 and no cell may claim credit "
                                 "for it")
    out["frictionless_gross"] = float(((f.exit_px_raw - f.entry_px_raw) * f.qty).sum())
    (OUT / "random_2026h1.json").write_text(json.dumps(out, indent=2, default=str),
                                            encoding="utf-8")
    print(f"\nfrictionless gross (no slippage, no costs): Rs.{out['frictionless_gross']:,.0f}")
    print(f"VERDICT ON THE FORWARD WINDOW: random is "
          f"{'NET-POSITIVE -> forward sign is UNINFORMATIVE' if m['net_total'] > 0 else 'net-negative -> forward sign carries information'}")


if __name__ == "__main__":
    sys.exit(main())
