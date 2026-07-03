"""Trend-timed buy-write + upside tail hedge (>20DMA only):
 LONG Nifty (~Rs1Cr) + SHORT daily ~1% OTM weekly CE (covered, 5 lots, intraday)
 + LONG monthly ~1.5sigma CE (0.5x = 2.5 lots, rolled ~21td). Cash when <20DMA.
Compares vs Nifty buy&hold and vs long-Nifty->20DMA-only (no overlays)."""
import sys; from pathlib import Path
import numpy as np, pandas as pd
R = Path(__file__).resolve().parent; sys.path.insert(0, str(R))
from options.bs_pricing import bs_price
from options.option_selector import ExpiryCalendar
from config import RISK_FREE_RATE as r, DIVIDEND_YIELD as q, LOT_SIZE as LOT
P = R / "datasets" / "processed"
nif = pd.read_parquet(P / "nifty_1min.parquet")["close"]
vix = pd.read_parquet(P / "vix_1min.parquet")["vix"]
day = nif.index.normalize()
s0 = nif.groupby(day).first(); sc = nif.groupby(day).last()
v0 = vix.groupby(vix.index.normalize()).first().reindex(s0.index).ffill()
days = pd.DatetimeIndex(s0.index); dpos = {d: i for i, d in enumerate(days)}
sma20 = sc.rolling(20).mean().shift(1); green = (s0 > sma20)
ret = sc.pct_change()                                  # close-to-close
cal = ExpiryCalendar(days); M, SLIP, TMY = 0.80, 0.02, 252*375
CAP0 = 1e7

def shortcall(d):                                       # intraday short ~1% OTM weekly CE, per lot
    exp = cal.next_expiry(d, min_dte=0)
    if exp not in dpos: return 0.0
    dte = (exp-d).days; gap = dpos[exp]-dpos[d]; off = 0.005 if dte <= 1 else 0.01
    sig = float(v0[d])/100*M; k = round(float(s0[d])*(1+off)/50)*50
    e = float(bs_price(s0[d], k, (375+375*gap)/TMY, sig, r, q, True))
    x = float(bs_price(sc[d], k, (1+375*gap)/TMY, sig, r, q, True))
    if e < 1: return 0.0
    return (e*(1-SLIP)-x*(1+SLIP))*LOT - (0.000625*e*LOT + 0.00053*(e+x)*LOT*1.18 + 2*20*1.18)

# monthly long call: roll every 21 td, strike=spot*(1+1.5*VIX/sqrt(12)), MTM daily, per lot
mexp_k = {}; mexp_exp = {}
for i, d in enumerate(days):
    if i % 21 == 0:
        sig_m = float(v0[d])/100/np.sqrt(12)
        mexp_k[i] = round(float(s0[d])*(1+1.5*sig_m)/50)*50
        mexp_exp[i] = min(i+21, len(days)-1)
cur = None
def monthly_mtm(i):                                     # daily MTM change of 1 long monthly call, per lot
    global cur
    if i in mexp_k: cur = i
    if cur is None: return 0.0
    k = mexp_k[cur]; ei = mexp_exp[cur]
    t1 = max(ei-i, 0.5)/252; t0 = max(ei-(i-1), 0.5)/252
    sig = float(v0[days[i]])/100*M
    p1 = float(bs_price(sc[days[i]], k, t1, sig, r, q, True))
    p0 = float(bs_price(sc[days[i-1]], k, t0, sig, r, q, True)) if i > 0 else p1
    return (p1-p0)*LOT

cap_bw = CAP0; cap_long = CAP0; cap_bh = CAP0
eq = {"buy&hold": [], "long>20DMA": [], "buywrite": []}
for i, d in enumerate(days):
    rr = 0.0 if pd.isna(ret[d]) else float(ret[d])
    cap_bh *= (1+rr)
    if bool(green.get(d, False)):
        pnl = cap_long*rr                               # long-only leg
        cap_long *= (1+rr)
        bw = cap_bw*rr + 5*shortcall(d) + 2.5*monthly_mtm(i)
        cap_bw += bw
    else:
        pass                                            # cash both
    eq["buy&hold"].append(cap_bh); eq["long>20DMA"].append(cap_long); eq["buywrite"].append(cap_bw)
idx = days
def stat(name):
    e = pd.Series(eq[name], index=idx); rr = e.pct_change().dropna()
    yrs = (idx[-1]-idx[0]).days/365.25; cagr = (e.iloc[-1]/CAP0)**(1/yrs)-1
    sh = (rr.mean()*252-0.06)/(rr.std()*np.sqrt(252)) if rr.std() > 0 else 0
    mdd = ((e.cummax()-e)/e.cummax()).max()
    print(f"{name:14} CAGR {cagr:+6.1%}  Sharpe {sh:5.2f}  MaxDD {mdd:5.1%}  final Rs.{e.iloc[-1]/1e7:.2f}Cr")
print("Trend-timed buy-write + monthly 1.5sigma CE hedge (2015-2026), Rs.1Cr:\n")
for n in ["buy&hold", "long>20DMA", "buywrite"]:
    stat(n)
print("\n(buy&hold=always long Nifty; long>20DMA=long only in uptrend, else cash;")
print(" buywrite=long>20DMA + 5x covered short weekly CE + 2.5x long monthly 1.5sd CE)")
print("CAVEAT: synthetic call pricing (call-skew overprices the short CE = optimistic);")
print(" overnight-gap risk on the covered structure not fully modeled; confirm w/ live chain.")
