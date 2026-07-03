"""VRP edge under REALISTIC assumptions: trading-time clock, calibrated
trading-time IV multiplier (default_iv_mult, ~0.90), and conservative 0DTE
execution costs (per-leg slippage 0.5-2%, SL exits gap 2-3x).

This is the honest test of whether the short-vol edge survives reality. We
report full-period and OOS daily Sharpe (1-lot), win rate, PF, worst day and
SL rate for S3 (0DTE) and S2 (weekly intraday) straddles across stop widths
and slippage levels. Pass/fail bar: OOS Sharpe > 1.5 after costs.
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest.engine_v2 import ExitPolicy, default_iv_mult, simulate_orders  # noqa: E402
from config import PROCESSED_DIR, RESULTS_DIR  # noqa: E402
from features.horizon import day_features  # noqa: E402
from strategies.sleeves import all_expiry_days, s2_range_premium, s3_zero_dte  # noqa: E402

nifty = pd.read_parquet(PROCESSED_DIR / "nifty_1min.parquet")
vix = pd.read_parquet(PROCESSED_DIR / "vix_on_bars.parquet")["vix"]
filters = pd.read_parquet(PROCESSED_DIR / "filters.parquet")
days = pd.DatetimeIndex(pd.read_csv(PROCESSED_DIR / "trading_calendar.csv",
                                    parse_dates=["day"])["day"])
oos_start = days[int(len(days) * 0.70)]
dayf = day_features(nifty, vix)
expiry_days = all_expiry_days(days)

base = {"S2": s2_range_premium(nifty, dayf, filters, expiry_days),
        "S3": s3_zero_dte(nifty, dayf, filters, expiry_days)}
print(f"orders: S2={len(base['S2'])} S3={len(base['S3'])}; "
      f"m(0DTE)={default_iv_mult(0):.2f} m(1)={default_iv_mult(1):.2f} "
      f"m(3)={default_iv_mult(3):.2f}")


def perf(tr: pd.DataFrame, seg_mask=None) -> dict:
    if seg_mask is not None:
        tr = tr[seg_mask(tr)]
    if len(tr) < 20:
        return {"n": len(tr)}
    pnl = tr["pnl_per_lot"] - tr["fixed_cost"]
    td = tr["entry_dt"].dt.normalize()
    daily_trade = pnl.groupby(td).sum()             # trade-days only
    wins = pnl > 0
    gl = -pnl[~wins].sum()
    # per-deployment Sharpe (annualised by ACTUAL trade-days/yr) — the edge per
    # opportunity; relevant if diversified across expiries/instruments to deploy ~daily
    span_yrs = max((td.max() - td.min()).days / 365.25, 0.5)
    tpy = len(daily_trade) / span_yrs
    sh_deploy = (daily_trade.mean() / daily_trade.std(ddof=0) * np.sqrt(tpy)
                 if daily_trade.std(ddof=0) > 1e-9 else 0.0)
    # fund Sharpe: idle calendar days = 0 P&L (single-instrument standalone)
    cal = days[(days >= td.min()) & (days <= td.max())]
    daily_cal = daily_trade.reindex(cal).fillna(0.0)
    sh_fund = (daily_cal.mean() / daily_cal.std(ddof=0) * np.sqrt(252)
               if daily_cal.std(ddof=0) > 1e-9 else 0.0)
    return {"n": len(tr), "wr": round(float(wins.mean()), 3),
            "pf": round(float(pnl[wins].sum() / gl), 2) if gl > 0 else np.inf,
            "avg_lot": round(float(pnl.mean())),
            "worst_lot": round(float(pnl.min())),
            "tpy": round(tpy),
            "sharpe": round(float(sh_deploy), 2),       # per-deployment
            "sharpe_fund": round(float(sh_fund), 2)}    # standalone single-instrument


rows = []
# realistic 0DTE execution: per-leg slip and SL gap multiplier
for sleeve, ods in base.items():
    hard = "14:30" if sleeve == "S3" else "15:00"
    for sl in [0.25, 0.40]:
        for slip in [0.005, 0.010, 0.020]:
            new = [replace(o, exit=ExitPolicy(sl=sl, pt=None, hard_exit=hard)) for o in ods]
            tr = simulate_orders(nifty, vix, new, iv_mult=default_iv_mult,
                                 slippage_pct=slip, stop_slip_mult=3.0)
            tr["day"] = tr["entry_dt"].dt.normalize()
            full = perf(tr)
            oos = perf(tr, lambda t: t["day"] >= oos_start)
            ins = perf(tr, lambda t: t["day"] < oos_start)
            rows.append({"sleeve": sleeve, "sl": sl, "slip": slip,
                         "WR": full.get("wr"), "PF": full.get("pf"),
                         "tpy": full.get("tpy"),
                         "avg_lot": full.get("avg_lot"), "worst_lot": full.get("worst_lot"),
                         "Sh_deploy": full.get("sharpe"), "Sh_fund": full.get("sharpe_fund"),
                         "Sh_deploy_IS": ins.get("sharpe"), "Sh_deploy_OOS": oos.get("sharpe"),
                         "Sh_fund_OOS": oos.get("sharpe_fund"), "PF_OOS": oos.get("pf")})
            print(f"{sleeve} sl={sl:.2f} slip={slip:.1%}: WR {full.get('wr')} "
                  f"PF {full.get('pf')} ~{full.get('tpy')}trd/yr avg/lot {full.get('avg_lot')} "
                  f"worst {full.get('worst_lot')} | Sh/deploy {full.get('sharpe')} "
                  f"(IS {ins.get('sharpe')} OOS {oos.get('sharpe')}) "
                  f"Sh/fund {full.get('sharpe_fund')} OOS {oos.get('sharpe_fund')}", flush=True)

pd.DataFrame(rows).to_csv(RESULTS_DIR / "vrp_realistic.csv", index=False)
print(f"\nsaved -> {RESULTS_DIR / 'vrp_realistic.csv'}")
