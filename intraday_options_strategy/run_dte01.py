"""Confirm the DTE<=1 short-vol book: 0DTE (expiry day) + DTE=1 (day before),
both delta-hedged. Reports IS/OOS for each and the combined near-2-day/week
NIFTY book. DTE>=2 excluded (unhedged vega tail kills it)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest.engine_v2 import (ExitPolicy, OrderSpec, simulate_delta_hedged)  # noqa: E402
from config import PROCESSED_DIR  # noqa: E402
from features.horizon import day_features  # noqa: E402
from options.option_selector import ExpiryCalendar, WEEKLY_START  # noqa: E402
from strategies.sleeves import STRADDLE  # noqa: E402

M, SLIP = 0.80, 0.02
nifty = pd.read_parquet(PROCESSED_DIR / "nifty_1min.parquet")
vix = pd.read_parquet(PROCESSED_DIR / "vix_on_bars.parquet")["vix"]
filters = pd.read_parquet(PROCESSED_DIR / "filters.parquet")
days = pd.DatetimeIndex(pd.read_csv(PROCESSED_DIR / "trading_calendar.csv",
                                    parse_dates=["day"])["day"])
oos = days[int(len(days) * 0.70)]
dayf = day_features(nifty, vix)
cal = ExpiryCalendar(days)


def bar_at(day, hhmm):
    t = day + pd.Timedelta(f"{hhmm}:00")
    return t if t in nifty.index else None


def make_orders(target_dte):
    out = []
    hard = "14:30" if target_dte == 0 else "15:00"
    sl = 0.25 if target_dte == 0 else 0.40
    for d in days:
        if d < WEEKLY_START:
            continue
        exp0 = cal.next_expiry(d, min_dte=0)
        if (exp0.normalize() - d).days != target_dte:
            continue
        dt = bar_at(d, "09:19")
        if dt is None or not bool(filters.loc[dt, "event_ok"]) or not bool(filters.loc[dt, "vix_ok"]):
            continue
        f = dayf.loc[d] if d in dayf.index else None
        if f is not None and not np.isnan(f["gap_pct"]) and abs(f["gap_pct"]) > 0.005:
            continue
        out.append(OrderSpec(signal_dt=dt, sleeve=f"DTE{target_dte}", side=-1,
                             legs=STRADDLE, exit=ExitPolicy(sl=sl, pt=None, hard_exit=hard),
                             min_dte=target_dte, direction_label="DH"))
    return out


def stats(tr, label):
    pnl = tr["pnl_per_lot"] - tr["fixed_cost"]
    d = pnl.groupby(tr["entry_dt"].dt.normalize()).sum()
    cal2 = days[(days >= d.index.min()) & (days <= d.index.max())]
    dc = d.reindex(cal2).fillna(0.0)
    w = pnl > 0; gl = -pnl[~w].sum()

    def sh(x):
        return x.mean() / x.std(ddof=0) * np.sqrt(252) if x.std(ddof=0) > 0 else 0
    print(f"{label:14} n={len(tr):4} WR={w.mean():.2f} PF={pnl[w].sum()/gl if gl>0 else 9:.2f} "
          f"avg/lot={pnl.mean():5.0f} Sh={sh(dc):.2f} IS={sh(dc[dc.index<oos]):.2f} "
          f"OOS={sh(dc[dc.index>=oos]):.2f}")
    return d


print(f"NIFTY short-vol book, delta-hedged, real m={M}, slip={SLIP:.0%}:")
tr0 = simulate_delta_hedged(nifty, vix, make_orders(0), iv_mult=M, slippage_pct=SLIP, hedge_band=0.25)
tr1 = simulate_delta_hedged(nifty, vix, make_orders(1), iv_mult=M, slippage_pct=SLIP, hedge_band=0.25)
d0 = stats(tr0, "DTE0 (expiry)")
d1 = stats(tr1, "DTE1 (pre-exp)")

# combined book (both sleeves, 1 lot each)
comb = (d0.reindex(days).fillna(0) + d1.reindex(days).fillna(0))
cc = comb[comb != 0]
co = comb[comb.index >= oos]

def sh(x):
    return x.mean() / x.std(ddof=0) * np.sqrt(252) if x.std(ddof=0) > 0 else 0
peak = comb.cumsum().cummax(); ddmax = (peak - comb.cumsum()).max()
print(f"\nCOMBINED DTE0+DTE1 book: deploy {len(cc)} days/{len(days)} "
      f"(~{len(cc)/(len(days)/252):.0f}/yr)")
print(f"  fund Sharpe full={sh(comb):.2f}  OOS={sh(co):.2f}  maxDD/lot={ddmax:,.0f}")
print(f"  corr(DTE0, DTE1) = {d0.reindex(days).fillna(0).corr(d1.reindex(days).fillna(0)):.2f}")
