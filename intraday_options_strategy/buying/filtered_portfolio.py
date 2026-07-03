"""FILTERED portfolio: keep ONLY sleeves with annualized return > 20% (CAGR) / XIRR > 30%.
Per user: keep earnings + FF calendar + anything clearing the bar; drop the rest.

From the 5-sleeve set, qualifiers (monthly-return annualized):
  ivrv_short   +66.9%   KEEP
  ff_calendar  +246.8%  KEEP
  earnings     +160.6%  KEEP
  equity       +15.0%   DROP (below 20%)
  combo        +6.6%    DROP (below 20%)

Rs.1cr, equal capital allocation across the KEPT sleeves, 0.3x Kelly leverage capped at 2x,
monthly P&L booked in exit month. Reports CAGR (==XIRR for a lump-sum reinvested book),
Sharpe, MaxDD, and per-sleeve recent-transactions summary.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
B = ROOT / "intraday_options_strategy/buying"
CAP = 1_00_00_000.0
KELLY = 0.3
LEV_CAP = 2.0
SPLIT = dt.date(2024, 12, 31)
START = pd.Timestamp(2021, 7, 1); END = pd.Timestamp(2026, 6, 30)
SLIP = 0.015


def monthly(df, exit_col, ret_col, clip=None):
    d = df[[exit_col, ret_col]].copy()
    d[exit_col] = pd.to_datetime(d[exit_col]); d = d.dropna()
    if clip:
        d[ret_col] = d[ret_col].clip(*clip)
    d["m"] = d[exit_col].dt.to_period("M").dt.to_timestamp("M")
    g = d.groupby("m")[ret_col]
    return g.mean(), g.size()


def wmonthly(df, exit_col, ret_col, w_col):
    """Capital-weighted monthly mean (weights = per-trade size). No clipping - tail accepted."""
    d = df[[exit_col, ret_col, w_col]].copy()
    d[exit_col] = pd.to_datetime(d[exit_col]); d = d.dropna()
    d["m"] = d[exit_col].dt.to_period("M").dt.to_timestamp("M")
    return d.groupby("m").apply(lambda g: np.average(g[ret_col], weights=g[w_col]), include_groups=False)


# --- KEPT sleeves ---
rv = pd.read_parquet(B / "rv_iv_vol.parquet"); rv = rv[rv["iv_rv"] >= 1.4]
s_ivrv, _ = monthly(rv, "exit", "short_ret", clip=(-3, 1))

ff = pd.read_parquet(B / "forward_factor_v2.parquet")
ff["ret"] = (ff["CE_fe"] * (1 - SLIP) - ff["CE_be"] * (1 + SLIP)
             - ff["CE_fx"] * (1 + SLIP) + ff["CE_bx"] * (1 - SLIP)) / ff["CE_be"]
ff = ff[ff["ff"] >= 0.25].copy()               # user floor 0.25; NO stop/filter/hedge - tail accepted
ff["w"] = ff["ff"].apply(lambda f: 0.75 if f < 0.5 else (1.0 if f < 0.75 else 1.25))  # FF-tier sizing
s_ff = wmonthly(ff, "m1_exp", "ret", "w")

ev = pd.read_parquet(B / "stock_earnings_vol.parquet")
s_earn, _ = monthly(ev, "earn", "c4_short_thru")

sg = pd.read_parquet(B / "shortlist_shortvol.parquet")   # NEW qualifier: managed short strangle
s_str, _ = monthly(sg, "exp", "strangle_managed")

idx = pd.date_range(START, END, freq="ME")
M = pd.DataFrame({
    "ivrv_short": s_ivrv.reindex(idx).fillna(0.0),
    "ff_calendar": s_ff.reindex(idx).fillna(0.0),
    "earnings_shortvol": s_earn.reindex(idx).fillna(0.0),
    "short_strangle": s_str.reindex(idx).fillna(0.0),
})
Mb = M[M.index.date <= SPLIT]

a = 1.0 / M.shape[1]
lev = {}
print(f"KEPT {list(M.columns)}  | equal alloc a={a:.3f} | lev=min(0.3*Kelly,{LEV_CAP})")
for c in M.columns:
    cb = Mb[c]; f = cb.mean() / cb.var() if cb.var() > 0 else 0
    lev[c] = float(np.clip(KELLY * f, 0, LEV_CAP))
    ann = (1 + M[c].mean()) ** 12 - 1; vol = M[c].std() * np.sqrt(12)
    print(f"  {c:20s} ann {ann:+7.1%} vol {vol:6.1%} Sharpe {ann/vol if vol else 0:4.2f} "
          f"Kelly {f:5.2f} 0.3x {KELLY*f:4.2f} applied {lev[c]:.2f}")

port = sum(a * lev[c] * M[c] for c in M.columns)


def stats(r):
    r = r.dropna(); e = (1 + r).cumprod() * CAP
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    cagr = (e.iloc[-1] / CAP) ** (1 / yrs) - 1
    sh = r.mean() / r.std() * np.sqrt(12) if r.std() else 0
    dd = (e / e.cummax() - 1).min()
    return cagr, sh, dd, r.min(), e


print("\n=== FILTERED PORTFOLIO (Rs.1cr, 3 high-return sleeves, 0.3x Kelly cap 2x) ===")
for lab, r in [("BUILD  2021-24", port[port.index.date <= SPLIT]),
               ("FORWARD 25-26 ", port[port.index.date > SPLIT]),
               ("ALL          ", port)]:
    c, sh, dd, wm, e = stats(r)
    print(f"  {lab}: CAGR/XIRR {c:>+7.1%} | Sharpe {sh:>5.2f} | MaxDD {dd:>5.0%} | worstMo {wm:>+6.1%} | Rs.{e.iloc[-1]:,.0f}")

_, _, _, _, e_all = stats(port)
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(e_all.index, e_all.values / 1e7, lw=1.9, color="#b91c1c",
        label="Filtered (IV/RV + FF + earnings), 0.3x Kelly")
ax.axhline(1.0, color="black", lw=0.6, alpha=0.4)
ax.axvline(pd.Timestamp(SPLIT), color="gray", ls=":", lw=1)
ax.text(pd.Timestamp(SPLIT), ax.get_ylim()[1] * 0.9, " forward >", color="gray", fontsize=9)
ax.set_title("Rs.1cr FILTERED portfolio - only >20% CAGR sleeves (0.3x Kelly, monthly)",
             fontsize=12, fontweight="bold")
ax.set_ylabel("Portfolio value (Rs. crore)"); ax.legend(fontsize=9, loc="upper left")
fig.autofmt_xdate(); fig.tight_layout()
fig.savefig(B / "filtered_portfolio_pnl.png", dpi=130)
print(f"\nsaved graph -> {B / 'filtered_portfolio_pnl.png'}")

# ---------- recent transactions summary ----------
print("\n" + "=" * 78)
print("RECENT TRANSACTIONS  (last 8 trades per kept strategy)")
print("=" * 78)

print("\n--- IV/RV short straddle (IV/RV>=1.4) --- ret = short_ret (per unit premium)")
r8 = rv.sort_values("entry").tail(8)[["sym", "entry", "exit", "iv", "rv", "iv_rv", "short_ret"]]
for _, x in r8.iterrows():
    print(f"  {x['sym']:12s} {pd.to_datetime(x['entry']).date()} -> {pd.to_datetime(x['exit']).date()} "
          f"IV {x['iv']:.0%} RV {x['rv']:.0%} IV/RV {x['iv_rv']:.2f}  ret {x['short_ret']:+.1%}")

print("\n--- Forward-Factor CE calendar (FF>=0.25, sized 0.75/1.0/1.25 by tier) --- ret = P&L / back-leg premium")
f8 = ff.sort_values("entry").tail(8)[["sym", "entry", "m1_exp", "strike", "ff", "ret"]]
for _, x in f8.iterrows():
    print(f"  {x['sym']:12s} {pd.to_datetime(x['entry']).date()} -> {pd.to_datetime(x['m1_exp']).date()} "
          f"K {x['strike']:.0f}  FF {x['ff']:.2f}  ret {x['ret']:+.1%}")

print("\n--- Earnings short-vol (short straddle through print) --- ret = c4_short_thru (% of spot)")
e8 = ev.sort_values("earn").tail(8)[["sym", "earn", "exp", "spot", "k", "c4_short_thru"]]
for _, x in e8.iterrows():
    print(f"  {x['sym']:12s} earn {pd.to_datetime(x['earn']).date()} exp {pd.to_datetime(x['exp']).date()} "
          f"spot {x['spot']:.0f} K {x['k']:.0f}  ret {x['c4_short_thru']:+.2%}")

print("\n--- Short strangle ~14DTE, 5% OTM, managed@50% --- ret = % of spot")
g8 = sg.sort_values("entry").tail(8)[["sym", "entry", "exp", "spot", "strangle_managed", "man_exit"]]
for _, x in g8.iterrows():
    early = "TP@50%" if pd.to_datetime(x["man_exit"]).date() != pd.to_datetime(x["exp"]).date() else "held"
    print(f"  {x['sym']:12s} {pd.to_datetime(x['entry']).date()} -> {pd.to_datetime(x['man_exit']).date()} "
          f"spot {x['spot']:.0f}  ret {x['strangle_managed']:+.2%}  ({early})")

# ---------- ACCEPTED tail: worst trades kept in the book (no stop/filter/hedge) ----------
print("\n" + "=" * 78)
print("WORST TRADES YOU'RE ACCEPTING (no stop/filter/hedge - shown, not removed)")
print("=" * 78)
print("\n--- FF calendar: 8 worst (kept; sized by FF tier 0.75/1.0/1.25) ---")
fw = ff.sort_values("ret").head(8)[["sym", "entry", "m1_exp", "ff", "w", "ret"]]
for _, x in fw.iterrows():
    print(f"  {x['sym']:12s} {pd.to_datetime(x['entry']).date()} FF {x['ff']:.2f} size {x['w']:.2f}x  ret {x['ret']:+.0%}")
print("\n--- Earnings short-vol: 6 worst (kept) ---")
ew = ev.sort_values("c4_short_thru").head(6)[["sym", "earn", "c4_short_thru"]]
for _, x in ew.iterrows():
    print(f"  {x['sym']:12s} earn {pd.to_datetime(x['earn']).date()}  ret {x['c4_short_thru']:+.1%}")
print("\n--- Short strangle: 6 worst (kept) ---")
gw = sg.sort_values("strangle_managed").head(6)[["sym", "entry", "strangle_managed"]]
for _, x in gw.iterrows():
    print(f"  {x['sym']:12s} {pd.to_datetime(x['entry']).date()}  ret {x['strangle_managed']:+.1%}")
