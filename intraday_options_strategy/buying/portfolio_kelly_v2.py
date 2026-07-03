"""Rs.1 crore, 0.3x Kelly portfolio of ALL profitable strategies -- HONEST version.

v1 spread each trade's return across its holding days -> fabricated near-zero daily
variance -> Sharpe 7-10, Kelly f*=300. Pure artifact. This version books each trade's
P&L in the MONTH IT EXITS (lumpiness preserved), builds a real monthly return series,
does per-trade / monthly Kelly, and caps leverage at what a margin account can run.

Sleeves (all forward-positive in prior tests):
  1 equity_mom_lowvol : Mom12 + LowVol inverse-vol blend  (daily long-equity -> diversifier)
  2 ivrv_short        : IV/RV>=1.4 short straddle          (return per unit premium)
  3 ff_calendar       : Forward-Factor CE calendar FF>=0.20 (P&L / back-leg premium)
  4 combo_shortvol    : covered-call + short-put, monthly   (% of spot)
  5 earnings_shortvol : short vol through earnings (crush)  (% of spot)

NOTE on bases: sleeves quote returns on different capital bases (premium / spot / debit).
We treat each sleeve's monthly mean trade-return as its 'return on deployed capital' and
give each sleeve an EQUAL 1/N capital allocation, then lever each at min(0.3*Kelly, CAP).
This is a return-on-capital approximation, not a margin-exact sim -- caveated in output.
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
B = ROOT / "intraday_options_strategy/buying"; S = ROOT / "swing_momentum"
CAP = 1_00_00_000.0
KELLY = 0.3
LEV_CAP = 2.0                    # no sleeve may run above 2x its allocation (margin realism)
SPLIT = dt.date(2024, 12, 31)
START = pd.Timestamp(2021, 7, 1); END = pd.Timestamp(2026, 6, 30)
SLIP = 0.015


def monthly_from_trades(df, exit_col, ret_col, clip=None):
    """Mean per-trade return booked in each trade's EXIT month. Real lumpiness kept."""
    d = df[[exit_col, ret_col]].copy()
    d[exit_col] = pd.to_datetime(d[exit_col])
    d = d.dropna()
    if clip is not None:
        d[ret_col] = d[ret_col].clip(*clip)
    d["m"] = d[exit_col].dt.to_period("M").dt.to_timestamp("M")
    g = d.groupby("m")[ret_col]
    return g.mean(), g.size()


# sleeve 1: equity daily -> compound to monthly
eq = pd.read_parquet(S / "multi_backtest_daily.parquet"); eq.index = pd.to_datetime(eq.index)
sub = eq[["mom_12_1", "lowvol_126"]]
bw = sub[sub.index.date <= SPLIT].std(); w = (1 / bw) / (1 / bw).sum()
eq_daily = (sub * w).sum(axis=1)
sleeve_equity = eq_daily.resample("ME").apply(lambda x: (1 + x).prod() - 1)

# sleeve 2: IV/RV short straddle
rv = pd.read_parquet(B / "rv_iv_vol.parquet"); rv = rv[rv["iv_rv"] >= 1.4]
s_ivrv, n_ivrv = monthly_from_trades(rv, "exit", "short_ret", clip=(-3, 1))

# sleeve 3: FF CE calendar
ff = pd.read_parquet(B / "forward_factor_v2.parquet")
ff["ret"] = (ff["CE_fe"] * (1 - SLIP) - ff["CE_be"] * (1 + SLIP)
             - ff["CE_fx"] * (1 + SLIP) + ff["CE_bx"] * (1 - SLIP)) / ff["CE_be"]
ff = ff[ff["ff"] >= 0.20]
s_ff, n_ff = monthly_from_trades(ff, "m1_exp", "ret")

# sleeve 4: combo short-vol
cm = pd.read_parquet(B / "combo_menu.parquet")
cm["ret"] = (cm["covered_call"] + cm["short_put_csp"]) / 2
s_combo, n_combo = monthly_from_trades(cm, "exp", "ret")

# sleeve 5: earnings short vol
ev = pd.read_parquet(B / "stock_earnings_vol.parquet")
s_earn, n_earn = monthly_from_trades(ev, "earn", "c4_short_thru")

idx = pd.date_range(START, END, freq="ME")
M = pd.DataFrame({
    "equity_mom_lowvol": sleeve_equity.reindex(idx).fillna(0.0),
    "ivrv_short": s_ivrv.reindex(idx).fillna(0.0),
    "ff_calendar": s_ff.reindex(idx).fillna(0.0),
    "combo_shortvol": s_combo.reindex(idx).fillna(0.0),
    "earnings_shortvol": s_earn.reindex(idx).fillna(0.0),
})
N = pd.DataFrame({
    "ivrv_short": n_ivrv.reindex(idx).fillna(0).astype(int),
    "ff_calendar": n_ff.reindex(idx).fillna(0).astype(int),
    "combo_shortvol": n_combo.reindex(idx).fillna(0).astype(int),
    "earnings_shortvol": n_earn.reindex(idx).fillna(0).astype(int),
})

