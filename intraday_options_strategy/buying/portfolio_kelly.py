"""Rs.1 crore, 0.3x Kelly portfolio of ALL profitable strategies found so far.

Sleeves (all forward-positive):
  1 equity_mom_lowvol : Mom12 + LowVol blend (daily, long-equity) -- the diversifier
  2 ivrv_short        : IV/RV>=1.4 short straddle (single-stock)
  3 ff_calendar       : Forward-Factor single-CE calendar, FF>=0.20
  4 combo_shortvol    : covered-call + short-put (monthly hold)
  5 earnings_shortvol : short vol through earnings (IV crush)
Multi-day option trades are SPREAD across their holding period -> continuous daily returns.
Risk-parity weights, then 0.3x Kelly leverage. Build 2021-2024 / forward 2025-2026.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
B = ROOT / "intraday_options_strategy/buying"; S = ROOT / "swing_momentum"
CAP = 1_00_00_000.0            # Rs 1 crore
KELLY = 0.3
SPLIT = dt.date(2024, 12, 31)
START = dt.date(2021, 7, 1); END = dt.date(2026, 6, 2)
SLIP = 0.015


def spread_daily(df, entry_col, exit_col, ret_col):
    """Distribute each trade's return across business days in [entry, exit]; mean across
    overlapping trades (shared sleeve capital)."""
    recs = []
    for _, r in df.iterrows():
        e, x = pd.Timestamp(r[entry_col]), pd.Timestamp(r[exit_col])
        if pd.isna(e) or pd.isna(x) or x < e:
            continue
        days = pd.bdate_range(e, x)
        if len(days) == 0:
            continue
        d = float(r[ret_col]) / len(days)      # linear spread (avoids complex roots on <-100% trades)
        recs.extend((day, d) for day in days)
    if not recs:
        return pd.Series(dtype=float)
    return pd.DataFrame(recs, columns=["day", "d"]).groupby("day")["d"].mean()


# sleeve 1: equity (daily returns already)
eq = pd.read_parquet(S / "multi_backtest_daily.parquet"); eq.index = pd.to_datetime(eq.index)
sub = eq[["mom_12_1", "lowvol_126"]]
bw = sub[sub.index.date <= SPLIT].std(); w = (1 / bw) / (1 / bw).sum()
sleeve_equity = (sub * w).sum(axis=1)

# sleeve 2: IV/RV short straddle
rv = pd.read_parquet(B / "rv_iv_vol.parquet"); rv = rv[rv["iv_rv"] >= 1.4]
sleeve_ivrv = spread_daily(rv, "entry", "exit", "short_ret")

# sleeve 3: FF single-CE calendar, FF>=0.20 (ret = pnl / back-leg premium)
ff = pd.read_parquet(B / "forward_factor_v2.parquet")
ff["ret"] = (ff["CE_fe"] * (1 - SLIP) - ff["CE_be"] * (1 + SLIP)
             - ff["CE_fx"] * (1 + SLIP) + ff["CE_bx"] * (1 - SLIP)) / ff["CE_be"]
ff = ff[ff["ff"] >= 0.20]
sleeve_ff = spread_daily(ff, "entry", "m1_exp", "ret")

# sleeve 4: combo short-vol (covered call + short put), monthly hold
cm = pd.read_parquet(B / "combo_menu.parquet")
cm["ret"] = (cm["covered_call"] + cm["short_put_csp"]) / 2
sleeve_combo = spread_daily(cm, "entry", "exp", "ret")

# sleeve 5: earnings short vol (Case4), ~2-day hold booked around earnings
ev = pd.read_parquet(B / "stock_earnings_vol.parquet")
ev["e0"] = pd.to_datetime(ev["earn"]) - pd.Timedelta(days=2)
ev["e1"] = pd.to_datetime(ev["earn"]) + pd.Timedelta(days=1)
sleeve_earn = spread_daily(ev.rename(columns={"c4_short_thru": "ret"}), "e0", "e1", "ret")

idx = pd.bdate_range(START, END)
M = pd.DataFrame({
    "equity_mom_lowvol": sleeve_equity.reindex(idx).fillna(0.0),
    "ivrv_short": sleeve_ivrv.reindex(idx).fillna(0.0),
    "ff_calendar": sleeve_ff.reindex(idx).fillna(0.0),
    "combo_shortvol": sleeve_combo.reindex(idx).fillna(0.0),
    "earnings_shortvol": sleeve_earn.reindex(idx).fillna(0.0),
})

print("=== sleeve daily-return stats (annualized) ===")
for c in M.columns:
    s = M[c]; ann_ret = s.mean() * 252; ann_vol = s.std() * np.sqrt(252)
    print(f"  {c:20s}: ann {ann_ret:+7.1%} | vol {ann_vol:6.1%} | Sharpe {ann_ret/ann_vol if ann_vol else 0:5.2f} | active {int((s!=0).sum())}")

print("\n=== correlation (build) ===")
Mb = M[M.index.date <= SPLIT]
print(Mb.corr().round(2).to_string())

# risk-parity weights (inverse build-vol)
bvol = Mb.std().replace(0, np.nan); rw = (1 / bvol) / (1 / bvol).sum()
combo = (M * rw).sum(axis=1)                          # risk-parity daily return
print(f"\nrisk-parity weights: {rw.round(2).to_dict()}")

# 0.3x Kelly leverage (daily-return Kelly, capped for realism)
cb = combo[combo.index.date <= SPLIT]
fstar = cb.mean() / cb.var() if cb.var() > 0 else 0
lev = min(KELLY * fstar, 4.0)                          # cap 4x
print(f"full Kelly f* (daily) = {fstar:.1f} -> 0.3x = {KELLY*fstar:.2f}, applied leverage = {lev:.2f}x (cap 4)")

port = combo * lev


def stats(r, cap):
    r = r.dropna()
    eqc = (1 + r).cumprod() * cap
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    cagr = (eqc.iloc[-1] / cap) ** (1 / yrs) - 1
    sharpe = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0
    dd = (eqc / eqc.cummax() - 1).min()
    return cagr, sharpe, dd, eqc.iloc[-1]


for lab, r in [("BUILD", port[port.index.date <= SPLIT]),
               ("FORWARD", port[port.index.date > SPLIT]),
               ("ALL", port)]:
    c, sh, dd, fin = stats(r, CAP)
    print(f"\n{lab}: CAGR {c:+.1%} | Sharpe {sh:.2f} | MaxDD {dd:.0%} | final Rs.{fin:,.0f}")

# also unlevered (0.3x-Kelly OFF, pure risk-parity) for reference
c0, sh0, dd0, _ = stats(combo, CAP)
print(f"\n[reference] unlevered risk-parity: CAGR {c0:+.1%} | Sharpe {sh0:.2f} | MaxDD {dd0:.0%}")
M.to_parquet(B / "portfolio_sleeves_daily.parquet")
print("\nsaved sleeve daily returns -> portfolio_sleeves_daily.parquet")
