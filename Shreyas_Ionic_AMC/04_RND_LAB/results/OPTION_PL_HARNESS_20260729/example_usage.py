r"""COPY-PASTE TEMPLATE for calling the shared option-P&L harness.

    import sys; sys.path.insert(0, r"<this folder>")
    import opt_pl as H

Two arms shown: (1) an intraday trigger, (2) a multi-day trend-catcher.
Run this file for a live 200-signal demo on the strongest measured trigger family.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import opt_pl as H     # noqa: E402


# ---------------------------------------------------------------------------
# 1) INTRADAY ARM  -- flat by 15:25, 1-7 DTE weekly, ATM, 50% target / 30% stop
# ---------------------------------------------------------------------------
CFG_INTRADAY = H.OptCfg(
    min_dte=1, max_dte=7,          # avoid 0DTE unless you also set expiry_handling
    strike_offset=0,               # 0 = ATM ; +1 = 1 step OTM ; -1 = 1 step ITM
    target_pct=0.50, stop_pct=0.30,
    max_hold_days=0, squareoff_hhmm="15:25",
    lots=1,                        # fixed 1 lot -> per-trade % returns are comparable
    allow_opposite_signal_exit=True,
)

# ---------------------------------------------------------------------------
# 2) TREND-CATCHER ARM -- multi-day hold, 3-9 DTE, 2 steps OTM, ride the tail
#    NOTE strike_offset SIGN: +2 here = 2 steps OTM. The legacy engine_swing.py
#    called that "-2 / ITM2" -- its label was wrong. Do not copy the old sign.
# ---------------------------------------------------------------------------
CFG_TREND = H.OptCfg(
    min_dte=3, max_dte=9, strike_offset=+2,
    target_pct=1.00, stop_pct=0.35, trail_pct=0.35,
    max_hold_days=4, squareoff_hhmm="15:15",
    expiry_handling="settle_intrinsic",   # carried-to-expiry => intrinsic, never a settle print
    lots=1, allow_opposite_signal_exit=False,
)


def demo_signals(n: int = 200, seed: int = 1) -> list[tuple]:
    """Stand-in for a real trigger: `n` timestamps from real sessions.
    A REAL caller passes its own (timestamp, direction) list -- e.g. the
    sweep_priorday_reclaim signal timestamps -- with `t` = the SIGNAL BAR's stamp.
    The harness fills at the NEXT bar; do not pre-shift the timestamp yourself."""
    sp = H.load_spot()
    days = sorted({d for d in sp.index.date if d.year in (2022, 2023, 2024)})
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        d = days[int(rng.integers(0, len(days)))]
        m = int(rng.integers(0, 300))
        out.append((pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=25 + m),
                    int(rng.choice([1, -1])), "demo"))
    return out


if __name__ == "__main__":
    sigs = demo_signals(200)
    for name, cfg in [("INTRADAY arm", CFG_INTRADAY), ("TREND arm", CFG_TREND)]:
        tr = H.run_signals(sigs, cfg)
        H.summarize(tr, name, capital=3_00_000.0)
        H.fill_report(tr, quiet=True)
        # what a caller normally does next:
        filled = tr[tr.status == "filled"]
        print(f"   -> {len(filled)} filled of {len(tr)} signals; "
              f"mean net ret/trade {filled.ret_pct_net.mean():+.2%}")