print("=== sleeve MONTHLY-return stats (trade P&L booked in exit month) ===")
print(f"  {'sleeve':20s} {'ann.ret':>8} {'ann.vol':>8} {'Sharpe':>7} {'monthsActive':>13} {'trades':>7}")
for c in M.columns:
    s = M[c]; act = s[s != 0]
    ann = (1 + s.mean()) ** 12 - 1; vol = s.std() * np.sqrt(12)
    ntr = int(N[c].sum()) if c in N else len(act)
    print(f"  {c:20s} {ann:>+8.1%} {vol:>8.1%} {ann/vol if vol else 0:>7.2f} "
          f"{len(act):>13d} {ntr:>7d}")

print("\n=== monthly correlation (build period) ===")
Mb = M[M.index.date <= SPLIT]
print(Mb.corr().round(2).to_string())

# equal capital allocation, per-sleeve 0.3x Kelly leverage on MONTHLY returns, capped
a = 1.0 / M.shape[1]
print(f"\nequal allocation a = {a:.2f} per sleeve; leverage = min(0.3*Kelly_monthly, {LEV_CAP})")
print(f"  {'sleeve':20s} {'Kelly f*':>9} {'0.3x':>7} {'applied':>8}")
lev = {}
for c in M.columns:
    cb = Mb[c]
    fstar = cb.mean() / cb.var() if cb.var() > 0 else 0.0
    L = float(np.clip(KELLY * fstar, 0, LEV_CAP))
    lev[c] = L
    print(f"  {c:20s} {fstar:>9.2f} {KELLY*fstar:>7.2f} {L:>8.2f}")

port = sum(a * lev[c] * M[c] for c in M.columns)


def stats(r, cap):
    r = r.dropna()
    eqc = (1 + r).cumprod() * cap
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    cagr = (eqc.iloc[-1] / cap) ** (1 / yrs) - 1
    sharpe = r.mean() / r.std() * np.sqrt(12) if r.std() > 0 else 0
    dd = (eqc / eqc.cummax() - 1).min()
    worst = r.min()
    return cagr, sharpe, dd, worst, eqc


print("\n=== PORTFOLIO (Rs.1cr, equal-weight, 0.3x Kelly capped @2x, monthly) ===")
for lab, r in [("BUILD  2021-24", port[port.index.date <= SPLIT]),
               ("FORWARD 25-26 ", port[port.index.date > SPLIT]),
               ("ALL          ", port)]:
    c, sh, dd, wm, e = stats(r, CAP)
    print(f"  {lab}: CAGR {c:>+7.1%} | Sharpe {sh:>5.2f} | MaxDD {dd:>5.0%} | worstMo {wm:>+6.1%} | final Rs.{e.iloc[-1]:,.0f}")

# unlevered reference
p0 = sum(a * M[c] for c in M.columns)
c0, sh0, dd0, wm0, _ = stats(p0, CAP)
print(f"\n[reference] unlevered equal-weight: CAGR {c0:+.1%} | Sharpe {sh0:.2f} | MaxDD {dd0:.0%} | worstMo {wm0:+.1%}")

# equity curve
_, _, _, _, e_all = stats(port, CAP)
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(e_all.index, e_all.values / 1e7, lw=1.8, color="#0f766e", label="0.3x Kelly portfolio (Rs.cr)")
_, _, _, _, e0 = stats(p0, CAP)
ax.plot(e0.index, e0.values / 1e7, lw=1.2, color="#9ca3af", ls="--", label="unlevered equal-weight")
ax.axhline(1.0, color="black", lw=0.6, alpha=0.4)
ax.axvline(pd.Timestamp(SPLIT), color="gray", ls=":", lw=1)
ax.text(pd.Timestamp(SPLIT), ax.get_ylim()[1] * 0.95, " forward >", color="gray", fontsize=9)
ax.set_title("Rs.1cr multi-strategy portfolio - 0.3x Kelly, monthly P&L (HONEST build)",
             fontsize=12, fontweight="bold")
ax.set_ylabel("Portfolio value (Rs. crore)"); ax.set_xlabel("")
ax.legend(fontsize=9, loc="upper left")
fig.autofmt_xdate(); fig.tight_layout()
out = B / "portfolio_kelly_v2_pnl.png"
fig.savefig(out, dpi=130)
M.to_parquet(B / "portfolio_monthly_v2.parquet")
print(f"\nsaved equity graph -> {out}")
print("saved monthly sleeve returns -> portfolio_monthly_v2.parquet")
